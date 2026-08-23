"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { V2Card } from "@/components/v2/V2Primitives";

export default function HistoryPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header"><p className="v2-eyebrow">History</p><h1>Project history</h1><p>A human-readable record of completed work will live here.</p></header>
      <V2Card><h2>No completed changes yet</h2><p>Your history will show up after the first full build-and-check loop. Codize will not turn plan status into fake verification.</p><Link className="v2-button v2-button-secondary" href={`/app/project/${id}`}>Back to Project</Link></V2Card>
    </div>
  );
}
