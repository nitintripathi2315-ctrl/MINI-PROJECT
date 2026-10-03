import json
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import Groq
from pydantic import BaseModel
from pypdf import PdfReader


load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise ValueError("GROQ_API_KEY is missing. Add it to your .env file.")

client = Groq(api_key=_api_key)
model = "openai/gpt-oss-120b"

# Optional: set CHAT_REASONING_EFFORT=low (or medium/high) in .env or on Render
# to make the model think less before answering. Empty = model default.
CHAT_REASONING_EFFORT = os.getenv("CHAT_REASONING_EFFORT", "").strip()

# Resume path is relative to this file, so it works from any folder
BASE_DIR = Path(__file__).resolve().parent
RESUME_PATH = Path(os.getenv("RESUME_PATH", BASE_DIR / "my_resume.pdf"))


# ---------- Schemas ----------
class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    duration: str | None = None
    description: str | None = None
    skills_used: list[str] = []


class Resume(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    total_experience_years: float | None = None

    skills: list[str] = []
    experiences: list[Experience] = []
    education: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []


resume_schema = Resume.model_json_schema()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    # Frontend sends "message" + "history".
    # "question" is kept so your old requests still work.
    message: str | None = None
    question: str | None = None
    history: list[ChatMessage] = []


class MatchRequest(BaseModel):
    job_description: str


# ---------- PDF ----------
def read_pdf(file_path: Path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


# ---------- Resume parsing ----------
def parse_resume(resume_text):
    system_prompt = f"""
    You are an expert resume parser.

    Extract information from the resume based on its meaning,
    not only based on exact section headings.

    Different resumes may use different headings.

    For example:
    - Experience
    - Professional Experience
    - Work History
    - Employment
    - Internships

    These may all contain relevant experience.

    Skills may also appear in the skills section, work experience,
    internships or projects.

    Return ONLY valid JSON matching this schema:

    {resume_schema}

    Important rules:

    1. Do not invent information.
    2. If a value is not available, return null.
    3. If a list has no information, return an empty list.
    4. Include internships inside experiences.
    5. Extract skills mentioned across the entire resume.
    6. For each project, keep the project name AND its description/technologies
       in a single string, so no detail is lost.
    """
    user_prompt = f"""
    Parse the following resume:

    {resume_text}
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return Resume(**data)


# ---------- Chat ----------
def build_chat_messages(question: str, resume: Resume, history: list[ChatMessage]):
    system_prompt = f"""
You are an AI assistant on a portfolio website. You represent the candidate
below and talk to recruiters and HR.

Everything you know about the candidate:

{resume.model_dump_json(indent=2)}

Rules:

1. Answer only using this information.
2. Never hallucinate or invent skills, projects or experience.
3. If information is unavailable, say
   "I don't have enough information to answer that."
4. Be professional, friendly and concise.
5. Speak about the candidate in the third person ("{resume.name or 'The candidate'}
   built...", "He has..."), not as the candidate.
6. Use Markdown (bullet points, bold) when it makes the answer easier to read.
7. Use the earlier conversation to understand follow-up questions.
"""

    messages = [{"role": "system", "content": system_prompt}]
    # Keep only the last 10 messages to control cost and length
    for m in history[-10:]:
        if m.role in ("user", "assistant"):
            messages.append({"role": m.role, "content": m.content[:4000]})
    messages.append({"role": "user", "content": question})
    return messages


def ask_candidate(question: str, resume: Resume, history: list[ChatMessage]):
    """Normal (non-streaming) answer. Kept as a fallback for /chat."""
    messages = build_chat_messages(question, resume, history)
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content


def stream_candidate(question: str, resume: Resume, history: list[ChatMessage]):
    """Opens a streaming request to Groq; returns an iterator of chunks."""
    messages = build_chat_messages(question, resume, history)
    extra = {}
    if CHAT_REASONING_EFFORT:
        extra["reasoning_effort"] = CHAT_REASONING_EFFORT
    return client.chat.completions.create(
        model=model, messages=messages, stream=True, **extra
    )


# ---------- Job description matching ----------
def match_job(job_description: str, resume: Resume):
    system_prompt = f"""
You are an honest recruiting assistant. Compare the candidate to the job
description using ONLY the candidate data below.

Candidate data:

{resume.model_dump_json(indent=2)}

Return ONLY valid JSON with exactly these keys:

{{
  "match_percentage": <integer 0-100>,
  "matching_skills": [<skills required by the JD that the candidate has>],
  "missing_skills": [<skills required by the JD that the candidate lacks or has limited evidence for>],
  "relevant_projects": [<candidate projects relevant to this JD>],
  "education_fit": "<one sentence>",
  "explanation": "<3-5 sentence honest explanation of the score>"
}}

Rules:
1. Never claim a skill the candidate data does not show.
2. Be realistic. Do not inflate the percentage.
3. The candidate is a student looking for internships; judge accordingly.
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Job Description:\n\n{job_description}"},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ---------- Simple per-visitor rate limit ----------
RATE_LIMIT = 20   # max requests per visitor...
RATE_WINDOW = 60  # ...per 60 seconds
_hits: dict[str, deque] = defaultdict(deque)


def check_rate_limit(http_request: Request):
    forwarded = http_request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = http_request.client.host if http_request.client else "unknown"
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute and try again.",
        )
    q.append(now)


# ---------- App ----------
# Parse the resume ONCE when the server starts, not on every request
resume: Resume | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global resume
    resume = parse_resume(read_pdf(RESUME_PATH))
    print("Resume loaded for:", resume.name)
    yield


app = FastAPI(title="Personal AI Resume Chatbot", lifespan=lifespan)

# Local development addresses are always allowed.
# On Render, set ALLOWED_ORIGINS to your Vercel URL(s), comma-separated.
DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
allowed_origins = list(dict.fromkeys(DEFAULT_DEV_ORIGINS + env_origins))  # dedupe, keep order

print("CORS allowed origins:", allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Personal AI Resume Chatbot API is running"}


@app.get("/health")
def health():
    return {"status": "ok", "resume_loaded": resume is not None}


def prepare_chat(request: ChatRequest, http_request: Request) -> str:
    """Shared checks for /chat and /chat/stream. Returns the cleaned message."""
    check_rate_limit(http_request)
    text = (request.message or request.question or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(text) > 12000:
        raise HTTPException(status_code=400, detail="Message is too long.")
    if resume is None:
        raise HTTPException(status_code=503, detail="Resume not loaded yet.")
    return text


@app.post("/chat")
def chat(request: ChatRequest, http_request: Request):
    text = prepare_chat(request, http_request)
    try:
        answer = ask_candidate(text, resume, request.history)
    except Exception:
        raise HTTPException(status_code=502, detail="The AI service failed. Try again.")
    return {"answer": answer}


@app.post("/chat/stream")
def chat_stream(request: ChatRequest, http_request: Request):
    text = prepare_chat(request, http_request)

    # Open the connection to Groq BEFORE replying, so a failure becomes a
    # proper error response instead of a half-empty stream.
    try:
        groq_stream = stream_candidate(text, resume, request.history)
    except Exception:
        raise HTTPException(status_code=502, detail="The AI service failed. Try again.")

    def token_generator():
        try:
            for chunk in groq_stream:
                if not chunk.choices:
                    continue
                piece = chunk.choices[0].delta.content
                if piece:
                    yield piece
        except Exception:
            # Connection broke mid-answer: just end the stream.
            # The frontend keeps whatever text already arrived.
            return

    return StreamingResponse(
        token_generator(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/match")
def match(request: MatchRequest, http_request: Request):
    check_rate_limit(http_request)
    jd = request.job_description.strip()
    if not jd:
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
    if resume is None:
        raise HTTPException(status_code=503, detail="Resume not loaded yet.")
    try:
        return match_job(jd[:12000], resume)  # cap very long JDs
    except Exception:
        raise HTTPException(status_code=502, detail="The AI service failed. Try again.")