import { V2Card } from "@/components/v2/V2Primitives";

export default function AppSettingsPage() {
  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header"><p className="v2-eyebrow">Settings</p><h1>Settings</h1><p>Account and presentation preferences belong here.</p></header>
      <V2Card><h2>Presentation</h2><p>Dialogue sound, animation, and reduced-motion controls will be connected when those systems exist. Your system reduced-motion setting is already respected by this foundation.</p></V2Card>
    </div>
  );
}
