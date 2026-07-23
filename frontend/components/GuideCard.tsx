"use client";

import { useEffect, useState } from "react";

// A guidance-rail card: contextual help that lives in the workspace's right
// column. Collapsed by default since M13E.3 (pilot feedback: the app read as
// text-heavy) — the title is always visible, the body opens on demand.
// Progressive disclosure: guidance exists, but never as a wall of text.
export default function GuideCard({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  useEffect(() => {
    if (defaultOpen) setOpen(true);
  }, [defaultOpen]);

  return (
    <details
      className="guide"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>{title}</summary>
      <div className="guide-body">{children}</div>
    </details>
  );
}
