import path from "node:path";
import type { ProxyOptions } from "vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { shouldServeAdminSpa } from "./vite/adminProxyBypass";

const apiTarget = process.env.VITE_API_PROXY || "http://127.0.0.1:8010";
const devHost = process.env.VITE_DEV_HOST || "127.0.0.1";

function apiProxy(extra: ProxyOptions = {}): ProxyOptions {
  return {
    target: apiTarget,
    changeOrigin: true,
    ...extra,
  };
}

/** LAN dev: avoid buffering SSE so colleagues see the same streaming UX as localhost. */
function sseProxy(): ProxyOptions {
  return apiProxy({
    timeout: 0,
    proxyTimeout: 0,
    configure: (proxy) => {
      proxy.on("proxyRes", (proxyRes) => {
        const ct = proxyRes.headers["content-type"];
        if (ct && String(ct).includes("text/event-stream")) {
          proxyRes.headers["cache-control"] = "no-cache, no-transform";
          proxyRes.headers["x-accel-buffering"] = "no";
        }
      });
    },
  });
}

function adminApiProxy(): ProxyOptions {
  return apiProxy({
    bypass(req) {
      if (shouldServeAdminSpa(req)) return false;
    },
  });
}

export default defineConfig({
  plugins: [tailwindcss(), react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: devHost,
    port: 8502,
    proxy: {
      // API only — do NOT proxy GET /chat (React Router SPA route)
      "/chat/sessions": apiProxy(),
      "/chat/documents": apiProxy({ timeout: 300_000 }),
      "/chat/stream": sseProxy(),
      "/chat/transcribe": apiProxy({ timeout: 120_000 }),
      "/users": apiProxy(),
      "/config": apiProxy(),
      "/feedback": apiProxy(),
      "/health": apiProxy(),
      "/ingest": apiProxy({ timeout: 300_000 }),
      "/debug": apiProxy(),
      "/sources": apiProxy(),
      "/retrieve": apiProxy(),
      "/admin": adminApiProxy(),
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
