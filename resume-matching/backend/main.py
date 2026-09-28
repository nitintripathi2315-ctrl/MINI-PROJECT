import os
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from file_reader import read_resume_bytes
from jd_parser import parse_job_description
from matcher import final_score
from resume_parser import parse_resume

app = FastAPI(title="Resume Matcher API")

# In production, set FRONTEND_URL to your deployed Vercel URL
# (e.g. https://my-resume-matcher.vercel.app). Locally it defaults
# to the Next.js dev server.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB per resume


def _status_from_score(score: float) -> str:
    if score >= 75:
        return "Strong Match"
    elif score >= 50:
        return "Moderate Match"
    else:
        return "Low Match"


@app.post("/api/analyze")
async def analyze(
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required.")

    if not files:
        raise HTTPException(status_code=400, detail="At least one resume file is required.")

    try:
        job = parse_job_description(job_description)
    except Exception:
        # LLM call failed or returned something we couldn't parse into JobD.
        raise HTTPException(
            status_code=502,
            detail="Could not analyze the job description. Please try again in a moment.",
        )

    candidates = []
    skipped = []  # files that failed for any reason, with a human-readable cause

    for upload in files:
        filename = upload.filename or "Unnamed file"

        if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".docx")):
            skipped.append({"file": filename, "reason": "Unsupported file type. Only PDF and DOCX are accepted."})
            continue

        content = await upload.read()

        if len(content) > MAX_FILE_SIZE_BYTES:
            skipped.append({"file": filename, "reason": "File is too large (max 5 MB)."})
            continue

        try:
            resume_text = read_resume_bytes(filename, content)
        except Exception:
            # Corrupted, password-protected, or otherwise unreadable file.
            skipped.append({"file": filename, "reason": "Could not read this file. It may be corrupted or password-protected."})
            continue

        if not resume_text or not resume_text.strip():
            skipped.append({"file": filename, "reason": "No readable text was found in this resume."})
            continue

        try:
            resume = parse_resume(resume_text)
        except Exception:
            # LLM call failed, hit a rate limit, or returned invalid JSON.
            skipped.append({"file": filename, "reason": "Could not extract information from this resume. Please try again."})
            continue

        try:
            result = final_score(job, resume)
        except Exception:
            skipped.append({"file": filename, "reason": "Could not score this resume against the job description."})
            continue

        candidates.append({
            "name": resume.name,
            "email": resume.email,
            "phone": resume.phone,
            "score": result.score,
            "status": _status_from_score(result.score),
            "details": result.details,
            "resume": resume.model_dump(),
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)

    return {"candidates": candidates, "skipped": skipped}


@app.get("/api/health")
def health():
    return {"status": "ok"}
