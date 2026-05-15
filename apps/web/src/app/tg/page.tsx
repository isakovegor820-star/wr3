import Script from "next/script";
import { TelegramMiniAppClient } from "@/components/TelegramMiniAppClient";

export default function TelegramMiniAppPage() {
  return (
    <>
      <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
      <TelegramMiniAppClient />
    </>
  );
}
