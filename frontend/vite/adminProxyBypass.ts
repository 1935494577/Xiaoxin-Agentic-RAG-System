import type { IncomingMessage } from "node:http";

/** Browser refresh on /admin/* must serve the SPA, not FastAPI (which only has /admin/feedback/* APIs). */
export function shouldServeAdminSpa(req: IncomingMessage): boolean {
  const method = (req.method || "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") return false;
  const accept = String(req.headers.accept || "");
  if (!accept.includes("text/html")) return false;
  const path = (req.url || "").split("?")[0];
  return path === "/admin" || path.startsWith("/admin/");
}
