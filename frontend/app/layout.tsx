import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Codize — Stop debugging blindly",
  description:
    "Codize is an AI coding workflow trainer: plan, prompt, review, verify, and defend AI-generated code before your project collapses into patch loops.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
