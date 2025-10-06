import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  images: {
    remotePatterns: [
      new URL("https://picsum.photos/**"),
      new URL("https://wizeline.atlassian.net/**"),
      new URL("https://bytescribe-image-audio-bucket.s3.ap-southeast-2.amazonaws.com/**")
    ],
  },
};

export default nextConfig;
