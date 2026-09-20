import Link from "next/link";
import type { ReactNode } from "react";

import styles from "./public-document.module.css";

type PublicDocumentLayoutProps = {
  currentPath: "/why-codize" | "/how-it-works";
  eyebrow: string;
  title: ReactNode;
  intro: string;
  children: ReactNode;
};

export const PUBLIC_CONTACT = "codizeapp@gmail.com";

const publicLinks = [
  { href: "/why-codize", label: "Why Codize" },
  { href: "/how-it-works", label: "How it works" },
] as const;

export default function PublicDocumentLayout({
  currentPath,
  eyebrow,
  title,
  intro,
  children,
}: PublicDocumentLayoutProps) {
  return (
    <div className={styles.page}>
      <a className={styles.skip} href="#main-content">Skip to main content</a>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="Codize home">
          CODIZE<span aria-hidden="true">_</span>
        </Link>
        <nav className={styles.headerNav} aria-label="Public pages">
          {publicLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={currentPath === link.href ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
          <Link href="/login" prefetch={false} className={styles.signIn}>Sign in</Link>
        </nav>
      </header>

      <main id="main-content" className={styles.main}>
        <section className={styles.hero} aria-labelledby="public-page-title">
          <p className={styles.eyebrow}>{eyebrow}</p>
          <h1 id="public-page-title">{title}</h1>
          <p className={styles.intro}>{intro}</p>
        </section>
        {children}
      </main>

      <footer className={styles.footer}>
        <div>
          <Link href="/" className={styles.footerBrand} aria-label="Codize home">
            CODIZE<span aria-hidden="true">_</span>
          </Link>
          <p>One project. One feature. One useful habit.</p>
        </div>
        <nav aria-label="Footer">
          {publicLinks.map((link) => <Link key={link.href} href={link.href}>{link.label}</Link>)}
          <a href={`mailto:${PUBLIC_CONTACT}`}>Contact</a>
          <Link href="/login" prefetch={false}>Sign in</Link>
        </nav>
      </footer>
    </div>
  );
}
