import { createFileRoute, Outlet } from '@tanstack/react-router';
import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { DashboardHeader } from '../../components/dashboard-header/dashboard-header';
import { DevModeBanner } from '../../components/dev-mode/DevModeBanner';

export const Route = createFileRoute('/_protected')({
  component: ProtectedPages,
});

function ProtectedPages() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen flex flex-col">
        {/* Development Mode Banner */}
        <DevModeBanner />

        {/* Dashboard Header */}
        <DashboardHeader />

        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </ProtectedRoute>
  );
}
