"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, matchJob, sendMessage, warmUpServer } from "@/lib/api";
import { looksLikeJobDescription } from "@/lib/jd";
import { profile } from "@/lib/profile";
import type { Prompt } from "@/lib/prompts";
import type { ChatMessage, JobMatchResult } from "@/lib/types";
import ChatWindow from "./ChatWindow";
import Sidebar from "./Sidebar";
import { MenuIcon, PlusIcon } from "./icons";

let idCounter = 0;
const newId = () => `${Date.now()}-${idCounter++}`;

// Text version of a match result, so follow-up questions ("why is Docker missing?")
// still have context. The card itself is drawn from result.jobMatch.
function summarize(r: JobMatchResult): string {
  return (
    `Job match analysis: ${r.match_percentage}% match. ` +
    `Matching skills: ${r.matching_skills.join(", ") || "none"}. ` +
    `Missing or limited skills: ${r.missing_skills.join(", ") || "none"}. ` +
    r.explanation
  );
}

export default function ChatApp() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
    useEffect(() => {
    warmUpServer();
  }, []);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  // Changes on every "New Chat", so a slow reply from an old chat can't leak into the new one
  const sessionRef = useRef(0);

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || loading) return;

      const session = sessionRef.current;
      const isCurrent = () => session === sessionRef.current;
      const history = messages; // conversation BEFORE this question

      setMessages([...history, { id: newId(), role: "user", content: text }]);
      setInput("");
      setLoading(true);

      try {
        if (looksLikeJobDescription(text)) {
          const result = await matchJob(text);
          if (!isCurrent()) return;
          setMessages((prev) => [
            ...prev,
            { id: newId(), role: "assistant", content: summarize(result), jobMatch: result },
          ]);
        } else {
          const answer = await sendMessage(text, history);
          if (!isCurrent()) return;
          setMessages((prev) => [
            ...prev,
            { id: newId(), role: "assistant", content: answer },
          ]);
        }
      } catch (err) {
        if (!isCurrent()) return;
        const msg =
          err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
        setMessages((prev) => [
          ...prev,
          { id: newId(), role: "assistant", content: msg, isError: true },
        ]);
      } finally {
        if (isCurrent()) setLoading(false);
      }
    },
    [messages, loading]
  );

  function newChat() {
    sessionRef.current += 1;
    setMessages([]);
    setInput("");
    setLoading(false);
    setSidebarOpen(false);
  }

  function handlePrompt(p: Prompt) {
    setSidebarOpen(false);
    if (p.kind === "send") {
      send(p.text);
    } else {
      // "Analyze this job description": fill the box so the user can paste the JD
      setInput(p.text);
      setTimeout(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.focus();
        el.setSelectionRange(el.value.length, el.value.length);
      }, 0);
    }
  }

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-bg text-fg">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={newChat}
        onPrompt={handlePrompt}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        {/* Top bar, mobile only */}
        <header className="flex items-center gap-2 border-b border-line px-3 py-2.5 md:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="rounded-lg p-2 hover:bg-surface"
          >
            <MenuIcon />
          </button>
          <span className="text-sm font-medium">{profile.shortName}&apos;s AI Assistant</span>
          <button
            onClick={newChat}
            aria-label="New chat"
            className="ml-auto rounded-lg p-2 hover:bg-surface"
          >
            <PlusIcon />
          </button>
        </header>

        <ChatWindow
          messages={messages}
          loading={loading}
          input={input}
          onInputChange={setInput}
          onSend={() => send(input)}
          onPrompt={handlePrompt}
          textareaRef={textareaRef}
        />
      </main>
    </div>
  );
}