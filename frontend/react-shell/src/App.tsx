import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/lib/auth";
import AppShell from "@/components/gtex/AppShell";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import Onboarding from "@/pages/Onboarding";
import ControlCenter from "@/pages/ControlCenter";
import MyClubs from "@/pages/MyClubs";
import Market from "@/pages/Market";
import TransferHub from "@/pages/TransferHub";
import RegenWorld from "@/pages/RegenWorld";
import RegenAwards from "@/pages/RegenAwards";
import Competitions from "@/pages/Competitions";
import CompetitionDetail from "@/pages/CompetitionDetail";
import MatchCenter from "@/pages/MatchCenter";
import Squad from "@/pages/Squad";
import Lineup from "@/pages/Lineup";
import Academy from "@/pages/Academy";
import CreatorAccess from "@/pages/CreatorAccess";
import CoinTraders from "@/pages/CoinTraders";
import Finance from "@/pages/Finance";
import InboxPage from "@/pages/Inbox";
import Admin from "@/pages/Admin";
import AdminAdvertising from "@/pages/AdminAdvertising";
import CommercialPublicPortal from "@/pages/CommercialPublicPortal";
import AdvertiserAuthPage from "@/pages/AdvertiserAuthPage";
import AdvertiserWorkspacePortal from "@/pages/AdvertiserWorkspacePortal";
import PaymentCallback from "@/pages/PaymentCallback";
import NationalTeam from "@/pages/NationalTeam";
import { ClubStory } from "@/pages/ClubStory";
import PublicClubProfile from "@/pages/PublicClubProfile";
import { Newsroom } from "@/pages/Newsroom";
import { Showroom } from "@/pages/Showroom";
import ClubCampus from "@/pages/ClubCampus";
import Jackpot from "@/pages/Jackpot";
import AppearanceStudio from "@/pages/AppearanceStudio";
import { ClubAuthorityPage } from "@/pages/ClubAuthorityPage";
import { SkinProvider } from "@/lib/skin-engine";
import { ROUTER_BASENAME } from "@/lib/publicPath";
import { GtexAdvertisingProvider } from "@/components/advertising/GtexAdvertising";
import { GtexAudioProvider } from "@/lib/audio";
import { Loading } from "@/components/gtex/ui";

function AdvertiserRouteGuard({ children }: { children: React.ReactElement }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Opening GTEX Commercial Network..." />;
  if (!user) return <Navigate to="/advertiser/login" replace />;
  const role = String(user.role || "").toLowerCase();
  const accountType = String(user.account_type || user.accountType || "").toLowerCase();
  const isAllowed =
    role === "advertiser" ||
    accountType === "advertiser" ||
    role === "admin" ||
    role === "super_admin";
  if (!isAllowed) {
    return <Navigate to="/advertise" replace />;
  }
  return children;
}

function LegacyAdvertisingRedirect() {
  const { user } = useAuth();
  const role = String(user?.role || "").toLowerCase();
  const accountType = String(user?.account_type || user?.accountType || "").toLowerCase();
  if (role === "advertiser" || accountType === "advertiser") {
    return <Navigate to="/advertiser/dashboard" replace />;
  }
  return <Navigate to="/advertise" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <SkinProvider>
        <GtexAudioProvider>
          <BrowserRouter basename={ROUTER_BASENAME}>
            <Routes>
              {/* Public GTEX Consumer Routes */}
              <Route path="/" element={<GtexAdvertisingProvider><Landing /></GtexAdvertisingProvider>} />
              <Route path="/login" element={<GtexAdvertisingProvider><AuthPage mode="login" /></GtexAdvertisingProvider>} />
              <Route path="/signup" element={<GtexAdvertisingProvider><AuthPage mode="signup" /></GtexAdvertisingProvider>} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/payment/callback" element={<PaymentCallback />} />
              <Route path="/club/:clubSlug" element={<PublicClubProfile />} />
              <Route path="/clubs/:clubSlug" element={<PublicClubProfile />} />
              <Route path="/inbox" element={<Navigate to="/app/inbox" replace />} />

              {/* Dedicated GTEX Commercial Network Public Portal */}
              <Route path="/advertise" element={<CommercialPublicPortal />} />
              <Route path="/advertise/music" element={<CommercialPublicPortal division="music" initialTab="music" />} />
              <Route path="/advertise/brands" element={<CommercialPublicPortal division="brands" initialTab="brands" />} />
              <Route path="/advertise/pricing" element={<CommercialPublicPortal initialTab="pricing" />} />
              <Route path="/advertise/login" element={<Navigate to="/advertiser/login" replace />} />
              <Route path="/advertise/register" element={<Navigate to="/advertiser/register" replace />} />

              {/* Dedicated Commercial Advertiser Authentication Routes */}
              <Route path="/advertiser/login" element={<AdvertiserAuthPage mode="login" initialMode="login" />} />
              <Route path="/advertiser/register" element={<AdvertiserAuthPage mode="register" initialMode="register" />} />

              {/* Dedicated Independent Advertiser Workspace Management Portal */}
              <Route path="/advertiser" element={<Navigate to="/advertiser/dashboard" replace />} />
              <Route
                path="/advertiser/dashboard"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="dashboard" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/campaigns"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="campaigns" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/campaigns/new"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="new-campaign" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/campaigns/:id"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="campaign-detail" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/brands"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="brands" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/music"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="music" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/billing"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="billing" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/subscriptions"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="subscriptions" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/reports"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="reports" /></AdvertiserRouteGuard>}
              />
              <Route
                path="/advertiser/settings"
                element={<AdvertiserRouteGuard><AdvertiserWorkspacePortal section="settings" /></AdvertiserRouteGuard>}
              />

              {/* Dedicated Top-Level Commercial Administration Routes */}
              <Route path="/admin/advertising" element={<AdminAdvertising initialSection="campaigns" />} />
              <Route path="/admin/advertising/accounts" element={<AdminAdvertising initialSection="accounts" />} />
              <Route path="/admin/advertising/campaigns" element={<AdminAdvertising initialSection="campaigns" />} />
              <Route path="/admin/advertising/music" element={<AdminAdvertising initialSection="music" />} />
              <Route path="/admin/advertising/placements" element={<AdminAdvertising initialSection="placements" />} />
              <Route path="/admin/advertising/pricing" element={<AdminAdvertising initialSection="pricing" />} />
              <Route path="/admin/advertising/payments" element={<AdminAdvertising initialSection="payments" />} />
              <Route path="/admin/advertising/analytics" element={<AdminAdvertising initialSection="analytics" />} />

              {/* Authenticated Normal GTEX Application Routes */}
              <Route path="/app" element={<AppShell />}>
                <Route index element={<ControlCenter />} />
                <Route path="clubs" element={<MyClubs />} />
                <Route path="governance" element={<ClubAuthorityPage />} />
                <Route path="clubs/:clubId/governance" element={<ClubAuthorityPage />} />
                <Route path="authority" element={<ClubAuthorityPage />} />
                <Route path="clubs/:clubId/authority" element={<ClubAuthorityPage />} />
                <Route path="showroom" element={<Showroom />} />
                <Route path="clubs/:clubId/showroom" element={<Showroom />} />
                <Route path="campus" element={<ClubCampus />} />
                <Route path="clubs/:clubId/campus" element={<ClubCampus />} />
                <Route path="story" element={<ClubStory />} />
                <Route path="clubs/:clubId/story" element={<ClubStory />} />
                <Route path="newsroom" element={<Newsroom />} />
                <Route path="market" element={<Market />} />
                <Route path="transfer-hub" element={<TransferHub />} />
                <Route path="regen-world" element={<RegenWorld />} />
                <Route path="awards" element={<RegenAwards />} />
                <Route path="competitions" element={<Competitions />} />
                <Route path="competitions/:id" element={<CompetitionDetail />} />
                <Route path="match/:id" element={<MatchCenter />} />
                <Route path="squad" element={<Squad />} />
                <Route path="lineup" element={<Lineup />} />
                <Route path="academy" element={<Academy />} />
                <Route path="build-a-son" element={<Academy />} />
                <Route path="regens/create-son" element={<Academy />} />
                <Route path="trophies" element={<ClubStory />} />
                <Route path="dynasty" element={<ClubStory />} />
                <Route path="player-cards" element={<Navigate to="/app/market" replace />} />
                <Route path="club-sale-market" element={<Navigate to="/app/market?tab=club-sales" replace />} />
                <Route path="clubs/sale-market" element={<Navigate to="/app/market?tab=club-sales" replace />} />
                <Route path="national" element={<NationalTeam />} />
                <Route path="finance" element={<Finance />} />
                <Route path="jackpot" element={<Jackpot />} />
                <Route path="creator-access" element={<CreatorAccess />} />
                <Route path="advertising" element={<LegacyAdvertisingRedirect />} />
                <Route path="coin-traders" element={<CoinTraders />} />
                <Route path="inbox" element={<InboxPage />} />
                <Route path="admin" element={<Admin />} />
                <Route path="admin/advertising" element={<AdminAdvertising initialSection="campaigns" />} />
                <Route path="admin/advertising/accounts" element={<AdminAdvertising initialSection="accounts" />} />
                <Route path="admin/advertising/campaigns" element={<AdminAdvertising initialSection="campaigns" />} />
                <Route path="admin/advertising/music" element={<AdminAdvertising initialSection="music" />} />
                <Route path="admin/advertising/placements" element={<AdminAdvertising initialSection="placements" />} />
                <Route path="admin/advertising/pricing" element={<AdminAdvertising initialSection="pricing" />} />
                <Route path="admin/advertising/payments" element={<AdminAdvertising initialSection="payments" />} />
                <Route path="admin/advertising/analytics" element={<AdminAdvertising initialSection="analytics" />} />
                <Route path="settings/appearance" element={<AppearanceStudio />} />
                <Route path="appearance" element={<Navigate to="/app/settings/appearance" replace />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
          <Toaster theme="dark" position="top-right" richColors />
        </GtexAudioProvider>
      </SkinProvider>
    </AuthProvider>
  );
}
