import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Frontend → Backend → External services. No proxying/rewrites: the app
  // calls the FastAPI backend directly with a Supabase Bearer JWT.
};

export default nextConfig;
