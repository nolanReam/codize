import type { Metadata } from "next";
import { Cormorant_Garamond, DM_Sans, IBM_Plex_Mono, Space_Grotesk } from "next/font/google";

import "./globals.css";

const sans = DM_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});
const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", display: "swap" });
// Editorial display face for the big landing headlines (open-source Garamond).
const editorial = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-editorial",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Codize — Stop debugging blindly",
  description:
    "Codize is an AI coding workflow trainer: plan, prompt, review, verify, and defend AI-generated code before your project collapses into patch loops.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${mono.variable} ${display.variable} ${editorial.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
