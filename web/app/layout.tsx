import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nexora — LSA-64",
  description: "Real-time Argentine Sign Language recognition powered by CTR-GCN",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="antialiased">{children}</body>
    </html>
  );
}
