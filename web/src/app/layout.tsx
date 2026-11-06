import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sonar // Acoustic Side-Channel Security & Forensics Suite",
  description: "Local-first acoustic geolocation detection, active privacy cloaking, and spatiotemporal alibi forensics.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-sonar-bg text-sonar-text min-h-screen font-sans antialiased selection:bg-sonar-cyan/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
