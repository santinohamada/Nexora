import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Conversación con paciente",
};

export default function RecepcionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
