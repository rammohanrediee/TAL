import type { Metadata } from "next";

import ProofWorkspace from "@/components/proof-workspace";

export const metadata: Metadata = {
  title: "Chat | TAL",
  description: "Your evidence-led career workspace",
};

export default function ChatPage() {
  return <ProofWorkspace />;
}
