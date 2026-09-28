# Resume Matcher

An AI-assisted resume screening tool for recruiters. Paste a job description, upload multiple resumes (PDF or DOCX), and get a ranked list of candidates with an explainable match score and a detailed breakdown for each one.

The score is **calculated by deterministic Python logic**, not guessed by an LLM. The LLM is used only to extract structured data from text and to write a short human-readable verdict.

## Features

- Paste a job description and upload several resumes at once (drag & drop or browse)
- Supports `.pdf` and `.docx` resumes, up to 5 MB each
- Extracts structured data from the job description and from each resume
- Weighted, explainable match score with a per-category breakdown
- Ranked results table with Strong / Moderate / Low match badges
- Candidate detail panel: contact info, matched and missing skills, education, projects, certifications, and a written verdict
- Per-file error handling: one bad resume is skipped with a reason and never breaks the rest of the batch
- Responsive dark UI

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, Uvicorn |
| AI | Groq API (`openai/gpt-oss-120b`) for extraction and verdict text |
| Parsing | `pypdf` (PDF), `python-docx` (DOCX) |
| Validation | Pydantic models |
| Deployment | Vercel (frontend), Render (backend) |

## Architecture

```
Browser (Next.js)
   |  POST /api/analyze  (job description + resume files, multipart form)
   v
FastAPI backend
   1. Validate input (file type, size, empty job description)
   2. Extract text from each resume (PDF / DOCX)
   3. LLM: job description -> structured requirements (JobD)
   4. LLM: resume text -> structured profile (Resume)
   5. Python: weighted score + per-category breakdown
   6. LLM: short verdict written from the computed numbers
   7. Return ranked candidates + a list of skipped files
```

No database is used. Each request is processed in memory and nothing is stored, which also means candidate data is never persisted on the server.

## How the Score Works

The final score (0-100) is a weighted sum computed in Python:

| Category | Weight | How it is scored |
|---|---:|---|
| Required skills | 40% | Share of the JD's required skills found in the resume |
| Preferred skills | 15% | Share of the JD's preferred skills found in the resume |
| Experience | 20% | Resume years vs. the JD minimum, with partial credit |
| Education | 10% | Whether an education entry matches the JD requirement |
| Projects | 10% | Whether the resume lists projects |
| Certifications | 5% | Whether the resume lists certifications |

Status thresholds: **Strong Match** at 75 and above, **Moderate Match** at 50 and above, otherwise **Low Match**.

If the job description lists nothing for a category (for example no preferred skills), that category counts as fully satisfied instead of dragging the score down.

The LLM never decides the number. It only receives the already-computed breakdown and writes a 2-3 sentence explanation.

## Project Structure

```
resume-matching/
├── backend/
│   ├── main.py            # FastAPI app and /api/analyze endpoint
│   ├── jd_parser.py       # Job description -> structured requirements
│   ├── resume_parser.py   # Resume text -> structured profile
│   ├── matcher.py         # Deterministic scoring + verdict generation
│   ├── file_reader.py     # PDF / DOCX text extraction
│   ├── models.py          # Pydantic models
│   ├── llm_client.py      # Groq client setup
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── page.tsx       # Main UI
    │   └── layout.tsx
    └── package.json
```

## Local Setup

Prerequisites: Python 3.10+, Node.js 18+, and a free [Groq API key](https://console.groq.com/keys).

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Open `backend/.env` and put your real key in it:

```env
GROQ_API_KEY=your_key_here
FRONTEND_URL=http://localhost:3000
```

Start the API:

```powershell
python -m uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/api/health`; it should return `{"status":"ok"}`.

### 2. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. By default the frontend calls the backend at `http://127.0.0.1:8000`.

### 3. Try it

Paste a job description, drop in one or more resumes, and click **Analyze candidates**. Click any row in the results to open the candidate's details.

## Environment Variables

| Variable | Where | Purpose |
|---|---|---|
| `GROQ_API_KEY` | backend | Groq API key. Never commit it. |
| `FRONTEND_URL` | backend | Frontend origin allowed by CORS (your Vercel URL in production). |
| `NEXT_PUBLIC_API_URL` | frontend | Backend base URL. Falls back to `http://127.0.0.1:8000` when unset. |

`.env` files are ignored by git. The Groq key lives only on the backend and is never sent to the browser.

## API

### `POST /api/analyze`

Multipart form data:

| Field | Type | Description |
|---|---|---|
| `job_description` | text | The job description |
| `files` | file(s) | One or more `.pdf` / `.docx` resumes |

Response:

```json
{
  "candidates": [
    {
      "name": "Candidate A",
      "email": "a@example.com",
      "phone": "+00-0000000000",
      "score": 85.0,
      "status": "Strong Match",
      "details": {
        "overall_score": 85.0,
        "category_scores": { "required_skills": 100.0, "preferred_skills": 50.0 },
        "required_skills_matched": [],
        "required_skills_missing": [],
        "preferred_skills_matched": [],
        "preferred_skills_missing": [],
        "experience_requirement_met": true,
        "education_requirement_met": true,
        "has_projects": true,
        "has_certifications": false,
        "verdict": "Short written explanation of the score."
      },
      "resume": { "skills": [], "education": [], "projects": [], "certifications": [] }
    }
  ],
  "skipped": [
    { "file": "notes.txt", "reason": "Unsupported file type. Only PDF and DOCX are accepted." }
  ]
}
```

Error responses: `400` for a missing job description or files, `502` if the job description could not be analyzed.

### `GET /api/health`

Returns `{"status": "ok"}`.

## Deployment

The repo is set up so the two halves deploy separately.

### Backend on Render

1. Create a new **Web Service** from this GitHub repo.
2. Set **Root Directory** to `resume-matching/backend`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `GROQ_API_KEY` and `FRONTEND_URL` (your Vercel URL, set after step 2 below).

### Frontend on Vercel

1. Import the same repo in Vercel.
2. Set **Root Directory** to `resume-matching/frontend`.
3. Add the environment variable `NEXT_PUBLIC_API_URL` set to your Render backend URL.
4. Deploy, then copy the Vercel URL into `FRONTEND_URL` on Render and redeploy the backend so CORS allows it.

## Screenshots

_Add screenshots here, for example `docs/screenshots/home.png` and `docs/screenshots/candidate-detail.png`._

## Known Limitations

- Skill matching is case-insensitive substring matching, so synonyms such as "Postgres" and "PostgreSQL" or "SQL" may not match.
- Resumes are processed one after another, so large batches are slow and can hit LLM rate limits.
- Projects and certifications are scored by presence, not by relevance to the role.
- No authentication or rate limiting on the API yet.

## Future Improvements

- Semantic skill matching (embeddings or an LLM check for synonyms)
- Retry with backoff on LLM rate limits, and parallel processing
- Relevance scoring for projects and experience
- Export results to CSV
- Optional saved analysis history (would need a database)
- Authentication and per-user limits
