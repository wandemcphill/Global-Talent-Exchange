import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { publicUrl } from "@/lib/publicPath";
import { Btn, Loading } from "@/components/gtex/ui";
import { TURNSTILE_SITE_KEY, TurnstileChallenge } from "@/components/gtex/TurnstileChallenge";
import { GtexAuthAdvertisingPanel } from "@/components/advertising/GtexAdvertising";
import { Building2, Megaphone, ArrowRight, Copy, ShieldCheck } from "lucide-react";

type AccountType = "user" | "creator" | "coin_trader";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block min-w-0">
      <span className="gx-label">{label}</span>
      {children}
    </label>
  );
}

function generateBase32Secret(): string {
  const bytes = new Uint8Array(20);
  window.crypto.getRandomValues(bytes);
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = 0;
  let value = 0;
  let output = "";
  for (const byte of bytes) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      output += alphabet[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) output += alphabet[(value << (5 - bits)) & 31];
  return output;
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

/**
 * PINs and recovery phrases are never sent as plain text. PBKDF2 with a unique
 * random salt gives the backend an opaque, verifiable credential representation.
 */
async function hashTraderSecret(purpose: "recovery" | "pin", value: string): Promise<string> {
  const salt = window.crypto.getRandomValues(new Uint8Array(16));
  const key = await window.crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(value.normalize("NFKC")),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  const derived = await window.crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: 210000, hash: "SHA-256" },
    key,
    256,
  );
  return "pbkdf2-sha256$210000$" + purpose + "$" + toHex(salt) + "$" + toHex(new Uint8Array(derived));
}

export default function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { user, loading: authLoading, login, signup } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedRole = (searchParams.get("role") || "").toLowerCase().trim();

  const [busy, setBusy] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [accountType, setAccountType] = useState<AccountType>(
    requestedRole === "creator" ? "creator" : requestedRole === "trader" || requestedRole === "coin_trader" ? "coin_trader" : "user",
  );
  const [userFields, setUserFields] = useState({
    full_name: "",
    username: "",
    email: "",
    password: "",
    over18: false,
  });
  const [creatorFields, setCreatorFields] = useState({
    creator_name: "",
    username: "",
    country: "Nigeria",
    category: "sports",
    primary_language: "English",
    main_club_supported: "",
  });
  const [traderFields, setTraderFields] = useState({
    full_name: "",
    trading_alias: "",
    phone_number: "",
    country: "Nigeria",
    preferred_currency: "NGN",
    trading_experience: "beginner",
    totp_code: "",
    recovery_phrase: "",
    security_pin: "",
  });
  const [totpSecret] = useState(() => generateBase32Secret());
  const [termsAccepted, setTermsAccepted] = useState(false);

  const updateUser = (key: keyof typeof userFields) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setUserFields((previous) => ({
      ...previous,
      [key]: event.target.type === "checkbox" ? event.target.checked : event.target.value,
    }));
  const updateCreator = (key: keyof typeof creatorFields) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => setCreatorFields((previous) => ({ ...previous, [key]: event.target.value }));
  const updateTrader = (key: keyof typeof traderFields) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => setTraderFields((previous) => ({ ...previous, [key]: event.target.value }));

  const copyTotpSecret = async () => {
    try {
      await navigator.clipboard.writeText(totpSecret);
      toast.success("Authenticator setup key copied.");
    } catch {
      toast.error("Copy was blocked by this browser. Select and copy the setup key instead.");
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        const result = await login(userFields.email.trim(), userFields.password);
        const type = String(result.user?.account_type || result.user?.accountType || "user").toLowerCase();
        const landingRoute = String(result.landingRoute || "");
        navigate(
          type === "creator" || landingRoute === "/app/hub"
            ? "/app/creator-access"
            : type === "coin_trader" || landingRoute === "/trader" || landingRoute === "/app/trader-dashboard"
              ? "/app/coin-traders"
              : "/app",
        );
        return;
      }

      if (!termsAccepted) {
        throw new Error("Accept the GTEX terms to continue.");
      }
      if (accountType === "user" && !userFields.over18) {
        throw new Error("You must be 18 or older to sign up for a GTEX account.");
      }
      if (TURNSTILE_SITE_KEY && !turnstileToken) {
        throw new Error("Complete the security check to continue.");
      }
      const securityFields: Record<string, unknown> = {};
      if (TURNSTILE_SITE_KEY && turnstileToken) {
        securityFields.turnstile_token = turnstileToken;
      }

      let signupPayload: Record<string, unknown>;
      if (accountType === "creator") {
        if (creatorFields.creator_name.trim().length < 2 || creatorFields.username.trim().length < 3) {
          throw new Error("Enter a Creator name and a username of at least 3 characters.");
        }
        if (creatorFields.country.trim().length < 2 || creatorFields.category.trim().length < 2 || creatorFields.primary_language.trim().length < 2) {
          throw new Error("Complete your country, creator category and primary language.");
        }
        signupPayload = {
          account_type: "creator",
          creator_name: creatorFields.creator_name.trim(),
          username: creatorFields.username.trim(),
          email: userFields.email.trim(),
          password: userFields.password,
          country: creatorFields.country.trim(),
          category: creatorFields.category.trim(),
          primary_language: creatorFields.primary_language.trim(),
          ...(creatorFields.main_club_supported.trim()
            ? { main_club_supported: creatorFields.main_club_supported.trim() }
            : {}),
          ...securityFields,
        };
      } else if (accountType === "coin_trader") {
        if (traderFields.full_name.trim().length < 2 || traderFields.trading_alias.trim().length < 2) {
          throw new Error("Enter your full name and a trading alias.");
        }
        if (traderFields.phone_number.trim().length < 6 || traderFields.country.trim().length < 2) {
          throw new Error("Enter a valid phone number and country.");
        }
        if (!/^\+?[0-9()\-\s]{6,32}$/.test(traderFields.phone_number.trim())) {
          throw new Error("Enter your phone number using digits and an optional leading +.");
        }
        if (traderFields.preferred_currency.trim().length < 2) {
          throw new Error("Choose your preferred trading currency.");
        }
        if (!/^\d{6,12}$/.test(traderFields.totp_code.trim())) {
          throw new Error("Enter the current 6–12 digit code from your authenticator app.");
        }
        if (traderFields.recovery_phrase.trim().split(/\s+/).length < 8) {
          throw new Error("Your recovery phrase must contain at least 8 words.");
        }
        if (!/^\d{6,12}$/.test(traderFields.security_pin.trim())) {
          throw new Error("Choose a security PIN containing 6–12 digits.");
        }
        signupPayload = {
          account_type: "coin_trader",
          full_name: traderFields.full_name.trim(),
          trading_alias: traderFields.trading_alias.trim(),
          email: userFields.email.trim(),
          password: userFields.password,
          phone_number: traderFields.phone_number.trim(),
          country: traderFields.country.trim(),
          preferred_currency: traderFields.preferred_currency.trim().toUpperCase(),
          trading_experience: traderFields.trading_experience,
          interests: ["GTEX Coin", "Fan Coins", "P2P"],
          wallet_label: "GTEX Trading Wallet",
          totp_secret: totpSecret,
          totp_code: traderFields.totp_code.trim(),
          recovery_phrase_hash: await hashTraderSecret("recovery", traderFields.recovery_phrase.trim()),
          security_pin_hash: await hashTraderSecret("pin", traderFields.security_pin.trim()),
          ...securityFields,
        };
      } else {
        if (userFields.full_name.trim().length < 2 || userFields.username.trim().length < 3) {
          throw new Error("Enter your full name and a username of at least 3 characters.");
        }
        signupPayload = {
          account_type: "user",
          full_name: userFields.full_name.trim(),
          username: userFields.username.trim(),
          email: userFields.email.trim(),
          password: userFields.password,
          is_over_18: true,
          ...securityFields,
        };
      }

      await signup(signupPayload);
      navigate(
        accountType === "creator"
          ? "/app/creator-access"
          : accountType === "coin_trader"
            ? "/app/coin-traders"
            : "/app",
      );
    } catch (error: any) {
      toast.error(error?.response ? errMsg(error) : error.message);
    } finally {
      setBusy(false);
    }
  };

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

  const otpUri = "otpauth://totp/GTEX:" + encodeURIComponent(userFields.email || traderFields.trading_alias || "CoinTrader") +
    "?secret=" + totpSecret + "&issuer=GTEX&algorithm=SHA1&digits=6&period=30";

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
      <div className="flex items-center justify-center px-4 py-8 sm:px-6 sm:py-12">
        <form onSubmit={submit} data-testid={mode + "-form"} className="w-full max-w-xl space-y-4">
          <div className="lg:hidden">
            <GtexAuthAdvertisingPanel compact />
          </div>
          <Link to="/" className="gx-display text-3xl font-black text-white">GTEX</Link>
          <h1 className="gx-h2">{mode === "login" ? "Sign in" : "Create a GTEX account"}</h1>

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
              <Field label="Account type">
                <select
                  data-testid="signup-account-type"
                  className="gx-input"
                  value={accountType}
                  onChange={(event) => setAccountType(event.target.value as AccountType)}
                >
                  <option value="user">Fan or club owner</option>
                  <option value="coin_trader">Coin trader</option>
                  <option value="creator">Creator</option>
                </select>
              </Field>
              <p className="mt-2 leading-5 text-slate-400">
                Fans and club owners use the same account. Coin traders and creators register into their own desks. Advertisers use the corporate signup above.
              </p>
              {requestedRole && (
                <div className="mt-2 inline-flex items-center gap-1.5 rounded border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                  <span>Specialization intent:</span>
                  <span className="font-bold capitalize text-white">{requestedRole}</span>
                  <span className="text-slate-400">— selected account path</span>
                </div>
              )}
            </div>
          )}

          {mode === "signup" && accountType === "user" && (
            <>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Full name">
                  <input required data-testid="signup-fullname-input" className="gx-input" value={userFields.full_name} onChange={updateUser("full_name")} placeholder="Alex Ferguson" />
                </Field>
                <Field label="Username">
                  <input required minLength={3} data-testid="signup-username-input" className="gx-input" value={userFields.username} onChange={updateUser("username")} placeholder="alex_ferguson" />
                </Field>
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" data-testid="signup-over18-checkbox" checked={userFields.over18} onChange={updateUser("over18")} />
                I am 18 or older.
              </label>
            </>
          )}

          {mode === "signup" && accountType === "creator" && (
            <section data-testid="creator-signup-fields" className="space-y-3 rounded-xl border border-fuchsia-400/20 bg-fuchsia-500/[0.04] p-4">
              <p className="text-sm font-semibold text-fuchsia-200">Creator account details</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Creator or brand name">
                  <input required minLength={2} data-testid="creator-name-input" className="gx-input" value={creatorFields.creator_name} onChange={updateCreator("creator_name")} placeholder="Your public creator name" />
                </Field>
                <Field label="Creator username">
                  <input required minLength={3} data-testid="creator-username-input" className="gx-input" value={creatorFields.username} onChange={updateCreator("username")} placeholder="creator_handle" />
                </Field>
                <Field label="Country">
                  <input required data-testid="creator-country-input" className="gx-input" value={creatorFields.country} onChange={updateCreator("country")} />
                </Field>
                <Field label="Creator category">
                  <select required data-testid="creator-category-input" className="gx-input" value={creatorFields.category} onChange={updateCreator("category")}>
                    <option value="sports">Sports</option>
                    <option value="gaming">Gaming</option>
                    <option value="entertainment">Entertainment</option>
                    <option value="music">Music</option>
                    <option value="education">Education</option>
                    <option value="other">Other</option>
                  </select>
                </Field>
                <Field label="Primary language">
                  <input required data-testid="creator-language-input" className="gx-input" value={creatorFields.primary_language} onChange={updateCreator("primary_language")} placeholder="English" />
                </Field>
                <Field label="Main club supported (optional)">
                  <input data-testid="creator-club-input" className="gx-input" value={creatorFields.main_club_supported} onChange={updateCreator("main_club_supported")} placeholder="Your club" />
                </Field>
              </div>
            </section>
          )}

          {mode === "signup" && accountType === "coin_trader" && (
            <section data-testid="trader-signup-fields" className="space-y-4 rounded-xl border border-amber-400/20 bg-amber-500/[0.04] p-4">
              <p className="text-sm font-semibold text-amber-200">Coin Trader account details</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Full name">
                  <input required minLength={2} data-testid="trader-fullname-input" className="gx-input" value={traderFields.full_name} onChange={updateTrader("full_name")} placeholder="Your legal name" />
                </Field>
                <Field label="Trading alias">
                  <input required minLength={2} data-testid="trader-alias-input" className="gx-input" value={traderFields.trading_alias} onChange={updateTrader("trading_alias")} placeholder="Public trader desk name" />
                </Field>
                <Field label="Phone number">
                  <input required type="tel" data-testid="trader-phone-input" className="gx-input" value={traderFields.phone_number} onChange={updateTrader("phone_number")} placeholder="+234 800 000 0000" />
                </Field>
                <Field label="Country">
                  <input required data-testid="trader-country-input" className="gx-input" value={traderFields.country} onChange={updateTrader("country")} />
                </Field>
                <Field label="Preferred currency">
                  <select required data-testid="trader-currency-input" className="gx-input" value={traderFields.preferred_currency} onChange={updateTrader("preferred_currency")}>
                    <option value="NGN">NGN — Nigerian naira</option>
                    <option value="USD">USD — US dollar</option>
                    <option value="EUR">EUR — Euro</option>
                    <option value="GBP">GBP — Pound sterling</option>
                  </select>
                </Field>
                <Field label="Trading experience">
                  <select required data-testid="trader-experience-input" className="gx-input" value={traderFields.trading_experience} onChange={updateTrader("trading_experience")}>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="professional">Professional</option>
                  </select>
                </Field>
              </div>

              <div className="rounded-lg border border-cyan-400/20 bg-cyan-500/[0.04] p-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-cyan-100">
                  <ShieldCheck size={17} /> Set up your authenticator app
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-400">
                  Add GTEX to Google Authenticator, Microsoft Authenticator or another TOTP app using this setup key. Keep it private.
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <code data-testid="signup-totp-secret" className="select-all break-all rounded bg-slate-950 px-2 py-2 text-xs tracking-wider text-cyan-100">{totpSecret}</code>
                  <button type="button" onClick={copyTotpSecret} className="inline-flex items-center gap-1 rounded border border-cyan-400/30 px-2 py-2 text-xs text-cyan-100">
                    <Copy size={13} /> Copy key
                  </button>
                </div>
                <a href={otpUri} className="mt-2 inline-block text-xs text-cyan-300 underline" data-testid="trader-otpauth-link">
                  Open authenticator setup link
                </a>
                <Field label="Current 6-digit authenticator code">
                  <input required inputMode="numeric" autoComplete="one-time-code" maxLength={12} data-testid="trader-totp-code-input" className="gx-input mt-1" value={traderFields.totp_code} onChange={updateTrader("totp_code")} placeholder="000000" />
                </Field>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Recovery phrase (at least 8 words)">
                  <input required minLength={32} autoComplete="off" data-testid="trader-recovery-input" type="password" className="gx-input" value={traderFields.recovery_phrase} onChange={updateTrader("recovery_phrase")} placeholder="Create a private recovery phrase" />
                </Field>
                <Field label="Security PIN (6–12 digits)">
                  <input required inputMode="numeric" maxLength={12} autoComplete="new-password" data-testid="trader-pin-input" type="password" className="gx-input" value={traderFields.security_pin} onChange={updateTrader("security_pin")} placeholder="Create a private PIN" />
                </Field>
              </div>
              <p className="text-xs leading-5 text-slate-400">
                Your recovery phrase and PIN are hashed in the browser before submission. GTEX staff will never ask you to send either one.
              </p>
            </section>
          )}

          <Field label="Email">
            <input required type="email" data-testid={mode + "-email-input"} className="gx-input" value={userFields.email} onChange={(event) => setUserFields((previous) => ({ ...previous, email: event.target.value }))} placeholder="alex@example.com" />
          </Field>
          <Field label="Password">
            <input required type="password" minLength={8} data-testid={mode + "-password-input"} className="gx-input" value={userFields.password} onChange={(event) => setUserFields((previous) => ({ ...previous, password: event.target.value }))} placeholder="••••••••" />
          </Field>

          {mode === "signup" && (
            <>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" data-testid="signup-terms-checkbox" checked={termsAccepted} onChange={(event) => setTermsAccepted(event.target.checked)} />
                I accept the GTEX terms and privacy policy.
              </label>
              <TurnstileChallenge onTokenChange={setTurnstileToken} />
            </>
          )}

          <Btn type="submit" disabled={busy} className="w-full py-3" data-testid={mode + "-submit-button"}>
            {busy ? "Please wait…" : mode === "login" ? "Enter the console" : "Create GTEX account"}
          </Btn>
          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? (
              <>
                New to GTEX?{" "}
                <Link data-testid="goto-signup-link" className="text-emerald-400 hover:text-emerald-300" to="/signup">Create account</Link>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <Link data-testid="goto-login-link" className="text-emerald-400 hover:text-emerald-300" to="/login">Sign in</Link>
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
