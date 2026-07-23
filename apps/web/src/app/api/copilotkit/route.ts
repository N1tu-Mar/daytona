// CopilotKit runtime endpoint — intentionally inert.
//
// The app no longer mounts a CopilotKit provider (see src/components/Providers.tsx),
// so nothing in the app calls this route. It's kept only so that a stale
// browser tab from an older build that still POSTs here gets a clean, valid
// response instead of hitting a runtime that throws `CopilotApiDiscoveryError`
// and crashes the server process.
//
// To restore a real copilot: reinstate the CopilotRuntime + a real LLM
// adapter here (see git history for the previous EmptyAdapter version) and
// re-mount <CopilotKit> in Providers.tsx.
import { NextResponse } from "next/server";

export const POST = async () => {
  return NextResponse.json({ data: null }, { status: 200 });
};

export const GET = async () => {
  return NextResponse.json({ status: "copilot runtime disabled in demo" }, { status: 200 });
};
