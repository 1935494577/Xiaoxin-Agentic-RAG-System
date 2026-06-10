import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_API_PROXY || "http://127.0.0.1:8010";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 8502,
    proxy: {
      "/chat": { target: apiTarget, changeOrigin: true },
      "/config": { target: apiTarget, changeOrigin: true },
      "/feedback": { target: apiTarget, changeOrigin: true },
      "/health": { target: apiTarget, changeOrigin: true },
    },
  },
});
