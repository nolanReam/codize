import React from "react";
import Link from "next/link";
import LandingMotion from "../components/landing/LandingMotion";
import { CapabilityAct, GapAct, InterruptionAct, ScopeAct } from "../components/landing/StormActs";
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
            <Link href="/login" prefetch={false} className={styles.startLink}>Start one change <span aria-hidden="true">↗</span></Link>
          </div>
          <div className={styles.heroArt} aria-hidden="true">
            <pre className={styles.heroFar}>{"              .       .\n    { }   .       /\n         src/        .\n  .        +       [ ]\n      .        =>\n           .       ."}</pre>
            <pre className={styles.heroStructure}>{"       ┌──────────┐\n      /          /│\n     /   {  }   / │\n    ┌──────────┐  │\n    │          │  +\n    │  idea_   │ /\n    │          │/\n    └──────────┘"}</pre>
            <span className={styles.heroBracket}>[<span>_</span>]</span>
          </div>
        </section>
        <CapabilityAct />
        <GapAct />
        <InterruptionAct />
        <ScopeAct />
        <ProductProof />
      </main>
      <footer className={styles.footer}><span>CODIZE<span aria-hidden="true">_</span></span><p>One project. One current change. One useful habit.</p><Link href="/login" prefetch={false}>Sign in</Link></footer>
      <LandingMotion />
    </div>
  );
}
