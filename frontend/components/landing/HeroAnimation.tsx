"use client";

import React, { useEffect, useRef } from "react";

const reducedMotionQuery = "(prefers-reduced-motion: reduce)";

export default function HeroAnimation() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    const preference = window.matchMedia(reducedMotionQuery);
    const syncPlayback = () => {
      if (!video) return;
      video.pause();
      video.load();
      if (!preference.matches) void video.play().catch(() => {});
    };
    preference.addEventListener("change", syncPlayback);
    return () => {
      preference.removeEventListener("change", syncPlayback);
      video?.pause();
    };
  }, []);

  return <video
    ref={videoRef}
    autoPlay
    muted
    loop
    playsInline
    preload="metadata"
    poster="/landing/codize-hero-ascii-still.png"
    width="800"
    height="605"
    aria-hidden="true"
    tabIndex={-1}
  >
    <source media="(prefers-reduced-motion: no-preference)" src="/landing/codize-hero-ascii.webm" type="video/webm; codecs=vp9" />
    <source media="(prefers-reduced-motion: no-preference)" src="/landing/codize-hero-ascii.mp4" type="video/mp4" />
  </video>;
}
