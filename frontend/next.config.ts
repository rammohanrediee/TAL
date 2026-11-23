import type { NextConfig } from "next";

const apiUrl = process.env.TAL_API_URL ?? "http://127.0.0.1:8000";
const chatUrl = process.env.TAL_CHAT_URL ?? process.env.TAL_API_URL ?? "http://127.0.0.1:8787";
const publicChatUrl =
  process.env.NEXT_PUBLIC_TAL_CHAT_URL ?? process.env.TAL_CHAT_URL ?? process.env.TAL_API_URL ?? "";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_TAL_CHAT_URL: publicChatUrl,
  },
  transpilePackages: ["@astryxdesign/core"],
  devIndicators: false,
  turbopack: { root: __dirname },
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
      {
        source: "/agents/:path*",
        destination: `${chatUrl}/agents/:path*`,
      },
    ];
  },
};

export default nextConfig;
