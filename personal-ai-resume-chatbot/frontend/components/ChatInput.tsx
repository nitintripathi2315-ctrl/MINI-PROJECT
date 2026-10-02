"use client";

import { useEffect, type KeyboardEvent, type RefObject } from "react";
import { SendIcon } from "./icons";

const MAX_CHARS = 12000; // the backend also cuts job descriptions at 12,000 characters

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
}

export default function ChatInput({ value, onChange, onSubmit, disabled, textareaRef }: Props) {
  // Grow the box as the user types (up to 200px), then scroll inside it
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value, textareaRef]);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter makes a new line
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      onSubmit();
    }
  }

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div>
      <div className="flex items-end gap-2 rounded-2xl border border-line bg-surface p-2 transition-colors focus-within:border-accent">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={MAX_CHARS}
          rows={1}
          placeholder="Ask about Nitin, or paste a job description..."
          className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-2 text-[15px] outline-none placeholder:text-muted"
        />
        <button
          type="button"
          onClick={onSubmit}
          disabled={!canSend}
          aria-label="Send message"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SendIcon />
        </button>
      </div>
      <p className="mt-2 text-center text-xs text-muted">
        {value.length > MAX_CHARS * 0.8
          ? `${value.length.toLocaleString()} / ${MAX_CHARS.toLocaleString()} characters`
          : "Answers are based on Nitin's resume. Please verify important details."}
      </p>
    </div>
  );
}