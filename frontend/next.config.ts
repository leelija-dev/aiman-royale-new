import type { NextConfig } from 'next';
const backend = process.env.INTERNAL_API_URL || 'http://127.0.0.1:8000';
const cdn = process.env.MEDIA_CDN_DOMAIN;
const config: NextConfig = {
  output: 'standalone', poweredByHeader: false,
  images: { formats: ['image/avif','image/webp'], qualities: [75,85], remotePatterns: cdn ? [{ protocol:'https', hostname:cdn }] : [] },
  async rewrites() { return ['api','media','accounts','static','admin'].map(path => ({source:`/${path}/:path*`,destination:`${backend}/${path}/:path*`})); },
  async headers() { return [{source:'/:path*',headers:[{key:'X-Content-Type-Options',value:'nosniff'},{key:'Referrer-Policy',value:'strict-origin-when-cross-origin'},{key:'X-Frame-Options',value:'SAMEORIGIN'},{key:'Permissions-Policy',value:'camera=(), microphone=(), geolocation=()'}]}]; }
};
export default config;
