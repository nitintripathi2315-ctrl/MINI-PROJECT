import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nitin's AI Assistant",
  description: "Chat with an AI version of Nitin Tripathi's resume and portfolio.",
};

// Runs before the page paints, so there's no white flash when dark mode is saved
const themeScript = `
(function () {
  try {
    var t = localStorage.getItem('theme');
    if (!t) t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    if (t === 'dark') document.documentElement.classList.add('dark');
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}