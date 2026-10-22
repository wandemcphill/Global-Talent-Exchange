import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { publicUrl } from "@/lib/publicPath";
import { Btn, Loading } from "@/components/gtex/ui";
import { TURNSTILE_SITE_KEY, TurnstileChallenge } from "@/components/gtex/TurnstileChallenge";

type SignupAccountType = "user" | "creator" | "coin_trader";

const TOTP_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function generateTotpSecret(): string {
  if (typeof window === "undefined" || !window.crypto?.getRandomValues) {
    throw new Error("Secure authenticator setup is not available in this browser.");
  }
  const random = new Uint8Array(32);
  window.crypto.getRandomValues(random);
  return Array.from(random, (value) => TOTP_ALPHABET[value % TOTP_ALPHABET.length]).join("");
}

async function sha256Hex(value: string): Promise<string> {
  if (typeof window === "undefined" || !window.crypto?.subtle) {
    throw new Error("Secure credential hashing is not available in this browser.");
  }
  const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function Field({ label, children }: any) {
  return (
    <label className="block">
      <span className="gx-label">{label}</span>
      {children}
    </label>
  );
}

const accountChoices: Array<{ id: SignupAccountType; title: string; detail: string }> = [
  {
    id: "user",
    title: "User Account",
    detail: "Create a club any time after signing in. Creator promotion requires that you no longer own any clubs; sell or transfer them first.",
  },
  {
    id: "creator",
    title: "Creator Account",
    detail: "Sign up directly into a dedicated Creator lane. It cannot switch back to User or Club Owner.",
  },
  {
    id: "coin_trader",
    title: "Coin Trader Account",
    detail: "A dedicated coin-trading lane. It cannot switch to User, Club Owner, or Creator.",
  },
];

export default function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { user, loading: authLoading, login, signup } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [accountType, setAccountType] = useState<SignupAccountType>("user");
  const [totpSecret, setTotpSecret] = useState("");
  const [securitySetupError, setSecuritySetupError] = useState("");
  const [f, setF] = useState<any>({
    full_name: "",
    username: "",
    email: "",
    password: "",
    over18: false,
    country: "NG",
    category: "football_news",
    main_club_supported: "",
    primary_language: "English",
    phone_number: "",
    preferred_currency: "NGN",
    trading_experience: "beginner",
    totp_code: "",
    recovery_phrase: "",
    security_pin: "",
  });

  const set = (key: string) => (event: any) =>
    setF((previous: any) => ({
      ...previous,
      [key]: event.target.type === "checkbox" ? event.target.checked : event.target.value,
    }));

  useEffect(() => {
    if (mode !== "signup" || accountType !== "coin_trader" || totpSecret) return;
    try {
      setTotpSecret(generateTotpSecret());
      setSecuritySetupError("");
    } catch (error: any) {
      setSecuritySetupError(error?.message || "Secure authenticator setup is unavailable.");
    }
  }, [mode, accountType, totpSecret]);

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

      if (!f.over18) throw new Error("You must be 18 or older to sign up for a GTEX account.");
      if (TURNSTILE_SITE_KEY && !turnstileToken) {
        throw new Error("Complete the security check to continue.");
      }

      const securityFields: Record<string, unknown> = {};
      // Never send a development bypass token. Only include a real challenge
      // token when the public site key configured for this build is present.
      if (TURNSTILE_SITE_KEY && turnstileToken) securityFields.turnstile_token = turnstileToken;

      let signupPayload: Record<string, unknown>;
      if (accountType === "creator") {
        signupPayload = {
          account_type: "creator",
          creator_name: f.full_name.trim(),
          username: f.username.trim(),
          email: f.email.trim(),
          password: f.password,
          country: f.country.trim(),
          category: f.category.trim(),
          main_club_supported: f.main_club_supported.trim() || null,
          primary_language: f.primary_language.trim(),
          monetization: ["donations", "fan_coin_revenue"],
          ...securityFields,
        };
      } else if (accountType === "coin_trader") {
        if (!totpSecret) throw new Error(securitySetupError || "Generate a secure authenticator setup before continuing.");
        if (f.recovery_phrase.trim().length < 12) {
          throw new Error("Choose a recovery phrase with at least 12 characters and store it securely.");
        }
        if (f.security_pin.trim().length < 4) {
          throw new Error("Choose a security PIN with at least 4 characters.");
        }
        if (!/^\d{6,8}$/.test(f.totp_code.trim())) {
          throw new Error("Enter the current 6–8 digit code from your authenticator app.");
        }
        signupPayload = {
          account_type: "coin_trader",
          full_name: f.full_name.trim(),
          trading_alias: f.username.trim(),
          email: f.email.trim(),
          password: f.password,
          phone_number: f.phone_number.trim(),
          country: f.country.trim(),
          preferred_currency: f.preferred_currency.trim().toUpperCase(),
          trading_experience: f.trading_experience,
          interests: ["GTEX Coin", "Fan Coin", "P2P"],
          wallet_label: "GTEX Trading Wallet",
          totp_secret: totpSecret,
          totp_code: f.totp_code.trim(),
          recovery_phrase_hash: await sha256Hex(f.recovery_phrase.trim()),
          security_pin_hash: await sha256Hex(f.security_pin.trim()),
          ...securityFields,
        };
      } else {
        signupPayload = {
          account_type: "user",
          full_name: f.full_name.trim(),
          username: f.username.trim(),
          email: f.email.trim(),
          password: f.password,
          is_over_18: true,
          ...securityFields,
        };
      }

      await signup(signupPayload);
      navigate(accountType === "creator" ? "/app/creator-access" : accountType === "coin_trader" ? "/app/coin-traders" : "/app");
    } catch (error: any) {
      toast.error(error?.response ? errMsg(error) : error.message);
    } finally {
      setBusy(false);
    }
  };

  const totpUri = totpSecret
    ? `otpauth://totp/GTEX:${encodeURIComponent(f.email || f.username || "coin-trader")}?secret=${totpSecret}&issuer=GTEX`
    : "";

  // Direct registration creates a separate account, never converts the
  // currently signed-in ID. Require sign-out first to avoid accidental lane
  // changes when the signup response replaces browser session tokens.
  if (mode === "signup" && authLoading) {
    return <Loading label="Checking your GTEX session..." />;
  }
  if (mode === "signup" && user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#070B11] px-6 py-12">
        <section className="w-full max-w-lg space-y-4 rounded-xl border border-white/10 bg-white/[0.02] p-6">
          <p className="gx-eyebrow">Dedicated account types</p>
          <h1 className="gx-h2 text-white">You are already signed in.</h1>
          <p className="text-sm leading-6 text-slate-300">
            GTEX does not switch this account between User, Creator, and Coin Trader. Sign out first to register a separate account, or continue to your current account. Normal User accounts may request Creator promotion only after they no longer own any clubs.
          </p>
          <Link to="/app" className="inline-flex rounded-md bg-emerald-400 px-4 py-2 text-sm font-bold text-slate-950">
            Return to current account
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="grid min-h-screen bg-[#070B11] lg:grid-cols-2">
      <div className="relative hidden overflow-hidden lg:block">
        <img src={publicUrl("/img/hero.jpg")} alt="Stadium under lights" className="absolute inset-0 h-full w-full object-cover opacity-50" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#070B11] via-[#070B11]/40 to-transparent" />
        <div className="absolute bottom-12 left-12 right-12">
          <p className="gx-eyebrow mb-3">GTEX Platform</p>
          <p className="gx-h2">{mode === "login" ? "Back to the boardroom." : "Choose your GTEX account."}</p>
          <p className="mt-3 max-w-md text-sm text-slate-300">
            {mode === "login"
              ? "Sign in to your dedicated account lane."
              : "User, Creator, and Coin Trader accounts are separate account types. Choose the account you intend to use."}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} data-testid={`${mode}-form`} className="w-full max-w-xl space-y-4">
          <Link to="/" className="gx-display text-3xl font-black text-white">
            GTEX
          </Link>
          <h1 className="gx-h2">{mode === "login" ? "Sign in" : "Create a GTEX account"}</h1>

          {mode === "signup" && (
            <div className="grid gap-2 sm:grid-cols-3" role="group" aria-label="Account type">
              {accountChoices.map((choice) => (
                <button
                  key={choice.id}
                  type="button"
                  data-testid={`signup-account-${choice.id}`}
                  aria-pressed={accountType === choice.id}
                  onClick={() => setAccountType(choice.id)}
                  className={`rounded-lg border p-3 text-left transition-colors ${
                    accountType === choice.id
                      ? "border-emerald-400/60 bg-emerald-500/10 text-white"
                      : "border-white/10 bg-white/[0.02] text-slate-300 hover:border-white/25"
                  }`}
                >
                  <span className="block text-xs font-black uppercase tracking-wide">{choice.title}</span>
                  <span className="mt-2 block text-xs leading-5 text-slate-400">{choice.detail}</span>
                </button>
              ))}
            </div>
          )}

          {mode === "signup" && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Full name">
                <input required data-testid="signup-fullname-input" className="gx-input" value={f.full_name} onChange={set("full_name")} />
              </Field>
              <Field label={accountType === "coin_trader" ? "Trading alias" : accountType === "creator" ? "Creator handle" : "Username"}>
                <input required minLength={3} data-testid="signup-username-input" className="gx-input" value={f.username} onChange={set("username")} />
              </Field>
            </div>
          )}

          <Field label="Email">
            <input required type="email" data-testid={`${mode}-email-input`} className="gx-input" value={f.email} onChange={set("email")} />
          </Field>
          <Field label="Password">
            <input required type="password" minLength={8} data-testid={`${mode}-password-input`} className="gx-input" value={f.password} onChange={set("password")} />
          </Field>

          {mode === "signup" && accountType === "creator" && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Country">
                <input required minLength={2} className="gx-input" value={f.country} onChange={set("country")} />
              </Field>
              <Field label="Creator category">
                <select className="gx-input" value={f.category} onChange={set("category")}>
                  <option value="football_news">Football news</option>
                  <option value="match_reactions">Match reactions</option>
                  <option value="tactical_analysis">Tactical analysis</option>
                  <option value="comedy">Football comedy</option>
                  <option value="watchalong">Watchalong</option>
                  <option value="transfer_news">Transfer news</option>
                </select>
              </Field>
              <Field label="Main club supported (optional)">
                <input className="gx-input" value={f.main_club_supported} onChange={set("main_club_supported")} />
              </Field>
              <Field label="Primary language">
                <input required minLength={2} className="gx-input" value={f.primary_language} onChange={set("primary_language")} />
              </Field>
              <p className="col-span-2 text-xs leading-5 text-slate-500">
                This creates a dedicated Creator account directly. It is separate from Creator promotion requested from a normal User account.
              </p>
            </div>
          )}

          {mode === "signup" && accountType === "coin_trader" && (
            <div className="space-y-4 rounded-lg border border-amber-300/20 bg-amber-300/[0.04] p-4">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Phone number">
                  <input required minLength={6} className="gx-input" value={f.phone_number} onChange={set("phone_number")} />
                </Field>
                <Field label="Country">
                  <input required minLength={2} className="gx-input" value={f.country} onChange={set("country")} />
                </Field>
                <Field label="Preferred currency">
                  <input required minLength={2} maxLength={12} className="gx-input" value={f.preferred_currency} onChange={set("preferred_currency")} />
                </Field>
                <Field label="Trading experience">
                  <select className="gx-input" value={f.trading_experience} onChange={set("trading_experience")}>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="professional">Professional</option>
                  </select>
                </Field>
              </div>
              <div className="rounded border border-white/10 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-amber-200">Authenticator setup</p>
                <p className="mt-2 text-xs leading-5 text-slate-400">
                  Add this secret to your authenticator app as a time-based one-time password, then enter the current code below. Keep the secret private.
                </p>
                {securitySetupError ? (
                  <p role="alert" className="mt-2 text-sm text-red-200">{securitySetupError}</p>
                ) : (
                  <>
                    <code data-testid="signup-totp-secret" className="mt-2 block break-all rounded bg-black/40 p-2 text-xs text-white">{totpSecret || "Generating secure secret…"}</code>
                    <p className="mt-2 break-all text-[10px] text-slate-500">{totpUri}</p>
                  </>
                )}
              </div>
              <Field label="Current authenticator code">
                <input required inputMode="numeric" autoComplete="one-time-code" minLength={6} maxLength={8} className="gx-input" value={f.totp_code} onChange={set("totp_code")} />
              </Field>
              <Field label="Recovery phrase (at least 12 characters)">
                <input required minLength={12} type="password" autoComplete="off" className="gx-input" value={f.recovery_phrase} onChange={set("recovery_phrase")} />
              </Field>
              <Field label="Security PIN (at least 4 characters)">
                <input required minLength={4} type="password" autoComplete="new-password" className="gx-input" value={f.security_pin} onChange={set("security_pin")} />
              </Field>
              <p className="text-xs leading-5 text-slate-500">
                Coin Trader accounts stay in the trading lane and cannot switch to User, Club Owner, or Creator. Your recovery phrase and PIN are hashed in the browser before submission.
              </p>
            </div>
          )}

          {mode === "signup" && (
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <input type="checkbox" data-testid="signup-over18-checkbox" checked={f.over18} onChange={set("over18")} /> I am 18 or older and accept the terms.
            </label>
          )}
          {mode === "signup" && <TurnstileChallenge onTokenChange={setTurnstileToken} />}

          <Btn type="submit" disabled={busy || (mode === "signup" && accountType === "coin_trader" && (!totpSecret || Boolean(securitySetupError)))} className="w-full py-3" data-testid={`${mode}-submit-button`}>
            {busy ? "Please wait…" : mode === "login" ? "Enter the console" : accountType === "creator" ? "Create Creator account" : accountType === "coin_trader" ? "Create Coin Trader account" : "Create User account"}
          </Btn>
          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? (
              <>New to GTEX? <Link data-testid="goto-signup-link" className="text-emerald-400 hover:text-emerald-300" to="/signup">Create account</Link></>
            ) : (
              <>Already have an account? <Link data-testid="goto-login-link" className="text-emerald-400 hover:text-emerald-300" to="/login">Sign in</Link></>
            )}
          </p>
        </form>
      </div>
    </div>
  );
}
