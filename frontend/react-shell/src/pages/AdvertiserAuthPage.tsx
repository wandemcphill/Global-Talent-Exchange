import React, { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Building2, Disc3, Lock, Mail, Phone, ShieldCheck, Users } from "lucide-react";
import { toast } from "sonner";
import { parseError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { commercialApi } from "@/lib/commercial/api";

export interface AdvertiserAuthPageProps {
  mode?: "register" | "login";
  initialMode?: "register" | "login";
}

export default function AdvertiserAuthPage({
  mode,
  initialMode,
}: AdvertiserAuthPageProps = {}) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refresh } = useAuth();

  const activeMode = mode || initialMode;
  const pathname = typeof window !== "undefined" ? window.location.pathname : "";
  const isRegister = activeMode ? activeMode === "register" : pathname.includes("/register");
  const initialType = (searchParams.get("type") as "business" | "agency" | "music") || "business";

  const [accountType, setAccountType] = useState<"business" | "agency" | "music">(
    ["business", "agency", "music"].includes(initialType) ? initialType : "business",
  );
  const [companyName, setCompanyName] = useState("");
  const [contactName, setContactName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [stageName, setStageName] = useState("");
  const [labelName, setLabelName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      if (isRegister) {
        const res = await commercialApi.registerAdvertiser({
          account_type: accountType,
          company_name: companyName.trim(),
          contact_name: contactName.trim() || undefined,
          email: email.trim(),
          phone_number: phoneNumber.trim(),
          password,
          website_url: websiteUrl.trim() || undefined,
          stage_name: accountType === "music" ? stageName.trim() || undefined : undefined,
          label_name: accountType === "music" ? labelName.trim() || undefined : undefined,
        });
        await refresh().catch(() => {});
        toast.success("GTEX Commercial Network workspace created.");
        if (res?.workspace?.account_type === "music") {
          navigate("/advertiser/music");
        } else {
          navigate("/advertiser/dashboard");
        }
      } else {
        const res = await commercialApi.loginAdvertiser({
          email: email.trim(),
          password,
        });
        await refresh().catch(() => {});
        toast.success("Signed in to GTEX Commercial Network.");
        if (res?.workspace?.account_type === "music") {
          navigate("/advertiser/music");
        } else {
          navigate("/advertiser/dashboard");
        }
      }
    } catch (err) {
      const msg = parseError(err);
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="min-h-screen bg-[#050811] text-slate-100 flex flex-col justify-between p-4 sm:p-8"
      data-testid="advertiser-auth-page"
    >
      <div className="mx-auto w-full max-w-6xl flex items-center justify-between">
        <Link
          to="/advertise"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to GTEX Commercial Network
        </Link>
        <div className="text-xs font-bold uppercase tracking-widest text-emerald-400">
          Dedicated Commercial Portal • NGN (₦)
        </div>
      </div>

      <div className="mx-auto my-8 w-full max-w-xl rounded-3xl border border-white/10 bg-slate-900/80 p-6 sm:p-10 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 font-black text-slate-950">
            GTEX
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-widest text-emerald-400">
              GTEX COMMERCIAL NETWORK
            </div>
            <h1 className="text-2xl font-bold text-white">
              {isRegister ? "Register Advertiser Workspace" : "Advertiser Sign In"}
            </h1>
          </div>
        </div>

        <p className="mt-3 text-xs leading-relaxed text-slate-400">
          {isRegister
            ? "Create an independent commercial account for Brand Advertising, Agency Client Management, or Music Promotion. Advertiser accounts are isolated from normal GTEX player accounts."
            : "Sign in to your dedicated GTEX Commercial Network workspace to manage campaigns, creative uploads, NGN billing, and analytics."}
        </p>

        {errorMessage && (
          <div
            className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs font-medium text-rose-200"
            role="alert"
          >
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {isRegister && (
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                Advertiser Account Type
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {[
                  {
                    id: "business",
                    label: "Business Advertiser",
                    sub: "Company / Brand",
                    icon: Building2,
                  },
                  {
                    id: "agency",
                    label: "Advertising Agency",
                    sub: "Multi-Client Brands",
                    icon: Users,
                  },
                  {
                    id: "music",
                    label: "Music Advertiser",
                    sub: "Artist / Record Label",
                    icon: Disc3,
                  },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setAccountType(opt.id as any)}
                    data-testid={`account-type-${opt.id}`}
                    className={`flex flex-col items-start rounded-xl border p-3 text-left transition ${
                      accountType === opt.id
                        ? "border-emerald-400 bg-emerald-500/15 text-white"
                        : "border-white/10 bg-slate-950/60 text-slate-400 hover:border-white/20"
                    }`}
                  >
                    <opt.icon className="h-4 w-4 text-emerald-400" />
                    <div className="mt-2 text-xs font-bold text-white">{opt.label}</div>
                    <div className="text-[11px] text-slate-400">{opt.sub}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {isRegister && (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  {accountType === "music"
                    ? "Artist / Record Label / Promoter Name *"
                    : accountType === "agency"
                      ? "Advertising Agency Name *"
                      : "Company or Organisation Name *"}
                </label>
                <input
                  type="text"
                  required
                  minLength={2}
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder={
                    accountType === "music"
                      ? "e.g. Starboy Entertainment / Kazeem"
                      : "e.g. Apex Telecom Nigeria Ltd"
                  }
                  className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
                  data-testid="advertiser-company-name-input"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Contact Person Name
                  </label>
                  <input
                    type="text"
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    placeholder="Full name"
                    className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Contact Telephone *
                  </label>
                  <input
                    type="tel"
                    required
                    minLength={6}
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="+234 800 000 0000"
                    className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
                    data-testid="advertiser-phone-input"
                  />
                </div>
              </div>

              {accountType === "music" ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Stage Name (Optional)
                    </label>
                    <input
                      type="text"
                      value={stageName}
                      onChange={(e) => setStageName(e.target.value)}
                      placeholder="Performing artist name"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Record Label (Optional)
                    </label>
                    <input
                      type="text"
                      value={labelName}
                      onChange={(e) => setLabelName(e.target.value)}
                      placeholder="Independent or Label"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Website URL (Optional)
                  </label>
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    placeholder="https://yourcompany.com"
                    className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
                  />
                </div>
              )}
            </>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Business / Contact Email *
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="commercial@company.com"
              className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
              data-testid="advertiser-email-input"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Password *
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
              data-testid="advertiser-password-input"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-emerald-500 py-3 text-sm font-bold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-50"
            data-testid="advertiser-auth-submit"
          >
            {submitting
              ? "Connecting to GTEX Commercial Network..."
              : isRegister
                ? "Create Advertiser Workspace"
                : "Sign In to Advertiser Portal"}
          </button>
        </form>

        <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4 text-xs text-slate-400">
          {isRegister ? (
            <>
              <span>Already have an advertiser workspace?</span>
              <Link to="/advertiser/login" className="font-bold text-emerald-400 hover:underline">
                Sign In
              </Link>
            </>
          ) : (
            <>
              <span>Need a new commercial workspace?</span>
              <Link to="/advertiser/register" className="font-bold text-emerald-400 hover:underline">
                Register Advertiser Account
              </Link>
            </>
          )}
        </div>
      </div>

      <div className="mx-auto text-center text-xs text-slate-500">
        GTEX Commercial Network • Independent Advertiser Authentication • All Billing in Nigerian Naira (₦) •{" "}
        <a href="mailto:omotundeoni@playgtex.app" className="text-slate-400 hover:text-emerald-400">
          omotundeoni@playgtex.app
        </a>{" "}
        •{" "}
        <a href="tel:+2348069938718" className="text-slate-400 hover:text-emerald-400">
          +234 806 993 8718
        </a>{" "}
        • Lagos, Nigeria
      </div>
    </div>
  );
}
