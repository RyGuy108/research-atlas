import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Research Atlas",
  description: "Map a research field and evaluate how its papers were discovered.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
