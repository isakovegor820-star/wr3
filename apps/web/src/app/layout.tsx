import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "wr3",
  description: "AI-предаудит и триаж рисков смарт-контрактов"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
