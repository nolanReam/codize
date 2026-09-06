"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";

import { CODYBARA_IDLE_FRAME_MS, CODYBARA_IDLE_FRAMES } from "../../lib/codybara";

export default function V2Character({ size = "medium" }: { size?: "mini" | "small" | "medium" | "large" }) {
  const [frame, setFrame] = useState(0);
  const [loadAnimationFrames, setLoadAnimationFrames] = useState(false);
  const [loadedAnimationFrames, setLoadedAnimationFrames] = useState(0);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frameRequest: number | null = null;

    const updateAnimation = () => {
      if (frameRequest !== null) {
        window.cancelAnimationFrame(frameRequest);
        frameRequest = null;
      }
      setFrame(0);
      setLoadedAnimationFrames(0);
      setLoadAnimationFrames(false);
      if (!reducedMotion.matches) {
        frameRequest = window.requestAnimationFrame(() => {
          frameRequest = null;
          if (!reducedMotion.matches) setLoadAnimationFrames(true);
        });
      }
    };

    updateAnimation();
    reducedMotion.addEventListener("change", updateAnimation);
    return () => {
      reducedMotion.removeEventListener("change", updateAnimation);
      if (frameRequest !== null) window.cancelAnimationFrame(frameRequest);
      frameRequest = null;
    };
  }, []);

  useEffect(() => {
    if (!loadAnimationFrames || loadedAnimationFrames < CODYBARA_IDLE_FRAMES.length - 1) return;
    const interval = window.setInterval(() => {
      setFrame((current) => (current + 1) % CODYBARA_IDLE_FRAMES.length);
    }, CODYBARA_IDLE_FRAME_MS);
    return () => window.clearInterval(interval);
  }, [loadAnimationFrames, loadedAnimationFrames]);

  const renderedFrames = loadAnimationFrames ? CODYBARA_IDLE_FRAMES : CODYBARA_IDLE_FRAMES.slice(0, 1);

  return (
    <span className={`v2-character v2-character-${size}`} aria-hidden="true" data-character="codybara">
      {renderedFrames.map((src, index) => (
        <Image
          key={src}
          className={index === frame ? "v2-character-frame is-current" : "v2-character-frame"}
          src={src}
          alt=""
          width={686}
          height={694}
          draggable={false}
          loading={index === 0 ? "eager" : "lazy"}
          priority={index === 0}
          unoptimized
          onLoad={index === 0 ? undefined : () => setLoadedAnimationFrames((current) => current + 1)}
        />
      ))}
    </span>
  );
}
