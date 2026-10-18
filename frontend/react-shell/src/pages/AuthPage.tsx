import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { publicUrl } from "@/lib/publicPath";
import { Btn } from "@/components/gtex/ui";

function Field({ label, children }: any) {
  return (
    <label className="block">
      <span className="gx-label">{label}</span>
      {children}
    </label>
  );
}

export default function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { login, signup } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  // Normal account first (issue #228 / #274). Club creation stays on /onboarding.
  const [f, setF] = useState<any>({
    full_name: "",
    username: "",
    email: "",
    password: "",
    country: "",
    city: "",
    over18: false,
  });
  const set = (k: string) => (e: any) =>
    setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const submit = async (e: any) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        await login(f.email, f.password);
        navigate("/app");
      } else {
        if (!f.over18) throw new Error("You must be 18 or older to create a GTEX account.");
        const country = String(f.country || "").trim();
        if (!country) throw new Error("Enter your country.");
        await signup({
          full_name: f.full_name,
          username: f.username,
          email: f.email,
          password: f.password,
          country,
          city: String(f.city || "").trim() || undefined,
          is_over_18: true,
        });
        navigate("/onboarding");
      }
    } catch (err: any) {
      toast.error(err?.response ? errMsg(err) : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen bg-[#070B11] lg:grid-cols-2">
      <div className="relative hidden overflow-hidden lg:block">
        <img src={publicUrl("/img/hero.jpg")} alt="Stadium under lights" className="absolute inset-0 h-full w-full object-cover opacity-50" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#070B11] via-[#070B11]/40 to-transparent" />
        <div className="absolute bottom-12 left-12 right-12">
          <p className="gx-eyebrow mb-3">GTEX Owner Console</p>
          <p className="gx-h2">{mode === "login" ? "Back to the boardroom." : "Start with a normal GTEX account."}</p>
          <p className="mt-3 max-w-md text-sm text-slate-300">
            Create your identity first. You claim or create a club after sign-in.
          </p>
        </div>
      </div>
      <div className="flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} data-testid={`${mode}-form`} className="w-full max-w-md space-y-4">
          <Link to="/" className="gx-display text-3xl font-black text-white">
            GTEX
          </Link>
          <h1 className="gx-h2">{mode === "login" ? "Sign in" : "Create account"}</h1>
          {mode === "signup" && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Full name">
                  <input required data-testid="signup-fullname-input" className="gx-input" value={f.full_name} onChange={set("full_name")} />
                </Field>
                <Field label="Username">
                  <input required minLength={3} data-testid="signup-username-input" className="gx-input" value={f.username} onChange={set("username")} />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Country">
                  <input required data-testid="signup-country-input" className="gx-input" placeholder="Nigeria" value={f.country} onChange={set("country")} />
                </Field>
                <Field label="City (optional)">
                  <input data-testid="signup-city-input" className="gx-input" placeholder="Lagos" value={f.city} onChange={set("city")} />
                </Field>
              </div>
            </>
          )}
          <Field label="Email">
            <input required type="email" data-testid={`${mode}-email-input`} className="gx-input" value={f.email} onChange={set("email")} />
          </Field>
          <Field label="Password">
            <input required type="password" minLength={8} data-testid={`${mode}-password-input`} className="gx-input" value={f.password} onChange={set("password")} />
          </Field>
          {mode === "signup" && (
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <input type="checkbox" data-testid="signup-over18-checkbox" checked={f.over18} onChange={set("over18")} /> I am 18 or older and accept the GTEX terms.
            </label>
          )}
          <Btn type="submit" disabled={busy} className="w-full py-3" data-testid={`${mode}-submit-button`}>
            {busy ? "Please wait…" : mode === "login" ? "Enter the console" : "Create account"}
          </Btn>
          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? (
              <>
                New here?{" "}
                <Link data-testid="goto-signup-link" className="text-emerald-400 hover:text-emerald-300" to="/signup">
                  Create an account
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
        </form>
      </div>
    </div>
  );
}
