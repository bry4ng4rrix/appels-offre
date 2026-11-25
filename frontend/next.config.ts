import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Image Docker legere : server.js et ses seules dependances (voir Dockerfile).
  output: "standalone",
  // Quelques PNG et SVG fixes : pas besoin du serveur d'optimisation (ni de sharp).
  images: { unoptimized: true },
  experimental: {
    agentFeedback: true,
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
