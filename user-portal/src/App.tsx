import { useEffect, useState } from 'react';

import { PaywallModal } from './components/billing/PaywallModal';
import { api } from './lib/api';
import { isAuthenticated } from './lib/auth';
import AuthCallbackPage from './pages/AuthCallbackPage';
import BillingPage from './pages/BillingPage';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';
import DevPrimitivesPage from './pages/DevPrimitivesPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import InterviewPrepDetailPage from './pages/InterviewPrepDetailPage';
import InterviewPrepListPage from './pages/InterviewPrepListPage';
import JobDetailPage from './pages/JobDetailPage';
import LoginPage from './pages/LoginPage';
import NegotiationDetailPage from './pages/NegotiationDetailPage';
import NegotiationListPage from './pages/NegotiationListPage';
import OnboardingPage from './pages/OnboardingPage';
import OnboardingPayoffPage from './pages/OnboardingPayoffPage';
import PipelinePage from './pages/PipelinePage';
import ProfilePage from './pages/ProfilePage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import ScanDetailPage from './pages/ScanDetailPage';
import ScansPage from './pages/ScansPage';
import SignupPage from './pages/SignupPage';
import StoryBankPage from './pages/StoryBankPage';
import SubscribeRedirect from './pages/SubscribeRedirect';
import VerifyEmailPage from './pages/VerifyEmailPage';

function matchRoute(pathname: string) {
  if (pathname === '/signup') return 'signup';
  if (pathname === '/login') return 'login';
  if (pathname === '/auth/verify') return 'auth-verify';
  if (pathname === '/auth/forgot') return 'auth-forgot';
  if (pathname === '/auth/reset') return 'auth-reset';
  if (pathname === '/auth/callback') return 'auth-callback';
  if (pathname === '/settings/billing') return 'billing';
  if (pathname === '/billing/success') return 'subscribe-redirect';
  if (pathname === '/billing/cancel') return 'subscribe-redirect';
  if (pathname === '/onboarding') return 'onboarding';
  if (pathname.startsWith('/onboarding/evaluation/')) return 'onboarding-payoff';
  if (pathname === '/pipeline') return 'pipeline';
  if (pathname === '/scans') return 'scans';
  if (pathname.startsWith('/scans/')) return 'scan-detail';
  if (pathname.startsWith('/jobs/')) return 'job-detail';
  if (pathname === '/story-bank') return 'story-bank';
  if (pathname === '/interview-prep') return 'interview-prep-list';
  if (pathname.startsWith('/interview-prep/')) return 'interview-prep-detail';
  if (pathname === '/negotiations') return 'negotiations-list';
  if (pathname.startsWith('/negotiations/')) return 'negotiation-detail';
  if (pathname.startsWith('/profile')) return 'profile';
  if (pathname === '/ask' || pathname === '/chat') return 'chat';
  if (pathname === '/_dev/primitives') return 'dev-primitives';
  if (pathname === '/' || pathname === '/dashboard') return 'dashboard';
  return 'dashboard';
}

const PUBLIC_ROUTES = new Set([
  'signup',
  'login',
  'auth-verify',
  'auth-forgot',
  'auth-reset',
  'auth-callback',
  'dev-primitives',
]);

const ROUTES_THAT_SKIP_ONBOARDING = new Set([
  ...PUBLIC_ROUTES,
  'billing',
  'subscribe-redirect',
  'onboarding',
]);

function requiresProfile(route: string): boolean {
  return !ROUTES_THAT_SKIP_ONBOARDING.has(route);
}

function App() {
  const [path, setPath] = useState<string>(() => window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const route = matchRoute(path);
  const isPublicRoute = PUBLIC_ROUTES.has(route);
  const [needsOnboarding, setNeedsOnboarding] = useState<boolean | null>(null);

  useEffect(() => {
    if (!isPublicRoute && !isAuthenticated()) {
      window.location.replace('/login');
    }
  }, [route, isPublicRoute]);

  useEffect(() => {
    if (!isAuthenticated()) return;
    let cancelled = false;
    (async () => {
      try {
        const response = await api.profile.get();
        if (!cancelled) setNeedsOnboarding(response.data.onboarding_state !== 'done');
      } catch {
        if (!cancelled) setNeedsOnboarding(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (needsOnboarding && requiresProfile(route)) {
      window.location.replace('/onboarding');
    }
  }, [needsOnboarding, route]);

  if (!isPublicRoute && !isAuthenticated()) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-ink-3">
        Redirecting to sign-in…
      </div>
    );
  }

  const resetToken =
    route === 'auth-reset'
      ? new URLSearchParams(window.location.search).get('token') ?? ''
      : '';
  const interviewPrepId =
    route === 'interview-prep-detail' ? path.replace(/^\/interview-prep\//, '') : '';
  const negotiationId =
    route === 'negotiation-detail' ? path.replace(/^\/negotiations\//, '') : '';
  const onboardingPayoffId =
    route === 'onboarding-payoff' ? path.replace(/^\/onboarding\/evaluation\//, '') : '';
  const jobId = route === 'job-detail' ? path.replace(/^\/jobs\//, '') : '';

  return (
    <>
      {route === 'login' && <LoginPage />}
      {route === 'signup' && <SignupPage />}
      {route === 'auth-verify' && <VerifyEmailPage />}
      {route === 'auth-forgot' && <ForgotPasswordPage />}
      {route === 'auth-reset' && <ResetPasswordPage token={resetToken} />}
      {route === 'auth-callback' && <AuthCallbackPage />}
      {route === 'onboarding' && <OnboardingPage />}
      {route === 'onboarding-payoff' && onboardingPayoffId && (
        <OnboardingPayoffPage id={onboardingPayoffId} />
      )}
      {route === 'dashboard' && <DashboardPage />}
      {route === 'chat' && <ChatPage />}
      {route === 'billing' && <BillingPage />}
      {route === 'subscribe-redirect' && <SubscribeRedirect />}
      {route === 'pipeline' && <PipelinePage />}
      {route === 'scans' && <ScansPage />}
      {route === 'scan-detail' && <ScanDetailPage />}
      {route === 'job-detail' && jobId && <JobDetailPage id={jobId} />}
      {route === 'story-bank' && <StoryBankPage />}
      {route === 'interview-prep-list' && <InterviewPrepListPage />}
      {route === 'interview-prep-detail' && interviewPrepId && (
        <InterviewPrepDetailPage id={interviewPrepId} />
      )}
      {route === 'negotiations-list' && <NegotiationListPage />}
      {route === 'negotiation-detail' && negotiationId && (
        <NegotiationDetailPage id={negotiationId} />
      )}
      {route === 'profile' && <ProfilePage />}
      {route === 'dev-primitives' && <DevPrimitivesPage />}
      <PaywallModal />
    </>
  );
}

export default App;
