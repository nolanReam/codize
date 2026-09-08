import React from "react";
import styles from "./landing.module.css";

export const ideaPrompt = "Build me a volleyball stats tracker for my team.";
const requests = ["Can you also add player profiles?", "Add game history.", "Could you add charts?", "Add team login."];
const files = [
  ["PlayerForm.tsx", "function PlayerForm() {\n  return <form>\n    <input name=\"player\" />\n  </form>\n}"],
  ["src/", "components/\n  PlayerForm.tsx\n  TeamPage.tsx\nlib/\n  stats.ts\n  storage.ts"],
  ["stats.ts", "function total(games) {\n  return games.reduce(\n    (sum, game) =>\n      sum + game.kills, 0\n  )\n}"],
  ["storage.ts", "const save = (players) => {\n  localStorage.setItem(\n    'players',\n    JSON.stringify(players)\n  )\n}"],
  ["TeamPage.tsx", "<Team>\n  <PlayerList />\n  <GameHistory />\n  <StatsChart />\n</Team>"],
];

function ProjectArtifacts() {
  return <div className={styles.artifacts} aria-hidden="true">
    <svg className={styles.connections} viewBox="0 0 1000 700" preserveAspectRatio="none"><path pathLength="1" d="M180 170 L740 290 L640 560 L160 470 M740 290 L800 130 M180 170 L160 470" /><circle cx="180" cy="170" r="4" /><circle cx="740" cy="290" r="4" /><circle cx="640" cy="560" r="4" /></svg>
    {requests.map((request, index) => <div key={request} className={styles.request} data-storm-request style={{ "--artifact-index": index } as React.CSSProperties}><span>CODING AI <i>↗</i></span><p>{request}</p></div>)}
    {files.map(([name, code], index) => <div key={name} className={styles.fileWindow} data-storm-file style={{ "--artifact-index": index } as React.CSSProperties}><div>{name}<span>···</span></div><pre>{code}</pre></div>)}
  </div>;
}

export function AsciiField({ mode }: { mode: "journey" | "scope" }) {
  return <div className={styles.field} data-storm-field={mode} aria-hidden="true">
    <pre className={styles.asciiFallback}>{"PlayerForm.tsx     { }      /players\n   onClick()      stats.ts      =>\n[ name, number ]      TeamPage.tsx\n  /games       storage.ts     save()\n    render()      api/     [ ]"}</pre>
    <canvas data-storm-canvas={mode} aria-hidden="true" />
  </div>;
}

/** One persistent window and field: the idea literally becomes the project.
 * The baseline is a readable sequence of posters; only enhancement layers it. */
export function StoryAct() {
  return <div className={styles.journey} data-storm-act="journey" data-storm-pin>
    <div className={styles.journeyStage} data-storm-stage>
      <section className={styles.ideaBeat} aria-labelledby="idea-title" data-story-beat="idea">
        <h2 id="idea-title">An idea.</h2>
        <p className={styles.semanticPrompt}>{ideaPrompt}</p>
        <div className={styles.agentWindow} data-agent-window aria-hidden="true">
          <div className={styles.agentChrome}><span><i /> CODING AI</span><span>+ &nbsp; ···</span></div>
          <div className={styles.agentConversation}><span className={styles.agentMark}>{">_"}</span><p className={styles.agentWelcome}>What do you want to build?</p><span className={styles.agentWorking}>Working on your idea<span> ···</span></span></div>
          <div className={styles.agentEmptyPrompt}>Ask a follow-up<span>↑</span></div>
          <div className={styles.agentPrompt}><span data-prompt-text>{ideaPrompt}</span><i className={styles.typingCaret} /><span className={styles.sendMark}>↑</span></div>
          <div className={styles.agentFoot}>Project workspace <span>↗</span></div>
        </div>
      </section>
      <section className={styles.expansionBeat} aria-labelledby="possibilities-title" data-story-beat="possibilities">
        <h2 id="possibilities-title">Then, <em>possibilities.</em></h2>
        <p className={styles.semanticPrompt}>{requests.join(" ")}</p>
        <div className={styles.projectStorm}><AsciiField mode="journey" /><ProjectArtifacts /></div>
      </section>
      <section className={styles.growthBeat} aria-labelledby="growth-title" data-story-beat="understanding"><h2 id="growth-title">Your project can grow<br /><em>faster than your understanding.</em></h2></section>
      <section className={styles.filesBeat} aria-labelledby="files-title" data-story-beat="files"><h2 id="files-title">More files.</h2></section>
      <section className={styles.connectionsBeat} aria-labelledby="connections-title" data-story-beat="connections"><h2 id="connections-title">More connections.</h2></section>
      <section className={styles.lostBeat} aria-labelledby="lost-title" data-story-beat="lost"><h2 id="lost-title">Where did your<br />one idea go?</h2></section>
      <section className={styles.interruption} aria-labelledby="interruption-title" data-story-beat="silence">
        <span aria-hidden="true" className={styles.caret}>[ _ ]</span>
        <h2 id="interruption-title"><span className={styles.semanticQuestions}>What changed? Could you explain it?</span><span className={styles.visualQuestions} aria-hidden="true"><span data-question="first">What changed?</span><br /><span data-question="second">Could you explain it?</span><i className={styles.typingCaret} /></span></h2>
      </section>
    </div>
  </div>;
}

export const method = [
  ["PLAN", "Pick one feature."],
  ["PROMPT", "Give your AI a clear boundary."],
  ["BUILD", "Use your coding agent."],
  ["CHECK", "Try what actually changed."],
  ["UNDERSTAND", "Know why it works."],
] as const;

export function ScopeAct() {
  return <section id="scope" className={styles.scope} aria-labelledby="scope-title" data-storm-act="scope" data-storm-pin>
    <div className={styles.scopeStage} data-storm-stage>
      <p className={styles.codizeEntrance}>This is where<br /><em>Codize</em> comes in.</p>
      <div className={styles.scopeHeading}><h2 id="scope-title">Scope the storm.</h2></div>
      <div className={styles.scopeComposition}>
        <div className={styles.stormPoster}><AsciiField mode="scope" /></div>
        <div className={styles.focusChange} data-storm-focus>
          <div className={styles.lens} aria-hidden="true"><i /><i /><i /><i /></div>
          <div className={styles.focusCopy}><p className={styles.focusLabel}>FOCUS ON ONE FEATURE</p><h3>Add a player’s name<br />and jersey number.</h3></div>
        </div>
        <div className={styles.method}>
          <ol aria-label="A way to stay in control">{method.map(([verb, explanation], index) => <li key={verb} data-storm-verb style={{ "--verb-index": index } as React.CSSProperties}><span className={styles.verb}>{verb}</span><span className={styles.verbExplanation}>{explanation}</span></li>)}</ol>
          <p className={styles.methodEnd}>One useful habit at a time.</p>
        </div>
      </div>
    </div>
  </section>;
}
