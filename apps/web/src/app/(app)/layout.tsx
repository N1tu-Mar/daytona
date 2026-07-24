import DemoBanner from "@/components/DemoBanner";
import NavBar from "@/components/NavBar";

// Chrome for the product pages (worklist, intake, PA packets, dashboard).
// The landing page at / has its own full-bleed dark layout, so the shared
// light app shell lives here rather than in the root layout.
export default function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <DemoBanner />
      <NavBar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">{children}</main>
      <footer className="mx-auto w-full max-w-6xl px-4 py-6 text-xs text-slate-400 sm:px-6">
        Meridian — routes referrals to the right urgency of GI appointment. It does not diagnose.
      </footer>
    </div>
  );
}
