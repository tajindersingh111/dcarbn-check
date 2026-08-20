/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'https://dcarbn-check-production.up.railway.app';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  }
};

export default nextConfig;
