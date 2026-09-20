import type { Metadata } from "next";
import Link from "next/link";

import PublicDocumentLayout from "@/components/public/PublicDocumentLayout";
import styles from "@/components/public/public-document.module.css";

export const metadata: Metadata = {
  title: "How Codize Works | Plan, prompt, build, check, understand",
  description: "See how Codize works beside your coding AI, one current change at a time.",
};

const steps = [
  { name: "PLAN", summary: "Choose one current change and name what done looks like.", example: "Volleyball Tracker: Add a player form. It is done when I can enter a name and jersey number, submit, and see that player in the list." },
  { name: "PROMPT", summary: "Review an editable handoff with the goal, context, boundaries, and check.", example: "Codize prepares the prompt. You choose your coding AI and effort level, then review the wording before accepting it." },
  { name: "BUILD", summary: "Copy the prompt into the coding AI where you are already working.", example: "Your coding AI handles the requested change in its own environment. Codize waits for you to return; it does not write the code or run the project itself." },
  { name: "CHECK", summary: "Try the relevant behavior and report what you personally observed.", example: "Enter Alex and 12, submit the form, and look for Alex in the player list. The coding AI saying “it works” is not the check." },
  { name: "UNDERSTAND", summary: "Connect the result to one useful idea before choosing the next change.", example: "For this change, that might be identifying what action submits the form or how the new player reaches the displayed list." },
] as const;

export default function HowItWorksPage() {
  return (
    <PublicDocumentLayout
      currentPath="/how-it-works"
      eyebrow="How it works"
      title={<>Build with your coding AI. <em>Keep the thinking connected.</em></>}
      intro="Codize is a mentor around the coding tools you already use. It helps you shape one understandable change, hand it off clearly, check the real result, and keep what you learned attached to the project."
    >
      <section className={styles.section} aria-labelledby="workflow-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>One real example</p><h2 id="workflow-title">A player form, from idea to understood change.</h2></div>
          <p>This is a static, fictional walkthrough of the implemented manual workflow. It uses no student data and does not imply that Codize can see or operate the external coding tool.</p>
        </div>
        <div className={styles.workflow}>
          {steps.map((step, index) => (
            <article className={styles.workflowStep} key={step.name}>
              <p className={styles.stepNumber}>{String(index + 1).padStart(2, "0")}</p>
              <div><h3><span>{step.name}</span></h3><p>{step.summary}</p></div>
              <div className={styles.example}><p className={styles.exampleLabel}>Static example</p><p>{step.example}</p></div>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.section} aria-labelledby="boundary-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>A deliberate handoff</p><h2 id="boundary-title">Three roles. No invisible automation.</h2></div>
          <p>The separation is important: Codize prepares and records the learning workflow, the coding AI works on the project, and the student performs the consequential check.</p>
        </div>
        <div className={styles.boundaryGrid}>
          <article className={styles.boundaryCard}><h3>Codize</h3><p>Helps scope the current change, prepares an editable prompt, records the return outcome, guides a check, and supports recovery and understanding.</p></article>
          <article className={styles.boundaryCard}><h3>Your coding AI</h3><p>Receives the prompt you copy into it and may inspect or edit the project in its own environment.</p></article>
          <article className={styles.boundaryCard}><h3>You</h3><p>Choose the change, review the prompt, operate the coding AI, try the project, and report what you actually observed.</p></article>
        </div>
        <ul className={styles.truthList} aria-label="Current product boundaries">
          <li>Codize does not automatically write code or inspect your repository.</li>
          <li>Codize does not execute tests or verify that the behavior works.</li>
          <li>Codize does not currently connect to GitHub.</li>
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="recovery-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>When it does not work</p><h2 id="recovery-title">Investigate before another patch.</h2></div>
          <p>Recovery stays attached to the same current change. Codize keeps the student&apos;s observation separate from whatever the coding AI suggests.</p>
        </div>
        <div className={styles.recovery}>
          <ol>
            <li><span>01</span>Describe what happened without guessing at the cause.</li>
            <li><span>02</span>Record what worked before the change.</li>
            <li><span>03</span>Copy an investigation prompt that asks the coding AI to inspect before editing.</li>
            <li><span>04</span>Save its finding as a suggestion, not a verified root cause.</li>
            <li><span>05</span>Apply a bounded correction and personally recheck the behavior.</li>
          </ol>
          <aside className={styles.recoveryAside}><strong>The truth boundary</strong><p>A coding agent&apos;s explanation can help narrow the problem. It does not replace the student trying the behavior again.</p></aside>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="outcome-title">
        <div className={styles.sectionHeading}>
          <div><p className={styles.sectionLabel}>What you leave with</p><h2 id="outcome-title">Useful project context, not a certificate.</h2></div>
          <p>Codize preserves the structure around the work so the next decision does not begin in a blank chat.</p>
        </div>
        <div className={styles.outcomeGrid}>
          <article className={styles.outcomeCard}><h3>For the current change</h3><p>A clear finish line, an accepted prompt, a recorded check, and—when needed—a recovery trail.</p></article>
          <article className={styles.outcomeCard}><h3>For the next change</h3><p>Project history and support signals that help Codize provide relevant guidance without claiming grades, mastery, or guaranteed outcomes.</p></article>
        </div>
      </section>

      <section className={styles.closing} aria-labelledby="how-closing-title">
        <div><h2 id="how-closing-title">Bring the idea. Keep your coding AI. Build one clear piece.</h2><p>Codize supplies the structure around the handoff and the return.</p></div>
        <Link href="/login" prefetch={false} className={styles.primaryLink}>Start your first project <span aria-hidden="true">↗</span></Link>
      </section>
    </PublicDocumentLayout>
  );
}
