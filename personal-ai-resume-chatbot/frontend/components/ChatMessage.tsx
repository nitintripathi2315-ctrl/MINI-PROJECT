import ReactMarkdown from "react-markdown";
import type { ChatMessage as Msg } from "@/lib/types";
import JobMatch from "./JobMatch";

export function Avatar({ size = "sm" }: { size?: "sm" | "lg" }) {
  const dims = size === "lg" ? "h-14 w-14 text-2xl rounded-2xl" : "h-8 w-8 text-sm rounded-lg";
  return (
    <div
      className={`flex shrink-0 items-center justify-center bg-accent font-semibold text-white ${dims}`}
    >
      N
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex gap-3" aria-label="Assistant is typing">
      <Avatar />
      <div className="flex items-center gap-1.5 pt-2.5">
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted" />
      </div>
    </div>
  );
}

export default function ChatMessage({ message }: { message: Msg }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-h-72 max-w-[85%] overflow-y-auto whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-user-bg px-4 py-2.5 text-[15px] leading-relaxed text-user-fg sm:max-w-[75%]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <Avatar />
      <div className="min-w-0 flex-1">
        {message.isError ? (
          <div className="rounded-xl border border-rose-300/60 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
            {message.content}
          </div>
        ) : message.jobMatch ? (
          <JobMatch result={message.jobMatch} />
        ) : (
          <div className="markdown text-[15px] leading-relaxed">
            <ReactMarkdown
              components={{
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}