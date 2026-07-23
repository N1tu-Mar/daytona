// Invariant #6: persistent, non-dismissible banner on every page. No close
// button, no localStorage-based "don't show again" — do not add one.
export default function DemoBanner() {
  return (
    <div
      role="alert"
      className="sticky top-0 z-50 w-full border-b border-red-900/20 bg-red-700 px-4 py-2 text-center text-sm font-semibold tracking-wide text-white shadow-sm"
    >
      DEMO — synthetic data. Not for clinical use.
    </div>
  );
}
