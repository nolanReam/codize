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
  return (
    <details className="guide" open={defaultOpen}>
      <summary>{title}</summary>
      <div className="guide-body">{children}</div>
    </details>
  );
}
