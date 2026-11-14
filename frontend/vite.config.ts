import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Geliştirme: npm run dev → API istekleri backend'e (localhost:8000) yönlendirilir.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/mcp": "http://localhost:8000",
    },
  },
  build: { outDir: "dist", chunkSizeWarningLimit: 1200 },
});
