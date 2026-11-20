import type { Metadata } from "next";

import ChatWorkspace from "@/components/chat-workspace";

export const metadata: Metadata = {
  title: "Chat | TAL",
  description: "Your evidence-led career workspace",
};

export default function ChatPage() {
  const host = new URL(
    process.env.TAL_CHAT_URL ?? process.env.TAL_API_URL ?? "http://127.0.0.1:8787",
  ).host;
  return <ChatWorkspace host={host} />;
}
