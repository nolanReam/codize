import React from "react";
import Link from "next/link";
import LandingCharacter from "./LandingCharacter";
import styles from "./landing.module.css";

export default function ProductProof() {
  return <section id="product-proof" className={styles.proof} aria-labelledby="proof-title" data-storm-act="proof" tabIndex={-1}>
    <div className={styles.proofIntro}><h2 id="proof-title" data-storm-enter>Your project.<br />Your thinking.<br /><em>A little backup.</em></h2><p data-storm-enter="after">Keep your coding AI. Codize helps you scope the next change, write a clear prompt, and check the result.</p></div>
    <figure className={styles.specimen}>
      <figcaption>INSIDE CODIZE <span>Build example · static preview</span></figcaption>
      <div className={styles.specimenHeader}><p>Volleyball Tracker</p><h3>Add the player form</h3></div>
      <div className={`${styles.specimenDialogue} v2-character-message`}><LandingCharacter /><div><p>Before we ask your coding AI, what should you be able to do when this is finished?</p></div></div>
      <div className={styles.specimenAnswer}><span>AN EXAMPLE ANSWER</span><p>Type a player’s name and jersey number, then add them to my team.</p></div>
      <p className={styles.specimenNote}>A clear result gives you something real to check.</p>
    </figure>
    <div className={styles.ending}><p>Big ideas. Understandable steps.</p><Link href="/login" prefetch={false} className={styles.finalLink}>Start one change <span aria-hidden="true">↗</span></Link><p className={styles.endingSupport}>Build with your AI. Come back to check, understand,<br />or work out what broke.</p></div>
  </section>;
}
