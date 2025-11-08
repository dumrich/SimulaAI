import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Configure to handle WASM files
  webpack: (config) => {
    // Handle WASM files
    config.experiments = {
      ...config.experiments,
      asyncWebAssembly: true,
    };
    
    return config;
  },
};

export default nextConfig;
