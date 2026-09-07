import React from "react";
import styles from "./landing.module.css";

// Whole lines, not hundreds of individually animated glyph nodes. This is also
// the deliberately composed no-Canvas / no-JavaScript illustration.
const fragments = [
  "{ idea }     ->     [ ]", "src/       +       form.tsx", "   onClick()    { + }",
  "[ name, number ]     =>", "   list.map()     /players", "state/    { ... }    save()",
  "     +    components/", "[ ]   ->   storage.ts", "  return { }     /routes",
  "data/    =>    [ ... ]", "    .filter()    +    /ui", "{ input }    ->    render()",
];

export function AsciiField({ mode }: { mode: "speed" | "gap" | "scope" }) {
  return <div className={`${styles.field} ${styles[`${mode}Field`]}`} data-storm-field={mode} aria-hidden="true">
    <pre className={styles.asciiFallback}>{[...fragments, ...fragments.slice().reverse()].join("\n")}</pre>
    <canvas data-storm-canvas={mode} aria-hidden="true" />
  </div>;
}

export function CapabilityAct() {
  return <section className={styles.capability} aria-labelledby="capability-title" data-storm-act="speed" data-storm-pin>
    <div className={styles.speedStage} data-storm-stage>
      <div className={styles.speedCopy}><h2 id="capability-title" data-storm-enter>An idea.<br />Then, <em>possibilities.</em></h2><p data-storm-enter="after">With coding AI, you can make more than you thought.</p></div>
      <AsciiField mode="speed" />
      <div className={styles.intention}><span>YOUR IDEA</span><p>“A stat tracker for my team.”</p><span aria-hidden="true">{"> _"}</span></div>
    </div>
  </section>;
}

export function GapAct() {
  return <section className={styles.gap} aria-labelledby="gap-title" data-storm-act="gap">
    <AsciiField mode="gap" />
    <p className={styles.lostIntention}>“A stat tracker for my team.”</p>
    <div className={styles.gapCopy}><h2 id="gap-title" data-storm-enter>Your project can grow<br /><em>faster than your<br />understanding.</em></h2><p>More files. More connections.<br />Where did your one idea go?</p></div>
    <span className={styles.gapBracket} aria-hidden="true">{'}'}</span>
  </section>;
}

export function InterruptionAct() {
  return <section className={styles.interruption} aria-labelledby="interruption-title" data-storm-act="silence">
    <span aria-hidden="true" className={styles.caret}>[ _ ]</span>
    <h2 id="interruption-title">What changed?<br /><span>Could you explain it?</span></h2>
  </section>;
}

export const method = [
  ["PLAN", "Pick one change."],
  ["PROMPT", "Give your AI a clear boundary."],
  ["BUILD", "Use your coding agent."],
  ["CHECK", "Try what actually changed."],
  ["UNDERSTAND", "Know why it works."],
] as const;

export function ScopeAct() {
  return <section id="scope" className={styles.scope} aria-labelledby="scope-title" data-storm-act="scope" data-storm-pin>
    <div className={styles.scopeStage} data-storm-stage>
      <div className={styles.scopeHeading}><p>THIS IS WHERE CODIZE COMES IN.</p><h2 id="scope-title">Scope the storm.</h2></div>
      <div className={styles.scopeComposition}>
        <div className={styles.stormPoster}><AsciiField mode="scope" /><p className={styles.staticStormLabel}>A whole system. Find one place to start.</p></div>
        <div className={styles.focusChange} data-storm-focus>
          <div className={styles.lens} aria-hidden="true"><i /><i /><i /><i /></div>
          <div className={styles.focusCopy}><p className={styles.focusLabel}>ONE CURRENT CHANGE</p><h3>Add a player’s name<br />and jersey number.</h3><p>A result you can explain.<br />A boundary your AI can follow.</p></div>
        </div>
        <div className={styles.method}>
          <p className={styles.methodIntro}>Keep the ambition. Give it structure.</p>
          <ol aria-label="A way to stay in control">{method.map(([verb, explanation], index) => <li key={verb} data-storm-verb style={{ "--verb-index": index } as React.CSSProperties}><span className={styles.verb}>{verb}</span><span className={styles.verbExplanation}>{explanation}</span></li>)}</ol>
          <p className={styles.methodEnd}>One useful habit at a time.</p>
        </div>
      </div>
    </div>
  </section>;
}
