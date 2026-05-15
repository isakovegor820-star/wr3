import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { BillingMock } from "@/components/BillingMock";

export default function BillingPage() {
  return (
    <main className="audit-shell">
      <nav className="top-nav">
        <Link href="/">
          <ArrowLeft aria-hidden="true" size={17} />
          Новый скан
        </Link>
      </nav>
      <BillingMock />
    </main>
  );
}
