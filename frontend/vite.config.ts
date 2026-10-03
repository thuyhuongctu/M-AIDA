import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output stays in `build/` so the existing Dockerfile/nginx (which serve
// /app/build) keep working unchanged.
export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  // three.js (3D logo) is a separate ~560 kB chunk loaded only by the sign-in
  // page and the logo dialog; the limit is raised so that known chunk does not
  // warn on every build.
  build: { outDir: "build", chunkSizeWarningLimit: 600 },
});
