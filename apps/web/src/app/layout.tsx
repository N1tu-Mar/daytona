import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import DemoBanner from "@/components/DemoBanner";
import NavBar from "@/components/NavBar";
import Providers from "@/components/Providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Meridian — referral triage, not diagnosis",
  description:
    "An agent that moves a patient from 'something's wrong' to a booked colonoscopy with prior auth approved. DEMO — synthetic data. Not for clinical use.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <Providers>
          <DemoBanner />
          <NavBar />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
            {children}
          </main>
          <footer className="mx-auto w-full max-w-6xl px-4 py-6 text-xs text-slate-400 sm:px-6">
            Meridian — routes referrals to the right urgency of GI appointment. It does not diagnose.
          </footer>
        </Providers>
      </body>
    </html>
  );
}
