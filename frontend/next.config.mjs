/** @type {import('next').NextConfig} */
const apiBase =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const nextConfig = {
  env: {
    NEXT_PUBLIC_API_BASE: apiBase,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
