// next.config.ts
import type { NextConfig } from "next";
const config: NextConfig = {
  output: "standalone",
  images: { domains: ["educat.ai", "lh3.googleusercontent.com"] },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_BASE_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};
export default config;
