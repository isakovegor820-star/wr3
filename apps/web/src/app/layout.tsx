import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Manrope } from "next/font/google";
import "./globals.css";

export const metadata: Metadata = {
  title: "wr3",
  description: "ИИ-предаудит и триаж рисков смарт-контрактов"
};

const uiFont = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-ui",
  display: "swap"
});

const monoFont = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-mono",
  display: "swap"
});

const interFont = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap"
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className={`${uiFont.variable} ${monoFont.variable} ${interFont.variable}`}>{children}</body>
    </html>
  );
}
