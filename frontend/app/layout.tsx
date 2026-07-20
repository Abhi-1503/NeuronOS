import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/tokens.css";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NeuronOS",
  description: "The intelligence layer for every business.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} antialiased`}>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
