import { ScoutClient } from "@/components/ScoutClient";

export default function ScoutPage() {
  return (
    <main className="app-shell cockpit-shell">
      <section className="command-center">
        <ScoutClient />
      </section>
    </main>
  );
}
