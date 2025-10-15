/**
 * Alert Service
 * Handles all alert-related API operations
 */

import type {
  Alert,
  AlertRule,
  ApiNotificationResponse,
  AlertRuleData,
  SimilarityResult,
  AlertTriggerHistory,
} from '../schemas/transaction';
import { apiClient } from './apiClient';
import { type ApiAlertRuleResponse } from './user';

export class AlertService {
  static async getAlerts(): Promise<Alert[]> {
    const response = await apiClient.fetch('/api/alerts/notifications');
    if (!response.ok) {
      throw new Error('Failed to fetch alerts');
    }

    const notifications = await response.json();

    // Transform API data to match UI schema
    return notifications.map((notification: ApiNotificationResponse) => ({
      id: notification.id,
      title: notification.title,
      description: notification.message,
      severity:
        notification.status === 'ERROR'
          ? 'high'
          : notification.status === 'WARNING'
            ? 'medium'
            : 'low',
      timestamp: notification.created_at,
      transaction_id: notification.transaction_id,
      resolved: notification.read_at !== null,
    }));
  }

  static async getAlertRules(): Promise<AlertRule[]> {
    const response = await apiClient.fetch('/api/alerts/rules');
    if (!response.ok) {
      throw new Error('Failed to fetch alert rules');
    }

    const rules = await response.json();

    // Transform API data to match UI schema
    return rules.map((rule: ApiAlertRuleResponse) => ({
      id: rule.id,
      rule: rule.name,
      status: rule.is_active ? 'active' : 'inactive',
      triggered: rule.trigger_count || 0,
      last_triggered: rule.last_triggered
        ? new Date(rule.last_triggered).toLocaleString()
        : 'Never',
      created_at: rule.created_at,
    }));
  }

  static async validateAlertRule(rule: string): Promise<{
    status: 'valid' | 'warning' | 'invalid' | 'error';
    message: string;
    alert_rule?: AlertRuleData;
    sql_query?: string;
    sql_description?: string;
    similarity_result?: SimilarityResult;
    valid_sql?: boolean;
  }> {
    const response = await apiClient.fetch('/api/alerts/rules/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ natural_language_query: rule }),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to validate alert rule: ${response.status} ${response.statusText}`,
      );
    }

    return response.json();
  }

  static async createAlertRuleFromValidation(validationResult: {
    alert_rule: Record<string, unknown>;
    sql_query: string;
    natural_language_query: string;
  }): Promise<AlertRule> {
    const response = await apiClient.fetch('/api/alerts/rules', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(validationResult),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to create alert rule: ${response.status} ${response.statusText}`,
      );
    }

    const apiRule = await response.json();

    // Transform API response to match UI schema
    return {
      id: apiRule.id,
      rule:
        apiRule.natural_language_query ||
        apiRule.name ||
        validationResult.natural_language_query,
      status: apiRule.is_active ? 'active' : 'inactive',
      triggered: apiRule.trigger_count || 0,
      last_triggered: apiRule.last_triggered || 'Never',
      created_at: apiRule.created_at,
    };
  }

  static async createAlertRule(rule: string): Promise<AlertRule> {
    const response = await apiClient.fetch('/api/alerts/rules', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ natural_language_query: rule }),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to create alert rule: ${response.status} ${response.statusText}`,
      );
    }

    const apiRule = await response.json();

    // Transform API response to match UI schema
    return {
      id: apiRule.id,
      rule: apiRule.natural_language_query || apiRule.name || rule,
      status: apiRule.is_active ? 'active' : 'inactive',
      triggered: apiRule.trigger_count || 0,
      last_triggered: apiRule.last_triggered || 'Never',
      created_at: apiRule.created_at,
    };
  }

  static async toggleAlertRule(id: string): Promise<AlertRule | null> {
    // First get the current rule to determine its status
    const rules = await this.getAlertRules();
    const currentRule = rules.find((r) => r.id === id);

    if (!currentRule) {
      console.warn(`Alert rule with id ${id} not found`);
      return null;
    }

    // Determine new status (toggle between active and paused)
    const newIsActive = currentRule.status !== 'active';

    // Make API call to update the rule
    const response = await apiClient.fetch(`/api/alerts/rules/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_active: newIsActive }),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to toggle alert rule: ${response.status} ${response.statusText}`,
      );
    }

    const updatedApiRule = await response.json();

    // Transform API response to match UI schema
    return {
      id: updatedApiRule.id,
      rule: updatedApiRule.natural_language_query || updatedApiRule.name,
      status: updatedApiRule.is_active ? 'active' : 'inactive',
      triggered: updatedApiRule.trigger_count || 0,
      last_triggered: updatedApiRule.last_triggered
        ? new Date(updatedApiRule.last_triggered).toLocaleString()
        : 'Never',
      created_at: updatedApiRule.created_at,
    };
  }

  static async deleteAlertRule(id: string): Promise<void> {
    const response = await apiClient.fetch(`/api/alerts/rules/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(
        `Failed to delete alert rule: ${response.status} ${response.statusText}`,
      );
    }
  }

  static async getAlertRuleHistory(ruleId: string): Promise<AlertTriggerHistory[]> {
    const response = await apiClient.fetch(`/api/alerts/rules/${ruleId}/notifications`);

    if (!response.ok) {
      throw new Error('Failed to fetch alert history');
    }

    return response.json();
  }
}
