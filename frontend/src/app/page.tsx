import ChatWorkspace from "@/components/chat-workspace";

export default function Home() {
  const host = new URL(
    process.env.TAL_CHAT_URL ?? process.env.TAL_API_URL ?? "http://127.0.0.1:8787",
  ).host;
  return <ChatWorkspace host={host} />;
}
