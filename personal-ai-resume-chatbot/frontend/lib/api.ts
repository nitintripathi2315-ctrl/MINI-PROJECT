import type { ChatMessage, JobMatchResult } from "./types";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const TIMEOUT_MS = 90_000; // allows for a sleeping free-tier backend to wake up

export class ApiError extends Error {}

// ---------- shared helpers ----------
async function readErrorDetail(res: Response): Promise<string> {
  let detail = "";
  try {
    const data = await res.json();
    if (typeof data.detail === "string") detail = data.detail;
  } catch {
    // response had no JSON body; use the generic message below
  }
  return detail || `The server returned an error (${res.status}). Please try again.`;
}

function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  if (err instanceof DOMException && err.name === "AbortError") {
    return new ApiError("The request took too long. Please try again.");
  }
  return new ApiError("Can't reach the server right now. Please try again in a moment.");
}

// Only real conversation goes to the backend as history (no error bubbles).
function toHistory(messages: ChatMessage[]) {
  return messages
    .filter((m) => !m.isError && m.content.trim())
    .map((m) => ({ role: m.role, content: m.content }));
}

// ---------- normal JSON request (used by /chat and /match) ----------
async function post<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!res.ok) throw new ApiError(await readErrorDetail(res));

    try {
      return (await res.json()) as T;
    } catch {
      throw new ApiError("The server sent an invalid response.");
    }
  } catch (err) {
    throw toApiError(err);
  } finally {
    clearTimeout(timer);
  }
}

// ---------- chat: whole answer at once (fallback) ----------
export async function sendMessage(
  message: string,
  history: ChatMessage[]
): Promise<string> {
  const data = await post<{ answer?: unknown }>("/chat", {
    message,
    history: toHistory(history),
  });

  if (typeof data.answer !== "string" || !data.answer.trim()) {
    throw new ApiError("I got an empty answer. Please try asking again.");
  }
  return data.answer;
}

// ---------- chat: streamed answer (words appear as they are written) ----------
// onUpdate is called again and again with the full text received so far.
export async function streamMessage(
  message: string,
  history: ChatMessage[],
  onUpdate: (textSoFar: string) => void
): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let full = "";

  try {
    const res = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: toHistory(history) }),
      signal: controller.signal,
    });

    if (!res.ok) throw new ApiError(await readErrorDetail(res));
    if (!res.body) throw new ApiError("The server sent an invalid response.");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        full += decoder.decode(value, { stream: true });
        onUpdate(full);
      }
      full += decoder.decode(); // flush any leftover bytes
    } catch (err) {
      // Nothing arrived yet: report the error.
      // Some text arrived: keep the partial answer instead of throwing it away.
      if (!full.trim()) throw err;
    }

    if (!full.trim()) {
      throw new ApiError("I got an empty answer. Please try asking again.");
    }
    return full;
  } catch (err) {
    throw toApiError(err);
  } finally {
    clearTimeout(timer);
  }
}

// ---------- job match (needs the full JSON, so no streaming) ----------
export async function matchJob(jobDescription: string): Promise<JobMatchResult> {
  const data = await post<Partial<JobMatchResult>>("/match", {
    job_description: jobDescription,
  });

  const percent = Number(data.match_percentage);
  if (!Number.isFinite(percent) || typeof data.explanation !== "string") {
    throw new ApiError("The job match result was incomplete. Please try again.");
  }

  const asList = (v: unknown) =>
    Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];

  return {
    // The number comes from the backend; we only keep it within 0-100.
    match_percentage: Math.max(0, Math.min(100, Math.round(percent))),
    matching_skills: asList(data.matching_skills),
    missing_skills: asList(data.missing_skills),
    relevant_projects: asList(data.relevant_projects),
    education_fit:
      typeof data.education_fit === "string" ? data.education_fit : undefined,
    explanation: data.explanation,
  };
}

// Called when the page opens, so a sleeping backend starts waking up early
export function warmUpServer() {
  fetch(`${API_URL}/health`).catch(() => {
    /* ignore: this is only a wake-up call */
  });
}