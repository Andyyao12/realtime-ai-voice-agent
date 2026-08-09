import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Harborlight Voice Concierge",
  description: "Realtime AI voice agent engineering showcase",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
