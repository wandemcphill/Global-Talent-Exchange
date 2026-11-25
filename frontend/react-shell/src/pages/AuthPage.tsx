import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowRight, Building2, Megaphone } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { errMsg } from "@/lib/api";
import { publicUrl } from "@/lib/publicPath";
import { Btn, Loading } from "@/components/gtex/ui";
import { TURNSTILE_SITE_KEY, TurnstileChallenge } from "@/components/gtex/TurnstileChallenge";
import { GtexAuthAdvertisingPanel } from "@/components/advertising/GtexAdvertising";
import { DocumentHead } from "@/components/seo/DocumentHead";

type AccountType = "user" | "creator" | "coin_trader";

const REQUIRED_TRADER_DESKS = ["GTEX Coin", "Fan Coins", "P2P", "Escrow"] as const;

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block min-w-0">
      <span className="gx-label">{label}</span>
      {children}
      {error && (
        <span className="mt-1 block text-xs text-red-300" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}

function parseAuthError(error: any): { summary: string; fieldErrors: Record<string, string> } {
  const detail = error?.response?.data?.detail;
  const mappedFields: Record<string, string> = {};
  if (Array.isArray(detail)) {
    const messages: string[] = [];
    for (const item of detail) {
      if (item && typeof item === "object") {
        const loc = Array.isArray(item.loc) ? item.loc : [];
        const field = String(loc[loc.length - 1] || "");
        const friendlyField = field.replace(/_/g, " ");
        const msg = String(item.msg || "Invalid value").replace(/^Value error,\s*/i, "");
        if (field) {
          const uiKey =
            field === "recovery_phrase_hash"
              ? "recovery_phrase"
              : field === "security_pin_hash"
                ? "security_pin"
                : field;
          mappedFields[uiKey] = msg;
          messages.push(friendlyField ? `${friendlyField}: ${msg}` : msg);
        } else if (msg) {
          messages.push(msg);
        }
      }
    }
    if (messages.length > 0) {
      return { summary: messages[0], fieldErrors: mappedFields };
    }
  }
  const message = error?.response ? errMsg(error) : error?.message || "Unable to complete request.";
  return { summary: message, fieldErrors: mappedFields };
}

export default function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { user, loading: authLoading, login, signup } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedRole = String(searchParams.get("role") || "").toLowerCase();

  const [busy, setBusy] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [accountType, setAccountType] = useState<AccountType>(
    requestedRole === "creator"
      ? "creator"
      : requestedRole === "trader" || requestedRole === "coin_trader"
        ? "coin_trader"
        : "user",
  );
  const [referralCode, setReferralCode] = useState(() => {
    const fromUrl = (
      searchParams.get("ref") ||
      searchParams.get("referral") ||
      searchParams.get("referral_code") ||
      ""
    ).trim();
    const stored = window.sessionStorage.getItem("gtex_referral_code") || "";
    return (fromUrl || stored).trim().toUpperCase();
  });
  useEffect(() => {
    const fromUrl = (
      searchParams.get("ref") ||
      searchParams.get("referral") ||
      searchParams.get("referral_code") ||
      ""
    ).trim();
    if (!fromUrl) return;
    const normalized = fromUrl.toUpperCase();
    window.sessionStorage.setItem("gtex_referral_code", normalized);
    setReferralCode(normalized);
  }, [searchParams]);
  const [userFields, setUserFields] = useState({
    full_name: "",
    username: "",
    email: "",
    password: "",
    date_of_birth: "",
    over18: false,
    totp_code: "",
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
    wallet_label: "GTEX Trading Wallet",
  });
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [needsAuthenticator, setNeedsAuthenticator] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const clearFieldError = (key: string) => {
    setFormError(null);
    setFieldErrors((previous) => {
      if (!previous[key]) return previous;
      const next = { ...previous };
      delete next[key];
      return next;
    });
  };

  const updateUser =
    (key: keyof typeof userFields) => (event: React.ChangeEvent<HTMLInputElement>) => {
      clearFieldError(key);
      setUserFields((previous) => ({
        ...previous,
        [key]: event.target.type === "checkbox" ? event.target.checked : event.target.value,
      }));
    };

  const updateCreator =
    (key: keyof typeof creatorFields) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      clearFieldError(key);
      setCreatorFields((previous) => ({ ...previous, [key]: event.target.value }));
    };

  const updateTrader =
    (key: keyof typeof traderFields) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      clearFieldError(key);
      setTraderFields((previous) => ({ ...previous, [key]: event.target.value }));
    };

  const validateSignupBeforeSubmit = (): {
    valid: boolean;
    errors: Record<string, string>;
    summary?: string;
  } => {
    const errors: Record<string, string> = {};
    if (!termsAccepted) {
      errors.terms = "Accept the GTEX terms to continue.";
    }
    if (!userFields.email.trim() || !userFields.email.includes("@")) {
      errors.email = "Enter a valid email address.";
    }
    if (userFields.password.length < 8) {
      errors.password = "Password must be at least 8 characters."; // pragma: allowlist secret
    }
    if (TURNSTILE_SITE_KEY && !turnstileToken) {
      errors.turnstile = "Complete the security check to continue.";
    }

    if (accountType === "user") {
      if (!userFields.over18) {
        errors.over18 = "You must be 18 or older to sign up for a GTEX account.";
      }
      if (userFields.full_name.trim().length < 2) {
        errors.full_name = "Enter your full name (at least 2 characters).";
      }
      if (userFields.username.trim().length < 3) {
        errors.username = "Username must be at least 3 characters.";
      }
    } else if (accountType === "creator") {
      if (creatorFields.creator_name.trim().length < 2) {
        errors.creator_name = "Enter a Creator name (at least 2 characters).";
      }
      if (creatorFields.username.trim().length < 3) {
        errors.username = "Creator username must be at least 3 characters.";
      }
      if (creatorFields.country.trim().length < 2) {
        errors.country = "Enter your country.";
      }
      if (creatorFields.category.trim().length < 2) {
        errors.category = "Select a creator category.";
      }
      if (creatorFields.primary_language.trim().length < 2) {
        errors.primary_language = "Enter your primary language.";
      }
    } else {
      if (traderFields.full_name.trim().length < 2) {
        errors.full_name = "Enter your full legal name.";
      }
      if (traderFields.trading_alias.trim().length < 2) {
        errors.trading_alias = "Enter a trading alias (at least 2 characters).";
      }
      const phone = traderFields.phone_number.trim();
      if (phone.length < 6 || !/^\+?[0-9()\-\s]{6,32}$/.test(phone)) {
        errors.phone_number = "Enter a valid phone number using digits and optional +.";
      }
      if (traderFields.country.trim().length < 2) {
        errors.country = "Enter your country.";
      }
      if (traderFields.preferred_currency.trim().length < 2) {
        errors.preferred_currency = "Select your preferred trading currency.";
      }
      if (!traderFields.wallet_label.trim()) {
        errors.wallet_label = "Enter a label for your trading wallet.";
      }
    }

    const firstKey = Object.keys(errors)[0];
    return {
      valid: Object.keys(errors).length === 0,
      errors,
      summary: firstKey ? errors[firstKey] : undefined,
    };
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});
    setBusy(true);
    try {
      if (mode === "login") {
        const email = userFields.email.trim();
        const totpCode = userFields.totp_code.trim();
        const result = totpCode
          ? await login(email, userFields.password, { totp_code: totpCode })
          : await login(email, userFields.password);
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

      const check = validateSignupBeforeSubmit();
      if (!check.valid) {
        setFieldErrors(check.errors);
        setFormError(check.summary || "Please fix the highlighted fields.");
        toast.error(check.summary || "Please check all required fields.");
        return;
      }

      const securityFields: Record<string, unknown> = {};
      if (TURNSTILE_SITE_KEY && turnstileToken) {
        securityFields.turnstile_token = turnstileToken;
      }
      const referralFields = referralCode.trim() ? { referral_code: referralCode.trim() } : {};

      let signupPayload: Record<string, unknown>;
      if (accountType === "creator") {
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
          ...referralFields,
          ...securityFields,
        };
      } else if (accountType === "coin_trader") {
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
          interests: [...REQUIRED_TRADER_DESKS],
          wallet_label: traderFields.wallet_label.trim() || "GTEX Trading Wallet",
          ...referralFields,
          ...securityFields,
        };
      } else {
        signupPayload = {
          account_type: "user",
          full_name: userFields.full_name.trim(),
          username: userFields.username.trim(),
          email: userFields.email.trim(),
          password: userFields.password,
          is_over_18: true,
          ...(userFields.date_of_birth.trim()
            ? { date_of_birth: userFields.date_of_birth.trim() }
            : {}),
          ...referralFields,
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
      const parsed = parseAuthError(error);
      if (mode === "login" && /authenticator/i.test(parsed.summary)) {
        setNeedsAuthenticator(true);
        setFieldErrors({
          totp_code: "Enter the current 6-digit code from your authenticator app.",
        });
        setFormError("This account uses an authenticator. Enter the current 6-digit code.");
        toast.error("Enter the code from your authenticator app.");
        return;
      }
      setFieldErrors(parsed.fieldErrors);
      setFormError(parsed.summary);
      toast.error(parsed.summary);
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
        <div className="gx-card max-w-md space-y-4 p-8 text-center">
          <p className="gx-eyebrow text-emerald-400">Active session</p>
          <h1 className="gx-h2">You are already signed in</h1>
          <p className="text-sm leading-6 text-slate-300">
            You are signed in as{" "}
            <span className="font-semibold text-white">{user.username || user.email}</span>.
            Specialized creator, trading, and club ownership capabilities can be managed in your
            console.
          </p>
          <div className="pt-2">
            <Link
              to="/app"
              data-testid="return-to-console-link"
              className="gx-btn-primary inline-flex w-full justify-center py-3"
            >
              Return to GTEX Console
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-h-screen bg-[#070B11] lg:grid-cols-2">
      <DocumentHead
        title={
          mode === "signup"
            ? "Create a GTEX account in Nigeria | Club, trader, or creator"
            : "Sign in to GTEX | playgtex.app"
        }
        description={
          mode === "signup"
            ? "Open a free GTEX account in Nigeria. Found a football club, apply as a naira coin trader, or join as a creator."
            : "Sign in to GTEX to run your club, trade coins in naira, and manage players."
        }
        path={mode === "signup" ? "/signup" : "/login"}
      />
      <div className="relative hidden overflow-hidden lg:block">
        <img
          src={publicUrl("assets/stadium_bg.png")}
          alt="GTEX Stadium"
          className="h-full w-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#070B11] via-[#070B11]/60 to-transparent" />
        <div className="absolute bottom-12 left-12 right-12 max-w-md">
          <p className="gx-eyebrow mb-2">GTEX · Club Platform</p>
          <h2 className="gx-h1 text-3xl">Your club awaits.</h2>
          <p className="mt-2 text-sm text-slate-400">
            Live match simulation, squad planning, transfers and tournaments.
          </p>
          <div className="mt-6">
            <GtexAuthAdvertisingPanel />
          </div>
        </div>
      </div>
      <div className="flex items-center justify-center px-4 py-8 sm:px-6 sm:py-12">
        <form
          onSubmit={submit}
          noValidate
          data-testid={mode + "-form"}
          className="w-full max-w-xl space-y-4"
        >
          <div className="lg:hidden">
            <GtexAuthAdvertisingPanel compact />
          </div>
          <Link to="/" className="gx-display text-3xl font-black text-white">
            GTEX
          </Link>
          <h1 className="gx-h2">{mode === "login" ? "Sign in" : "Create a GTEX account"}</h1>

          <div
            data-testid="auth-corporate-advertiser-banner"
            className="rounded-xl border border-[#D4AF37]/40 bg-[#13233A]/90 p-4 shadow-xl backdrop-blur-md"
          >
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#D4AF37]/30 bg-[#D4AF37]/15 text-[#D4AF37]">
                <Building2 className="h-4.5 w-4.5" />
              </div>
              <div className="min-w-0 flex-1 text-xs">
                <p className="font-bold uppercase tracking-[0.14em] text-[#D4AF37]">
                  Corporate Advertiser &amp; Sponsor Portal
                </p>
                <p className="mt-1 leading-relaxed text-[#9AA7BD]">
                  Brands, corporations, and music artists do not need a personal player, creator, or
                  coin trader account to advertise. You can configure and pay for ads directly, or
                  use a dedicated corporate workspace.
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2.5">
                  <Link
                    to="/advertise"
                    data-testid="auth-advertise-direct-link"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#D4AF37] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-[#07111F] transition hover:bg-[#e5c14d]"
                  >
                    <Megaphone className="h-3.5 w-3.5" /> Advertise Directly{" "}
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                  <Link
                    to="/advertiser/register"
                    data-testid="auth-corporate-signup-link"
                    className="inline-flex items-center gap-1 rounded-lg border border-[#22385A] bg-[#0B1729] px-3 py-1.5 text-[11px] font-semibold text-white transition hover:border-[#D4AF37]/60"
                  >
                    Corporate Sign Up
                  </Link>
                  <Link
                    to="/advertiser/login"
                    data-testid="auth-corporate-login-link"
                    className="inline-flex items-center gap-1 rounded-lg border border-transparent px-2.5 py-1.5 text-[11px] font-semibold text-[#9AA7BD] transition hover:text-white"
                  >
                    Corporate Sign In
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {formError && (
            <div
              role="alert"
              data-testid="auth-form-error"
              className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200"
            >
              {formError}
            </div>
          )}

          {mode === "signup" && (
            <section
              className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-4"
              data-testid="signup-account-type-options"
            >
              <p className="mb-3 text-sm font-semibold text-emerald-300">
                Choose your GTEX account
              </p>
              <div
                className="grid grid-cols-1 gap-2 sm:grid-cols-3"
                role="radiogroup"
                aria-label="GTEX account type"
              >
                {[
                  {
                    value: "user" as const,
                    title: "Fan / Club Owner",
                    detail: "Top up, create a club, and hire staff. Your manager runs matchday.",
                  },
                  {
                    value: "coin_trader" as const,
                    title: "Coin Trader",
                    detail: "Buy and sell GTEX Coin. Members get more value for money through you.",
                  },
                  {
                    value: "creator" as const,
                    title: "Creator",
                    detail: "Publish content and build an audience.",
                  },
                ].map((option) => {
                  const selected = accountType === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      data-testid={`signup-account-type-${option.value}`}
                      onClick={() => {
                        setAccountType(option.value);
                        setFieldErrors({});
                        setFormError(null);
                      }}
                      className={`min-h-24 rounded-lg border p-3 text-left transition ${
                        selected
                          ? "border-emerald-400 bg-emerald-400/10 text-white shadow-[0_0_0_1px_rgba(52,211,153,0.15)]"
                          : "border-white/10 bg-slate-950/50 text-slate-300 hover:border-white/25"
                      }`}
                    >
                      <span className="block text-sm font-bold">{option.title}</span>
                      <span className="mt-1 block text-[11px] leading-4 text-slate-400">
                        {option.detail}
                      </span>
                      <span
                        className={`mt-2 block text-[10px] font-semibold uppercase tracking-wider ${selected ? "text-emerald-300" : "text-slate-500"}`}
                      >
                        {selected ? "Selected" : "Choose account"}
                      </span>
                    </button>
                  );
                })}
              </div>
              <select
                data-testid="signup-account-type"
                aria-hidden="true"
                tabIndex={-1}
                className="sr-only"
                value={accountType}
                onChange={(event) => {
                  setAccountType(event.target.value as AccountType);
                  setFieldErrors({});
                  setFormError(null);
                }}
              >
                <option value="user">Fan or club owner</option>
                <option value="coin_trader">Coin trader</option>
                <option value="creator">Creator</option>
              </select>
              <p className="mt-3 text-[11px] leading-5 text-slate-400">
                Fan and club owners share one account type. Coin Traders and Creators have dedicated
                account spaces. Companies and sponsors should use the separate Corporate Advertiser
                portal above.
              </p>
              {accountType === "user" && (
                <ol
                  className="mt-3 space-y-1.5 text-[11px] leading-5 text-slate-300"
                  data-testid="signup-user-guide"
                >
                  <li>
                    Top up your GTEX Coin wallet. Buying and selling through coin traders guarantees
                    more value for money.
                  </li>
                  <li>Create your club. The first 500 club owners receive 2,500 GTEX Coin.</li>
                  <li>
                    Gameplay is not required. Hire the right staff. Your manager handles matchday
                    and tactics.
                  </li>
                </ol>
              )}
              {requestedRole && (
                <div className="mt-2 inline-flex items-center gap-1.5 rounded border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                  <span>Selected path:</span>
                  <span className="font-bold capitalize text-white">{requestedRole}</span>
                </div>
              )}
            </section>
          )}

          {mode === "signup" && accountType === "user" && (
            <>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Full name" error={fieldErrors.full_name}>
                  <input
                    required
                    data-testid="signup-fullname-input"
                    className="gx-input"
                    value={userFields.full_name}
                    onChange={updateUser("full_name")}
                    placeholder="Alex Ferguson"
                  />
                </Field>
                <Field label="Username" error={fieldErrors.username}>
                  <input
                    required
                    minLength={3}
                    data-testid="signup-username-input"
                    className="gx-input"
                    value={userFields.username}
                    onChange={updateUser("username")}
                    placeholder="alex_ferguson"
                  />
                </Field>
              </div>
              <Field label="Date of birth (optional)" error={fieldErrors.date_of_birth}>
                <input
                  type="date"
                  data-testid="signup-dob-input"
                  className="gx-input"
                  value={userFields.date_of_birth}
                  onChange={updateUser("date_of_birth")}
                />
              </Field>
              <div>
                <label className="flex items-center gap-2 text-xs text-slate-400">
                  <input
                    type="checkbox"
                    data-testid="signup-over18-checkbox"
                    checked={userFields.over18}
                    onChange={updateUser("over18")}
                  />
                  I am 18 or older.
                </label>
                {fieldErrors.over18 && (
                  <span className="mt-1 block text-xs text-red-300" role="alert">
                    {fieldErrors.over18}
                  </span>
                )}
              </div>
            </>
          )}

          {mode === "signup" && accountType === "creator" && (
            <section
              data-testid="creator-signup-fields"
              className="space-y-3 rounded-xl border border-fuchsia-400/20 bg-fuchsia-500/[0.04] p-4"
            >
              <p className="text-sm font-semibold text-fuchsia-200">Creator account details</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Creator or brand name" error={fieldErrors.creator_name}>
                  <input
                    required
                    minLength={2}
                    data-testid="creator-name-input"
                    className="gx-input"
                    value={creatorFields.creator_name}
                    onChange={updateCreator("creator_name")}
                    placeholder="Your public creator name"
                  />
                </Field>
                <Field label="Creator username" error={fieldErrors.username}>
                  <input
                    required
                    minLength={3}
                    data-testid="creator-username-input"
                    className="gx-input"
                    value={creatorFields.username}
                    onChange={updateCreator("username")}
                    placeholder="creator_handle"
                  />
                </Field>
                <Field label="Country" error={fieldErrors.country}>
                  <input
                    required
                    data-testid="creator-country-input"
                    className="gx-input"
                    value={creatorFields.country}
                    onChange={updateCreator("country")}
                  />
                </Field>
                <Field label="Creator category" error={fieldErrors.category}>
                  <select
                    required
                    data-testid="creator-category-input"
                    className="gx-input"
                    value={creatorFields.category}
                    onChange={updateCreator("category")}
                  >
                    <option value="sports">Sports</option>
                    <option value="gaming">Gaming</option>
                    <option value="entertainment">Entertainment</option>
                    <option value="music">Music</option>
                    <option value="education">Education</option>
                    <option value="other">Other</option>
                  </select>
                </Field>
                <Field label="Primary language" error={fieldErrors.primary_language}>
                  <input
                    required
                    data-testid="creator-language-input"
                    className="gx-input"
                    value={creatorFields.primary_language}
                    onChange={updateCreator("primary_language")}
                    placeholder="English"
                  />
                </Field>
                <Field
                  label="Main club supported (optional)"
                  error={fieldErrors.main_club_supported}
                >
                  <input
                    data-testid="creator-club-input"
                    className="gx-input"
                    value={creatorFields.main_club_supported}
                    onChange={updateCreator("main_club_supported")}
                    placeholder="Your club"
                  />
                </Field>
              </div>
            </section>
          )}

          {mode === "signup" && accountType === "coin_trader" && (
            <section
              data-testid="trader-signup-fields"
              className="space-y-4 rounded-xl border border-amber-400/20 bg-amber-500/[0.04] p-4"
            >
              <p className="text-sm font-semibold text-amber-200">Coin Trader account details</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Full legal name" error={fieldErrors.full_name}>
                  <input
                    required
                    minLength={2}
                    data-testid="trader-fullname-input"
                    className="gx-input"
                    value={traderFields.full_name}
                    onChange={updateTrader("full_name")}
                    placeholder="Your legal name"
                  />
                </Field>
                <Field label="Trading alias" error={fieldErrors.trading_alias}>
                  <input
                    required
                    minLength={2}
                    data-testid="trader-alias-input"
                    className="gx-input"
                    value={traderFields.trading_alias}
                    onChange={updateTrader("trading_alias")}
                    placeholder="Public trader desk name"
                  />
                </Field>
                <Field label="Phone number" error={fieldErrors.phone_number}>
                  <input
                    required
                    type="tel"
                    data-testid="trader-phone-input"
                    className="gx-input"
                    value={traderFields.phone_number}
                    onChange={updateTrader("phone_number")}
                    placeholder="+234 800 000 0000"
                  />
                </Field>
                <Field label="Country" error={fieldErrors.country}>
                  <input
                    required
                    data-testid="trader-country-input"
                    className="gx-input"
                    value={traderFields.country}
                    onChange={updateTrader("country")}
                  />
                </Field>
                <Field label="Preferred currency" error={fieldErrors.preferred_currency}>
                  <select
                    required
                    data-testid="trader-currency-input"
                    className="gx-input"
                    value={traderFields.preferred_currency}
                    onChange={updateTrader("preferred_currency")}
                  >
                    <option value="NGN">NGN — Nigerian naira</option>
                    <option value="USD">USD — US dollar</option>
                    <option value="EUR">EUR — Euro</option>
                    <option value="GBP">GBP — Pound sterling</option>
                  </select>
                </Field>
                <Field label="Trading experience" error={fieldErrors.trading_experience}>
                  <select
                    required
                    data-testid="trader-experience-input"
                    className="gx-input"
                    value={traderFields.trading_experience}
                    onChange={updateTrader("trading_experience")}
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="professional">Professional</option>
                  </select>
                </Field>
              </div>

              <Field label="Wallet label" error={fieldErrors.wallet_label}>
                <input
                  required
                  data-testid="trader-wallet-label-input"
                  className="gx-input"
                  value={traderFields.wallet_label}
                  onChange={updateTrader("wallet_label")}
                  placeholder="GTEX Trading Wallet"
                />
              </Field>

              <div data-testid="trader-required-desks">
                <span className="gx-label">Desk coverage (required)</span>
                <p className="mt-1 text-xs leading-5 text-slate-400">
                  A coin trader desk always includes GTEX Coin, Fan Coin, P2P, and Escrow. You
                  cannot leave one out.
                </p>
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {REQUIRED_TRADER_DESKS.map((interest) => (
                    <span
                      key={interest}
                      data-testid={`trader-interest-${interest.toLowerCase().replace(/\s+/g, "-")}`}
                      className="rounded-lg border border-amber-400/50 bg-amber-400/15 px-2.5 py-1 text-xs font-medium text-amber-100"
                    >
                      {interest === "Fan Coins" ? "Fan Coin" : interest}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          )}

          {mode === "signup" && (
            <div
              className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-3"
              data-testid="signup-referral-panel"
            >
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-cyan-300">
                Friend's invite
              </p>
              <p className="mt-1 text-sm leading-6 text-slate-200">
                Register with this referral code and receive a 10% bonus on your first qualifying
                deposit. Your friend earns 10% too.
              </p>
              <Field label="Referral code" error={fieldErrors.referral_code}>
                <input
                  type="text"
                  data-testid="signup-referral-code"
                  className="gx-input mt-2 uppercase"
                  value={referralCode}
                  onChange={(event) => {
                    const next = event.target.value.toUpperCase();
                    setReferralCode(next);
                    window.sessionStorage.setItem("gtex_referral_code", next.trim());
                  }}
                  placeholder="CREATOR10"
                />
              </Field>
              {referralCode.trim() && (
                <p className="mt-2 text-xs text-cyan-200" data-testid="signup-referral-applied">
                  Applied referral code: {referralCode.trim()}
                </p>
              )}
            </div>
          )}
          <Field label="Email" error={fieldErrors.email}>
            <input
              required
              type="email"
              data-testid={mode + "-email-input"}
              className="gx-input"
              value={userFields.email}
              onChange={(event) => {
                clearFieldError("email");
                setUserFields((previous) => ({ ...previous, email: event.target.value }));
              }}
              placeholder="alex@example.com"
            />
          </Field>
          <Field label="Password" error={fieldErrors.password}>
            <input
              required
              type="password"
              minLength={8}
              data-testid={mode + "-password-input"}
              className="gx-input"
              value={userFields.password}
              onChange={(event) => {
                clearFieldError("password");
                setUserFields((previous) => ({ ...previous, password: event.target.value }));
              }}
              placeholder="••••••••"
            />
          </Field>
          {mode === "login" && needsAuthenticator && (
            <Field label="Authenticator code" error={fieldErrors.totp_code}>
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                data-testid="login-totp-input"
                className="gx-input"
                value={userFields.totp_code}
                onChange={(event) => {
                  clearFieldError("totp_code");
                  setUserFields((previous) => ({ ...previous, totp_code: event.target.value }));
                }}
                placeholder="6-digit code, if your account uses one"
              />
            </Field>
          )}

          {mode === "signup" && (
            <>
              <div>
                <label className="flex items-center gap-2 text-xs text-slate-400">
                  <input
                    type="checkbox"
                    data-testid="signup-terms-checkbox"
                    checked={termsAccepted}
                    onChange={(event) => {
                      clearFieldError("terms");
                      setTermsAccepted(event.target.checked);
                    }}
                  />
                  I accept the GTEX terms and privacy policy.
                </label>
                {fieldErrors.terms && (
                  <span className="mt-1 block text-xs text-red-300" role="alert">
                    {fieldErrors.terms}
                  </span>
                )}
              </div>
              <TurnstileChallenge
                onTokenChange={(token) => {
                  clearFieldError("turnstile");
                  setTurnstileToken(token);
                }}
              />
            </>
          )}

          <Btn
            type="submit"
            disabled={busy}
            className="w-full py-3"
            data-testid={mode + "-submit-button"}
          >
            {busy ? "Please wait…" : mode === "login" ? "Enter the console" : "Create GTEX account"}
          </Btn>
          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? (
              <>
                New to GTEX?{" "}
                <Link
                  data-testid="goto-signup-link"
                  className="text-emerald-400 hover:text-emerald-300"
                  to="/signup"
                >
                  Create account
                </Link>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <Link
                  data-testid="goto-login-link"
                  className="text-emerald-400 hover:text-emerald-300"
                  to="/login"
                >
                  Sign in
                </Link>
              </>
            )}
          </p>

          <div className="border-t border-[#22385A]/60 pt-3 text-center text-xs text-[#9AA7BD]">
            <span>Representing a company or sponsor? </span>
            <Link to="/advertise" className="font-semibold text-[#D4AF37] hover:underline">
              Visit GTEX Corporate Portal →
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
