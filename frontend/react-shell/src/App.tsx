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
import PaymentCallback from "@/pages/PaymentCallback";
import NationalTeam from "@/pages/NationalTeam";
import { ClubStory } from "@/pages/ClubStory";
import PublicClubProfile from "@/pages/PublicClubProfile";
import { Newsroom } from "@/pages/Newsroom";
import { Showroom } from "@/pages/Showroom";
import { ROUTER_BASENAME } from "@/lib/publicPath";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename={ROUTER_BASENAME}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/signup" element={<AuthPage mode="signup" />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/payment/callback" element={<PaymentCallback />} />
          <Route path="/club/:clubSlug" element={<PublicClubProfile />} />
          <Route path="/app" element={<AppShell />}>
            <Route index element={<ControlCenter />} />
            <Route path="clubs" element={<MyClubs />} />
            <Route path="showroom" element={<Showroom />} />
            <Route path="clubs/:clubId/showroom" element={<Showroom />} />
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
            <Route path="national" element={<NationalTeam />} />
            <Route path="finance" element={<Finance />} />
            <Route path="creator-access" element={<CreatorAccess />} />
            <Route path="coin-traders" element={<CoinTraders />} />
            <Route path="inbox" element={<InboxPage />} />
            <Route path="admin" element={<Admin />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme="dark" position="top-right" richColors />
    </AuthProvider>
  );
}