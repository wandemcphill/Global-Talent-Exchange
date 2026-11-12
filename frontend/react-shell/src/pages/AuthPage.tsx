import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { publicUrl } from "@/lib/publicPath";
import { Btn, Loading } from "@/components/gtex/ui";
import { TURNSTILE_SITE_KEY, TurnstileChallenge } from "@/components/gtex/TurnstileChallenge";
import { GtexAuthAdvertisingPanel } from "@/components/advertising/GtexAdvertising";
import { Building2, Megaphone, ArrowRight } from "lucide-react";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="gx-label">{label}</span>
      {children}
    </label>
  );
}

export default function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { user, loading: authLoading, login, signup } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedRole = (searchParams.get("role") || "").toLowerCase().trim();

  const [busy, setBusy] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [accountType, setAccountType] = useState(
    requestedRole === "creator" ? "creator" : requestedRole === "trader" || requestedRole === "coin_trader" ? "coin_trader" : "user",
  );
  const [f, setF] = useState({
    full_name: "",
    username: "",
    email: "",
    password: "",
    over18: false,
  });

  const set = (key: keyof typeof f) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setF((previous) => ({
      ...previous,
      [key]: event.target.type === "checkbox" ? event.target.checked : event.target.value,
    }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        const result = await login(f.email.trim(), f.password);
        const type = String(result.user?.account_type || result.user?.accountType || "user").toLowerCase();
        const landingRoute = String(result.landingRoute || "");
        navigate(
          type === "creator" || landingRoute === "/app/hub"
            ? "/app/creator-access"
            : type === "coin_trader" ||
                landingRoute === "/trader" ||
                landingRoute === "/app/trader-dashboard"
              ? "/app/coin-traders"
              : "/app",
        );
        return;
      }

      if (!f.over18) {
        throw new Error("You must be 18 or older to sign up for a GTEX account.");
      }
      if (TURNSTILE_SITE_KEY && !turnstileToken) {
        throw new Error("Complete the security check to continue.");
      }

      const securityFields: Record<string, unknown> = {};
      // Never send a development bypass token. Only include a real challenge
      // token when the public site key configured for this build is present.
      if (TURNSTILE_SITE_KEY && turnstileToken) {
        securityFields.turnstile_token = turnstileToken;
      }

      const signupPayload = {
        account_type: accountType,
        full_name: f.full_name.trim(),
        username: f.username.trim(),
        email: f.email.trim(),
        password: f.password,
        is_over_18: true,
        ...securityFields,
      };

      await signup(signupPayload);

      // Route users into their requested specialization desk or default console
      if (requestedRole === "creator") {
        navigate("/app/creator-access");
      } else if (requestedRole === "trader" || requestedRole === "coin_trader") {
        navigate("/app/coin-traders");
      } else {
        navigate("/app");
      }
    } catch (error: any) {
      toast.error(error?.response ? errMsg(error) : error.message);
    } finally {
      setBusy(false);
    }
  };

  // Direct registration creates a clean account. If already signed in,
  // guide the user back to the console or advise signing out.
  if (mode === "signup" && authLoading) {
    return <Loading label="Checking your GTEX session..." />;
  }
  if (mode === "signup" && user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#070B11] px-6 py-12">
        <section className="w-full max-w-lg space-y-4 rounded-xl border border-white/10 bg-white/[0.02] p-6 text-center">
          <p className="gx-eyebrow">GTEX Account</p>
          <h1 className="gx-h2 text-white">You are already signed in</h1>
          <p className="text-sm leading-6 text-slate-300">
            You are signed in as <span className="font-semibold text-white">{user.username || user.email}</span>. Specialized creator, trading, and club ownership capabilities can be managed in your console.
          </p>

          <div className="pt-2">
            <Link
              to="/app"
              data-testid="return-to-console-link"
              className="inline-flex rounded-md bg-emerald-400 px-5 py-2.5 text-sm font-bold text-slate-950 hover:bg-emerald-300 transition-colors"
            >
              Return to console
            </Link>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="grid min-h-screen bg-[#070B11] lg:grid-cols-2">
      <div className="relative hidden overflow-hidden lg:block">
        <img
          src={publicUrl("/img/hero.jpg")}
          alt="Stadium under lights"
          className="absolute inset-0 h-full w-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#070B11] via-[#070B11]/40 to-transparent" />
        <div className="relative z-10 flex min-h-screen items-center justify-center p-8 xl:p-12">
          <GtexAuthAdvertisingPanel />
        </div>
      </div>
      <div className="flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} data-testid={`${mode}-form`} className="w-full max-w-xl space-y-4">
          <div className="lg:hidden">
            <GtexAuthAdvertisingPanel compact />
          </div>
          <Link to="/" className="gx-display text-3xl font-black text-white">
            GTEX
          </Link>
          <h1 className="gx-h2">{mode === "login" ? "Sign in" : "Create a GTEX account"}</h1>

          {/* Corporate Advertiser & Brand Direct Access Notice */}
          <div
            data-testid="auth-corporate-advertiser-banner"
            className="rounded-xl border border-[#D4AF37]/40 bg-[#13233A]/90 p-4 shadow-xl backdrop-blur-md"
          >
            <div className="flex items-start gap-3.5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#D4AF37]/50 bg-[#D4AF37]/15 text-[#D4AF37]">
                <Megaphone size={20} />
              </div>
              <div className="flex-1 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-1.5">
                  <span className="font-['Barlow_Condensed'] text-base font-extrabold uppercase tracking-wide text-[#F2F4F8]">
                    Looking to advertise or sponsor on GTEX?
                  </span>
                  <span className="rounded bg-[#D4AF37]/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#E8C766]">
                    No Gamer Account Required
                  </span>
                </div>
                <p className="mt-1 leading-relaxed text-[#9AA7BD]">
                  Brands, corporations, and music artists do not need a personal player, creator, or coin trader account to advertise. You can configure and pay for ads directly, or use a dedicated corporate workspace.
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-2.5">
                  <Link
                    to="/advertise"
                    data-testid="auth-direct-ad-cta"
                    className="inline-flex items-center gap-1.5 rounded-md border border-[#D4AF37] bg-[#D4AF37] px-3.5 py-1.5 font-['Barlow_Condensed'] text-xs font-black uppercase tracking-wider text-[#0B1626] transition hover:bg-[#E8C766]"
                  >
                    <span>Launch Advert Directly</span>
                    <ArrowRight size={13} />
                  </Link>
                  {mode === "signup" ? (
                    <Link
                      to="/advertiser/register"
                      data-testid="auth-advertiser-register-cta"
                      className="inline-flex items-center gap-1.5 rounded-md border border-[#22385A] bg-[#0B1626] px-3 py-1.5 text-xs font-semibold text-[#F2F4F8] transition hover:border-[#D4AF37]/60 hover:text-[#D4AF37]"
                    >
                      <Building2 size={13} className="text-[#D4AF37]" />
                      <span>Corporate Workspace Signup</span>
                    </Link>
                  ) : (
                    <Link
                      to="/advertiser/login"
                      data-testid="auth-advertiser-login-cta"
                      className="inline-flex items-center gap-1.5 rounded-md border border-[#22385A] bg-[#0B1626] px-3 py-1.5 text-xs font-semibold text-[#F2F4F8] transition hover:border-[#D4AF37]/60 hover:text-[#D4AF37]"
                    >
                      <Building2 size={13} className="text-[#D4AF37]" />
                      <span>Advertiser Workspace Sign In</span>
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </div>

          {mode === "signup" && (
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 text-xs text-slate-300">
              <p className="font-semibold text-emerald-300">Choose how you join</p>
              <label className="mt-2 block">
                <span className="gx-label">Account type</span>
                <select
                  data-testid="signup-account-type"
                  className="gx-input"
                  value={accountType}
                  onChange={(event) => setAccountType(event.target.value)}
                >
                  <option value="user">Fan or club owner</option>
                  <option value="coin_trader">Coin trader</option>
                  <option value="creator">Creator</option>
                </select>
              </label>
              <p className="mt-2 leading-5 text-slate-400">
                Fans and club owners use the same account. Coin traders and creators register into their own desks. Advertisers use the corporate signup above.
              </p>

              {requestedRole && (
                <div className="mt-2 inline-flex items-center gap-1.5 rounded border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                  <span>Specialization intent:</span>
                  <span className="font-bold capitalize text-white">{requestedRole}</span>
                  <span className="text-slate-400">— ready to activate in console</span>
                </div>
              )}
            </div>
          )}

          {mode === "signup" && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Full name">
                <input
                  required
                  data-testid="signup-fullname-input"
                  className="gx-input"
                  value={f.full_name}
                  onChange={set("full_name")}
                  placeholder="Alex Ferguson"
                />
              </Field>
              <Field label="Username">
                <input
                  required
                  minLength={3}
                  data-testid="signup-username-input"
                  className="gx-input"
                  value={f.username}
                  onChange={set("username")}
                  placeholder="alex_ferguson"
                />
              </Field>
            </div>
          )}

          <Field label="Email">
            <input
              required
              type="email"
              data-testid={`${mode}-email-input`}
              className="gx-input"
              value={f.email}
              onChange={set("email")}
              placeholder="alex@example.com"
            />
          </Field>
          <Field label="Password">
            <input
              required
              type="password"
              minLength={8}
              data-testid={`${mode}-password-input`}
              className="gx-input"
              value={f.password}
              onChange={set("password")}
              placeholder="••••••••"
            />
          </Field>

          {mode === "signup" && (
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                data-testid="signup-over18-checkbox"
                checked={f.over18}
                onChange={set("over18")}
              />{" "}
              I am 18 or older and accept the terms.
            </label>
          )}

          {mode === "signup" && <TurnstileChallenge onTokenChange={setTurnstileToken} />}

          <Btn
            type="submit"
            disabled={busy}
            className="w-full py-3"
            data-testid={`${mode}-submit-button`}
          >
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Enter the console"
                : "Create GTEX account"}
          </Btn>
          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? (
              <>
                New to GTEX?{" "}
                <Link data-testid="goto-signup-link" className="text-emerald-400 hover:text-emerald-300" to="/signup">
                  Create account
                </Link>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <Link data-testid="goto-login-link" className="text-emerald-400 hover:text-emerald-300" to="/login">
                  Sign in
                </Link>
              </>
            )}
          </p>

          <div className="border-t border-[#22385A]/60 pt-3 text-center text-xs text-[#9AA7BD]">
            <span>Representing a company or sponsor? </span>
            <Link to="/advertise" className="font-semibold text-[#D4AF37] hover:underline">
              Explore Commercial Ad Rates & Placement Options &rarr;
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
