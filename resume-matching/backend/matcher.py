from llm_client import client, MODEL
from models import JobD, MatchResult, Resume

# Fixed weights — must sum to 1.0. This is the single place that controls
# how much each category counts toward the final score.
WEIGHTS = {
    "required_skills": 0.40,
    "preferred_skills": 0.15,
    "experience": 0.20,
    "education": 0.10,
    "projects": 0.10,
    "certifications": 0.05,
}


def _normalize(text: str) -> str:
    return text.strip().lower()


def _match_skills(jd_skills: list[str], resume_skills: list[str]) -> tuple[list[str], list[str]]:
    """Returns (matched, missing) from jd_skills, checked against resume_skills.

    Matching is case-insensitive substring matching in either direction,
    e.g. JD skill 'sql' matches resume skill 'SQL Server'.
    """
    normalized_resume_skills = [_normalize(s) for s in resume_skills]

    matched = []
    missing = []
    for jd_skill in jd_skills:
        jd_norm = _normalize(jd_skill)
        found = any(
            jd_norm in resume_skill or resume_skill in jd_norm
            for resume_skill in normalized_resume_skills
        )
        if found:
            matched.append(jd_skill)
        else:
            missing.append(jd_skill)
    return matched, missing


def _score_skills(jd_skills: list[str], resume_skills: list[str]) -> tuple[float, list[str], list[str]]:
    """Returns (score 0-1, matched, missing). If JD lists no skills in this
    category, treat it as fully satisfied (nothing to fail on)."""
    if not jd_skills:
        return 1.0, [], []

    matched, missing = _match_skills(jd_skills, resume_skills)
    score = len(matched) / len(jd_skills)
    return score, matched, missing


def _score_experience(minimum_experience: float | None, resume_years: float | None) -> tuple[float, bool]:
    """Returns (score 0-1, requirement_met)."""
    if minimum_experience is None:
        # JD doesn't specify a minimum — nothing to fail on.
        return 1.0, True

    if resume_years is None:
        # JD wants experience, resume has no data on it at all.
        return 0.0, False

    if resume_years >= minimum_experience:
        return 1.0, True

    # Partial credit for getting close, floor at 0.
    ratio = resume_years / minimum_experience if minimum_experience > 0 else 0.0
    return max(0.0, min(ratio, 1.0)), False


def _score_education(jd_education: list[str], resume_education: list[str]) -> tuple[float, bool]:
    """Returns (score 0-1, match_found). If JD lists no education
    requirements, treat it as fully satisfied."""
    if not jd_education:
        return 1.0, True

    normalized_resume_edu = [_normalize(e) for e in resume_education]

    for requirement in jd_education:
        req_norm = _normalize(requirement)
        if any(req_norm in edu or edu in req_norm for edu in normalized_resume_edu):
            return 1.0, True

    return 0.0, False


def _score_presence(items: list[str]) -> float:
    """Simple presence-based score: 1.0 if the candidate lists anything
    in this category, 0.0 otherwise. Used for projects and certifications,
    since JDs rarely name specific ones to check against."""
    return 1.0 if items else 0.0


def _compute_breakdown(job: JobD, resume: Resume) -> dict:
    req_score, req_matched, req_missing = _score_skills(job.required_skills, resume.skills)
    pref_score, pref_matched, pref_missing = _score_skills(job.preferred_skills, resume.skills)
    exp_score, exp_met = _score_experience(job.minimum_experience, resume.total_experience_years)
    edu_score, edu_met = _score_education(job.education_requirements, resume.education)
    proj_score = _score_presence(resume.projects)
    cert_score = _score_presence(resume.certifications)

    category_scores = {
        "required_skills": req_score,
        "preferred_skills": pref_score,
        "experience": exp_score,
        "education": edu_score,
        "projects": proj_score,
        "certifications": cert_score,
    }

    overall = sum(category_scores[cat] * WEIGHTS[cat] for cat in WEIGHTS) * 100

    return {
        "overall_score": round(overall, 1),
        "category_scores": {k: round(v * 100, 1) for k, v in category_scores.items()},
        "required_skills_matched": req_matched,
        "required_skills_missing": req_missing,
        "preferred_skills_matched": pref_matched,
        "preferred_skills_missing": pref_missing,
        "experience_requirement_met": exp_met,
        "education_requirement_met": edu_met,
        "has_projects": bool(resume.projects),
        "has_certifications": bool(resume.certifications),
    }


def _generate_verdict(job: JobD, resume: Resume, breakdown: dict) -> str:
    """LLM's only job now: turn already-computed numbers into a short,
    readable verdict. It does not decide the score."""
    prompt = f"""
    You are an HR recruiter writing a short candidate verdict.

    Candidate name: {resume.name}
    Overall match score (already calculated, do not change it): {breakdown['overall_score']}%

    Matched required skills: {breakdown['required_skills_matched']}
    Missing required skills: {breakdown['required_skills_missing']}
    Matched preferred skills: {breakdown['preferred_skills_matched']}
    Missing preferred skills: {breakdown['preferred_skills_missing']}
    Experience requirement met: {breakdown['experience_requirement_met']}
    Education requirement met: {breakdown['education_requirement_met']}

    Write a 2-3 sentence verdict explaining why this candidate got this
    score, mentioning the most important strengths and gaps. Do not
    invent a different score. Return plain text only, no JSON.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def final_score(job: JobD, resume: Resume) -> MatchResult:
    breakdown = _compute_breakdown(job, resume)
    verdict = _generate_verdict(job, resume, breakdown)
    breakdown["verdict"] = verdict

    return MatchResult(score=breakdown["overall_score"], details=breakdown)
