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
      intro="Coding AI can help you build faster. Understanding the result helps you choose what comes next, spot problems, and keep going when the first answer is not quite right."
    >
      <section className={styles.section} aria-labelledby="leverage-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>The opportunity</p><h2 id="leverage-title">Use AI. Keep control.</h2></div>
          <p>AI coding tools can help you build projects you could not tackle alone. Codize helps you choose one change, check what happened, and understand enough to move forward.</p>
        </div>
        <div className={styles.principles}>
          <article className={styles.principle}><h3>Choose the change</h3><p>A clear goal gives your coding AI a better target and gives you a result you can check.</p></article>
          <article className={styles.principle}><h3>Check reality</h3><p>An answer can sound confident and still miss the behavior you needed. Try the result and record what you actually observed.</p></article>
          <article className={styles.principle}><h3>Know what comes next</h3><p>Knowing how the change works gives you a starting point for the next feature or bug.</p></article>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="evidence-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>What research tells us</p><h2 id="evidence-title">Move faster. Still check.</h2></div>
          <p>Research shows both the promise and the frustrations of coding with AI. These findings are about other tools and developers—not results from Codize.</p>
        </div>
        <div className={styles.evidenceGrid}>
          <article className={styles.evidenceCard}>
            <p className={styles.sourceType}>GitHub research</p>
            <div className={styles.statLine}><strong className={styles.stat}>55%</strong><span className={styles.statQualifier}>faster</span></div>
            <h3>With Copilot on one coding task.</h3>
            <p>AI can help you move faster. Checking what it builds still matters.</p>
            <details>
              <summary>Where this comes from</summary>
              <ul className={styles.sourceNotes}>
                <li><a href="https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/">GitHub research report</a>, published September 7, 2022 and updated May 21, 2024.</li>
                <li>95 professional developers were randomly assigned to use Copilot or work without it. Both groups built an HTTP server in JavaScript—a program that responds to web requests.</li>
                <li>Average completion time was 1 hour 11 minutes with Copilot and 2 hours 41 minutes without it.</li>
                <li>The reported p-value was .0017: the observed difference would be unlikely if the groups had no real difference in completion speed. The 95% confidence interval was 21%–89%, showing the uncertainty around the estimated speed improvement.</li>
                <li>One task, one early Copilot version, and developers already familiar with JavaScript. This does not establish long-term productivity, learning, code quality, or maintainability.</li>
              </ul>
            </details>
          </article>
          <article className={styles.evidenceCard}>
            <p className={styles.sourceType}>2025 Stack Overflow survey</p>
            <div className={styles.statLine}><strong className={styles.stat}>66%</strong><span className={styles.statQualifier}>of surveyed devs</span></div>
            <h3>Frustrated by AI&apos;s &quot;almost right&quot; answers.</h3>
            <p>AI can get you close. Knowing what to check gets you further.</p>
            <details>
              <summary>Where this comes from</summary>
              <ul className={styles.sourceNotes}>
                <li><a href="https://survey.stackoverflow.co/2025/ai">Stack Overflow Developer Survey 2025, AI section</a>.</li>
                <li>The question was: “When using AI tools, which of the following problems or frustrations have you encountered? Select all that apply.” The selected answer was “AI solutions that are almost right, but not quite.”</li>
                <li>31,476 respondents answered this multi-select question. The full retained survey included 49,009 responses from 177 countries.</li>
                <li><a href="https://survey.stackoverflow.co/2025/methodology">Methodology</a>: the survey ran May 29–June 23, 2025. Respondents were recruited mainly through Stack Overflow-owned channels, so highly engaged users were more likely to participate. This is not a representative sample of every developer.</li>
                <li>This is reported frustration, not a measured rate of incorrect AI outputs or proof of what caused the frustration.</li>
              </ul>
            </details>
          </article>
        </div>
        <aside className={styles.researchNote}><strong>AI can speed things up, but good working habits still matter.</strong><p>Google&apos;s DORA research describes AI as strengthening the practices and conditions already around a team—both good and bad. It studies software-development organizations, not Codize or student learning. <a href="https://research.google/pubs/dora-2025-state-of-ai-assisted-software-development-report/">Read the 2025 DORA report overview.</a></p></aside>
      </section>

      <section className={styles.section} aria-labelledby="control-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>The useful middle</p><h2 id="control-title">You do not need to write every line to stay in control.</h2></div>
          <p>You do need to know what should change, what should stay untouched, and how you will check the result. If something unexpected happens, start with what you saw.</p>
        </div>
        <div className={styles.principles}>
          <article className={styles.principle}><h3>Direct</h3><p>Tell your coding AI what to build and what not to change. Work on one piece instead of the whole idea at once.</p></article>
          <article className={styles.principle}><h3>Check</h3><p>Keep what the coding AI says separate from what you personally tried and saw in the project.</p></article>
          <article className={styles.principle}><h3>Recover</h3><p>When something breaks, describe the problem and investigate before asking for another fix.</p></article>
        </div>
      </section>

      <section className={styles.closing} aria-labelledby="why-closing-title">
        <div><h2 id="why-closing-title">Codize keeps the thinking connected to the build.</h2><p>One project, one current change, and one useful habit at a time.</p></div>
        <Link href="/how-it-works" className={styles.primaryLink}>See how it works <span aria-hidden="true">→</span></Link>
      </section>
    </PublicDocumentLayout>
  );
}
