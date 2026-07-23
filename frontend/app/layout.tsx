import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "../styles/tokens.css";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

// Brand system (docs/mockups/neuronos_brand_concept.html §03): Space Grotesk for the
// wordmark and section heads, JetBrains Mono for anything that reads as a measurement
// (captions, timestamps, version tags) — Inter stays the body/UI font, unchanged from
// every already-shipped screen.
const spaceGrotesk = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
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
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} antialiased`}>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
