"use client";

import React, { useEffect, useRef, useState } from "react";
import Image from "next/image";
import V2Character from "../v2/V2Character";
import { CODYBARA_IDLE_FRAMES } from "../../lib/codybara";
import styles from "./landing.module.css";

export default function LandingCharacter() {
  const host = useRef<HTMLSpanElement>(null);
  const [active, setActive] = useState(false);

  useEffect(() => {
    const element = host.current;
    if (!element || typeof IntersectionObserver === "undefined") return;
    let disposed = false;
    let visible = false;
    const sync = () => { if (!disposed) setActive(visible && !document.hidden); };
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
    observer.observe(element);
    document.addEventListener("visibilitychange", sync);
    return () => { disposed = true; observer.disconnect(); document.removeEventListener("visibilitychange", sync); };
  }, []);

  return <span ref={host} className={styles.character} aria-hidden="true">
    {active ? <V2Character size="medium" /> : <Image src={CODYBARA_IDLE_FRAMES[0]} alt="" width={104} height={104} loading="lazy" unoptimized />}
  </span>;
}
