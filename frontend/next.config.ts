import type { NextConfig } from "next";

const repositoryName = process.env.GITHUB_REPOSITORY?.split("/")[1] ?? "MINI-DNS-SERVER-WITH-LIVE-CACHING-ANALYTICS-";
const basePath = process.env.GITHUB_ACTIONS ? `/${repositoryName}` : "";

const nextConfig: NextConfig = {
	output: "export",
	basePath,
	assetPrefix: basePath ? `${basePath}/` : undefined,
	trailingSlash: true,
	images: { unoptimized: true },
};

export default nextConfig;
