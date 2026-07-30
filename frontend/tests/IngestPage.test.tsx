import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import IngestPage, { resolveIngestChannel } from "../src/pages/admin/IngestPage";

vi.mock("../src/api/client", () => ({
  fetchUiConfig: async () => ({
    ingest_tag_presets: ["测试"],
    supported_upload_extensions: ["pdf", "docx"],
  }),
  uploadDocument: vi.fn(),
}));

vi.mock("../src/components/admin/IngestedSourcesTab", () => ({
  IngestedSourcesTab: () => <div>sources-tab</div>,
}));

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/admin/ingest" element={<IngestPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("resolveIngestChannel", () => {
  it("defaults to kb", () => {
    expect(resolveIngestChannel(null)).toBe("kb");
    expect(resolveIngestChannel("foo")).toBe("kb");
  });
  it("accepts exam", () => {
    expect(resolveIngestChannel("exam")).toBe("exam");
  });
});

describe("IngestPage channels", () => {
  it("shows exam channel CTA when ?channel=exam", () => {
    renderAt("/admin/ingest?channel=exam");
    expect(screen.getByTestId("exam-ingest-channel")).toBeTruthy();
    const cta = screen.getByTestId("exam-ingest-cta");
    expect(cta.getAttribute("href")).toBe("/admin/exam-bank/ingest?step=1");
  });

  it("shows knowledge upload on default channel", () => {
    renderAt("/admin/ingest");
    expect(screen.getByText("上传入库")).toBeTruthy();
    expect(screen.queryByTestId("exam-ingest-channel")).toBeNull();
  });
});
