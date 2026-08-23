"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";

import { CODYBARA_IDLE_FRAME_MS, CODYBARA_IDLE_FRAMES } from "../../lib/codybara";

export default function V2Character({ size = "medium" }: { size?: "mini" | "small" | "medium" | "large" }) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let interval: number | null = null;

    const updateAnimation = () => {
      if (interval !== null) {
        window.clearInterval(interval);
        interval = null;
      }
      setFrame(0);
      if (!reducedMotion.matches) {
        interval = window.setInterval(() => {
          setFrame((current) => (current + 1) % CODYBARA_IDLE_FRAMES.length);
        }, CODYBARA_IDLE_FRAME_MS);
      }
    };

    updateAnimation();
    reducedMotion.addEventListener("change", updateAnimation);
    return () => {
      reducedMotion.removeEventListener("change", updateAnimation);
      if (interval !== null) window.clearInterval(interval);
    };
  }, []);

  return (
    <span className={`v2-character v2-character-${size}`} aria-hidden="true" data-character="codybara">
      {CODYBARA_IDLE_FRAMES.map((src, index) => (
        <Image
          key={src}
          className={index === frame ? "v2-character-frame is-current" : "v2-character-frame"}
          src={src}
          alt=""
          width={686}
          height={694}
          draggable={false}
          loading="eager"
          unoptimized
        />
      ))}
    </span>
  );
}
