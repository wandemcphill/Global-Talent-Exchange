import { API, api, tokens } from "@/lib/api";

export const BACKEND_BASE_URL = API.replace(/\/api$/, "");

export function resolveCommercialMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  const trimmed = url.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://") || trimmed.startsWith("blob:") || trimmed.startsWith("data:")) {
    return trimmed;
  }
  if (trimmed.startsWith("/")) {
    return `${BACKEND_BASE_URL}${trimmed}`;
  }
  return trimmed;
}

export function formatNairaMinor(minorKobo: number | null | undefined): string {
  if (minorKobo === null || minorKobo === undefined) {
    return "Pricing pending admin configuration (NGN)";
  }
  const naira = minorKobo / 100;
  return `₦${naira.toLocaleString("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export const formatNairaFromKobo = formatNairaMinor;

export interface PublicBrandAd {
  id: string;
  brand_name: string;
  headline: string;
  description: string;
  cta_label?: string;
  placement: string;
  placements?: string[];
  destination_url: string;
  logo_url?: string | null;
  creative_url?: string | null;
  creative_media_type?: string | null;
  is_silent_creative?: boolean;
  sponsored_label?: string;
  priority?: number;
}

export interface AdPlacementSpec {
  id: string;
  placement_key: string;
  name: string;
  division: "brand" | "music";
  category: string;
  description: string;
  supported_media_types: string[];
  aspect_ratio: string;
  recommended_width: number | null;
  recommended_height: number | null;
  max_file_size_bytes: number;
  max_duration_seconds: number | null;
  requires_silent_media: boolean;
  weekly_rate_minor_ngn: number | null;
  weekly_rate_formatted_ngn: string | null;
  pricing_configured: boolean;
  is_enabled: boolean;
  delivery_surface_ready: boolean;
  frequency_cap_per_session: number;
  rotation_interval_seconds: number;
  priority_weight: number;
  device_compatibility: string[];
}

export interface AdPricingPackage {
  id: string;
  package_code: string;
  name: string;
  division: "brand" | "music";
  description: string;
  duration_days: number;
  placement_keys: string[];
  is_bundle: boolean;
  is_subscription: boolean;
  billing_interval_days: number | null;
  price_minor_ngn: number | null;
  price_formatted_ngn: string | null;
  pricing_configured: boolean;
  currency: "NGN";
  discount_percent: number;
  is_active: boolean;
  sort_order: number;
}

export interface CommercialPriceCalculation {
  division: "brand" | "music";
  placements: string[];
  duration_days: number;
  package_code: string | null;
  is_subscription: boolean;
  currency: "NGN";
  pricing_configured: boolean;
  pricing_status: "configured" | "unconfigured";
  subtotal_minor_ngn: number | null;
  discount_minor_ngn: number;
  total_minor_ngn: number | null;
  formatted_total_ngn: string | null;
  breakdown: Array<Record<string, any>>;
  unconfigured_items: string[];
}

export interface AdvertiserWorkspace {
  id: string;
  owner_user_id: string;
  account_type: "business" | "agency" | "music";
  company_name: string;
  contact_name: string | null;
  contact_email: string;
  contact_phone: string;
  website_url: string | null;
  logo_asset_id: string | null;
  logo_url: string | null;
  stage_name: string | null;
  label_name: string | null;
  status: string;
  verified_at: string | null;
  suspended_reason: string | null;
  default_currency: string;
  created_at: string;
  updated_at: string;
}

export type CommercialMediaAssetKind =
  | "logo"
  | "brand_image"
  | "brand_video"
  | "music_audio"
  | "music_artwork";

export const COMMERCIAL_MEDIA_RULES: Record<
  CommercialMediaAssetKind,
  {
    maxBytes: number;
    maxLabel: string;
    acceptedMimeTypes: string[];
    maxDurationSeconds?: number;
  }
> = {
  logo: {
    maxBytes: 5 * 1024 * 1024,
    maxLabel: "5 MB",
    acceptedMimeTypes: ["image/png", "image/jpeg", "image/webp"],
  },
  brand_image: {
    maxBytes: 15 * 1024 * 1024,
    maxLabel: "15 MB",
    acceptedMimeTypes: ["image/png", "image/jpeg", "image/webp"],
  },
  brand_video: {
    maxBytes: 50 * 1024 * 1024,
    maxLabel: "50 MB",
    acceptedMimeTypes: ["video/mp4", "video/webm"],
    maxDurationSeconds: 45,
  },
  music_audio: {
    maxBytes: 50 * 1024 * 1024,
    maxLabel: "50 MB",
    acceptedMimeTypes: ["audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/ogg", "audio/mp4", "audio/aac"],
    maxDurationSeconds: 420,
  },
  music_artwork: {
    maxBytes: 10 * 1024 * 1024,
    maxLabel: "10 MB",
    acceptedMimeTypes: ["image/png", "image/jpeg", "image/webp"],
  },
};

export function validateCommercialMediaFile(
  file: File,
  assetKind: CommercialMediaAssetKind,
): string | null {
  const rule = COMMERCIAL_MEDIA_RULES[assetKind];
  if (!rule) {
    return "Unsupported media asset kind.";
  }
  if (file.size <= 0) {
    return "Selected file is empty.";
  }
  if (file.size > rule.maxBytes) {
    return `File exceeds maximum size for ${assetKind.replace("_", " ")} (${rule.maxLabel}).`;
  }
  if (file.type && !rule.acceptedMimeTypes.includes(file.type.toLowerCase())) {
    return `Unsupported format '${file.type}'. Allowed: ${rule.acceptedMimeTypes.join(", ")}.`;
  }
  return null;
}

export interface AdvertiserMediaAsset {
  id: string;
  workspace_id: string | null;
  asset_kind: CommercialMediaAssetKind;
  original_filename: string;
  sanitized_filename: string;
  mime_type: string;
  size_bytes: number;
  sha256_hash: string;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  has_audio_track: boolean;
  is_silent_verified: boolean;
  validation_status: string;
  storage_provider?: string;
  storage_key?: string | null;
  cloudinary_public_id?: string | null;
  cloudinary_resource_type?: string | null;
  cloudinary_url?: string | null;
  preview_url?: string | null;
  access_classification?: string;
  metadata_json?: Record<string, any>;
  delivery_url: string;
  created_at: string;
}

export interface CommercialCampaign {
  id: string;
  workspace_id: string | null;
  advertiser_id: string | null;
  client_brand_id: string | null;
  campaign_type: "brand" | "music";
  brand_name: string;
  contact_email: string | null;
  contact_phone: string | null;
  contact_name: string | null;
  website_url: string | null;
  headline: string;
  description: string;
  placement: string;
  placements: string[];
  destination_url: string;
  logo_asset_id: string | null;
  logo_url: string | null;
  creative_asset_id: string | null;
  creative_url: string | null;
  creative_media_type: string | null;
  is_silent_creative: boolean;
  duration_days: number;
  start_at: string | null;
  end_at: string | null;
  status: string;
  payment_status: string;
  payment_reference: string | null;
  price_minor_ngn: number;
  price_formatted_ngn: string;
  currency: string;
  pricing_model: string;
  is_subscription: boolean;
  is_approved: boolean;
  is_active: boolean;
  review_note: string | null;
  music_title: string | null;
  music_artist_name: string | null;
  music_genre: string | null;
  music_audio_asset_id: string | null;
  music_artwork_asset_id: string | null;
  music_audio_url: string | null;
  music_artwork_url: string | null;
  music_explicit_content: boolean;
  music_rights_declaration_accepted: boolean;
  music_rights_verified: boolean;
  music_rights_holder: string | null;
  created_at: string;
  updated_at: string;
}

export interface MusicRotationTrack {
  campaign_id: string;
  track_id: string;
  title: string;
  artist: string;
  genre: string | null;
  audio_url: string;
  artwork_url: string | null;
  explicit_content: boolean;
  sponsored_disclosure: string;
  rights_holder: string | null;
  priority: number;
  duration_days: number;
  start_at: string;
  end_at: string;
}

export const commercialApi = {
  async listPublicPlacements(division?: "brand" | "music"): Promise<AdPlacementSpec[]> {
    const { data } = await api.get("/v2/public/ads/placements", {
      params: division ? { division } : undefined,
    });
    return Array.isArray(data) ? data : [];
  },

  async listPublicPackages(division?: "brand" | "music"): Promise<AdPricingPackage[]> {
    const { data } = await api.get("/v2/public/ads/packages", {
      params: division ? { division } : undefined,
    });
    return Array.isArray(data) ? data : [];
  },

  async calculatePrice(payload: {
    division: "brand" | "music";
    placements: string[];
    duration_days: number;
    package_code?: string | null;
    is_subscription?: boolean;
  }): Promise<CommercialPriceCalculation> {
    const { data } = await api.post("/v2/public/ads/calculate-price", payload);
    return data;
  },

  async getMusicRotationFeed(limit = 20): Promise<{
    generated_at: string;
    rotation_policy: Record<string, any>;
    tracks: MusicRotationTrack[];
  }> {
    const { data } = await api.get("/v2/public/ads/music/rotation", { params: { limit } });
    return data;
  },

  async getStadiumInventory(limit = 25): Promise<{
    generated_at: string;
    campaigns: PublicBrandAd[];
  }> {
    const { data } = await api.get("/v2/public/ads/stadium/inventory", { params: { limit } });
    return data;
  },

  async registerAdvertiser(payload: {
    account_type: "business" | "agency" | "music";
    company_name: string;
    contact_name?: string;
    email: string;
    phone_number: string;
    password: string;
    website_url?: string;
    stage_name?: string;
    label_name?: string;
  }) {
    const { data } = await api.post("/v2/advertiser/auth/register", payload);
    if (data?.access_token) {
      tokens.set(data.access_token, data.refresh_token);
    }
    return data;
  },

  async loginAdvertiser(payload: { email: string; password: string }) {
    const { data } = await api.post("/v2/advertiser/auth/login", payload);
    if (data?.access_token) {
      tokens.set(data.access_token, data.refresh_token);
    }
    return data;
  },

  async getWorkspaceOverview() {
    const { data } = await api.get("/v2/advertiser/workspace");
    return data;
  },

  async updateWorkspace(payload: Partial<AdvertiserWorkspace>) {
    const { data } = await api.patch("/v2/advertiser/workspace", payload);
    return data;
  },

  async uploadMediaAsset(
    file: File,
    assetKind: CommercialMediaAssetKind,
    options?: { onProgress?: (percent: number) => void },
  ): Promise<AdvertiserMediaAsset> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("asset_kind", assetKind);
    const config: Record<string, any> = {
      headers: {
        "X-Asset-Kind": assetKind,
        "X-Filename": file.name,
      },
    };
    if (options?.onProgress) {
      config.onUploadProgress = (evt: { loaded?: number; total?: number }) => {
        if (evt.total && evt.total > 0 && typeof evt.loaded === "number") {
          options.onProgress?.(Math.min(100, Math.round((evt.loaded / evt.total) * 100)));
        }
      };
    }
    const { data } = await api.post("/v2/advertiser/media/upload", formData, config);
    return data;
  },

  async listMediaAssets(assetKind?: CommercialMediaAssetKind): Promise<AdvertiserMediaAsset[]> {
    const { data } = await api.get("/v2/advertiser/media", {
      params: assetKind ? { asset_kind: assetKind } : undefined,
    });
    return Array.isArray(data) ? data : [];
  },

  async deleteMediaAsset(assetId: string): Promise<{ deleted: boolean; asset_id: string; storage_provider: string }> {
    const { data } = await api.delete(`/v2/advertiser/media/${encodeURIComponent(assetId)}`);
    return data;
  },

  async listCampaigns(division?: "brand" | "music"): Promise<CommercialCampaign[]> {
    const { data } = await api.get("/v2/advertiser/campaigns", {
      params: division ? { division } : undefined,
    });
    return Array.isArray(data) ? data : [];
  },

  async getCampaignDetail(campaignId: string) {
    const { data } = await api.get(`/v2/advertiser/campaigns/${campaignId}`);
    return data;
  },

  async createBrandCampaign(payload: {
    company_name: string;
    contact_email: string;
    contact_phone: string;
    contact_name?: string | null;
    website_url?: string | null;
    logo_asset_id?: string | null;
    client_brand_id?: string | null;
    placements: string[];
    creative_asset_id: string;
    headline: string;
    description?: string;
    duration_days: number;
    package_code?: string | null;
    is_subscription?: boolean;
    submit_immediately?: boolean;
  }): Promise<CommercialCampaign> {
    const { data } = await api.post("/v2/advertiser/campaigns/brand", payload);
    return data;
  },

  async createMusicPromotion(payload: {
    audio_asset_id: string;
    track_title?: string | null;
    artist_name?: string | null;
    stage_name?: string | null;
    label_name?: string | null;
    genre?: string | null;
    artwork_asset_id?: string | null;
    external_profile_url?: string | null;
    duration_days: number;
    package_code?: string | null;
    is_subscription?: boolean;
    explicit_content: boolean;
    rights_declaration_accepted: boolean;
    rights_holder?: string | null;
  }): Promise<CommercialCampaign> {
    const { data } = await api.post("/v2/advertiser/campaigns/music", payload);
    return data;
  },

  async campaignAction(campaignId: string, action: "pause" | "resume" | "archive"): Promise<CommercialCampaign> {
    const { data } = await api.post(`/v2/advertiser/campaigns/${campaignId}/action`, null, {
      params: { action },
    });
    return data;
  },

  async initiatePayment(payload: {
    campaign_id: string;
    provider: "paystack" | "korapay";
    callback_url?: string;
    subscription_consent_accepted?: boolean;
  }) {
    const { data } = await api.post("/v2/advertiser/payments/initiate", payload);
    return data;
  },

  async verifyPayment(reference: string) {
    const { data } = await api.post(`/v2/advertiser/payments/${encodeURIComponent(reference)}/verify`);
    return data;
  },

  async getBillingLedger() {
    const { data } = await api.get("/v2/advertiser/billing");
    return data;
  },

  async subscriptionAction(
    subscriptionId: string,
    action: "cancel" | "pause" | "resume" | "renew",
    reason?: string,
  ) {
    const { data } = await api.post(`/v2/advertiser/subscriptions/${subscriptionId}/action`, {
      action,
      reason,
    });
    return data;
  },

  async getReports() {
    const { data } = await api.get("/v2/advertiser/reports");
    return data;
  },

  async inviteMember(payload: { email: string; role: string }) {
    const { data } = await api.post("/v2/advertiser/members", payload);
    return data;
  },

  async createClientBrand(payload: {
    brand_name: string;
    contact_name?: string;
    contact_email?: string;
    contact_phone?: string;
    website_url?: string;
    logo_asset_id?: string | null;
    industry?: string;
  }) {
    const { data } = await api.post("/v2/advertiser/brands", payload);
    return data;
  },

  // Admin endpoints
  async getAdminOverview() {
    const { data } = await api.get("/v2/admin/advertising/overview");
    return data;
  },

  async listAdminAccounts(accountType?: string) {
    const { data } = await api.get("/v2/admin/advertising/accounts", {
      params: accountType ? { account_type: accountType } : undefined,
    });
    return Array.isArray(data) ? data : [];
  },

  async adminAccountAction(workspaceId: string, action: "verify" | "suspend" | "reactivate", note?: string) {
    const { data } = await api.post(`/v2/admin/advertising/accounts/${workspaceId}/action`, { action, note });
    return data;
  },

  async listAdminCampaigns(params?: { division?: "brand" | "music"; status?: string }): Promise<CommercialCampaign[]> {
    const { data } = await api.get("/v2/admin/advertising/campaigns", { params });
    return Array.isArray(data) ? data : [];
  },

  async adminModerateCampaign(
    campaignId: string,
    action: "approve" | "reject" | "request_changes" | "pause" | "resume" | "suspend" | "takedown" | "archive",
    note?: string,
  ): Promise<CommercialCampaign> {
    const { data } = await api.post(`/v2/admin/advertising/campaigns/${campaignId}/moderate`, { action, note });
    return data;
  },

  async listAdminPlacements(): Promise<AdPlacementSpec[]> {
    const { data } = await api.get("/v2/admin/advertising/placements");
    return Array.isArray(data) ? data : [];
  },

  async adminUpdatePlacement(placementKey: string, payload: Record<string, any>): Promise<AdPlacementSpec> {
    const { data } = await api.patch(`/v2/admin/advertising/placements/${placementKey}`, payload);
    return data;
  },

  async listAdminPricing(): Promise<AdPricingPackage[]> {
    const { data } = await api.get("/v2/admin/advertising/pricing");
    return Array.isArray(data) ? data : [];
  },

  async adminUpsertPricing(payload: Record<string, any>): Promise<AdPricingPackage> {
    const { data } = await api.put("/v2/admin/advertising/pricing", payload);
    return data;
  },

  async getAdminPayments() {
    const { data } = await api.get("/v2/admin/advertising/payments");
    return data;
  },

  async adminIssueRefund(payload: { payment_record_id: string; amount_minor_ngn?: number; reason: string }) {
    const { data } = await api.post("/v2/admin/advertising/payments/refund", payload);
    return data;
  },

  async getAdminAnalytics() {
    const { data } = await api.get("/v2/admin/advertising/analytics");
    return data;
  },

  async adminDetectOrphanedMedia(prefix = "gtex/commercial/") {
    const { data } = await api.get("/v2/admin/advertising/media/orphans", {
      params: { prefix },
    });
    return data;
  },
};
