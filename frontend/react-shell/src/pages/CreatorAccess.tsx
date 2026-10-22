import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BadgeCheck, Clock3, Video } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { Btn, Chip, Loading, Panel } from "@/components/gtex/ui";

const PLATFORMS = ["youtube", "twitch", "tiktok"];

export default function CreatorAccess() {
  const queryClient = useQueryClient();
  const { data: application, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["creator-application"],
    queryFn: async () => (await api.get("/creator/application")).data,
    retry: false,
  });
  const [handle, setHandle] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [platform, setPlatform] = useState("youtube");
  const [followers, setFollowers] = useState("0");
  const [socialLinks, setSocialLinks] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");

  const status = String(application?.status || "").toLowerCase();
  const canSubmit = !application || status === "rejected";

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError("");
    const links = socialLinks.split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
    const followerCount = Number(followers);
    if (links.length === 0) {
      setFormError("Add at least one public social link for review.");
      return;
    }
    if (!Number.isInteger(followerCount) || followerCount < 0) {
      setFormError("Enter a valid follower count.");
      return;
    }

    setBusy(true);
    try {
      await api.post("/creator/apply", {
        requested_handle: handle.trim().toLowerCase(),
        display_name: displayName.trim(),
        platform,
        follower_count: followerCount,
        social_links: links,
      });
      await queryClient.invalidateQueries({ queryKey: ["creator-application"] });
      await refetch();
      toast.success("Creator application submitted for review.");
    } catch (error: any) {
      const message = errMsg(error);
      setFormError(message);
      if (/email_verification_required|phone_verification_required/i.test(message)) {
        setFormError(
          "GTEX requires verified email and phone contact before creator review. Your application was not submitted. Complete the contact-verification step before trying again."
        );
      }
    } finally {
      setBusy(false);
    }
  };

  if (isLoading) return <Loading label="Loading creator access..." />;

  return (
    <div className="space-y-6 p-4 sm:p-8" data-testid="creator-access-screen">
      <Link to="/app" className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white">
        <ArrowLeft size={14} /> Back to GTEX
      </Link>

      <section className="relative overflow-hidden rounded-3xl border border-pink-400/25 bg-gradient-to-br from-[#241020] via-[#101522] to-[#070B11] p-6 sm:p-9">
        <div className="flex items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-pink-400/10 text-pink-300">
            <Video size={24} />
          </span>
          <div>
            <p className="gx-eyebrow mb-2 text-pink-300">Creator tools · existing GTEX account</p>
            <h1 className="gx-display text-3xl font-black uppercase text-white sm:text-4xl">Turn your football voice into a platform.</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
              Creator access is an optional capability on your normal GTEX account—not a separate login or account type. Submit your public creator identity for review; accepted creators can use the creator tools enabled for their profile.
            </p>
          </div>
        </div>
      </section>

      {isError && (
        <Panel eyebrow="Account status" title="Creator status unavailable">
          <p className="text-sm text-slate-300">{errMsg(error)}</p>
          <Btn className="mt-4" onClick={() => refetch()}>Retry status</Btn>
        </Panel>
      )}

      {application && (
        <Panel eyebrow="Application status" title={application.display_name || "Creator application"}>
          <div className="flex flex-wrap items-center gap-3">
            <Chip tone={status === "approved" ? "good" : status === "rejected" ? "warn" : "default"}>
              {status.replace(/_/g, " ") || "submitted"}
            </Chip>
            <span className="text-sm text-slate-400">@{application.requested_handle} · {application.platform}</span>
          </div>
          {application.review_notes && <p className="mt-3 text-sm text-slate-300">Review notes: {application.review_notes}</p>}
          {status === "approved" ? (
            <p className="mt-4 text-sm text-emerald-200"><BadgeCheck className="mr-2 inline" size={16} />Creator access is approved for this GTEX account.</p>
          ) : status === "pending" || status === "verification_requested" ? (
            <p className="mt-4 text-sm text-slate-300"><Clock3 className="mr-2 inline" size={16} />Your application is awaiting review. You do not need a separate creator login.</p>
          ) : null}
        </Panel>
      )}

      {canSubmit && (
        <Panel eyebrow={application ? "Resubmission" : "Next step"} title={application ? "Update your creator application" : "Apply for creator access"}>
          <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="gx-label">Requested handle</span>
              <input required minLength={3} maxLength={64} className="gx-input mt-2" placeholder="creator.name" value={handle} onChange={(e) => setHandle(e.target.value)} />
            </label>
            <label className="block">
              <span className="gx-label">Public display name</span>
              <input required minLength={2} maxLength={120} className="gx-input mt-2" placeholder="Your creator name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            </label>
            <label className="block">
              <span className="gx-label">Main platform</span>
              <select className="gx-input mt-2" value={platform} onChange={(e) => setPlatform(e.target.value)}>
                {PLATFORMS.map((item) => <option key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="gx-label">Follower count</span>
              <input required type="number" min={0} step={1} className="gx-input mt-2" value={followers} onChange={(e) => setFollowers(e.target.value)} />
            </label>
            <label className="block md:col-span-2">
              <span className="gx-label">Public social links (one per line)</span>
              <textarea required rows={3} className="gx-input mt-2" placeholder="https://..." value={socialLinks} onChange={(e) => setSocialLinks(e.target.value)} />
            </label>
            {formError && <p role="alert" className="md:col-span-2 rounded border border-red-500/30 bg-red-950/30 p-3 text-sm text-red-200">{formError}</p>}
            <div className="md:col-span-2">
              <Btn type="submit" disabled={busy}>{busy ? "Submitting..." : application ? "Resubmit for review" : "Submit creator application"}</Btn>
            </div>
          </form>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            Contact verification is enforced by the backend before an application can be submitted. This form does not mark an email or phone as verified on your behalf.
          </p>
        </Panel>
      )}
    </div>
  );
}
