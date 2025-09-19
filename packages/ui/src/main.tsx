import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider, createRouter } from '@tanstack/react-router';
import { routeTree } from './routeTree.gen';
import './styles/globals.css';
import { ThemeProvider } from './components/theme-provider/theme-provider';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from './components/atoms/tooltip/tooltip.tsx';
import { AuthProvider } from './contexts/AuthContext';
import { AuthErrorBoundary } from './components/auth/AuthErrorBoundary';
import { LocationProvider } from './components/location/LocationProvider';

const queryClient = new QueryClient();
const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthErrorBoundary>
      <AuthProvider>
        <LocationProvider>
          <ThemeProvider>
            <TooltipProvider>
              <QueryClientProvider client={queryClient}>
                <RouterProvider router={router} />
              </QueryClientProvider>
            </TooltipProvider>
          </ThemeProvider>
        </LocationProvider>
      </AuthProvider>
    </AuthErrorBoundary>
  </React.StrictMode>,
);
