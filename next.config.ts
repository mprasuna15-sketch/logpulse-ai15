import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    /* config options here */
    serverExternalPackages: [], 
    // Moving turbopack to top-level if experimental is rejected
    // and ensuring root is correctly set to silence warnings
    experimental: {
       // Using the structure that silences the workspace root warning
    },
    // Custom handling for turbopack based on the warning provided by the user
    logging: {
        fetches: {
            fullUrl: true,
        },
    },
};

// Some Next.js versions expect this at the top level, others under experimental.
// Based on the error "turbopack (invalid experimental key)", we try moving it.
(nextConfig as any).turbopack = {
    root: __dirname,
};

export default nextConfig;
