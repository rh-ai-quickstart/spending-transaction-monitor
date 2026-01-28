import { useState, useEffect } from 'react';
import { settingsService } from '../services/settings';
import type {
  SMTPConfig,
  SMSSettings,
  SMSSettingsUpdate,
} from '../schemas/settings';

export interface UseSettingsResult {
  // SMTP Settings (read-only)
  smtpConfig: SMTPConfig | null;
  smtpLoading: boolean;
  smtpError: string | null;

  // SMS Settings (read/write)
  smsSettings: SMSSettings | null;
  smsLoading: boolean;
  smsError: string | null;
  smsUpdating: boolean;

  // Actions
  refreshSmtpConfig: () => Promise<void>;
  refreshSmsSettings: () => Promise<void>;
  updateSmsSettings: (settings: SMSSettingsUpdate) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useSettings(): UseSettingsResult {
  // SMTP state
  const [smtpConfig, setSmtpConfig] = useState<SMTPConfig | null>(null);
  const [smtpLoading, setSmtpLoading] = useState(true);
  const [smtpError, setSmtpError] = useState<string | null>(null);

  // SMS state
  const [smsSettings, setSmsSettings] = useState<SMSSettings | null>(null);
  const [smsLoading, setSmsLoading] = useState(true);
  const [smsError, setSmsError] = useState<string | null>(null);
  const [smsUpdating, setSmsUpdating] = useState(false);

  const refreshSmtpConfig = async () => {
    try {
      setSmtpLoading(true);
      setSmtpError(null);
      const config = await settingsService.getSmtpSettings();
      setSmtpConfig(config);
    } catch (err) {
      console.error('Error fetching SMTP settings:', err);
      setSmtpError(err instanceof Error ? err.message : 'Failed to fetch SMTP settings');
      setSmtpConfig(null);
    } finally {
      setSmtpLoading(false);
    }
  };

  const refreshSmsSettings = async () => {
    try {
      setSmsLoading(true);
      setSmsError(null);
      const settings = await settingsService.getSmsSettings();
      setSmsSettings(settings);
    } catch (err) {
      console.error('Error fetching SMS settings:', err);
      setSmsError(err instanceof Error ? err.message : 'Failed to fetch SMS settings');
      setSmsSettings(null);
    } finally {
      setSmsLoading(false);
    }
  };

  const updateSmsSettings = async (settings: SMSSettingsUpdate) => {
    try {
      setSmsUpdating(true);
      setSmsError(null);
      const updatedSettings = await settingsService.updateSmsSettings(settings);
      setSmsSettings(updatedSettings);
    } catch (err) {
      console.error('Error updating SMS settings:', err);
      setSmsError(err instanceof Error ? err.message : 'Failed to update SMS settings');
      throw err; // Re-throw so the form can handle the error
    } finally {
      setSmsUpdating(false);
    }
  };

  const refresh = async () => {
    await Promise.all([refreshSmtpConfig(), refreshSmsSettings()]);
  };

  // Load settings on mount
  useEffect(() => {
    refresh();
  }, []);

  return {
    // SMTP Settings (read-only)
    smtpConfig,
    smtpLoading,
    smtpError,

    // SMS Settings (read/write)
    smsSettings,
    smsLoading,
    smsError,
    smsUpdating,

    // Actions
    refreshSmtpConfig,
    refreshSmsSettings,
    updateSmsSettings,
    refresh,
  };
}