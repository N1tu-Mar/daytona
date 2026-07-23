// CopilotKit runtime endpoint. Runs server-side only (no NEXT_PUBLIC_* keys
// involved — invariant: no backend API keys ship to the client).
//
// The demo doesn't wire the copilot to a real LLM yet (no Fireworks/OpenAI
// key is provisioned for the frontend), so this uses EmptyAdapter: it keeps
// the CopilotKit provider + sidebar chrome real and functioning rather than
// a commented-out stub, without pretending to answer clinical questions.
// Swapping in a real adapter later is a one-line change here.
import {
  CopilotRuntime,
  EmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

const runtime = new CopilotRuntime();
const serviceAdapter = new EmptyAdapter();

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
