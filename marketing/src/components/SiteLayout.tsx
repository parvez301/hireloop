import { Outlet } from 'react-router-dom';

import { Footer } from './Footer';
import { Nav } from './Nav';

export function SiteLayout() {
  return (
    <div className="min-h-screen bg-bg text-text-primary flex flex-col">
      <Nav />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
