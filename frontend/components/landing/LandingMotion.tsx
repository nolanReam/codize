"use client";

import { useEffect } from "react";
import { createStormController } from "./storm-controller";

export default function LandingMotion() {
  useEffect(() => {
    const root = document.getElementById("scope-the-storm");
    if (!root) return;
    return createStormController(root);
  }, []);
  return null;
}
