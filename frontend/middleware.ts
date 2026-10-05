import { NextRequest, NextResponse } from "next/server";

import { isLegacyAppPath } from "./lib/app-routes";

export async function middleware(request: NextRequest) {
  if (!isLegacyAppPath(request.nextUrl.pathname)) return NextResponse.next();

  // Read the same startup mode that selects FastAPI's routers. No browser
  // header, cookie, query, or second frontend flag controls this decision.
  try {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!base) throw new Error("Missing API origin");
    const response = await fetch(`${base.replace(/\/+$/, "")}/deployment-mode`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("Mode unavailable");
    const mode: unknown = await response.json();
    if (!mode || typeof mode !== "object" || !("pilot_v2_only" in mode) ||
      typeof mode.pilot_v2_only !== "boolean") throw new Error("Invalid mode");

    if (mode.pilot_v2_only) {
      const redirect = NextResponse.redirect(new URL("/app/projects", request.url), 307);
      redirect.headers.set("Cache-Control", "no-store");
      return redirect;
    }
    return NextResponse.next();
  } catch {
    // Do not render a misleading legacy workspace when mode cannot be read.
    return new NextResponse("Codize is temporarily unavailable. Please try again.", {
      status: 503,
      headers: { "Cache-Control": "no-store", "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

export const config = {
  matcher: ["/app", "/app/intake/:path*", "/app/phase/:path*", "/app/gate/:path*", "/app/report/:path*"],
};
