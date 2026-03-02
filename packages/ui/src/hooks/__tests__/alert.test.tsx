/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import {
  useAlerts,
  useAlertRules,
  useValidateAlertRule,
  useCreateAlertRuleFromValidation,
  useCreateAlertRule,
  useToggleAlertRule,
  useDeleteAlertRule,
  useAlertRuleHistory,
} from '../alert';
import { AlertService } from '../../services/alert';

vi.mock('../../services/alert');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  // eslint-disable-next-line react/display-name
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('Alert Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useAlerts', () => {
    it('should fetch alerts successfully', async () => {
      const mockAlerts = [
        { id: '1', message: 'Alert 1', severity: 'high' },
        { id: '2', message: 'Alert 2', severity: 'low' },
      ];
      vi.mocked(AlertService.getAlerts).mockResolvedValue(mockAlerts as any);

      const { result } = renderHook(() => useAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockAlerts);
      expect(AlertService.getAlerts).toHaveBeenCalledTimes(1);
    });

    it('should handle alerts fetch error', async () => {
      vi.mocked(AlertService.getAlerts).mockRejectedValue(new Error('Fetch failed'));

      const { result } = renderHook(() => useAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });
  });

  describe('useAlertRules', () => {
    it('should fetch alert rules successfully', async () => {
      const mockRules = [
        { id: '1', name: 'Rule 1', enabled: true },
        { id: '2', name: 'Rule 2', enabled: false },
      ];
      vi.mocked(AlertService.getAlertRules).mockResolvedValue(mockRules as any);

      const { result } = renderHook(() => useAlertRules(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockRules);
    });
  });

  describe('useValidateAlertRule', () => {
    it('should validate alert rule successfully', async () => {
      const mockValidation = { valid: true, alert_rule: {}, sql_query: 'SELECT *' };
      vi.mocked(AlertService.validateAlertRule).mockResolvedValue(
        mockValidation as any,
      );

      const { result } = renderHook(() => useValidateAlertRule(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('test rule');

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockValidation);
    });
  });

  describe('useCreateAlertRuleFromValidation', () => {
    it('should create alert rule from validation', async () => {
      const mockRule = { id: '1', name: 'New Rule' };
      vi.mocked(AlertService.createAlertRuleFromValidation).mockResolvedValue(
        mockRule as any,
      );

      const { result } = renderHook(() => useCreateAlertRuleFromValidation(), {
        wrapper: createWrapper(),
      });

      const validationResult = {
        alert_rule: { name: 'Test' },
        sql_query: 'SELECT *',
        natural_language_query: 'test',
      };

      result.current.mutate(validationResult);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockRule);
    });
  });

  describe('useCreateAlertRule', () => {
    it('should create alert rule', async () => {
      const mockRule = { id: '1', name: 'New Rule' };
      vi.mocked(AlertService.createAlertRule).mockResolvedValue(mockRule as any);

      const { result } = renderHook(() => useCreateAlertRule(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('create rule');

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockRule);
    });
  });

  describe('useToggleAlertRule', () => {
    it('should toggle alert rule', async () => {
      const mockRule = { id: '1', enabled: true };
      vi.mocked(AlertService.toggleAlertRule).mockResolvedValue(mockRule as any);

      const { result } = renderHook(() => useToggleAlertRule(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('1');

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(AlertService.toggleAlertRule).toHaveBeenCalledWith('1');
    });
  });

  describe('useDeleteAlertRule', () => {
    it('should delete alert rule', async () => {
      vi.mocked(AlertService.deleteAlertRule).mockResolvedValue(undefined as any);

      const { result } = renderHook(() => useDeleteAlertRule(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('1');

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(AlertService.deleteAlertRule).toHaveBeenCalledWith('1');
    });
  });

  describe('useAlertRuleHistory', () => {
    it('should fetch alert rule history', async () => {
      const mockHistory = [{ id: '1', timestamp: '2024-01-01', status: 'triggered' }];
      vi.mocked(AlertService.getAlertRuleHistory).mockResolvedValue(mockHistory as any);

      const { result } = renderHook(() => useAlertRuleHistory('rule-1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockHistory);
    });

    it('should not fetch when ruleId is empty', () => {
      const { result } = renderHook(() => useAlertRuleHistory(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
      expect(AlertService.getAlertRuleHistory).not.toHaveBeenCalled();
    });
  });
});
