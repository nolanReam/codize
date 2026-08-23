"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { getV2Plan, getV2Project } from "@/lib/v2-api";
import type { PlanItemView } from "@/lib/v2-types";

export default function PlanPage() {
  const { id } = useParams<{ id: string }>();
  const [name, setName] = useState("");
  const [items, setItems] = useState<PlanItemView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getV2Project(id), getV2Plan(id)])
      .then(([project, plan]) => {
        setName(project.display_name);
        setItems(plan.items);
      })
      .catch((reason) =>
        setError(reason instanceof ApiError ? reason.message : "Couldn't load the build plan.")
      );
  }, [id]);

  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header"><p className="v2-eyebrow">Build plan</p><h1>{name || "Build plan"}</h1><p>The whole direction, kept secondary to your current change.</p></header>
      {error && <V2Notice tone="error">{error}</V2Notice>}
      {!items && !error && <V2Card><V2Skeleton lines={5} /></V2Card>}
      {items && (
        <V2Card>
          <ol className="v2-plan-list">
            {items.filter((item) => item.status !== "removed").map((item) => (
              <li key={item.id} className={item.status === "done" ? "is-done" : ""}>
                <span aria-hidden="true">{item.status === "done" ? "✓" : item.scope_band === "later" ? "○" : "●"}</span>
                <span><strong>{item.label}</strong>{item.intended_outcome && <small>{item.intended_outcome}</small>}</span>
                <small>{item.scope_band === "later" ? "Later" : item.status}</small>
              </li>
            ))}
          </ol>
        </V2Card>
      )}
    </div>
  );
}
