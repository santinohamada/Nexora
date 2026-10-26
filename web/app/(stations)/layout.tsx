"use client";

import { StationProvider } from "../../components/stations/StationProvider";

export default function StationsLayout({ children }: { children: React.ReactNode }) {
  return <StationProvider>{children}</StationProvider>;
}
