"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <CopilotSidebar
        labels={{
          title: "Scoped Copilot",
          initial:
            "I can help you navigate the worklist, PA packets, and eval dashboard. I don't diagnose and I don't approve anything on your behalf — a nurse or physician always signs those.",
        }}
        defaultOpen={false}
        clickOutsideToClose
      >
        {children}
      </CopilotSidebar>
    </CopilotKit>
  );
}
