"use client";

import Link from "next/link";

// Shown when a workspace surface 409s: no active project/roadmap yet.
export default function NotReady({ title }: { title: string }) {
  return (
    <>
      <h1 className="page-title">{title}</h1>
      <div className="notice info">
        No active roadmap yet. Finish intake and generate your roadmap first — then this surface
        unlocks.
      </div>
      <Link href="/app/intake" className="btn primary">
        Go to intake
      </Link>
    </>
  );
}
