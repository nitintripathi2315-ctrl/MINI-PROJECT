const JD_HINTS = [
  "requirements",
  "responsibilities",
  "qualifications",
  "job description",
  "we are looking for",
  "about the role",
  "what you'll do",
  "must have",
  "preferred skills",
];

export function looksLikeJobDescription(text: string): boolean {
  const t = text.toLowerCase();
  if (t.length < 200) return false;
  const hits = JD_HINTS.filter((h) => t.includes(h)).length;
  // Long text with at least one JD phrase, or very long text
  return hits >= 1 || t.length > 1200;
}