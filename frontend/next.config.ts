import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  allowedDevOrigins: [
    '192.168.0.36',
    '192.168.18.103',
    '192.168.10.159',
    '192.168.1.5',
    'localhost',
    '127.0.0.1',
  ],
}

export default nextConfig
