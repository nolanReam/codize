"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { V2Card } from "@/components/v2/V2Primitives";

export default function LearningPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header"><p className="v2-eyebrow">Learning</p><h1>What you’re learning</h1><p>This stays optional and project-connected.</p></header>
      <V2Card><h2>Your learning will grow as your project does.</h2><p>Build your first change and Codize will begin connecting the habits and concepts you use.</p><Link className="v2-button v2-button-primary" href={`/app/project/${id}/build`}>Start building</Link></V2Card>
    </div>
  );
}
