import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const apiTarget = process.env.VITE_API_PROXY || "http://127.0.0.1:8010";

export default defineConfig({
  plugins: [tailwindcss(), react()],
  server: {
    host: "127.0.0.1",
    port: 8502,
    proxy: {
      "/chat": { target: apiTarget, changeOrigin: true },
      "/config": { target: apiTarget, changeOrigin: true },
      "/feedback": { target: apiTarget, changeOrigin: true },
      "/health": { target: apiTarget, changeOrigin: true },
      "/ingest": { target: apiTarget, changeOrigin: true, timeout: 300_000 },
      "/debug": { target: apiTarget, changeOrigin: true },
      "/admin/feedback": { target: apiTarget, changeOrigin: true },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes("node_modules/react-dom") || id.includes("node_modules/react/")) return "vendor";
          if (id.includes("node_modules/react-markdown") || id.includes("node_modules/remark-gfm")) return "markdown";
          if (id.includes("node_modules/")) return "libs";
        },
      },
    },
  },
});
