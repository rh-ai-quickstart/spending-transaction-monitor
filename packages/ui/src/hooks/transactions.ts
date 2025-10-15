import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TransactionService } from '../services/transaction';
import { userService } from '../services/user';
import type { TransactionStats, CreateTransaction } from '../schemas/transaction';
import { useAuth } from './useAuth';

// Transaction hooks
export const useRecentTransactions = (page = 1, limit = 10) => {
  return useQuery({
    queryKey: ['transactions', 'recent', page, limit],
    queryFn: () => TransactionService.getRecentTransactions(page, limit),
  });
};

export const useTransaction = (id: string) => {
  return useQuery({
    queryKey: ['transactions', id],
    queryFn: () => TransactionService.getTransactionById(id),
    enabled: !!id,
  });
};

export const useTransactionStats = (): {
  data: TransactionStats | undefined;
  isLoading: boolean;
  error: Error | null;
} => {
  return useQuery({
    queryKey: ['transactions', 'stats'],
    queryFn: () => TransactionService.getTransactionStats(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const useTransactionSearch = (query: string) => {
  return useQuery({
    queryKey: ['transactions', 'search', query],
    queryFn: () => TransactionService.searchTransactions(query),
    enabled: query.length > 2, // Only search with 3+ characters
  });
};

// Transaction Mutations
export const useCreateTransaction = () => {
  const queryClient = useQueryClient();
  const auth = useAuth();

  return useMutation({
    mutationFn: async (transaction: CreateTransaction) => {
      if (!auth.user?.id) {
        throw new Error('User not authenticated');
      }
      return TransactionService.createTransaction(transaction, auth.user.id);
    },
    onSuccess: () => {
      // Invalidate related queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['users', auth.user?.id] });
    },
  });
};

export const useUpdateTransaction = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      transaction,
    }: {
      id: string;
      transaction: Partial<CreateTransaction>;
    }) => TransactionService.updateTransaction(id, transaction),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
};

export const useDeleteTransaction = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => TransactionService.deleteTransaction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
};

export const useTransactionChartData = (timeRange: '7d' | '30d' | '90d' | '1y') => {
  return useQuery({
    queryKey: ['transactions', 'chart', timeRange],
    queryFn: () => TransactionService.getTransactionChartData(timeRange),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// User hooks
export const useUsers = () => {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => userService.getUsers(),
    staleTime: 30 * 1000, // 30 seconds
  });
};

export const useUser = (id: string) => {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => userService.getUserById(id),
    enabled: !!id,
  });
};

export const useUserTransactions = (user_id: string, limit = 50, offset = 0) => {
  return useQuery({
    queryKey: ['users', user_id, 'transactions', limit, offset],
    queryFn: () => userService.getUserTransactions(user_id, limit, offset),
    enabled: !!user_id,
  });
};

export const useUserCreditCards = (user_id: string) => {
  return useQuery({
    queryKey: ['users', user_id, 'credit-cards'],
    queryFn: () => userService.getUserCreditCards(user_id),
    enabled: !!user_id,
  });
};

export const useUserAlertRules = (user_id: string) => {
  return useQuery({
    queryKey: ['users', user_id, 'alert-rules'],
    queryFn: () => userService.getUserAlertRules(user_id),
    enabled: !!user_id,
  });
};
