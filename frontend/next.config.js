/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    const internalApiBase = process.env.INTERNAL_API_BASE || 'http://localhost:38000';
    return [
      {
        source: '/api/:path*',
        destination: `${internalApiBase}/api/:path*`,
      },
    ];
  },
  compress: true,
  allowedDevOrigins: ['localhost:33001'],
};

export default nextConfig;
