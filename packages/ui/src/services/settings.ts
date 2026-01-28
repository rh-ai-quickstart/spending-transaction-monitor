import { apiClient } from './apiClient';
import type {
  SMTPConfig,
  SMSSettings,
  SMSSettingsUpdate,
} from '../schemas/settings';

/**
 * Settings service for managing SMTP and SMS configuration
 */
export const settingsService = {
  /**
   * Get SMTP configuration settings (read-only)
   * Returns current SMTP config without sensitive data
   */
  async getSmtpSettings(): Promise<SMTPConfig> {
    const response = await apiClient.fetch('/api/settings/smtp');
    if (!response.ok) {
      throw new Error('Failed to fetch SMTP settings');
    }
    return response.json();
  },

  /**
   * Get SMS settings for the current user
   * Returns user's SMS preferences and Twilio configuration status
   */
  async getSmsSettings(): Promise<SMSSettings> {
    const response = await apiClient.fetch('/api/settings/sms');
    if (!response.ok) {
      throw new Error('Failed to fetch SMS settings');
    }
    return response.json();
  },

  /**
   * Update SMS settings for the current user
   * @param settings - SMS settings to update
   * @returns Updated SMS settings
   */
  async updateSmsSettings(settings: SMSSettingsUpdate): Promise<SMSSettings> {
    const response = await apiClient.fetch('/api/settings/sms', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to update SMS settings: ${errorText}`);
    }

    return response.json();
  },
};