import { AuthShell, AuthSwitch } from "@/components/auth/auth-shell";
import { SignupForm } from "@/components/auth/signup-form";

export const metadata = { title: "Sign up — GTEX Concepts" };

export default function SignupPage() {
  return (
    <AuthShell active="/signup" title="Join the exchange" subtitle="Pick your role first — we tailor your home screen around it.">
      <SignupForm />
      <AuthSwitch text="Already have an account?" href="/login" cta="Log in" />
    </AuthShell>
  );
}
