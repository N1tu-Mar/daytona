// Node.js-only instrumentation. Imported dynamically from instrumentation.ts
// ONLY when NEXT_RUNTIME === "nodejs", so `process.on` (a Node-only API) never
// gets bundled into the Edge runtime.
//
// Purpose: a fail-safe net so the demo server can never be killed by an
// unhandled promise rejection mid-presentation. The one known source is
// CopilotKit's runtime: an agent-discovery request against our adapter-less
// (EmptyAdapter) runtime rejects with `CopilotApiDiscoveryError` on an async
// path that a route-level try/catch can't capture. In Node, an unhandled
// rejection can terminate the process — which previously took every page down
// with "This page couldn't load".
//
// We swallow exactly that expected CopilotKit rejection, and for anything
// else we log loudly but still keep the process up (a demo server should
// degrade, not crash).
export function registerNode() {
  process.on("unhandledRejection", (reason: unknown) => {
    const name =
      reason && typeof reason === "object" && "name" in reason
        ? String((reason as { name?: unknown }).name)
        : undefined;
    const message = reason instanceof Error ? reason.message : String(reason);

    if (name === "CopilotError" || /No default agent provided/i.test(message)) {
      console.warn(
        "[copilotkit] swallowed expected adapter-less runtime rejection:",
        message,
      );
      return;
    }

    // Unexpected rejection: surface it, but don't hard-crash the demo server.
    console.error("[unhandledRejection]", reason);
  });
}
