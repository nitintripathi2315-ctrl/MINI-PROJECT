"use client";

import { MoonIcon, SunIcon } from "./icons";

export default function ThemeToggle() {
  function toggle() {
    const isDark = document.documentElement.classList.toggle("dark");
    try {
      localStorage.setItem("theme", isDark ? "dark" : "light");
    } catch {
      /* storage blocked: the theme just won't be remembered */
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label="Toggle light/dark theme"
      className="rounded-lg p-2 text-muted transition-colors hover:bg-surface hover:text-fg"
    >
      <SunIcon className="hidden dark:block" />
      <MoonIcon className="block dark:hidden" />
    </button>
  );
}