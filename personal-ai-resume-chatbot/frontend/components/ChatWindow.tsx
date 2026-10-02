"use client";

import { useEffect, useRef, type RefObject } from "react";
import type { Prompt } from "@/lib/prompts";
import type { ChatMessage as Msg } from "@/lib/types";
import ChatInput from "./ChatInput";
import ChatMessage, { TypingIndicator } from "./ChatMessage";
import WelcomeScreen from "./WelcomeScreen";

interface Props {
  messages: Msg[];
  loading: boolean;
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onPrompt: (p: Prompt) => void;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
}

export default function ChatWindow({
  messages,
  loading,
  input,
  onInputChange,
  onSend,
  onPrompt,
  textareaRef,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Smoothly scroll to the newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <WelcomeScreen onPrompt={onPrompt} />
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
            {messages.map((m) => (
              <ChatMessage key={m.id} message={m} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="px-4 pb-4 pt-2">
        <div className="mx-auto w-full max-w-3xl">
          <ChatInput
            value={input}
            onChange={onInputChange}
            onSubmit={onSend}
            disabled={loading}
            textareaRef={textareaRef}
          />
        </div>
      </div>
    </div>
  );
}