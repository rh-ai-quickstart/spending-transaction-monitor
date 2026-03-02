import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useHealth } from '../health';
import * as healthService from '../../services/health';

vi.mock('../../services/health');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  // eslint-disable-next-line react/display-name
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useHealth', () => {
  it('should fetch health data successfully', async () => {
    const mockHealth = [
      {
        name: 'api',
        status: 'healthy' as const,
        message: 'API is healthy',
        version: '1.0.0',
        start_time: '2024-01-01T00:00:00Z',
      },
    ];
    vi.mocked(healthService.getHealth).mockResolvedValue(mockHealth);

    const { result } = renderHook(() => useHealth(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockHealth);
    expect(healthService.getHealth).toHaveBeenCalled();
  });

  it('should handle errors', async () => {
    vi.mocked(healthService.getHealth).mockRejectedValue(
      new Error('Health check failed'),
    );

    const { result } = renderHook(() => useHealth(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeDefined();
  });

  it('should start in loading state', () => {
    vi.mocked(healthService.getHealth).mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useHealth(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});
