import type { Metadata, Viewport } from "next";
import { Barlow_Condensed, Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const barlow = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
  variable: "--font-barlow",
});

export const metadata: Metadata = {
  title: "GTEX Design Concepts — Floodlit",
  description:
    "UI/UX audit and redesign proposals for Global Talent Exchange: player cards, regen cards, command center, discovery and auth.",
};

export const viewport: Viewport = {
  themeColor: "#08140f",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${barlow.variable} bg-background`}>
      <body className="min-h-dvh font-sans antialiased">{children}</body>
    </html>
  );
}
