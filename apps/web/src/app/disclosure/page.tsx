import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { DisclosureManager } from "@/components/DisclosureManager";

export default function DisclosurePage() {
  return (
    <main className="audit-shell">
      <nav className="top-nav">
        <Link href="/">
          <ArrowLeft aria-hidden="true" size={17} />
          Новый скан
        </Link>
      </nav>
      <DisclosureManager />
    </main>
  );
}
