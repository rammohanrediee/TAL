import type { Metadata } from "next";

import TalWorkspace from "@/components/tal-workspace";

export const metadata: Metadata = {
  title: "Chat | TAL",
  description: "Your evidence-led career workspace",
};

export default function ChatPage() {
  return <TalWorkspace />;
}
