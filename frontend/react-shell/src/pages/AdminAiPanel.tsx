import React, { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { Btn, Chip, Loading, Panel, Stat } from "@/components/gtex/ui";

type AiFeature = {
  feature_key: string;
  enabled: boolean;
  audience: string;
  max_requests_per_day: number;
  max_output_tokens: number;
  cache_ttl_seconds: number;
};

type AiStatus = {
  integration_status: string;
  environment_enabled: boolean;
  admin_enabled: boolean;
  effective_enabled: boolean;
  api_key_configured: boolean;
  model: string;
  daily_budget_usd: number;
  monthly_budget_usd: number;
  max_input_tokens: number;
  max_output_tokens: number;
  user_requests_per_minute: number;
  global_requests_per_minute: number;
  legacy_clients_routed: boolean;
  config_errors: string[];
  features: AiFeature[];
  limits: { subject_type: string; subject_key: string; max_requests: number; window_seconds: number }[];
  usage: {
    today?: { request_count: number; input_tokens: number; output_tokens: number; estimated_cost_usd: number; error_count: number };
    month?: { request_count: number; estimated_cost_usd: number };
    recent_errors?: { feature: string; error_code: string | null; created_at: string }[];
  };
};

const EMPTY: AiStatus = {
  integration_status: "disabled",
  environment_enabled: false,
  admin_enabled: true,
  effective_enabled: false,
  api_key_configured: false,
  model: "",
  daily_budget_usd: 25,
  monthly_budget_usd: 400,
  max_input_tokens: 2000,
  max_output_tokens: 800,
  user_requests_per_minute: 12,
  global_requests_per_minute: 300,
  legacy_clients_routed: false,
  config_errors: [],
  features: [],
  limits: [],
  usage: {},
};

export function AdminAiPanel() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin-ai-status"],
    queryFn: async () => (await api.get("/v2/admin/ai/status")).data as AiStatus,
  });
  const status = data || EMPTY;
  const [enabled, setEnabled] = useState(true);
  const [dailyBudget, setDailyBudget] = useState("25");
  const [monthlyBudget, setMonthlyBudget] = useState("400");
  const [userRpm, setUserRpm] = useState("12");
  const [saving, setSaving] = useState(false);
  const [limitUser, setLimitUser] = useState("");
  const [limitMax, setLimitMax] = useState("6");

  useEffect(() => {
    if (!data) return;
    setEnabled(data.admin_enabled);
    setDailyBudget(String(data.daily_budget_usd ?? 25));
    setMonthlyBudget(String(data.monthly_budget_usd ?? 400));
    setUserRpm(String(data.user_requests_per_minute ?? 12));
  }, [data]);

  const saveSettings = async () => {
    setSaving(true);
    try {
      await api.put("/v2/admin/ai/settings", {
        enabled,
        model: status.model || null,
        daily_budget_usd: Number(dailyBudget),
        monthly_budget_usd: Number(monthlyBudget),
        max_input_tokens: status.max_input_tokens,
        max_output_tokens: status.max_output_tokens,
        user_requests_per_minute: Number(userRpm),
        global_requests_per_minute: status.global_requests_per_minute,
      });
      toast.success("AI settings saved.");
      await qc.invalidateQueries({ queryKey: ["admin-ai-status"] });
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  const toggleFeature = async (feature: AiFeature) => {
    try {
      await api.put(`/v2/admin/ai/features/${feature.feature_key}`, {
        enabled: !feature.enabled,
        max_requests_per_day: feature.max_requests_per_day,
        max_output_tokens: feature.max_output_tokens,
        cache_ttl_seconds: feature.cache_ttl_seconds,
      });
      await qc.invalidateQueries({ queryKey: ["admin-ai-status"] });
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  const saveUserLimit = async () => {
    if (!limitUser.trim()) return;
    try {
      await api.put("/v2/admin/ai/limits", {
        subject_type: "user",
        subject_key: limitUser.trim(),
        max_requests: Number(limitMax),
        window_seconds: 60,
      });
      setLimitUser("");
      toast.success("User limit saved.");
      await qc.invalidateQueries({ queryKey: ["admin-ai-status"] });
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  if (isLoading) return <Loading />;

  const today = status.usage?.today;
  const month = status.usage?.month;
  const errors = status.usage?.recent_errors || [];
  const tone = status.integration_status === "ready" ? "emerald" : status.integration_status === "misconfigured" ? "red" : "slate";

  return (
    <div className="space-y-6" data-testid="admin-ai-panel">
      <Panel eyebrow="OpenAI" title="AI configuration" testid="admin-ai-status">
        <p className="text-sm text-slate-300">
          The API key stays on the server. This desk can turn features on or off, but it cannot view or change the key.
          AI text is a recommendation. It does not move coin, change ownership, or rewrite results.
        </p>
        {isError && <p className="mt-3 text-sm text-red-300">AI status could not be loaded.</p>}
        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Integration" value={<Chip tone={tone}>{status.integration_status.replace(/_/g, " ")}</Chip>} />
          <Stat label="Model" value={status.model || "Not set"} />
          <Stat label="Key on server" value={status.api_key_configured ? "Configured" : "Missing"} />
          <Stat label="Requests today" value={String(today?.request_count ?? 0)} />
          <Stat label="Input tokens today" value={String(today?.input_tokens ?? 0)} />
          <Stat label="Output tokens today" value={String(today?.output_tokens ?? 0)} />
          <Stat label="Estimated spend today" value={`$${Number(today?.estimated_cost_usd ?? 0).toFixed(4)}`} />
          <Stat label="Estimated spend this month" value={`$${Number(month?.estimated_cost_usd ?? 0).toFixed(4)}`} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-400">
          <Chip tone={status.environment_enabled ? "emerald" : "slate"}>Server flag {status.environment_enabled ? "on" : "off"}</Chip>
          <Chip tone={status.legacy_clients_routed ? "blue" : "slate"}>
            Legacy clients {status.legacy_clients_routed ? "use the gateway" : "keep their own HTTP client"}
          </Chip>
          <Chip>Errors today {today?.error_count ?? 0}</Chip>
        </div>
        {status.config_errors?.length > 0 && (
          <ul className="mt-3 list-disc pl-5 text-sm text-red-300" data-testid="admin-ai-config-errors">
            {status.config_errors.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel eyebrow="Safeguards" title="Limits and budget" testid="admin-ai-limits">
        <div className="grid gap-3 md:grid-cols-4">
          <label className="text-xs text-slate-300">
            Admin switch
            <select className="gx-input mt-1" value={enabled ? "on" : "off"} onChange={(event) => setEnabled(event.target.value === "on")} data-testid="admin-ai-enabled">
              <option value="on">Enabled</option>
              <option value="off">Disabled</option>
            </select>
          </label>
          <label className="text-xs text-slate-300">
            Daily budget (USD)
            <input className="gx-input mt-1" value={dailyBudget} onChange={(event) => setDailyBudget(event.target.value)} data-testid="admin-ai-daily-budget" />
          </label>
          <label className="text-xs text-slate-300">
            Monthly budget (USD)
            <input className="gx-input mt-1" value={monthlyBudget} onChange={(event) => setMonthlyBudget(event.target.value)} data-testid="admin-ai-monthly-budget" />
          </label>
          <label className="text-xs text-slate-300">
            Requests per user / minute
            <input className="gx-input mt-1" value={userRpm} onChange={(event) => setUserRpm(event.target.value)} data-testid="admin-ai-user-rpm" />
          </label>
        </div>
        <div className="mt-3">
          <Btn onClick={saveSettings} disabled={saving} data-testid="admin-ai-save">
            {saving ? "Saving" : "Save AI settings"}
          </Btn>
        </div>
        <div className="mt-4 flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-300">
            Per-user cap
            <input className="gx-input mt-1" placeholder="User id" value={limitUser} onChange={(event) => setLimitUser(event.target.value)} data-testid="admin-ai-limit-user" />
          </label>
          <label className="text-xs text-slate-300">
            Max / window
            <input className="gx-input mt-1" value={limitMax} onChange={(event) => setLimitMax(event.target.value)} data-testid="admin-ai-limit-max" />
          </label>
          <Btn variant="secondary" onClick={saveUserLimit} data-testid="admin-ai-limit-save">
            Save user limit
          </Btn>
        </div>
        {status.limits?.length > 0 && (
          <ul className="mt-3 text-sm text-slate-300">
            {status.limits.map((limit) => (
              <li key={`${limit.subject_type}:${limit.subject_key}`}>
                {limit.subject_type} {limit.subject_key}: {limit.max_requests} / {limit.window_seconds}s
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel eyebrow="Features" title="What AI is allowed to draft" testid="admin-ai-features">
        <div className="grid gap-2 md:grid-cols-2">
          {status.features.map((feature) => (
            <button
              key={feature.feature_key}
              type="button"
              className="flex items-center justify-between rounded-sm border border-white/10 px-3 py-2 text-left text-sm"
              onClick={() => toggleFeature(feature)}
              data-testid={`admin-ai-feature-${feature.feature_key}`}
            >
              <span>
                <span className="text-white">{feature.feature_key.replace(/_/g, " ")}</span>
                <span className="ml-2 text-xs text-slate-500">{feature.audience}</span>
              </span>
              <Chip tone={feature.enabled ? "emerald" : "slate"}>{feature.enabled ? "On" : "Off"}</Chip>
            </button>
          ))}
        </div>
      </Panel>

      <Panel eyebrow="Failures" title="Recent AI errors" testid="admin-ai-errors">
        {errors.length === 0 ? (
          <p className="text-sm text-slate-500">No failed AI requests in this view.</p>
        ) : (
          <ul className="space-y-2 text-sm text-slate-300">
            {errors.map((item, index) => (
              <li key={`${item.created_at}-${index}`}>
                {item.feature}: {item.error_code || item.created_at}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
