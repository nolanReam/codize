import type { Metadata } from "next";
import Link from "next/link";

import PublicDocumentLayout from "@/components/public/PublicDocumentLayout";
import styles from "@/components/public/public-document.module.css";

export const metadata: Metadata = {
  title: "How Codize Works | Plan, prompt, build, check, understand",
  description: "See how Codize works beside your coding AI, one current change at a time.",
};

const steps = [
  { name: "PLAN", summary: "Choose one change and describe what done looks like.", example: "Volleyball Tracker: Add a player form. It is done when I can enter a name and jersey number, submit, and see that player in the list." },
  { name: "PROMPT", summary: "Review the prompt: what to build, what to leave alone, and how to check it.", example: "Codize prepares the prompt. You choose your coding AI and effort level, then edit or accept the wording." },
  { name: "BUILD", summary: "Copy the prompt into the coding AI where you are already working.", example: "Your coding AI handles the requested change in its own environment. Codize waits for you to return; it does not write the code or run the project itself." },
  { name: "CHECK", summary: "Try the change yourself and report what happened.", example: "Enter Alex and 12, submit the form, and look for Alex in the player list. The coding AI saying “it works” is not the check." },
  { name: "UNDERSTAND", summary: "Understand one useful idea before choosing the next change.", example: "For this form, that might mean explaining what submits it or how the new player appears in the list." },
] as const;

export default function HowItWorksPage() {
  return (
    <PublicDocumentLayout
      currentPath="/how-it-works"
      eyebrow="How it works"
      title={<>Build with your coding AI. <em>Keep the thinking connected.</em></>}
      intro="Codize works beside the coding AI you already use. It helps you plan one change, prepare a clear prompt, check the result yourself, and keep track of what you learned."
    >
      <section className={styles.section} aria-labelledby="workflow-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>One simple example</p><h2 id="workflow-title">A player form, from idea to working feature.</h2></div>
          <p>This fictional Volleyball Tracker example shows the manual workflow. You copy the prompt into your coding AI and bring the result back. Codize cannot see or operate that tool.</p>
        </div>
        <div className={styles.workflow}>
          {steps.map((step, index) => (
            <article className={styles.workflowStep} key={step.name}>
              <p className={styles.stepNumber}>{String(index + 1).padStart(2, "0")}</p>
              <div><h3><span>{step.name}</span></h3><p>{step.summary}</p></div>
              <div className={styles.example}><p className={styles.exampleLabel}>Fictional example</p><p>{step.example}</p></div>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.section} aria-labelledby="boundary-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>Who does what</p><h2 id="boundary-title">Codize guides. Your AI builds. You check.</h2></div>
          <p>Codize helps you plan and keep track of the work. Your coding AI makes the change. You try it and decide whether it does what you asked.</p>
        </div>
        <div className={styles.boundaryGrid}>
          <article className={styles.boundaryCard}><h3>Codize</h3><p>Helps choose a manageable change, prepares a prompt you can edit, saves the result you report, and guides your checks and next questions.</p></article>
          <article className={styles.boundaryCard}><h3>Your coding AI</h3><p>Receives the prompt you copy into it and may inspect or edit the project in its own environment.</p></article>
          <article className={styles.boundaryCard}><h3>You</h3><p>Choose the change, review the prompt, use the coding AI, try the project, and report what you actually saw.</p></article>
        </div>
        <ul className={styles.truthList} aria-label="Current product boundaries">
          <li>Codize does not automatically write code or inspect your repository.</li>
          <li>Codize does not execute tests or verify that the behavior works.</li>
          <li>Codize does not currently connect to GitHub.</li>
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="recovery-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>When it does not work</p><h2 id="recovery-title">Find the problem before another fix.</h2></div>
          <p>Stay with the same change. Codize keeps what you saw separate from what the coding AI thinks went wrong.</p>
        </div>
        <div className={styles.recovery}>
          <ol>
            <li><span>01</span>Describe what happened without guessing at the cause.</li>
            <li><span>02</span>Record what worked before the change.</li>
            <li><span>03</span>Copy an investigation prompt that asks the coding AI to inspect before editing.</li>
            <li><span>04</span>Save what it found as a suggestion, not a proven cause.</li>
            <li><span>05</span>Make one focused correction with your coding AI, then try the change again yourself.</li>
          </ol>
          <aside className={styles.recoveryAside}><strong>An explanation is not a check.</strong><p>Your coding AI can suggest where to look. You still need to try the change again.</p></aside>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="outcome-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>What you leave with</p><h2 id="outcome-title">A record you can build on.</h2></div>
          <p>Keep your project history so the next change does not start from a blank chat.</p>
        </div>
        <div className={styles.outcomeGrid}>
          <article className={styles.outcomeCard}><h3>For this change</h3><p>A clear finish line, the prompt you accepted, the check you reported, and notes on any problem you worked through.</p></article>
          <article className={styles.outcomeCard}><h3>For the next change</h3><p>Project history and notes about where you needed help, so Codize can keep its guidance relevant. These are not grades, proof of mastery, or guaranteed results.</p></article>
        </div>
      </section>

      <section className={styles.closing} aria-labelledby="how-closing-title">
        <div><h2 id="how-closing-title">Bring the idea. Keep your coding AI. Build one clear piece.</h2><p>Plan with Codize, build with your coding AI, then come back to check and understand.</p></div>
        <Link href="/login" prefetch={false} className={styles.primaryLink}>Start your first project <span aria-hidden="true">↗</span></Link>
      </section>
    </PublicDocumentLayout>
  );
}
