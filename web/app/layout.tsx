import type { Metadata } from "next";
import Script from "next/script";
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
      <head>
        <Script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" strategy="afterInteractive" />
        <Script src="https://cdn.jsdelivr.net/npm/@mediapipe/control_utils/control_utils.js" strategy="afterInteractive" />
        <Script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js" strategy="afterInteractive" />
        <Script src="https://cdn.jsdelivr.net/npm/@mediapipe/holistic/holistic.js" strategy="afterInteractive" />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
