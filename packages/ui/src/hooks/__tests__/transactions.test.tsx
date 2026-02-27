/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import {
  useRecentTransactions,
  useTransaction,
  useTransactionStats,
  useTransactionSearch,
  useCreateTransaction,
  useUpdateTransaction,
  useDeleteTransaction,
  useTransactionChartData,
  useUsers,
  useUser,
  useUserTransactions,
  useUserCreditCards,
  useUserAlertRules,
} from '../transactions';
import { TransactionService } from '../../services/transaction';
import { userService } from '../../services/user';
import { useAuth } from '../useAuth';

vi.mock('../../services/transaction');
vi.mock('../../services/user');
vi.mock('../useAuth');

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

describe('Transaction Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'user-1', email: 'test@example.com', username: 'test' },
      isAuthenticated: true,
      isLoading: false,
      error: null,
    } as any);
  });

  describe('useRecentTransactions', () => {
    it('should fetch recent transactions', async () => {
      const mockTransactions = [
        { id: '1', amount: 100, description: 'Test' },
        { id: '2', amount: 200, description: 'Test 2' },
      ];
      vi.mocked(TransactionService.getRecentTransactions).mockResolvedValue(
        mockTransactions as any,
      );

      const { result } = renderHook(() => useRecentTransactions(1, 10), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockTransactions);
      expect(TransactionService.getRecentTransactions).toHaveBeenCalledWith(1, 10);
    });

    it('should use default parameters', async () => {
      vi.mocked(TransactionService.getRecentTransactions).mockResolvedValue([] as any);

      const { result } = renderHook(() => useRecentTransactions(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(TransactionService.getRecentTransactions).toHaveBeenCalledWith(1, 10);
    });
  });

  describe('useTransaction', () => {
    it('should fetch transaction by id', async () => {
      const mockTransaction = { id: '1', amount: 100 };
      vi.mocked(TransactionService.getTransactionById).mockResolvedValue(
        mockTransaction as any,
      );

      const { result } = renderHook(() => useTransaction('1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockTransaction);
    });

    it('should not fetch when id is empty', () => {
      const { result } = renderHook(() => useTransaction(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
    });
  });

  describe('useTransactionStats', () => {
    it('should fetch transaction stats', async () => {
      const mockStats = { total: 1000, count: 10 };
      vi.mocked(TransactionService.getTransactionStats).mockResolvedValue(
        mockStats as any,
      );

      const { result } = renderHook(() => useTransactionStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.data).toEqual(mockStats);
    });
  });

  describe('useTransactionSearch', () => {
    it('should search transactions', async () => {
      const mockResults = [{ id: '1', description: 'Test' }];
      vi.mocked(TransactionService.searchTransactions).mockResolvedValue(
        mockResults as any,
      );

      const { result } = renderHook(() => useTransactionSearch('test query'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockResults);
    });

    it('should not search with less than 3 characters', () => {
      const { result } = renderHook(() => useTransactionSearch('ab'), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
      expect(TransactionService.searchTransactions).not.toHaveBeenCalled();
    });
  });

  describe('useCreateTransaction', () => {
    it('should create transaction', async () => {
      const mockTransaction = { id: '1', amount: 100 };
      vi.mocked(TransactionService.createTransaction).mockResolvedValue(
        mockTransaction as any,
      );

      const { result } = renderHook(() => useCreateTransaction(), {
        wrapper: createWrapper(),
      });

      const newTransaction = {
        amount: 100,
        description: 'Test',
        category: 'Food',
        date: '2024-01-01',
      };

      result.current.mutate(newTransaction as any);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockTransaction);
      expect(TransactionService.createTransaction).toHaveBeenCalledWith(
        newTransaction,
        'user-1',
      );
    });

    it('should throw error when user not authenticated', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      } as any);

      const { result } = renderHook(() => useCreateTransaction(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ amount: 100 } as any);

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error?.message).toBe('User not authenticated');
    });
  });

  describe('useUpdateTransaction', () => {
    it('should update transaction', async () => {
      const mockUpdated = { id: '1', amount: 200 };
      vi.mocked(TransactionService.updateTransaction).mockResolvedValue(
        mockUpdated as any,
      );

      const { result } = renderHook(() => useUpdateTransaction(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ id: '1', transaction: { amount: 200 } });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(TransactionService.updateTransaction).toHaveBeenCalledWith('1', {
        amount: 200,
      });
    });
  });

  describe('useDeleteTransaction', () => {
    it('should delete transaction', async () => {
      vi.mocked(TransactionService.deleteTransaction).mockResolvedValue(
        undefined as any,
      );

      const { result } = renderHook(() => useDeleteTransaction(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('1');

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(TransactionService.deleteTransaction).toHaveBeenCalledWith('1');
    });
  });

  describe('useTransactionChartData', () => {
    it('should fetch chart data', async () => {
      const mockChartData = [{ date: '2024-01-01', amount: 100 }];
      vi.mocked(TransactionService.getTransactionChartData).mockResolvedValue(
        mockChartData as any,
      );

      const { result } = renderHook(() => useTransactionChartData('7d'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockChartData);
      expect(TransactionService.getTransactionChartData).toHaveBeenCalledWith('7d');
    });
  });

  describe('useUsers', () => {
    it('should fetch users', async () => {
      const mockUsers = [
        { id: '1', name: 'User 1' },
        { id: '2', name: 'User 2' },
      ];
      vi.mocked(userService.getUsers).mockResolvedValue(mockUsers as any);

      const { result } = renderHook(() => useUsers(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockUsers);
    });
  });

  describe('useUser', () => {
    it('should fetch user by id', async () => {
      const mockUser = { id: '1', name: 'User 1' };
      vi.mocked(userService.getUserById).mockResolvedValue(mockUser as any);

      const { result } = renderHook(() => useUser('1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockUser);
    });

    it('should not fetch when id is empty', () => {
      const { result } = renderHook(() => useUser(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
    });
  });

  describe('useUserTransactions', () => {
    it('should fetch user transactions', async () => {
      const mockTransactions = [{ id: '1', amount: 100 }];
      vi.mocked(userService.getUserTransactions).mockResolvedValue(
        mockTransactions as any,
      );

      const { result } = renderHook(() => useUserTransactions('user-1', 50, 0), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockTransactions);
      expect(userService.getUserTransactions).toHaveBeenCalledWith('user-1', 50, 0);
    });

    it('should not fetch when user_id is empty', () => {
      const { result } = renderHook(() => useUserTransactions(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
    });
  });

  describe('useUserCreditCards', () => {
    it('should fetch user credit cards', async () => {
      const mockCards = [{ id: '1', last4: '1234' }];
      vi.mocked(userService.getUserCreditCards).mockResolvedValue(mockCards as any);

      const { result } = renderHook(() => useUserCreditCards('user-1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockCards);
    });

    it('should not fetch when user_id is empty', () => {
      const { result } = renderHook(() => useUserCreditCards(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
    });
  });

  describe('useUserAlertRules', () => {
    it('should fetch user alert rules', async () => {
      const mockRules = [{ id: '1', name: 'Rule 1' }];
      vi.mocked(userService.getUserAlertRules).mockResolvedValue(mockRules as any);

      const { result } = renderHook(() => useUserAlertRules('user-1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockRules);
    });

    it('should not fetch when user_id is empty', () => {
      const { result } = renderHook(() => useUserAlertRules(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
    });
  });
});
