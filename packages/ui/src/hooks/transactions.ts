import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  apiTransactionService as transactionService,
  realAlertService as alertService,
  userService,
} from '../services/api-transaction';
import type { TransactionStats } from '../schemas/transaction';

interface AlertRule {
  name: string;
  description: string;
  alert_type: string;
  amount_threshold?: number;
  merchant_category?: string;
  merchant_name?: string;
  location?: string;
  timeframe?: string;
}

// Transaction hooks
export const useRecentTransactions = (page = 1, limit = 10) => {
  return useQuery({
    queryKey: ['transactions', 'recent', page, limit],
    queryFn: () => transactionService.getRecentTransactions(page, limit),
  });
};

export const useTransaction = (id: string) => {
  return useQuery({
    queryKey: ['transactions', id],
    queryFn: () => transactionService.getTransactionById(id),
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
    queryFn: () => transactionService.getTransactionStats(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const useTransactionSearch = (query: string) => {
  return useQuery({
    queryKey: ['transactions', 'search', query],
    queryFn: () => transactionService.searchTransactions(query),
    enabled: query.length > 2, // Only search with 3+ characters
  });
};

// Alert hooks
export const useAlerts = () => {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertService.getAlerts(),
    refetchInterval: 60000, // Refetch every minute
  });
};

export const useAlertRules = () => {
  return useQuery({
    queryKey: ['alertRules'],
    queryFn: () => alertService.getAlertRules(),
  });
};

export const useValidateAlertRule = () => {
  return useMutation({
    mutationFn: (rule: string) => alertService.validateAlertRule(rule),
  });
};

export const useCreateAlertRuleFromValidation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (validationResult: {
      alert_rule: AlertRule;
      sql_query: string;
      natural_language_query: string;
    }) => alertService.createAlertRuleFromValidation(validationResult),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });
};

export const useCreateAlertRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (rule: string) => alertService.createAlertRule(rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });
};

export const useToggleAlertRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => alertService.toggleAlertRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });
};

export const useDeleteAlertRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => alertService.deleteAlertRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
};

// Alert recommendation hooks
export const useAlertRecommendations = () => {
  return useQuery({
    queryKey: ['alertRecommendations'],
    queryFn: () => alertService.getAlertRecommendations(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useCreateRuleFromRecommendation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (recommendation: {
      title: string;
      description: string;
      natural_language_query: string;
      category: string;
      priority: string;
      reasoning: string;
    }) => alertService.createRuleFromRecommendation(recommendation),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
      // Small delay to ensure rule is saved before refreshing recommendations
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['alertRecommendations'] });
      }, 500);
    },
  });
};

export const useTransactionChartData = (timeRange: '7d' | '30d' | '90d' | '1y') => {
  return useQuery({
    queryKey: ['transactions', 'chart', timeRange],
    queryFn: () => transactionService.getTransactionChartData(timeRange),
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
