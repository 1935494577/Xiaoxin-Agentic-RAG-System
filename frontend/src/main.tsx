import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "./context/AuthContext";
import { AppShell } from "./components/layout/AppShell";
import AdminLayout from "./components/layout/AdminLayout";
import AuthEntryLayout from "./components/layout/AuthEntryLayout";
import { RequireAuth } from "./components/layout/RequireAuth";
import "./index.css";

function lazyPage(importer: () => Promise<{ default: React.ComponentType }>) {
  return () => importer().then((m) => ({ Component: m.default }));
}

const router = createBrowserRouter([
  {
    element: <AuthEntryLayout />,
    children: [
      { index: true, lazy: lazyPage(() => import("./pages/WelcomePage")) },
      { path: "login", lazy: lazyPage(() => import("./pages/LoginPage")) },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "chat", lazy: lazyPage(() => import("./pages/ChatPage")) },

          // ---- Admin: Management pages ----
          {
            path: "admin",
            element: <AdminLayout />,
            children: [
              { index: true, lazy: lazyPage(() => import("./pages/admin/IngestPage")) },
              { path: "ingest", lazy: lazyPage(() => import("./pages/admin/IngestPage")) },
              { path: "processing", lazy: lazyPage(() => import("./pages/admin/ProcessingPage")) },
              { path: "vector-store", lazy: lazyPage(() => import("./pages/admin/VectorStorePage")) },
              { path: "memory", lazy: lazyPage(() => import("./pages/admin/MemoryPage")) },
              { path: "prompts", lazy: lazyPage(() => import("./pages/admin/PromptPage")) },
              { path: "models", lazy: lazyPage(() => import("./pages/admin/ModelPage")) },
              { path: "trace", lazy: lazyPage(() => import("./pages/admin/TracePage")) },
              { path: "feedback", lazy: lazyPage(() => import("./pages/admin/FeedbackInboxPage")) },
              { path: "eval-reports", lazy: lazyPage(() => import("./pages/admin/EvalReportsPage")) },
              { path: "tutorial", lazy: lazyPage(() => import("./pages/admin/TutorialPage")) },
            ],
          },
        ],
      },
    ],
  },
  {
    path: "*",
    lazy: lazyPage(() => import("./pages/NotFoundPage")),
  },
]);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster position="top-right" richColors />
      </QueryClientProvider>
    </AuthProvider>
  </StrictMode>
);
