import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { toast } from 'sonner';
import { useSettings } from '../useSettings';
import { settingsService } from '../../services/settings';
import type {
  SMTPConfig,
  SMSSettings,
  SMSSettingsUpdate,
} from '../../schemas/settings';

// Mock the settings service
vi.mock('../../services/settings');
vi.mock('sonner');

const mockSettingsService = vi.mocked(settingsService);
vi.mocked(toast);

describe('useSettings', () => {
  const mockSMTPConfig: SMTPConfig = {
    host: 'smtp.example.com',
    port: 587,
    from_email: 'noreply@example.com',
    reply_to_email: 'support@example.com',
    use_tls: true,
    use_ssl: false,
    is_configured: true,
  };

  const mockSMSSettings: SMSSettings = {
    phone_number: '+1234567890',
    sms_notifications_enabled: true,
    twilio_configured: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    console.error = vi.fn(); // Mock console.error
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initialization', () => {
    it('should load SMTP and SMS settings on mount', async () => {
      mockSettingsService.getSmtpSettings.mockResolvedValue(mockSMTPConfig);
      mockSettingsService.getSmsSettings.mockResolvedValue(mockSMSSettings);

      const { result } = renderHook(() => useSettings());

      // Initially loading
      expect(result.current.smtpLoading).toBe(true);
      expect(result.current.smsLoading).toBe(true);
      expect(result.current.smtpConfig).toBe(null);
      expect(result.current.smsSettings).toBe(null);
      expect(result.current.smtpError).toBe(null);
      expect(result.current.smsError).toBe(null);

      // Wait for data to load
      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
        expect(result.current.smsLoading).toBe(false);
      });

      // Check final state
      expect(result.current.smtpConfig).toEqual(mockSMTPConfig);
      expect(result.current.smsSettings).toEqual(mockSMSSettings);
      expect(mockSettingsService.getSmtpSettings).toHaveBeenCalledTimes(1);
      expect(mockSettingsService.getSmsSettings).toHaveBeenCalledTimes(1);
    });

    it('should handle SMTP loading errors', async () => {
      const errorMessage = 'Network error';
      mockSettingsService.getSmtpSettings.mockRejectedValue(new Error(errorMessage));
      mockSettingsService.getSmsSettings.mockResolvedValue(mockSMSSettings);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
        expect(result.current.smsLoading).toBe(false);
      });

      expect(result.current.smtpError).toBe(errorMessage);
      expect(result.current.smtpConfig).toBe(null);
      expect(result.current.smsSettings).toEqual(mockSMSSettings);
      expect(result.current.smsError).toBe(null);
    });

    it('should handle SMS loading errors', async () => {
      const errorMessage = 'SMS API error';
      mockSettingsService.getSmtpSettings.mockResolvedValue(mockSMTPConfig);
      mockSettingsService.getSmsSettings.mockRejectedValue(new Error(errorMessage));

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
        expect(result.current.smsLoading).toBe(false);
      });

      expect(result.current.smtpConfig).toEqual(mockSMTPConfig);
      expect(result.current.smtpError).toBe(null);
      expect(result.current.smsError).toBe(errorMessage);
      expect(result.current.smsSettings).toBe(null);
    });

    it('should handle non-Error rejection types', async () => {
      mockSettingsService.getSmtpSettings.mockRejectedValue('String error');
      mockSettingsService.getSmsSettings.mockRejectedValue(404);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
        expect(result.current.smsLoading).toBe(false);
      });

      expect(result.current.smtpError).toBe('Failed to fetch SMTP settings');
      expect(result.current.smsError).toBe('Failed to fetch SMS settings');
    });
  });

  describe('refreshSmtpConfig', () => {
    it('should successfully refresh SMTP config', async () => {
      const updatedConfig = { ...mockSMTPConfig, port: 465 };
      mockSettingsService.getSmtpSettings
        .mockResolvedValueOnce(mockSMTPConfig)
        .mockResolvedValueOnce(updatedConfig);
      mockSettingsService.getSmsSettings.mockResolvedValue(mockSMSSettings);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
      });

      // Refresh SMTP config
      await result.current.refreshSmtpConfig();

      await waitFor(() => {
        expect(result.current.smtpConfig).toEqual(updatedConfig);
      });
      expect(mockSettingsService.getSmtpSettings).toHaveBeenCalledTimes(2);
    });

    it('should handle SMTP refresh errors', async () => {
      mockSettingsService.getSmtpSettings
        .mockResolvedValueOnce(mockSMTPConfig)
        .mockRejectedValueOnce(new Error('Refresh failed'));
      mockSettingsService.getSmsSettings.mockResolvedValue(mockSMSSettings);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
      });

      // Refresh should fail
      await result.current.refreshSmtpConfig();

      await waitFor(() => {
        expect(result.current.smtpError).toBe('Refresh failed');
        expect(result.current.smtpConfig).toBe(null);
      });
    });
  });

  describe('refreshSmsSettings', () => {
    it('should successfully refresh SMS settings', async () => {
      const updatedSMSSettings = {
        ...mockSMSSettings,
        sms_notifications_enabled: false,
      };

      mockSettingsService.getSmtpSettings.mockResolvedValue(mockSMTPConfig);
      mockSettingsService.getSmsSettings
        .mockResolvedValueOnce(mockSMSSettings)
        .mockResolvedValueOnce(updatedSMSSettings);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smsLoading).toBe(false);
      });

      // Refresh SMS settings
      await result.current.refreshSmsSettings();

      await waitFor(() => {
        expect(result.current.smsSettings).toEqual(updatedSMSSettings);
      });
      expect(mockSettingsService.getSmsSettings).toHaveBeenCalledTimes(2);
    });

    it('should handle SMS refresh errors', async () => {
      mockSettingsService.getSmtpSettings.mockResolvedValue(mockSMTPConfig);
      mockSettingsService.getSmsSettings
        .mockResolvedValueOnce(mockSMSSettings)
        .mockRejectedValueOnce(new Error('SMS refresh failed'));

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smsLoading).toBe(false);
      });

      // Refresh should fail
      await result.current.refreshSmsSettings();

      await waitFor(() => {
        expect(result.current.smsError).toBe('SMS refresh failed');
        expect(result.current.smsSettings).toBe(null);
      });
    });
  });

  describe('updateSmsSettings', () => {
    it('should successfully update SMS settings', async () => {
      const updateData: SMSSettingsUpdate = {
        phone_number: '+9876543210',
        sms_notifications_enabled: false,
      };
      const updatedSettings = { ...mockSMSSettings, ...updateData };

      mockSettingsService.getSmtpSettings.mockResolvedValue(mockSMTPConfig);
      mockSettingsService.getSmsSettings.mockResolvedValue(mockSMSSettings);
      mockSettingsService.updateSmsSettings.mockResolvedValue(updatedSettings);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smsLoading).toBe(false);
      });

      // Update SMS settings
      expect(result.current.smsUpdating).toBe(false);

      await result.current.updateSmsSettings(updateData);

      await waitFor(() => {
        expect(result.current.smsUpdating).toBe(false);
        expect(result.current.smsSettings).toEqual(updatedSettings);
        expect(result.current.smsError).toBe(null);
      });
      expect(mockSettingsService.updateSmsSettings).toHaveBeenCalledWith(updateData);
    });

    it('should handle SMS update errors and re-throw', async () => {
      const updateData: SMSSettingsUpdate = {
        phone_number: 'invalid',
        sms_notifications_enabled: true,
      };
      const error = new Error('Validation failed');

      mockSettingsService.getSmtpSettings.mockResolvedValue(mockSMTPConfig);
      mockSettingsService.getSmsSettings.mockResolvedValue(mockSMSSettings);
      mockSettingsService.updateSmsSettings.mockRejectedValue(error);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smsLoading).toBe(false);
      });

      // Update should fail and re-throw
      await expect(result.current.updateSmsSettings(updateData)).rejects.toThrow(
        'Validation failed',
      );

      await waitFor(() => {
        expect(result.current.smsUpdating).toBe(false);
        expect(result.current.smsError).toBe('Validation failed');
        expect(result.current.smsSettings).toEqual(mockSMSSettings); // Should remain unchanged
      });
    });
  });

  describe('refresh', () => {
    it('should refresh both SMTP and SMS settings', async () => {
      const updatedSMTP = { ...mockSMTPConfig, host: 'smtp2.example.com' };
      const updatedSMS = { ...mockSMSSettings, phone_number: '+1111111111' };

      mockSettingsService.getSmtpSettings
        .mockResolvedValueOnce(mockSMTPConfig)
        .mockResolvedValueOnce(updatedSMTP);
      mockSettingsService.getSmsSettings
        .mockResolvedValueOnce(mockSMSSettings)
        .mockResolvedValueOnce(updatedSMS);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
        expect(result.current.smsLoading).toBe(false);
      });

      // Refresh both
      await result.current.refresh();

      await waitFor(() => {
        expect(result.current.smtpConfig).toEqual(updatedSMTP);
        expect(result.current.smsSettings).toEqual(updatedSMS);
      });
      expect(mockSettingsService.getSmtpSettings).toHaveBeenCalledTimes(2);
      expect(mockSettingsService.getSmsSettings).toHaveBeenCalledTimes(2);
    });

    it('should handle partial failures during refresh', async () => {
      const updatedSMS = { ...mockSMSSettings, phone_number: '+2222222222' };

      mockSettingsService.getSmtpSettings
        .mockResolvedValueOnce(mockSMTPConfig)
        .mockRejectedValueOnce(new Error('SMTP failed'));
      mockSettingsService.getSmsSettings
        .mockResolvedValueOnce(mockSMSSettings)
        .mockResolvedValueOnce(updatedSMS);

      const { result } = renderHook(() => useSettings());

      await waitFor(() => {
        expect(result.current.smtpLoading).toBe(false);
        expect(result.current.smsLoading).toBe(false);
      });

      // Refresh both (SMTP should fail, SMS should succeed)
      await result.current.refresh();

      await waitFor(() => {
        expect(result.current.smtpError).toBe('SMTP failed');
        expect(result.current.smtpConfig).toBe(null);
        expect(result.current.smsSettings).toEqual(updatedSMS);
        expect(result.current.smsError).toBe(null);
      });
    });
  });
});
