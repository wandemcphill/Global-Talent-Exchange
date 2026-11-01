import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BadgeCheck, Camera, Clock3, AlertTriangle, ShieldAlert, Video } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Btn, Chip, Loading, Panel } from "@/components/gtex/ui";

const PLATFORMS = [
  { id: "tiktok", label: "TikTok" },
  { id: "instagram", label: "Instagram" },
  { id: "twitch", label: "Twitch" },
  { id: "youtube", label: "YouTube" },
  { id: "x", label: "X (formerly Twitter)" },
];

export default function CreatorAccess() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const accountType = String(user?.account_type || user?.accountType || "user").toLowerCase();

  const {
    data: ownershipData,
    isLoading: isOwnershipLoading,
    isError: isOwnershipError,
    error: ownershipError,
    refetch: refetchOwnership,
  } = useQuery({
    queryKey: ["creator-promotion-owned-clubs", user?.id],
    queryFn: async () => (await api.get("/owner/onboarding")).data,
    enabled: Boolean(user?.id) && accountType === "user",
    retry: false,
  });

  const { data: application, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["creator-application", user?.id],
    queryFn: async () => (await api.get("/creator/application")).data,
    enabled: Boolean(user?.id) && accountType === "user",
    retry: false,
  });

  const [handle, setHandle] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [platform, setPlatform] = useState("tiktok");
  const [profileUrl, setProfileUrl] = useState("");
  const [followers, setFollowers] = useState("20000");
  const [socialLinks, setSocialLinks] = useState("");
  const [selfieAttachmentId, setSelfieAttachmentId] = useState("");
  const [selfiePreview, setSelfiePreview] = useState<string | null>(null);
  const [uploadingSelfie, setUploadingSelfie] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");

  const rawStatus = String(application?.status || "").toLowerCase();
  const status = rawStatus === "verification_requested" ? "additional_info_required" : rawStatus;
  const isCreatorAccount = accountType === "creator";
  const isCoinTraderAccount = accountType === "coin_trader";
  const ownedClubCount = Array.isArray(ownershipData?.clubs) ? ownershipData.clubs.length : 0;
  const stillOwnsClubs = ownedClubCount > 0;

  const canSubmit =
    !isCreatorAccount &&
    !isCoinTraderAccount &&
    !isOwnershipError &&
    !stillOwnsClubs &&
    (!application || status === "rejected" || status === "additional_info_required");

  const handleSelfieCapture = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadingSelfie(true);
    setFormError("");
    try {
      const reader = new FileReader();
      reader.onload = (e) => setSelfiePreview(e.target?.result as string);
      reader.readAsDataURL(file);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("scope", "creator_selfie");

      const response = await api.post("/attachments", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const attachmentId = response.data?.id || response.data?.attachment_id;
      if (attachmentId) {
        setSelfieAttachmentId(attachmentId);
        toast.success("Selfie captured and attached successfully.");
      }
    } catch (err: any) {
      toast.error("Failed to upload selfie: " + errMsg(err));
    } finally {
      setUploadingSelfie(false);
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError("");

    const followerCount = Number(followers);
    if (!Number.isInteger(followerCount) || followerCount < 20000) {
      setFormError("Applicant must have at least 20,000 followers on one eligible social media profile.");
      return;
    }

    if (!profileUrl.trim()) {
      setFormError("A public profile URL or username is required for manual audience review.");
      return;
    }

    if (platform === "facebook") {
      setFormError("Facebook is excluded from eligible Creator platforms.");
      return;
    }

    const additionalLinks = socialLinks
      .split(/\r?\n/)
      .map((val) => val.trim())
      .filter(Boolean);

    setBusy(true);
    try {
      await api.post("/creator/apply", {
        requested_handle: handle.trim().toLowerCase(),
        display_name: displayName.trim(),
        platform,
        follower_count: followerCount,
        profile_url: profileUrl.trim(),
        social_links: additionalLinks.length ? additionalLinks : [profileUrl.trim()],
        selfie_attachment_id: selfieAttachmentId || undefined,
      });
      await queryClient.invalidateQueries({ queryKey: ["creator-application"] });
      await refetch();
      toast.success("Creator application submitted for manual audience review.");
    } catch (err: any) {
      const backendDetail = err?.response?.data?.detail;
      const message = typeof backendDetail === "string" ? backendDetail : errMsg(err);
      if (/club_ownership_prevents_creator_promotion|active_club_prevents_creator_promotion/i.test(message)) {
        setFormError(
          "Creator promotion is available only when your account no longer owns any clubs. Sell or transfer all clubs you still own first, then apply again."
        );
      } else if (/coin_trader_account_cannot_be_promoted_to_creator|creator_promotion_requires_normal_account/i.test(message)) {
        setFormError(
          "This account cannot be promoted to Creator. Coin Trader is a separate account lane; use a normal User account or register directly as a Creator."
        );
      } else {
        setFormError(message);
      }
    } finally {
      setBusy(false);
    }
  };

  if (isLoading || (accountType === "user" && isOwnershipLoading)) {
    return <Loading label="Checking creator access and club eligibility..." />;
  }

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
            <p className="gx-eyebrow mb-2 text-pink-300">Creator account promotion</p>
            <h1 className="gx-display text-3xl font-black uppercase text-white sm:text-4xl">Turn your football voice into a platform.</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
              Apply for Creator status with at least <strong>20,000 followers</strong> on TikTok, Instagram, Twitch, YouTube, or X. All Creator applications undergo manual audience review before approval. Government identity documents (BVN/NIN) are never collected for Creator verification.
            </p>
          </div>
        </div>
      </section>

      {isCreatorAccount && (
        <Panel eyebrow="Dedicated account" title="Creator account active">
          <p className="text-sm leading-6 text-slate-300">
            This GTEX ID is a dedicated Creator account. Creator is an exclusive account lane and cannot be changed back to a club-owner or coin-trader account.
          </p>
        </Panel>
      )}

      {isCoinTraderAccount && (
        <Panel eyebrow="Dedicated account" title="Coin Trader accounts cannot promote to Creator">
          <p className="text-sm leading-6 text-slate-300">
            Coin Trader accounts operate in the exclusive trading lane. Creator promotion is available only to normal GTEX member accounts with no active clubs.
          </p>
        </Panel>
      )}

      {!isCreatorAccount && !isCoinTraderAccount && isOwnershipError && (
        <Panel eyebrow="Promotion eligibility" title="Could not verify club ownership">
          <p className="text-sm leading-6 text-slate-300">
            GTEX could not confirm whether this User account still owns clubs, so application submission is disabled. Retry the ownership check before applying.
          </p>
          <Btn className="mt-4" onClick={() => refetchOwnership()}>Retry ownership check</Btn>
          {ownershipError && <p className="mt-3 text-xs text-slate-500">{errMsg(ownershipError)}</p>}
        </Panel>
      )}

      {!isCreatorAccount && !isCoinTraderAccount && !isOwnershipError && stillOwnsClubs && (
        <Panel eyebrow="Promotion eligibility" title="Sell or transfer your clubs first">
          <p className="text-sm leading-6 text-slate-300">
            Creator promotion is available only to normal User accounts that no longer own any clubs. Your account currently has {ownedClubCount} club{ownedClubCount === 1 ? "" : "s"} under its ownership. Sell or transfer every club you still own before submitting a Creator application.
          </p>
        </Panel>
      )}

      {isError && (
        <Panel eyebrow="Account status" title="Creator status unavailable">
          <p className="text-sm text-slate-300">{errMsg(error)}</p>
          <Btn className="mt-4" onClick={() => refetch()}>Retry status</Btn>
        </Panel>
      )}

      {application && (
        <Panel eyebrow="Application status" title={application.display_name || "Creator application"}>
          <div className="flex flex-wrap items-center gap-3">
            <Chip tone={
              status === "approved" ? "emerald" :
              status === "rejected" ? "red" :
              status === "suspended" ? "amber" :
              status === "additional_info_required" ? "amber" : "blue"
            }>
              {status.replace(/_/g, " ").toUpperCase() || "PENDING"}
            </Chip>
            <span className="text-sm text-slate-400">@{application.requested_handle} · {application.platform}</span>
          </div>

          {application.profile_url && (
            <p className="mt-3 text-xs text-slate-400">
              Submitted profile: <a href={application.profile_url} target="_blank" rel="noopener noreferrer" className="text-pink-400 hover:underline">{application.profile_url}</a>
            </p>
          )}

          {application.review_notes && (
            <div className="mt-3 rounded-lg border border-slate-700 bg-slate-800/50 p-3">
              <p className="text-xs font-semibold uppercase text-slate-400">Admin Review Notes</p>
              <p className="mt-1 text-sm text-slate-200">{application.review_notes}</p>
            </div>
          )}

          {status === "approved" && (
            <p className="mt-4 text-sm text-emerald-200"><BadgeCheck className="mr-2 inline" size={16} />Creator access is approved for this GTEX account.</p>
          )}

          {status === "pending" && (
            <p className="mt-4 text-sm text-slate-300"><Clock3 className="mr-2 inline" size={16} />Your application is awaiting manual reviewer inspection. Privileges remain inactive while review is pending.</p>
          )}

          {status === "additional_info_required" && (
            <div className="mt-4 space-y-2">
              <p className="text-sm text-amber-200"><AlertTriangle className="mr-2 inline" size={16} />Additional information required. Please update your public profile URL or selfie and resubmit below.</p>
            </div>
          )}

          {status === "suspended" && (
            <p className="mt-4 text-sm text-red-300"><ShieldAlert className="mr-2 inline" size={16} />This Creator profile has been suspended by GTEX administration.</p>
          )}
        </Panel>
      )}

      {canSubmit && (
        <Panel eyebrow={application ? "Resubmission" : "Application"} title={application ? "Update creator application" : "Apply for Creator status"}>
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
                {PLATFORMS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="gx-label">Follower count (Minimum 20,000 on one platform)</span>
              <input required type="number" min={20000} step={1} className="gx-input mt-2" value={followers} onChange={(e) => setFollowers(e.target.value)} />
            </label>
            <label className="block md:col-span-2">
              <span className="gx-label">Public profile URL or handle (manual review will verify)</span>
              <input required type="url" className="gx-input mt-2" placeholder="https://tiktok.com/@username or https://instagram.com/username" value={profileUrl} onChange={(e) => setProfileUrl(e.target.value)} />
            </label>
            <label className="block md:col-span-2">
              <span className="gx-label">Additional social profile links (optional, one per line)</span>
              <textarea rows={2} className="gx-input mt-2" placeholder="https://youtube.com/@channel&#10;https://x.com/handle" value={socialLinks} onChange={(e) => setSocialLinks(e.target.value)} />
            </label>

            <div className="block md:col-span-2 rounded-xl border border-slate-700 bg-slate-900/60 p-4">
              <span className="gx-label block mb-2">Live selfie capture (application camera)</span>
              <p className="text-xs text-slate-400 mb-3">Capture a live selfie from your device camera to compare against your public creator profile during review.</p>
              <div className="flex items-center gap-4">
                <label className="cursor-pointer inline-flex items-center gap-2 rounded-xl border border-pink-500/40 bg-pink-500/10 px-4 py-2 text-xs font-semibold text-pink-300 hover:bg-pink-500/20">
                  <Camera size={16} />
                  <span>{uploadingSelfie ? "Uploading selfie..." : selfieAttachmentId ? "Retake selfie" : "Capture live selfie"}</span>
                  <input type="file" accept="image/*" capture="user" className="hidden" onChange={handleSelfieCapture} disabled={uploadingSelfie} />
                </label>
                {selfieAttachmentId && (
                  <span className="text-xs text-emerald-400 flex items-center gap-1">
                    <BadgeCheck size={14} /> Selfie attached
                  </span>
                )}
              </div>
              {selfiePreview && (
                <div className="mt-3">
                  <img src={selfiePreview} alt="Selfie preview" className="size-20 rounded-lg object-cover border border-slate-600" />
                </div>
              )}
            </div>

            {formError && <p role="alert" className="md:col-span-2 rounded border border-red-500/30 bg-red-950/30 p-3 text-sm text-red-200">{formError}</p>}
            <div className="md:col-span-2">
              <Btn type="submit" disabled={busy || uploadingSelfie}>
                {busy ? "Submitting..." : application ? "Resubmit creator application" : "Submit creator application"}
              </Btn>
            </div>
          </form>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            GTEX does not require BVN, NIN, or government identity cards for Creator audience verification. A manual administrator will open your profile URL and verify your public follower count and live selfie.
          </p>
        </Panel>
      )}
    </div>
  );
}
