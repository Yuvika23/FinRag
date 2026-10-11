import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "FinRAG — Financial Filing Intelligence Engine",
  description: "Enterprise-grade RAG and SQL engine for corporate annual reports, filings, and earnings transcripts.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground antialiased min-h-screen flex selection:bg-emerald-500/20 selection:text-emerald-300">
        <Sidebar />
        <main className="flex-1 min-h-screen overflow-x-hidden flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
