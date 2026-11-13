import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProofGate — Brand governance with proof",
  description: "Evidence-driven brand governance for accountable content review.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Providers>{children}</Providers></body></html>;
}
