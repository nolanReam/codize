// A guidance-rail card: contextual help that lives in the workspace's right
// column (what this page is for, what to do next, examples, glossary).
export default function GuideCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="guide">
      <h4>{title}</h4>
      {children}
    </div>
  );
}
