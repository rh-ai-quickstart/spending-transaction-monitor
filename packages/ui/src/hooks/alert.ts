/**
 * Alert Hooks
 * React Query hooks for alert-related operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertService } from '../services/alert';
import { useAuth } from './useAuth';

// Alert hooks
export const useAlerts = () => {
  const auth = useAuth();

  return useQuery({
    queryKey: ['alerts', auth.user?.id],
    queryFn: () => AlertService.getAlerts(),
    refetchInterval: 60000, // Refetch every minute
    enabled: !!auth.user?.id,
    staleTime: 0, // Always fetch fresh data, don't use stale cache
  });
};

export const useAlertRules = () => {
  const auth = useAuth();

  return useQuery({
    queryKey: ['alertRules', auth.user?.id],
    queryFn: () => AlertService.getAlertRules(),
    enabled: !!auth.user?.id,
    staleTime: 0, // Always fetch fresh data, don't use stale cache
  });
};

export const useValidateAlertRule = () => {
  return useMutation({
    mutationFn: (rule: string) => AlertService.validateAlertRule(rule),
  });
};

export const useCreateAlertRuleFromValidation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (validationResult: {
      alert_rule: Record<string, unknown>; // API validation result object
      sql_query: string;
      natural_language_query: string;
    }) => AlertService.createAlertRuleFromValidation(validationResult),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });
};

export const useCreateAlertRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (rule: string) => AlertService.createAlertRule(rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });
};

export const useToggleAlertRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => AlertService.toggleAlertRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
    },
  });
};

export const useDeleteAlertRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => AlertService.deleteAlertRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
};

export const useAlertRuleHistory = (ruleId: string) => {
  return useQuery({
    queryKey: ['alertRules', ruleId, 'alertHistory'],
    queryFn: () => AlertService.getAlertRuleHistory(ruleId),
    enabled: !!ruleId,
  });
};
