import { profile } from "@/lib/profile";
import { welcomePrompts, type Prompt } from "@/lib/prompts";
import { Avatar } from "./ChatMessage";

const topics = ["Skills", "Projects", "Education", "Resume", "Experience", "Career interests"];

export default function WelcomeScreen({ onPrompt }: { onPrompt: (p: Prompt) => void }) {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col items-center justify-center px-4 py-10 text-center">
      <Avatar size="lg" />
      <h1 className="mt-6 text-2xl font-semibold sm:text-3xl">
        Hi, I&apos;m {profile.shortName}&apos;s AI Assistant.
      </h1>
      <p className="mt-3 text-muted">
        Ask me anything about {profile.shortName}&apos;s background, or paste a job
        description to see how well he matches.
      </p>

      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {topics.map((t) => (
          <span key={t} className="rounded-full border border-line px-3 py-1 text-xs text-muted">
            {t}
          </span>
        ))}
      </div>

      <div className="mt-8 grid w-full gap-3 sm:grid-cols-2">
        {welcomePrompts.map((p) => (
          <button
            key={p.label}
            onClick={() => onPrompt(p)}
            className="rounded-xl border border-line bg-surface px-4 py-3 text-left text-sm transition-colors hover:border-accent"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}