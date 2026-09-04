import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import DemoLogin from './pages/DemoLogin'
import PricingPage from './pages/Pricing'
import WebsiteCheck from './pages/WebsiteCheck'
import Login from './pages/Login'
import Legal from './pages/Legal'
import Billing from './pages/Billing'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import Dashboard from './pages/Dashboard'
import Campaigns from './pages/Campaigns'
import CreateCampaign from './pages/CreateCampaign'
import CampaignDetail from './pages/CampaignDetail'
import LeadDetail from './pages/LeadDetail'
import LeadIntelligence from './pages/LeadIntelligence'
import LeadGeneration from './pages/LeadGeneration'
import Leads from './pages/Leads'
import Approvals from './pages/Approvals'
import Suppression from './pages/Suppression'
import Settings from './pages/Settings'
import Pipeline from './pages/Pipeline'
import Onboarding from './pages/Onboarding'
import Inbox from './pages/Inbox'
import Analytics from './pages/Analytics'
import LeadQuality from './pages/LeadQuality'
import Integrations from './pages/Integrations'
import Outreach from './pages/Outreach'
import AutoReply from './pages/AutoReply'
import Referrals from './pages/Referrals'
import Admin from './pages/Admin'
import { ReactNode } from 'react'
import { ToastProvider } from './components/ui'

function PrivateRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()
  if (loading)
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-slate-50"
        role="status"
        aria-label="Loading"
      >
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <div
            className="h-8 w-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"
            aria-hidden
          />
          <span className="text-sm">Loading…</span>
        </div>
      </div>
    )
  if (!isAuthenticated) {
    // Bare root for a signed-out visitor is the marketing landing page,
    // not an abrupt redirect — every other protected path still bounces
    // straight to /login.
    if (location.pathname === '/') return <Landing />
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return null
  if (isAuthenticated) return <Navigate to="/" replace />
  return <>{children}</>
}

function OnboardingGate({ children }: { children: ReactNode }) {
  const done = localStorage.getItem('onboarding_done')
  if (!done) return <Navigate to="/onboarding" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/legal/:doc" element={<Legal />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/tools/website-check" element={<WebsiteCheck />} />
            <Route
              path="/demo"
              element={
                <PublicOnly>
                  <DemoLogin />
                </PublicOnly>
              }
            />
            <Route
              path="/login"
              element={
                <PublicOnly>
                  <Login />
                </PublicOnly>
              }
            />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route
              path="/register"
              element={
                <PublicOnly>
                  <Register />
                </PublicOnly>
              }
            />

            <Route
              path="/onboarding"
              element={
                <PrivateRoute>
                  <div className="min-h-screen p-4 sm:p-8">
                    <Onboarding />
                  </div>
                </PrivateRoute>
              }
            />

            <Route
              path="/"
              element={
                <PrivateRoute>
                  <OnboardingGate>
                    <Layout />
                  </OnboardingGate>
                </PrivateRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="campaigns" element={<Campaigns />} />
              <Route path="campaigns/new" element={<CreateCampaign />} />
              <Route path="campaigns/:id" element={<CampaignDetail />} />
              <Route path="leads" element={<Leads />} />
              <Route path="leads/generate" element={<LeadGeneration />} />
              <Route path="leads/:id" element={<LeadDetail />} />
              <Route
                path="leads/:id/intelligence"
                element={<LeadIntelligence />}
              />
              <Route path="approvals" element={<Approvals />} />
              <Route path="outreach" element={<Outreach />} />
              <Route path="outreach/auto-reply" element={<AutoReply />} />
              <Route path="inbox" element={<Inbox />} />
              <Route path="pipeline" element={<Pipeline />} />
              <Route path="suppression" element={<Suppression />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="lead-quality" element={<LeadQuality />} />
              <Route path="integrations" element={<Integrations />} />
              <Route path="referrals" element={<Referrals />} />
              <Route path="settings" element={<Settings />} />
              <Route path="billing" element={<Billing />} />
              <Route path="admin" element={<Admin />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
