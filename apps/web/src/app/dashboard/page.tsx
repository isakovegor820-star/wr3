import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { DashboardClient } from "@/components/DashboardClient";

export default function DashboardPage() {
  return (
    <main className="audit-shell">
      <nav className="top-nav">
        <Link href="/">
          <ArrowLeft aria-hidden="true" size={17} />
          Новый скан
        </Link>
      </nav>
      <DashboardClient />
    </main>
  );
}
