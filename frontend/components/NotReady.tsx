"use client";

import Link from "next/link";

// Shown when a workspace surface 409s: no active project/roadmap yet.
export default function NotReady({ title }: { title: string }) {
  return (
    <>
      <h1 className="page-title">{title}</h1>
      <div className="notice info">
        Your project isn&rsquo;t set up yet — answer the five intake questions and Codize builds
        your roadmap. Then this page unlocks.
      </div>
      <Link href="/app/intake" className="btn primary">
        Start with intake
      </Link>
    </>
  );
}
