// Next.js server-startup hook (runs once when the server boots).
//
// instrumentation.ts is evaluated in every runtime (Node.js and Edge). The
// actual fail-safe uses `process.on`, a Node-only API, so it lives in
// ./instrumentation-node and is dynamically imported ONLY under the Node
// runtime. Keeping it out of this module is what prevents Turbopack from
// bundling `process.on` into the Edge runtime (and warning about it).
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { registerNode } = await import("./instrumentation-node");
    registerNode();
  }
}
