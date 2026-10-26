/** @type {import('next').NextConfig} */
const backendUrl =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://92.5.149.29";

const nextConfig = {
  env: {
    // If NEXT_PUBLIC_API_BASE is set, use it; otherwise use relative path so Vercel proxies through rewrites
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "",
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
