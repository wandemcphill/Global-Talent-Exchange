import { AuthShell, AuthSwitch, Field } from "@/components/auth/auth-shell";

export const metadata = { title: "Log in — GTEX Concepts" };

export default function LoginPage() {
  return (
    <AuthShell active="/login" title="Welcome back" subtitle="Your squad, watchlist and next fixture are waiting.">
      <form className="flex flex-col gap-4" action="/dashboard">
        <Field label="Email" name="email" type="email" autoComplete="email" />
        <Field label="Password" name="password" type="password" autoComplete="current-password" />
        <a href="#" className="-mt-1 self-end text-sm text-muted-foreground hover:text-foreground">
          Forgot password?
        </a>
        <button type="submit" className="mt-2 rounded-lg bg-primary px-4 py-3 font-medium text-primary-foreground transition-opacity hover:opacity-90">
          Log in
        </button>
      </form>
      <AuthSwitch text="New to GTEX?" href="/signup" cta="Create an account" />
    </AuthShell>
  );
}
