import { redirect } from "next/navigation";

export default async function SettingsAliasPage({
  searchParams,
}: {
  searchParams: Promise<{ project?: string | string[] }>;
}) {
  const project = (await searchParams).project;
  const projectId = Array.isArray(project) ? project[0] : project;
  redirect(projectId ? `/app/settings?project=${encodeURIComponent(projectId)}` : "/app/settings");
}
