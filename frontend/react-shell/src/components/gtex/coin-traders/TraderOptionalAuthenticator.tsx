import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { Btn } from "@/components/gtex/ui";

type SecurityStatus = {
  two_factor_enabled?: boolean;
  backup_code_count?: number;
};

/**
 * Optional authenticator for people who already use one.
 * Email and password stay the way everyone else signs in.
 */
export function TraderOptionalAuthenticator() {
  const qc = useQueryClient();
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  const securityQuery = useQuery<SecurityStatus | null>({
    queryKey: ["trader-security"],
    retry: false,
    queryFn: async () => {
      const { data } = await api.get("/v2/trader/security");
      if (!data || Array.isArray(data)) return null;
      return data as SecurityStatus;
    },
  });

  const enabled = Boolean(securityQuery.data?.two_factor_enabled);

  const copySecret = async () => {
    try {
      await navigator.clipboard.writeText(secret);
      toast.success("Authenticator setup key copied.");
    } catch {
      toast.error("Copy was blocked. Select the setup key and copy it yourself.");
    }
  };

  const startSetup = async () => {
    setBusy(true);
    setBackupCodes([]);
    try {
      const { data } = await api.post("/v2/trader/security/totp/setup");
      setSecret(String(data?.secret || ""));
      setCode("");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(code.trim())) {
      toast.error("Enter the current 6-digit code from your authenticator app.");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post("/v2/trader/security/totp/verify", {
        secret,
        code: code.trim(),
      });
      const codes = Array.isArray(data?.backup_codes) ? data.backup_codes.map(String) : [];
      setBackupCodes(codes);
      setSecret("");
      setCode("");
      toast.success("Authenticator is on for this account.");
      await qc.invalidateQueries({ queryKey: ["trader-security"] });
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="mb-6 rounded-xl border border-cyan-400/20 bg-cyan-500/[0.04] p-4"
      data-testid="trader-optional-authenticator"
    >
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 size-5 shrink-0 text-cyan-300" />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-cyan-100">Authenticator (optional)</h3>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Sign in with your email and password. Turn this on only if you already use an
            authenticator app. You can leave it off.
          </p>
          {enabled ? (
            <p className="mt-3 text-xs font-medium text-emerald-300" data-testid="trader-authenticator-enabled">
              Authenticator is on for this account.
            </p>
          ) : secret ? (
            <form onSubmit={verify} className="mt-3 space-y-2">
              <p className="text-xs text-slate-400">
                Add this setup key in your authenticator app, then enter the current 6-digit code.
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <code
                  data-testid="trader-authenticator-secret"
                  className="select-all break-all rounded bg-slate-950 px-2 py-2 text-xs tracking-wider text-cyan-100"
                >
                  {secret}
                </code>
                <button
                  type="button"
                  onClick={copySecret}
                  className="inline-flex items-center gap-1 rounded border border-cyan-400/30 px-2 py-2 text-xs text-cyan-100"
                >
                  <Copy size={13} /> Copy key
                </button>
              </div>
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                data-testid="trader-authenticator-code"
                className="gx-input max-w-xs"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="000000"
              />
              <Btn type="submit" disabled={busy}>
                {busy ? "Checking…" : "Turn on authenticator"}
              </Btn>
            </form>
          ) : (
            <Btn type="button" className="mt-3" disabled={busy} onClick={startSetup} data-testid="trader-authenticator-start">
              {busy ? "Preparing…" : "Set up authenticator"}
            </Btn>
          )}
          {backupCodes.length > 0 && (
            <div className="mt-3 rounded-lg border border-amber-400/30 bg-black/30 p-3" data-testid="trader-authenticator-backup-codes">
              <p className="text-xs font-medium text-amber-100">
                Save these backup codes. They are shown once.
              </p>
              <ul className="mt-2 grid gap-1 text-xs text-slate-200 sm:grid-cols-2">
                {backupCodes.map((item) => (
                  <li key={item} className="font-mono">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
