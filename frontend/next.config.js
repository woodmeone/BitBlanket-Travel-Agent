/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:38000/api/:path*',
      },
    ];
  },
  compress: true,
  allowedDevOrigins: ['localhost:33001'],
};

export default nextConfig;
