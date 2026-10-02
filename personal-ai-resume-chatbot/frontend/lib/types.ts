export type Role = "user" | "assistant";

export interface JobMatchResult {
  match_percentage: number;
  matching_skills: string[];
  missing_skills: string[];
  relevant_projects: string[];
  education_fit?: string;
  explanation: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string; // text shown (and sent back to the backend as history)
  jobMatch?: JobMatchResult; // set when this message is a JD analysis
  isError?: boolean; // friendly error bubble, not sent as history
}