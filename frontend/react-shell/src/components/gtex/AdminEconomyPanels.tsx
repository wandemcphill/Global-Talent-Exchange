import React, { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Panel } from "@/components/gtex/ui";
import { CoinTraderAdminExtras } from "@/components/gtex/coin-traders/CoinTraderAdminExtras";

type CoinUnit = "coin" | "credit";

interface AdminUserSummary {
  id: string;
  email: string;
  username: string;
  display_name?: string | null;
  role?: string;
  kyc_status?: string | null;
  is_active?: boolean;
}

function makeIdempotencyKey(prefix: string): string {
  const randomPart =
    typeof globalThis !== "undefined" && globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
      ? globalThis.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  return `${prefix}-${randomPart}`;
}

function unitDisplay(unit: CoinUnit): string {
  return unit === "coin" ? "GTEX Coin (GTC)" : "Fan Coin (FNC)";
}

function UserSearchSelector({
  labelText,
  selectedUser,
  manualUserId,
  onSelectUser,
  onManualUserIdChange,
  testIdPrefix,
}: {
  labelText: string;
  selectedUser: AdminUserSummary | null;
  manualUserId: string;
  onSelectUser: (user: AdminUserSummary) => void;
  onManualUserIdChange: (value: string) => void;
  testIdPrefix: string;
}) {
  const [search, setSearch] = useState("");
  const { data: users = [], isFetching } = useQuery<AdminUserSummary[]>({
    queryKey: ["admin-finance-users", testIdPrefix, search],
    queryFn: async () => {
      try {
        const res = await api.get(`/admin/finance/users?search=${encodeURIComponent(search)}&limit=12`);
        return Array.isArray(res.data) ? res.data : [];
      } catch {
        return [];
      }
    },
  });

  return (
    <div className="space-y-1.5">
      <label className="gx-label">{labelText}</label>
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          className="gx-input text-xs"
          placeholder="Search email, username or ID"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          data-testid={`${testIdPrefix}-search-input`}
        />
        <input
          className="gx-input text-xs gx-mono"
          placeholder="Selected or manual user ID"
          value={manualUserId}
          onChange={(e) => onManualUserIdChange(e.target.value)}
          data-testid={`${testIdPrefix}-id-input`}
        />
      </div>
      {selectedUser && (
        <p className="text-[11px] text-emerald-300" data-testid={`${testIdPrefix}-selected-summary`}>
          Selected: <b>{selectedUser.display_name || selectedUser.username}</b> ({selectedUser.email})
        </p>
      )}
      {isFetching ? (
        <p className="text-[11px] text-slate-400">Searching accounts…</p>
      ) : (
        users.length > 0 && (
          <div className="max-h-28 space-y-1 overflow-y-auto rounded-md border border-white/10 bg-black/30 p-1.5">
            {users.map((u) => {
              const active = manualUserId === u.id;
              return (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => onSelectUser(u)}
                  data-testid={`${testIdPrefix}-option-${u.id}`}
                  className={`flex w-full items-center justify-between rounded px-2 py-1 text-left text-xs transition-colors ${
                    active ? "bg-emerald-500/20 text-emerald-200 border border-emerald-400/40" : "text-slate-300 hover:bg-white/5"
                  }`}
                >
                  <span className="truncate">{u.display_name || u.username} · {u.email}</span>
                  <span className="gx-mono text-[10px] text-slate-400">{u.role || "user"}</span>
                </button>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}

export function AdminWalletAndPointsPanel() {
  const qc = useQueryClient();

  // Give someone coin state
  const [creditUser, setCreditUser] = useState<AdminUserSummary | null>(null);
  const [creditUserId, setCreditUserId] = useState("");
  const [creditUnit, setCreditUnit] = useState<CoinUnit>("coin");
  const [creditAmount, setCreditAmount] = useState("100");
  const [creditReason, setCreditReason] = useState("Admin ecosystem wallet allocation");
  const [creditBusy, setCreditBusy] = useState(false);
  const [creditResult, setCreditResult] = useState<any>(null);

  // Transfer between users state
  const [fromUser, setFromUser] = useState<AdminUserSummary | null>(null);
  const [fromUserId, setFromUserId] = useState("");
  const [toUser, setToUser] = useState<AdminUserSummary | null>(null);
  const [toUserId, setToUserId] = useState("");
  const [transferUnit, setTransferUnit] = useState<CoinUnit>("coin");
  const [transferAmount, setTransferAmount] = useState("25");
  const [transferReason, setTransferReason] = useState("Admin verified desk wallet transfer");
  const [transferBusy, setTransferBusy] = useState(false);
  const [transferResult, setTransferResult] = useState<any>(null);

  // Grant personal user points state
  const [pointsUser, setPointsUser] = useState<AdminUserSummary | null>(null);
  const [pointsUserId, setPointsUserId] = useState("");
  const [pointsAmount, setPointsAmount] = useState("50");
  const [pointsReason, setPointsReason] = useState("Admin personal engagement reward");
  const [pointsBusy, setPointsBusy] = useState(false);
  const [pointsResult, setPointsResult] = useState<any>(null);

  const resolvedPointsUserId = useMemo(() => (pointsUser?.id || pointsUserId).trim(), [pointsUser, pointsUserId]);
  const { data: selectedUserPoints, refetch: refetchUserPoints } = useQuery<any>({
    queryKey: ["admin-user-points", resolvedPointsUserId],
    enabled: Boolean(resolvedPointsUserId),
    queryFn: async () => {
      try {
        return (await api.get(`/admin/god-mode/users/${encodeURIComponent(resolvedPointsUserId)}/points`)).data;
      } catch {
        return null;
      }
    },
  });

  const invalidateAdminEconomy = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["admin"] }),
      qc.invalidateQueries({ queryKey: ["admin-god-mode-bootstrap"] }),
    ]);
  };

  const handleGiveCoin = async () => {
    const userId = (creditUser?.id || creditUserId).trim();
    const numericAmount = Number(creditAmount);
    if (!userId) return toast.error("Select or enter a target user first.");
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) return toast.error("Amount must be greater than zero.");
    if (creditReason.trim().length < 4) return toast.error("Reason must be at least 4 characters.");
    setCreditBusy(true);
    try {
      const { data } = await api.post("/admin/god-mode/wallets/credit", {
        user_id: userId,
        unit: creditUnit,
        amount: numericAmount,
        reason: creditReason.trim(),
        idempotency_key: makeIdempotencyKey("admin-credit"),
      });
      setCreditResult(data);
      toast.success(`Credited ${data.amount} ${creditUnit === "coin" ? "GTC" : "FNC"} to ${data.username || data.user_id}.`);
      await invalidateAdminEconomy();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setCreditBusy(false);
    }
  };

  const handleTransferCoin = async () => {
    const sourceId = (fromUser?.id || fromUserId).trim();
    const destId = (toUser?.id || toUserId).trim();
    const numericAmount = Number(transferAmount);
    if (!sourceId || !destId) return toast.error("Select both source and destination users.");
    if (sourceId === destId) return toast.error("Source and destination users must be different.");
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) return toast.error("Transfer amount must be greater than zero.");
    if (transferReason.trim().length < 4) return toast.error("Reason must be at least 4 characters.");
    setTransferBusy(true);
    try {
      const { data } = await api.post("/admin/god-mode/wallets/transfer", {
        from_user_id: sourceId,
        to_user_id: destId,
        unit: transferUnit,
        amount: numericAmount,
        reason: transferReason.trim(),
        idempotency_key: makeIdempotencyKey("admin-transfer"),
      });
      setTransferResult(data);
      toast.success(`Transferred ${data.amount} ${transferUnit === "coin" ? "GTC" : "FNC"} successfully.`);
      await invalidateAdminEconomy();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setTransferBusy(false);
    }
  };

  const handleGrantPoints = async () => {
    const userId = resolvedPointsUserId;
    const numericAmount = Number(pointsAmount);
    if (!userId) return toast.error("Select or enter a target user first.");
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) return toast.error("Points amount must be greater than zero.");
    if (pointsReason.trim().length < 4) return toast.error("Reason must be at least 4 characters.");
    setPointsBusy(true);
    try {
      const { data } = await api.post("/admin/god-mode/points/grant", {
        user_id: userId,
        amount: numericAmount,
        reason: pointsReason.trim(),
        idempotency_key: makeIdempotencyKey("admin-points"),
      });
      setPointsResult(data);
      toast.success(`Granted ${data.amount} personal reward points.`);
      await Promise.all([refetchUserPoints(), invalidateAdminEconomy()]);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setPointsBusy(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-economy-operations-panel">
      {/* 1. Give someone coin */}
      <Panel eyebrow="Direct Mint & Wallet Credit" title="Give someone coin (GTEX Coin or Fan Coin)" testid="admin-give-coin-panel">
        <div className="space-y-3">
          <UserSearchSelector
            labelText="Recipient account"
            selectedUser={creditUser}
            manualUserId={creditUserId}
            onSelectUser={(u) => {
              setCreditUser(u);
              setCreditUserId(u.id);
            }}
            onManualUserIdChange={(value) => {
              setCreditUser(null);
              setCreditUserId(value);
            }}
            testIdPrefix="give-coin-user"
          />
          <div className="grid gap-3 md:grid-cols-4">
            <div>
              <label className="gx-label">Unit</label>
              <select
                className="gx-input"
                value={creditUnit}
                onChange={(e) => setCreditUnit(e.target.value as CoinUnit)}
                data-testid="give-coin-unit-select"
              >
                <option value="coin">GTEX Coin (GTC)</option>
                <option value="credit">Fan Coin (FNC)</option>
              </select>
            </div>
            <div>
              <label className="gx-label">Amount</label>
              <input
                type="number"
                min="0.0001"
                step="any"
                className="gx-input"
                value={creditAmount}
                onChange={(e) => setCreditAmount(e.target.value)}
                data-testid="give-coin-amount-input"
              />
            </div>
            <div className="md:col-span-2">
              <label className="gx-label">Audit reason</label>
              <input
                className="gx-input"
                value={creditReason}
                onChange={(e) => setCreditReason(e.target.value)}
                data-testid="give-coin-reason-input"
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-slate-400">Crediting {unitDisplay(creditUnit)} via double-entry operations ledger.</span>
            <Btn onClick={handleGiveCoin} disabled={creditBusy} data-testid="give-coin-submit-btn">
              {creditBusy ? "Crediting…" : `Give ${creditUnit === "coin" ? "GTEX Coin" : "Fan Coin"}`}
            </Btn>
          </div>
          {creditResult && (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-200" data-testid="give-coin-result">
              Tx <span className="gx-mono">{creditResult.transaction_id}</span> · Before: <b>{fmt(creditResult.balance_before)}</b> → After: <b>{fmt(creditResult.balance_after)}</b>
            </div>
          )}
        </div>
      </Panel>

      {/* 2. Transfer coin between users */}
      <Panel eyebrow="P2P Desk Correction" title="Transfer coin between users" testid="admin-transfer-coin-panel">
        <div className="space-y-3">
          <div className="grid gap-4 md:grid-cols-2">
            <UserSearchSelector
              labelText="From user"
              selectedUser={fromUser}
              manualUserId={fromUserId}
              onSelectUser={(u) => {
                setFromUser(u);
                setFromUserId(u.id);
              }}
              onManualUserIdChange={(value) => {
                setFromUser(null);
                setFromUserId(value);
              }}
              testIdPrefix="transfer-from-user"
            />
            <UserSearchSelector
              labelText="To user"
              selectedUser={toUser}
              manualUserId={toUserId}
              onSelectUser={(u) => {
                setToUser(u);
                setToUserId(u.id);
              }}
              onManualUserIdChange={(value) => {
                setToUser(null);
                setToUserId(value);
              }}
              testIdPrefix="transfer-to-user"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <div>
              <label className="gx-label">Unit</label>
              <select
                className="gx-input"
                value={transferUnit}
                onChange={(e) => setTransferUnit(e.target.value as CoinUnit)}
                data-testid="transfer-coin-unit-select"
              >
                <option value="coin">GTEX Coin (GTC)</option>
                <option value="credit">Fan Coin (FNC)</option>
              </select>
            </div>
            <div>
              <label className="gx-label">Amount</label>
              <input
                type="number"
                min="0.0001"
                step="any"
                className="gx-input"
                value={transferAmount}
                onChange={(e) => setTransferAmount(e.target.value)}
                data-testid="transfer-coin-amount-input"
              />
            </div>
            <div className="md:col-span-2">
              <label className="gx-label">Audit reason</label>
              <input
                className="gx-input"
                value={transferReason}
                onChange={(e) => setTransferReason(e.target.value)}
                data-testid="transfer-coin-reason-input"
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-slate-400">Atomic double-entry transfer; rejects insufficient sender balance or same-user transfers.</span>
            <Btn variant="secondary" onClick={handleTransferCoin} disabled={transferBusy} data-testid="transfer-coin-submit-btn">
              {transferBusy ? "Transferring…" : `Transfer ${transferUnit === "coin" ? "GTEX Coin" : "Fan Coin"}`}
            </Btn>
          </div>
          {transferResult && (
            <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 p-3 text-xs text-sky-200" data-testid="transfer-coin-result">
              Tx <span className="gx-mono">{transferResult.transaction_id}</span> · From: {fmt(transferResult.from_balance_before)} → <b>{fmt(transferResult.from_balance_after)}</b> · To: {fmt(transferResult.to_balance_before)} → <b>{fmt(transferResult.to_balance_after)}</b>
            </div>
          )}
        </div>
      </Panel>

      {/* 3. Grant personal user points */}
      <Panel eyebrow="Isolated Reward Ledger" title="Grant personal user points" testid="admin-grant-points-panel">
        <div className="space-y-3">
          <p className="text-xs text-slate-400">
            Credits the user&apos;s dedicated personal reward points ledger (`UserPointAccount`), completely separate from Fan War and Club Loyalty points.
          </p>
          <UserSearchSelector
            labelText="Target user"
            selectedUser={pointsUser}
            manualUserId={pointsUserId}
            onSelectUser={(u) => {
              setPointsUser(u);
              setPointsUserId(u.id);
            }}
            onManualUserIdChange={(value) => {
              setPointsUser(null);
              setPointsUserId(value);
            }}
            testIdPrefix="grant-points-user"
          />
          {selectedUserPoints && (
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-white/10 bg-black/40 p-2.5 text-xs" data-testid="selected-user-points-balance">
              <Chip tone="gold">Balance: {fmt(selectedUserPoints.balance)} pts</Chip>
              <span className="text-slate-300">Lifetime earned: {fmt(selectedUserPoints.lifetime_earned)} pts</span>
              <span className="text-slate-400">Scope: {label(selectedUserPoints.source_scope || "personal_reward_points")}</span>
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="gx-label">Points amount</label>
              <input
                type="number"
                min="0.0001"
                step="any"
                className="gx-input"
                value={pointsAmount}
                onChange={(e) => setPointsAmount(e.target.value)}
                data-testid="grant-points-amount-input"
              />
            </div>
            <div className="md:col-span-2">
              <label className="gx-label">Audit reason</label>
              <input
                className="gx-input"
                value={pointsReason}
                onChange={(e) => setPointsReason(e.target.value)}
                data-testid="grant-points-reason-input"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Btn variant="gold" onClick={handleGrantPoints} disabled={pointsBusy} data-testid="grant-points-submit-btn">
              {pointsBusy ? "Granting…" : "Grant personal points"}
            </Btn>
          </div>
          {pointsResult && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200" data-testid="grant-points-result">
              Ref <span className="gx-mono">{pointsResult.reference}</span> · Balance: {fmt(pointsResult.balance_before)} → <b>{fmt(pointsResult.balance_after)}</b>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}

export function CoinTraderDeskAdminPanel() {
  const qc = useQueryClient();
  const [liquidityDrafts, setLiquidityDrafts] = useState<
    Record<string, { coin_unit: CoinUnit; amount: string; note: string }>
  >({});
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [lastLiquidityResult, setLastLiquidityResult] = useState<any>(null);

  const { data: tradersData = [], isLoading: loadingTraders } = useQuery<any[]>({
    queryKey: ["admin", "coin-traders", "/admin/coin-traders"],
    queryFn: async () => {
      try {
        const res = await api.get("/admin/coin-traders");
        return Array.isArray(res.data) ? res.data : res.data?.items || [];
      } catch {
        return [];
      }
    },
  });

  const { data: kycRecords = [], isLoading: loadingKyc } = useQuery<any[]>({
    queryKey: ["admin", "kyc-records", "/admin/kyc/records"],
    queryFn: async () => {
      try {
        const res = await api.get("/admin/kyc/records");
        return Array.isArray(res.data) ? res.data : res.data?.items || [];
      } catch {
        return [];
      }
    },
  });

  const latestRecordByProfileId = useMemo(() => {
    const map: Record<string, any> = {};
    for (const rec of kycRecords) {
      if (rec?.trader_profile_id && !map[rec.trader_profile_id]) {
        map[rec.trader_profile_id] = rec;
      }
    }
    return map;
  }, [kycRecords]);

  const refreshDeskData = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["admin", "coin-traders"] }),
      qc.invalidateQueries({ queryKey: ["admin", "kyc-records"] }),
      qc.invalidateQueries({ queryKey: ["admin"] }),
    ]);
  };

  const getDraft = (profileId: string) =>
    liquidityDrafts[profileId] || { coin_unit: "coin" as CoinUnit, amount: "100", note: "Desk inventory allocation" };

  const setDraft = (profileId: string, patch: Partial<{ coin_unit: CoinUnit; amount: string; note: string }>) => {
    const prev = getDraft(profileId);
    setLiquidityDrafts((curr) => ({ ...curr, [profileId]: { ...prev, ...patch } }));
  };

  const handleGovernanceAction = async (
    profileId: string,
    action: "approve" | "reject" | "freeze" | "suspend" | "reinstate",
    tier = "bronze",
  ) => {
    setBusyKey(`${profileId}:${action}`);
    try {
      const payload =
        action === "approve"
          ? { tier, note: "Approved by admin" }
          : action === "suspend" || action === "reinstate"
            ? { notes: `Admin ${action}` }
            : { note: `Admin ${action}` };
      await api.post(`/admin/coin-traders/${profileId}/${action}`, payload);
      toast.success(`Trader ${action} completed.`);
      await refreshDeskData();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyKey(null);
    }
  };

  const handleLiquidityTransfer = async (profileId: string, flow: "issue" | "redeem") => {
    const draft = getDraft(profileId);
    const numericAmount = Number(draft.amount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      return toast.error("Liquidity amount must be greater than zero.");
    }
    setBusyKey(`${profileId}:${flow}`);
    try {
      const { data } = await api.post(`/admin/coin-traders/${profileId}/liquidity/${flow}`, {
        coin_unit: draft.coin_unit,
        amount: numericAmount,
        note: draft.note.trim() || `Admin liquidity ${flow}`,
        idempotency_key: makeIdempotencyKey(`trader-${flow}`),
      });
      setLastLiquidityResult(data);
      toast.success(
        `${flow === "issue" ? "Issued" : "Redeemed"} ${data.amount} ${
          data.coin_unit === "coin" ? "GTC" : "FNC"
        }. Desk balance: ${fmt(data.available_balance)}.`,
      );
      await refreshDeskData();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="space-y-4">
      <Panel
        eyebrow="Desk compliance & liquidity"
        title={`Coin Traders & Verification (${tradersData.length})`}
        testid="admin-coin-traders-panel"
      >
        {loadingTraders ? (
          <p className="text-xs text-slate-400">Loading coin trader desks…</p>
        ) : tradersData.length === 0 ? (
          <p className="text-xs text-slate-400">No coin trader profiles found.</p>
        ) : (
          <div className="space-y-3">
            {tradersData.map((t: any) => {
              const latestKyc = latestRecordByProfileId[t.id];
              const isVerified = Boolean(t.verified_at) || latestKyc?.status === "verified";
              const isSuspended = Boolean(t.suspended_at) || t.status === "suspended";
              const draft = getDraft(t.id);
              return (
                <div
                  key={t.id}
                  className="space-y-3 rounded-lg border border-white/10 bg-white/[0.02] p-3 text-sm"
                  data-testid={`admin-trader-${t.id}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="font-bold text-white">{t.display_name}</span> · Tier:{" "}
                      <span className="capitalize">{t.tier}</span> · Status:{" "}
                      <Chip tone={t.status === "approved" ? "emerald" : t.status === "applied" ? "gold" : "red"}>
                        {label(t.status || "applied")}
                      </Chip>{" "}
                      <Chip tone={isVerified ? "emerald" : "gold"}>
                        {isVerified
                          ? `Verified (${t.verification_provider || latestKyc?.provider || "didit"})`
                          : latestKyc
                            ? `KYC: ${label(latestKyc.status || "pending")}`
                            : "Unverified"}
                      </Chip>
                      {isSuspended && <Chip tone="red">Suspended</Chip>}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {t.status === "applied" && (
                        <>
                          <Btn
                            onClick={() => handleGovernanceAction(t.id, "approve", t.tier || "bronze")}
                            disabled={Boolean(busyKey)}
                            data-testid={`approve-trader-${t.id}`}
                          >
                            Approve
                          </Btn>
                          <Btn
                            variant="danger"
                            onClick={() => handleGovernanceAction(t.id, "reject")}
                            disabled={Boolean(busyKey)}
                            data-testid={`reject-trader-${t.id}`}
                          >
                            Reject
                          </Btn>
                        </>
                      )}
                      {t.status === "approved" && (
                        <Btn
                          variant="secondary"
                          onClick={() => handleGovernanceAction(t.id, "freeze")}
                          disabled={Boolean(busyKey)}
                          data-testid={`freeze-trader-${t.id}`}
                        >
                          Freeze
                        </Btn>
                      )}
                      {!isSuspended ? (
                        <Btn
                          variant="danger"
                          onClick={() => handleGovernanceAction(t.id, "suspend")}
                          disabled={Boolean(busyKey)}
                          data-testid={`suspend-trader-${t.id}`}
                        >
                          Suspend Desk
                        </Btn>
                      ) : (
                        <Btn
                          onClick={() => handleGovernanceAction(t.id, "reinstate")}
                          disabled={Boolean(busyKey)}
                          data-testid={`reinstate-trader-${t.id}`}
                        >
                          Reinstate Desk
                        </Btn>
                      )}
                    </div>
                  </div>

                  {/* Liquidity issue & redeem bar (GTEX Coin & Fan Coin) */}
                  <div className="grid gap-2 rounded-md border border-white/10 bg-black/30 p-2.5 md:grid-cols-5">
                    <div>
                      <label className="gx-label">Coin unit</label>
                      <select
                        className="gx-input text-xs"
                        value={draft.coin_unit}
                        onChange={(e) => setDraft(t.id, { coin_unit: e.target.value as CoinUnit })}
                        data-testid={`trader-liquidity-unit-${t.id}`}
                      >
                        <option value="coin">GTEX Coin (GTC)</option>
                        <option value="credit">Fan Coin (FNC)</option>
                      </select>
                    </div>
                    <div>
                      <label className="gx-label">Amount</label>
                      <input
                        type="number"
                        min="0.0001"
                        step="any"
                        className="gx-input text-xs"
                        value={draft.amount}
                        onChange={(e) => setDraft(t.id, { amount: e.target.value })}
                        data-testid={`trader-liquidity-amount-${t.id}`}
                      />
                    </div>
                    <div>
                      <label className="gx-label">Note</label>
                      <input
                        className="gx-input text-xs"
                        value={draft.note}
                        onChange={(e) => setDraft(t.id, { note: e.target.value })}
                        data-testid={`trader-liquidity-note-${t.id}`}
                      />
                    </div>
                    <div className="flex items-end gap-2 md:col-span-2">
                      <Btn
                        onClick={() => handleLiquidityTransfer(t.id, "issue")}
                        disabled={busyKey === `${t.id}:issue`}
                        data-testid={`trader-issue-liquidity-${t.id}`}
                      >
                        {busyKey === `${t.id}:issue` ? "Issuing…" : "Issue liquidity"}
                      </Btn>
                      <Btn
                        variant="secondary"
                        onClick={() => handleLiquidityTransfer(t.id, "redeem")}
                        disabled={busyKey === `${t.id}:redeem`}
                        data-testid={`trader-redeem-liquidity-${t.id}`}
                      >
                        {busyKey === `${t.id}:redeem` ? "Redeeming…" : "Redeem liquidity"}
                      </Btn>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {lastLiquidityResult && (
          <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-200" data-testid="trader-liquidity-result">
            Liquidity {lastLiquidityResult.flow}: {fmt(lastLiquidityResult.amount)}{" "}
            {lastLiquidityResult.coin_unit === "coin" ? "GTC" : "FNC"} · Ref{" "}
            <span className="gx-mono">{lastLiquidityResult.reference}</span> · Balance:{" "}
            <b>{fmt(lastLiquidityResult.available_balance)}</b>
          </div>
        )}
      </Panel>

      <Panel
        eyebrow="Provider evidence (PII-sanitized)"
        title={`KYC Verification Records (${kycRecords.length})`}
        testid="admin-kyc-records-panel"
      >
        {loadingKyc ? (
          <p className="text-xs text-slate-400">Loading KYC verification records…</p>
        ) : kycRecords.length === 0 ? (
          <p className="text-xs text-slate-400">No identity verification sessions recorded yet.</p>
        ) : (
          <div className="space-y-2" data-testid="admin-kyc-records-list">
            {kycRecords.map((rec: any) => (
              <div
                key={rec.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-white/10 p-2.5 text-xs"
                data-testid={`admin-kyc-record-${rec.id}`}
              >
                <div>
                  <b className="text-white">{rec.trader_display_name || rec.user_email || rec.user_id}</b> ·{" "}
                  <span className="uppercase text-sky-300">{rec.provider}</span> ·{" "}
                  <span>{rec.verification_type}</span> · Session{" "}
                  <span className="gx-mono text-slate-400">{rec.provider_session_id || "—"}</span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Chip tone={rec.status === "verified" ? "emerald" : rec.status === "rejected" ? "red" : "gold"}>
                    {label(rec.status || "pending")}
                  </Chip>
                  {rec.decision && <Chip tone="slate">{label(rec.decision)}</Chip>}
                  {rec.checks_summary &&
                    typeof rec.checks_summary === "object" &&
                    Object.entries(rec.checks_summary).map(([k, v]) => (
                      <Chip key={k} tone="blue">
                        {k}: {String(v)}
                      </Chip>
                    ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <CoinTraderAdminExtras />
    </div>
  );
}

