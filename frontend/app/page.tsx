import React from "react";
import Link from "next/link";
import LandingMotion from "../components/landing/LandingMotion";
import { StoryAct, ScopeAct } from "../components/landing/StormActs";
import ProductProof from "../components/landing/ProductProof";
import styles from "../components/landing/landing.module.css";

export default function LandingPage() {
  return (
    <div id="scope-the-storm" className={styles.landing}>
      <a className={styles.skip} href="#product-proof">Skip to how Codize helps</a>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="Codize home">CODIZE<span aria-hidden="true">_</span></Link>
        <Link href="/login" prefetch={false} className={styles.signIn}>Sign in</Link>
      </header>
      <main>
        <section className={styles.hero} aria-labelledby="landing-thesis" data-storm-act="thesis">
          <div className={styles.heroType}>
            <h1 id="landing-thesis"><span>BUILD <br className={styles.mobileBreak} />WITH AI. </span><span>STAY IN <br className={styles.mobileBreak} />CONTROL.</span></h1>
            <p>Codize is your AI coding mentor.<br />Build your idea. Understand it as you go.</p>
            <Link href="/login" prefetch={false} className={styles.startLink}>Start your first project <span aria-hidden="true">↗</span></Link>
          </div>
          <div className={styles.heroArt} aria-hidden="true">
            <picture>
              <source media="(prefers-reduced-motion: no-preference)" srcSet="/landing/codize-hero-ascii.gif" type="image/gif" />
              {/* The supplied GIF is served byte-for-byte; the browser selects a still under reduced motion. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/landing/codize-hero-ascii-still.png" width="800" height="605" alt="" decoding="async" />
            </picture>
          </div>
        </section>
        <StoryAct />
        <ScopeAct />
        <ProductProof />
        <section className={styles.ending} aria-labelledby="ending-title" data-storm-act="ending">
          <h2 id="ending-title">Big ideas. Understandable steps.</h2>
          <Link href="/login" prefetch={false} className={styles.finalLink}>Start your first project <span aria-hidden="true">↗</span></Link>
          <p className={styles.endingSupport}>Build with your AI.<br />Come back to check, understand,<br />or work out what broke.</p>
        </section>
      </main>
      <footer className={styles.footer}><span>CODIZE<span aria-hidden="true">_</span></span><p>One project. One feature. One useful habit.</p><Link href="/login" prefetch={false}>Sign in</Link></footer>
      <LandingMotion />
    </div>
  );
}
