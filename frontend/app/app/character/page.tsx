import V2Character from "@/components/v2/V2Character";
import { V2Card } from "@/components/v2/V2Primitives";

export default function CharacterPage() {
  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header"><p className="v2-eyebrow">Character</p><h1>Your companion</h1><p>Character choice and cosmetics will live here, separate from Settings.</p></header>
      <V2Card className="v2-character-preview"><V2Character size="large" /><div><p className="v2-card-label">Current companion</p><h2>Codybara</h2><p>Your friendly starter companion is ready. Character switching and accessories will appear here when those systems are built.</p></div></V2Card>
    </div>
  );
}
