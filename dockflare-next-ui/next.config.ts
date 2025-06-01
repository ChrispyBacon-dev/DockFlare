// dockflare-next-ui/next.config.ts

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone', // Add this line
  // You can add other Next.js configurations here if needed in the future
  // For example:
  // reactStrictMode: true,
  // images: {
  //   domains: ['example.com'], // If you use external images with next/image
  // },
};

export default nextConfig;