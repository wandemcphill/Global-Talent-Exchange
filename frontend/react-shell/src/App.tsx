import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";
import AppShell from "@/components/gtex/AppShell";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import CreatorAccess from "@/pages/CreatorAccess";
import CoinTraders from "@/pages/CoinTraders";
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
import Finance from "@/pages/Finance";
import InboxPage from "@/pages/Inbox";
import Admin from "@/pages/Admin";
import AdvertiserAds from "@/pages/AdvertiserAds";
import AdminAdvertising from "@/pages/AdminAdvertising";
import PaymentCallback from "@/pages/PaymentCallback";
import NationalTeam from "@/pages/NationalTeam";
import { ClubStory } from "@/pages/ClubStory";
import PublicClubProfile from "@/pages/PublicClubProfile";
import { Newsroom } from "@/pages/Newsroom";
import { Showroom } from "@/pages/Showroom";
import ClubCampus from "@/pages/ClubCampus";
import Jackpot from "@/pages/Jackpot";
import AppearanceStudio from "@/pages/AppearanceStudio";
import { SkinProvider } from "@/lib/skin-engine";
import { ROUTER_BASENAME } from "@/lib/publicPath";
import { GtexAdvertisingProvider } from "@/components/advertising/GtexAdvertising";

export default function App() {
  return (
    <AuthProvider>
      <SkinProvider>
      <BrowserRouter basename={ROUTER_BASENAME}>
        <Routes>
          <Route path="/" element={<GtexAdvertisingProvider><Landing /></GtexAdvertisingProvider>} />
          <Route path="/login" element={<GtexAdvertisingProvider><AuthPage mode="login" /></GtexAdvertisingProvider>} />
          <Route path="/signup" element={<GtexAdvertisingProvider><AuthPage mode="signup" /></GtexAdvertisingProvider>} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/payment/callback" element={<PaymentCallback />} />
          <Route path="/club/:clubSlug" element={<PublicClubProfile />} />
          <Route path="/inbox" element={<Navigate to="/app/inbox" replace />} />
          <Route path="/app" element={<AppShell />}>
            <Route index element={<ControlCenter />} />
            <Route path="clubs" element={<MyClubs />} />
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
            <Route path="advertising" element={<AdvertiserAds />} />
            <Route path="coin-traders" element={<CoinTraders />} />
            <Route path="inbox" element={<InboxPage />} />
            <Route path="admin" element={<Admin />} />
            <Route path="admin/advertising" element={<AdminAdvertising />} />
            <Route path="settings/appearance" element={<AppearanceStudio />} />
            <Route path="appearance" element={<Navigate to="/app/settings/appearance" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme="dark" position="top-right" richColors />
    </SkinProvider>
    </AuthProvider>
  );
}