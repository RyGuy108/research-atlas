import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Research Atlas",
  description: "Turn a machine-learning topic into an evidence-backed research landscape.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  openGraph: {
    title: "Research Atlas",
    description: "Discover, rerank, extract, and map a machine-learning research field.",
    images: [{ url: "/research-atlas-social.png", width: 1200, height: 630 }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Research Atlas",
    description: "An evidence-backed reading map for machine-learning research.",
    images: ["/research-atlas-social.png"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
