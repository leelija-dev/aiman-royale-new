import type { NextConfig } from 'next';
const backend = process.env.INTERNAL_API_URL || 'http://127.0.0.1:8000';
const cdn = process.env.MEDIA_CDN_DOMAIN;
const config: NextConfig = {
  output: 'standalone', poweredByHeader: false,
  // Put the site CSS inside the HTML: removes the render-blocking stylesheet request flagged by PageSpeed.
  experimental: { inlineCss: true },
  // Django API endpoints require their trailing slash, including CSRF and login.
  skipTrailingSlashRedirect: true,
  images: { formats: ['image/avif','image/webp'], imageSizes: [32,48,64,96,128,256,384,480], qualities: [75,85,88,92], remotePatterns: cdn ? [{ protocol:'https', hostname:cdn }] : [] },
  async rewrites() { return ['api','media','accounts','static','admin'].map(path => ({source:`/${path}/:path*`,destination:`${backend}/${path}/:path*${['api','accounts','admin'].includes(path)?'/':''}`})); },
  async headers() { return [{source:'/:path*',headers:[{key:'X-Content-Type-Options',value:'nosniff'},{key:'Referrer-Policy',value:'strict-origin-when-cross-origin'},{key:'X-Frame-Options',value:'SAMEORIGIN'},{key:'Permissions-Policy',value:'camera=(), microphone=(), geolocation=()'}]}]; }, 
  allowedDevOrigins: cdn ? [`https://${cdn}`] : ["0.0.0.0", "169.254.101.90", "172.18.99.117", "localhost"]
};
export default config;
