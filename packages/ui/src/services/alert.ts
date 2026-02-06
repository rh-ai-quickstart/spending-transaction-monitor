/**
 * Alert Service
 * Handles all alert-related API operations
 */

import type { Alert, AlertRule, AlertTriggerHistory } from '../schemas/transaction';
import type {
  ApiNotificationResponse,
  AlertRuleData,
  SimilarityResult,
} from '../schemas/api';
import type { ApiAlertRuleResponse } from '../schemas/user';
import { apiClient } from './apiClient';

export class AlertService {
  static async getAlerts(): Promise<Alert[]> {
    const response = await apiClient.fetch('/api/alerts/notifications');
    if (!response.ok) {
      throw new Error('Failed to fetch alerts');
    }

    const notifications = await response.json();

    // Group notifications by alert event (same alert_rule_id + transaction_id + similar timestamp)
    const groupedNotifications = new Map<string, ApiNotificationResponse[]>();

    for (const notification of notifications) {
      // Create a grouping key based on alert_rule_id and transaction_id
      // This groups all notifications from the same alert trigger
      const groupKey = `${notification.alert_rule_id}-${notification.transaction_id || 'no-tx'}`;

      if (!groupedNotifications.has(groupKey)) {
        groupedNotifications.set(groupKey, []);
      }
      groupedNotifications.get(groupKey)!.push(notification);
    }

    // Transform grouped notifications to Alert objects
    return Array.from(groupedNotifications.values()).map((notificationGroup) => {
      // Use the first notification as the primary one
      const primary = notificationGroup[0];

      // Extract all notification methods
      const methods = notificationGroup.map((n) => n.notification_method);

      // Extract all notification IDs
      const ids = notificationGroup.map((n) => n.id);

      // Alert is resolved only if ALL notifications in the group are read
      const allRead = notificationGroup.every((n) => n.read_at !== null);

      return {
        id: primary.id,
        title: primary.title,
        description: primary.message,
        severity:
          primary.status === 'ERROR'
            ? 'high'
            : primary.status === 'WARNING'
              ? 'medium'
              : 'low',
        timestamp: primary.created_at,
        transaction_id: primary.transaction_id,
        resolved: allRead,
        notification_methods: methods,
        notification_ids: ids,
      } as Alert;
    });
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
