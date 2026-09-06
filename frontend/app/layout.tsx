import type { Metadata } from "next";
import {
  DM_Mono,
  DM_Sans,
  IBM_Plex_Mono,
  Inter,
  Press_Start_2P,
  Space_Grotesk,
} from "next/font/google";

import "./globals.css";

const sans = DM_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});
const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const v2Sans = Inter({ subsets: ["latin"], variable: "--font-v2-sans", display: "swap" });
const v2Mono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-v2-mono",
  display: "swap",
});
const v2Display = Press_Start_2P({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-v2-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Codize — Build with AI. Stay in control.",
  description:
    "Codize is an AI coding mentor for student builders. Scope one change, work with your coding AI, and understand what you build as you go.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${mono.variable} ${display.variable} ${v2Sans.variable} ${v2Mono.variable} ${v2Display.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
