import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { TelegramEmulator } from "@/components/TelegramEmulator";

export default function TelegramEmulatorPage() {
  return (
    <main className="audit-shell">
      <nav className="top-nav">
        <Link href="/">
          <ArrowLeft aria-hidden="true" size={17} />
          Новый скан
        </Link>
        <Link href="/tg">Предпросмотр Mini App</Link>
      </nav>
      <TelegramEmulator />
    </main>
  );
}
