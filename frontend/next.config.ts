import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pins the workspace root to this directory — without it, Turbopack walks up and
  // picks up an unrelated lockfile at C:\Users\Asus\package-lock.json, since this repo
  // isn't (yet) a JS monorepo with its own root lockfile.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
