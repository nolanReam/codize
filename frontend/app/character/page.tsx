import { redirect } from "next/navigation";

export default async function CharacterAliasPage({
  searchParams,
}: {
  searchParams: Promise<{ project?: string | string[] }>;
}) {
  const project = (await searchParams).project;
  const projectId = Array.isArray(project) ? project[0] : project;
  redirect(projectId ? `/app/character?project=${encodeURIComponent(projectId)}` : "/app/character");
}
