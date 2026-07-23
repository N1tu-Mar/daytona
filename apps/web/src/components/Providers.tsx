"use client";

/**
 * App providers.
 *
 * NOTE: CopilotKit was previously mounted here, but nothing in the app was
 * actually wired to it (no `useCopilotReadable`, no `useCopilotAction`, no
 * chat component). With no LLM adapter provisioned for the frontend, the only
 * thing the CopilotKit provider did was perform a runtime/agent-discovery
 * handshake against an adapter-less (EmptyAdapter) route — which failed with
 * `CopilotApiDiscoveryError` and broke page rendering ("This page couldn't
 * load"). A provider that adds no function and breaks the app has no business
 * in the render path, so it's been removed.
 *
 * To add a real copilot later:
 *   1. Provision an LLM adapter (e.g. OpenAIAdapter with a server-side key)
 *      in src/app/api/copilotkit/route.ts.
 *   2. Wrap {children} below in:
 *        <CopilotKit runtimeUrl="/api/copilotkit"> ... </CopilotKit>
 *      and add a <CopilotSidebar/> plus useCopilotReadable() where you want
 *      the worklist/verdict data exposed.
 */
export default function Providers({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
