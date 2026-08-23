import type { ButtonHTMLAttributes, ReactNode } from "react";

export function V2Button({
  tone = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: "primary" | "secondary" | "ghost";
}) {
  return <button className={`v2-button v2-button-${tone} ${className}`.trim()} {...props} />;
}

export function V2Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`v2-card ${className}`.trim()}>{children}</section>;
}

export function V2Notice({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "info" | "error" | "success";
}) {
  return (
    <div className={`v2-notice v2-notice-${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function V2Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="v2-skeleton" aria-label="Loading" role="status">
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} style={{ width: `${92 - index * 12}%` }} />
      ))}
    </div>
  );
}
