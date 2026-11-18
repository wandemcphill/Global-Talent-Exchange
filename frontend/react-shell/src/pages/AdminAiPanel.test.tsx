import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AdminAiPanel } from "./AdminAiPanel";

declare const describe: any;
declare const it: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;
declare const jest: any;

const mockApiGet = jest.fn();
const mockApiPut = jest.fn();
const mockToastSuccess = jest.fn();
const mockToastError = jest.fn();

jest.mock("@/lib/api", () => ({
  errMsg: (error: any) => error?.message || "error",
  api: {
    get: (...args: any[]) => mockApiGet(...args),
    put: (...args: any[]) => mockApiPut(...args),
  },
}));

jest.mock("sonner", () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}));

const status = {
  integration_status: "ready",
  environment_enabled: true,
  admin_enabled: true,
  effective_enabled: true,
  api_key_configured: true,
  model: "gpt-4o-mini",
  daily_budget_usd: 25,
  monthly_budget_usd: 400,
  max_input_tokens: 2000,
  max_output_tokens: 800,
  user_requests_per_minute: 12,
  global_requests_per_minute: 300,
  legacy_clients_routed: true,
  config_errors: [],
  features: [{ feature_key: "match_report", enabled: true, audience: "user", max_requests_per_day: 200, max_output_tokens: 500, cache_ttl_seconds: 600 }],
  limits: [],
  usage: {
    today: { request_count: 4, input_tokens: 100, output_tokens: 40, estimated_cost_usd: 0.01, error_count: 1 },
    month: { request_count: 4, estimated_cost_usd: 0.01 },
    recent_errors: [{ feature: "match_report", error_code: "timeout", created_at: "2026-11-18T00:00:00Z" }],
  },
};

describe("AdminAiPanel", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPut.mockReset();
    mockApiGet.mockResolvedValue({ data: status });
    mockApiPut.mockResolvedValue({ data: status });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  async function flush() {
    for (let i = 0; i < 6; i += 1) {
      await act(async () => {
        await Promise.resolve();
      });
    }
  }

  it("shows model and usage without an API key", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await act(async () => {
      root.render(
        <QueryClientProvider client={client}>
          <AdminAiPanel />
        </QueryClientProvider>,
      );
    });
    await flush();
    expect(container.textContent).toContain("gpt-4o-mini");
    expect(container.textContent).toContain("Configured");
    expect(container.textContent).not.toContain("sk-");
    expect(mockApiGet).toHaveBeenCalledWith("/v2/admin/ai/status");

    const save = container.querySelector('[data-testid="admin-ai-save"]') as HTMLButtonElement;
    await act(async () => {
      save.click();
    });
    await flush();
    const body = mockApiPut.mock.calls[0][1];
    expect(body.api_key).toBeUndefined();
    expect(body.model).toBe("gpt-4o-mini");
  });
});
