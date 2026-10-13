"use client";

import { useState } from "react";
import { Briefcase, Shield, Video } from "lucide-react";
import { Field } from "./auth-shell";
import { cn } from "@/lib/utils";

const roles = [
  { id: "manager", label: "Manager", desc: "Run a club, trade cards", icon: Shield },
  { id: "scout", label: "Scout", desc: "Find and develop regens", icon: Briefcase },
  { id: "creator", label: "Creator", desc: "Build a fan following", icon: Video },
] as const;

export function SignupForm() {
  const [role, setRole] = useState<(typeof roles)[number]["id"]>("manager");

  return (
    <form className="flex flex-col gap-5" action="/dashboard">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">I want to play as</legend>
        <div className="grid grid-cols-3 gap-2">
          {roles.map(({ id, label, desc, icon: Icon }) => (
            <label
              key={id}
              className={cn(
                "flex cursor-pointer flex-col gap-1.5 rounded-lg border p-3 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
                role === id ? "border-primary bg-primary/10" : "border-border bg-card hover:bg-muted",
              )}
            >
              <input type="radio" name="role" value={id} checked={role === id} onChange={() => setRole(id)} className="sr-only" />
              <Icon className={cn("size-5", role === id ? "text-primary" : "text-muted-foreground")} aria-hidden />
              <span className="font-display text-base font-bold uppercase leading-none">{label}</span>
              <span className="text-[11px] leading-snug text-muted-foreground">{desc}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <Field label="Club or display name" name="name" autoComplete="nickname" />
      <Field label="Email" name="email" type="email" autoComplete="email" />
      <Field label="Password" name="password" type="password" autoComplete="new-password" />
      <button type="submit" className="mt-1 rounded-lg bg-primary px-4 py-3 font-medium text-primary-foreground transition-opacity hover:opacity-90">
        Create account
      </button>
    </form>
  );
}
