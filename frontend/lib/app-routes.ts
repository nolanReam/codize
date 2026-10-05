export function isV2AppPath(pathname: string): boolean {
  return pathname === "/app/projects" ||
    pathname.startsWith("/app/project/") ||
    pathname === "/app/character" ||
    pathname === "/app/settings";
}

export function isLegacyAppPath(pathname: string): boolean {
  const path = pathname.replace(/\/+$/, "");
  return path === "/app" || ["intake", "phase", "gate", "report"].some(
    (segment) => path === `/app/${segment}` || path.startsWith(`/app/${segment}/`)
  );
}
