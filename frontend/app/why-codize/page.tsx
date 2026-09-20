import type { Metadata } from "next";
import Link from "next/link";

import PublicDocumentLayout from "@/components/public/PublicDocumentLayout";
import styles from "@/components/public/public-document.module.css";

export const metadata: Metadata = {
  title: "Why Codize | Build with AI and stay in control",
  description: "Why understanding, checking, and directing code still matter when AI can help you build faster.",
};

export default function WhyCodizePage() {
  return (
    <PublicDocumentLayout
      currentPath="/why-codize"
      eyebrow="Why Codize"
      title={<>AI changed how we code. <em>It didn&apos;t remove the need to understand.</em></>}
      intro="Coding AI can turn an idea into working software faster than ever. Understanding is what lets you decide what to build, recognize what happened, and keep moving when the first answer is not quite right."
    >
      <section className={styles.section} aria-labelledby="leverage-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>The opportunity</p><h2 id="leverage-title">Use the leverage. Keep the judgment.</h2></div>
          <p>Codize is not an argument against AI coding tools. They can make ambitious projects more reachable. The useful distinction is between generating a change and being able to direct, check, and maintain it.</p>
        </div>
        <div className={styles.principles}>
          <article className={styles.principle}><h3>Choose the change</h3><p>A clear, bounded goal gives the coding AI a better target and gives you something concrete to evaluate.</p></article>
          <article className={styles.principle}><h3>Check reality</h3><p>An answer can sound confident and still miss the behavior you needed. Try the result and record what you actually observed.</p></article>
          <article className={styles.principle}><h3>Own what happens next</h3><p>Understanding the important connection makes the next feature, bug, or requirement change easier to reason about.</p></article>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="evidence-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>What the evidence says</p><h2 id="evidence-title">Faster is real. So is the work of checking.</h2></div>
          <p>These studies answer different questions. One observed performance on a single controlled task; the other asked survey respondents about their experience. Neither measures Codize or proves that AI users do not understand their code.</p>
        </div>
        <div className={styles.evidenceGrid}>
          <article className={styles.evidenceCard}>
            <p className={styles.sourceType}>Observed outcome · randomized experiment</p>
            <strong className={styles.stat}>55%</strong>
            <h3>faster on one bounded JavaScript task</h3>
            <p>GitHub randomly split 95 professional developers into Copilot and non-Copilot groups for the same HTTP-server task.</p>
            <details>
              <summary>Source and limitations</summary>
              <ul className={styles.sourceNotes}>
                <li><a href="https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/">GitHub research report</a>, published 2022 and updated 2024.</li>
                <li>Average completion time was 1 hour 11 minutes with Copilot and 2 hours 41 minutes without it; reported p=.0017 and 95% confidence interval 21%–89%.</li>
                <li>One task, one early Copilot version, and developers already familiar with JavaScript. This does not establish long-term learning, code quality, or maintainability.</li>
              </ul>
            </details>
          </article>
          <article className={styles.evidenceCard}>
            <p className={styles.sourceType}>Developer-reported perception · survey</p>
            <strong className={styles.stat}>66%</strong>
            <h3>selected “almost right, but not quite” as an AI-tool frustration</h3>
            <p>The 2025 Stack Overflow survey asked: “When using AI tools, which of the following problems or frustrations have you encountered? Select all that apply.”</p>
            <details>
              <summary>Source and limitations</summary>
              <ul className={styles.sourceNotes}>
                <li><a href="https://survey.stackoverflow.co/2025/ai">Stack Overflow Developer Survey 2025, AI section</a>.</li>
                <li>31,476 respondents answered this multi-select question. The full retained survey included 49,009 responses from 177 countries.</li>
                <li><a href="https://survey.stackoverflow.co/2025/methodology">Methodology</a>: respondents were recruited mainly through Stack Overflow-owned channels, so highly engaged Stack Overflow users were more likely to participate.</li>
                <li>This is reported frustration, not an observed failure rate or causal evidence.</li>
              </ul>
            </details>
          </article>
        </div>
        <p className={styles.researchNote}>DORA&apos;s 2025 software-development research describes AI as an amplifier of the practices around it. That is organizational research—not evidence about Codize or student learning—but it reinforces the value of clear workflows and feedback. <a href="https://research.google/pubs/dora-2025-state-of-ai-assisted-software-development-report/">Read the DORA report overview.</a></p>
      </section>

      <section className={styles.section} aria-labelledby="control-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>The useful middle</p><h2 id="control-title">You do not need to write every line to stay in control.</h2></div>
          <p>You do need enough context to make consequential decisions: what should change, what should stay untouched, what result would count, what you observed, and what question to ask when the result surprises you.</p>
        </div>
        <div className={styles.principles}>
          <article className={styles.principle}><h3>Direct</h3><p>Give your coding AI a specific outcome, project context, and boundaries instead of handing it the entire idea at once.</p></article>
          <article className={styles.principle}><h3>Verify</h3><p>Separate what the coding AI claims from what you personally tried and observed in the project.</p></article>
          <article className={styles.principle}><h3>Recover</h3><p>When something breaks, narrow the symptom and investigate before asking for another broad patch.</p></article>
        </div>
      </section>

      <section className={styles.closing} aria-labelledby="why-closing-title">
        <div><h2 id="why-closing-title">Codize keeps the thinking connected to the build.</h2><p>One project, one current change, and one useful habit at a time.</p></div>
        <Link href="/how-it-works" className={styles.primaryLink}>See how it works <span aria-hidden="true">→</span></Link>
      </section>
    </PublicDocumentLayout>
  );
}
