import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";
import AppShell from "@/components/gtex/AppShell";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import Onboarding from "@/pages/Onboarding";
import ControlCenter from "@/pages/ControlCenter";
import MyClubs from "@/pages/MyClubs";
import Market from "@/pages/Market";
import Competitions from "@/pages/Competitions";
import CompetitionDetail from "@/pages/CompetitionDetail";
import MatchCenter from "@/pages/MatchCenter";
import Squad from "@/pages/Squad";
import Academy from "@/pages/Academy";
import Finance from "@/pages/Finance";
import InboxPage from "@/pages/Inbox";
import Admin from "@/pages/Admin";
import PaymentCallback from "@/pages/PaymentCallback";
import NationalTeam from "@/pages/NationalTeam";
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
          <Route path="/app" element={<AppShell />}>
            <Route index element={<ControlCenter />} />
            <Route path="clubs" element={<MyClubs />} />
            <Route path="market" element={<Market />} />
            <Route path="competitions" element={<Competitions />} />
            <Route path="competitions/:id" element={<CompetitionDetail />} />
            <Route path="match/:id" element={<MatchCenter />} />
            <Route path="squad" element={<Squad />} />
            <Route path="academy" element={<Academy />} />
            <Route path="national" element={<NationalTeam />} />
            <Route path="finance" element={<Finance />} />
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
