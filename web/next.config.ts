import type { NextConfig } from "next";

// Xuất tĩnh vào web/out; FastAPI phục vụ bản build này cùng /api (ADR-001).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
};

export default nextConfig;
