import "@fontsource/lato/400.css";
import "@fontsource/lato/700.css";
import "./styles/globals.css";

import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: {
    default: "D-carbN Carbon Platform",
    template: "%s | D-carbN"
  },
  description:
    "Standalone Scope 1, 2 and 3 carbon-accounting and reporting platform"
};

export default function RootLayout({
  children
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider><AppShell>{children}</AppShell></AuthProvider>
      </body>
    </html>
  );
}
