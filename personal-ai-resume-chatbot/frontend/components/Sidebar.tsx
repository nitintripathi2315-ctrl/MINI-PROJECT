"use client";

import { profile } from "@/lib/profile";
import { sidebarStarters, type Prompt } from "@/lib/prompts";
import { Avatar } from "./ChatMessage";
import { CloseIcon, PlusIcon } from "./icons";
import ThemeToggle from "./ThemeToggle";

interface Props {
  open: boolean; // only matters on mobile, where the sidebar is a slide-in drawer
  onClose: () => void;
  onNewChat: () => void;
  onPrompt: (p: Prompt) => void;
}

const links = [
  { label: "Resume", href: profile.links.resume },
  { label: "GitHub", href: profile.links.github },
  { label: "LinkedIn", href: profile.links.linkedin },
  { label: "Codolio", href: profile.links.codolio },
  { label: "Portfolio", href: profile.links.portfolio },
].filter((l) => l.href.trim() !== "");

export default function Sidebar({ open, onClose, onNewChat, onPrompt }: Props) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col border-r border-line bg-sidebar transition-transform duration-200 md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 px-4 py-4">
          <Avatar />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold leading-tight">Personal AI</p>
            <p className="truncate text-xs text-muted">{profile.name}</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="rounded-lg p-1.5 text-muted hover:bg-surface md:hidden"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="px-3">
          <button
            onClick={onNewChat}
            className="flex w-full items-center gap-2 rounded-xl border border-line px-3 py-2.5 text-sm font-medium transition-colors hover:bg-surface"
          >
            <PlusIcon width={18} height={18} />
            New Chat
          </button>
        </div>

        <nav className="mt-5 flex-1 overflow-y-auto px-3">
          <p className="px-2 pb-2 text-xs font-medium uppercase tracking-wide text-muted">
            Explore
          </p>
          <ul className="space-y-0.5">
            {sidebarStarters.map((p) => (
              <li key={p.label}>
                <button
                  onClick={() => onPrompt(p)}
                  className="w-full rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-surface"
                >
                  {p.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="border-t border-line px-3 py-3">
          <ul className="space-y-0.5">
            {links.map((l) => (
              <li key={l.label}>
                <a
                  href={l.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg px-2 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-fg"
                >
                  {l.label}
                  <span aria-hidden="true">&#8599;</span>
                </a>
              </li>
            ))}
          </ul>
          <div className="mt-2 flex items-center justify-between px-1">
            <span className="text-xs text-muted">Theme</span>
            <ThemeToggle />
          </div>
        </div>
      </aside>
    </>
  );
}