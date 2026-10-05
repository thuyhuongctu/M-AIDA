import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output stays in `build/` so the existing Dockerfile/nginx (which serve
// /app/build) keep working unchanged.
export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  // Two known large chunks, both loaded with import() only when needed:
  // three.js (~730 kB: 3D logo and the Cosmos sky) and the Natural Earth map
  // of the Cosmos Earth (~760 kB, world-atlas countries-50m). The limit is
  // raised so these do not warn on every build.
  build: { outDir: "build", chunkSizeWarningLimit: 800 },
});
