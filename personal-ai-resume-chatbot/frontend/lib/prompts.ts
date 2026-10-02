export interface Prompt {
  label: string;
  text: string;
  // "send" = send immediately, "fill" = put text in the input so the user can paste a JD
  kind: "send" | "fill";
}

const JD_TEMPLATE =
  "Based on this job description, how well does Nitin's profile match this role?\n\nJob Description:\n";

export const sidebarStarters: Prompt[] = [
  { label: "About Me", text: "Tell me about Nitin.", kind: "send" },
  { label: "Skills", text: "What technologies does Nitin know?", kind: "send" },
  { label: "Projects", text: "What projects has Nitin worked on?", kind: "send" },
  { label: "Education", text: "What is Nitin's educational background?", kind: "send" },
  {
    label: "Experience",
    text: "What experience does Nitin have, and what kind of internship is he looking for?",
    kind: "send",
  },
  { label: "Resume Analysis", text: "Give me a summary of Nitin's resume.", kind: "send" },
  { label: "Job Description Match", text: JD_TEMPLATE, kind: "fill" },
];

export const welcomePrompts: Prompt[] = [
  { label: "Tell me about Nitin's projects", text: "Tell me about Nitin's projects", kind: "send" },
  { label: "What technologies does he know?", text: "What technologies does he know?", kind: "send" },
  { label: "Analyze this job description", text: JD_TEMPLATE, kind: "fill" },
  { label: "Give me a summary of his resume", text: "Give me a summary of his resume.", kind: "send" },
];