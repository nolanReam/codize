import { redirect } from "next/navigation";

// M18B.1 compatibility route: old bookmarks and task links return to the one
// orientation dashboard, positioned at the current-phase summary.
export default function PhaseWorkspaceRedirect() {
  redirect("/app#current-phase");
}
