import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output stays in `build/` so the existing Dockerfile/nginx (which serve
// /app/build) keep working unchanged.
export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  build: { outDir: "build" },
});
