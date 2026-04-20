import { useEffect, useState } from 'react';

import { PaywallModal } from './components/billing/PaywallModal';
import { hostedUiUrl } from './lib/auth';
import AuthCallbackPage from './pages/AuthCallbackPage';
import BillingPage from './pages/BillingPage';
import ChatPage from './pages/ChatPage';
import InterviewPrepDetailPage from './pages/InterviewPrepDetailPage';
import InterviewPrepListPage from './pages/InterviewPrepListPage';
import NegotiationDetailPage from './pages/NegotiationDetailPage';
import NegotiationListPage from './pages/NegotiationListPage';
import PipelinePage from './pages/PipelinePage';
import ScanDetailPage from './pages/ScanDetailPage';
import ScansPage from './pages/ScansPage';
import StoryBankPage from './pages/StoryBankPage';
import SubscribeRedirect from './pages/SubscribeRedirect';

function matchRoute(pathname: string) {
  if (pathname === '/signup') return 'signup';
  if (pathname === '/login') return 'login';
  if (pathname === '/auth/callback') return 'auth-callback';
  if (pathname === '/settings/billing') return 'billing';
  if (pathname === '/billing/success') return 'subscribe-redirect';
  if (pathname === '/billing/cancel') return 'subscribe-redirect';
  if (pathname === '/pipeline') return 'pipeline';
  if (pathname === '/scans') return 'scans';
  if (pathname.startsWith('/scans/')) return 'scan-detail';
  if (pathname === '/story-bank') return 'story-bank';
  if (pathname === '/interview-prep') return 'interview-prep-list';
  if (pathname.startsWith('/interview-prep/')) return 'interview-prep-detail';
  if (pathname === '/negotiations') return 'negotiations-list';
  if (pathname.startsWith('/negotiations/')) return 'negotiation-detail';
  return 'chat';
}

function App() {
  const [path, setPath] = useState<string>(() => window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const route = matchRoute(path);

  useEffect(() => {
    if (route === 'signup' || route === 'login') {
      window.location.replace(hostedUiUrl(route));
    }
  }, [route]);

  if (route === 'signup' || route === 'login') {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-500">
        Redirecting to sign-in…
      </div>
    );
  }

  const interviewPrepId =
    route === 'interview-prep-detail' ? path.replace(/^\/interview-prep\//, '') : '';
  const negotiationId =
    route === 'negotiation-detail' ? path.replace(/^\/negotiations\//, '') : '';

  return (
    <>
      {route === 'auth-callback' && <AuthCallbackPage />}
      {route === 'chat' && <ChatPage />}
      {route === 'billing' && <BillingPage />}
      {route === 'subscribe-redirect' && <SubscribeRedirect />}
      {route === 'pipeline' && <PipelinePage />}
      {route === 'scans' && <ScansPage />}
      {route === 'scan-detail' && <ScanDetailPage />}
      {route === 'story-bank' && <StoryBankPage />}
      {route === 'interview-prep-list' && <InterviewPrepListPage />}
      {route === 'interview-prep-detail' && interviewPrepId && (
        <InterviewPrepDetailPage id={interviewPrepId} />
      )}
      {route === 'negotiations-list' && <NegotiationListPage />}
      {route === 'negotiation-detail' && negotiationId && (
        <NegotiationDetailPage id={negotiationId} />
      )}
      <PaywallModal />
    </>
  );
}

export default App;
