import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { settingsService } from '../settings';
import { apiClient } from '../apiClient';
import type { SMTPConfig, SMSSettings, SMSSettingsUpdate } from '../../schemas/settings';

// Mock the apiClient
vi.mock('../apiClient');

const mockApiClient = vi.mocked(apiClient);

describe('settingsService', () => {
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
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getSmtpSettings', () => {
    it('should fetch SMTP settings successfully', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockSMTPConfig),
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      const result = await settingsService.getSmtpSettings();

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/smtp');
      expect(mockResponse.json).toHaveBeenCalled();
      expect(result).toEqual(mockSMTPConfig);
    });

    it('should throw error when response is not ok', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      await expect(settingsService.getSmtpSettings()).rejects.toThrow(
        'Failed to fetch SMTP settings'
      );

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/smtp');
    });

    it('should throw error when fetch fails', async () => {
      const networkError = new Error('Network error');
      mockApiClient.fetch.mockRejectedValue(networkError);

      await expect(settingsService.getSmtpSettings()).rejects.toThrow('Network error');

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/smtp');
    });
  });

  describe('getSmsSettings', () => {
    it('should fetch SMS settings successfully', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockSMSSettings),
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      const result = await settingsService.getSmsSettings();

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms');
      expect(mockResponse.json).toHaveBeenCalled();
      expect(result).toEqual(mockSMSSettings);
    });

    it('should throw error when response is not ok', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      await expect(settingsService.getSmsSettings()).rejects.toThrow(
        'Failed to fetch SMS settings'
      );

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms');
    });

    it('should throw error when fetch fails', async () => {
      const authError = new Error('Unauthorized');
      mockApiClient.fetch.mockRejectedValue(authError);

      await expect(settingsService.getSmsSettings()).rejects.toThrow('Unauthorized');

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms');
    });
  });

  describe('updateSmsSettings', () => {
    const updateData: SMSSettingsUpdate = {
      phone_number: '+9876543210',
      sms_notifications_enabled: false,
    };

    const updatedSettings: SMSSettings = {
      phone_number: '+9876543210',
      sms_notifications_enabled: false,
      twilio_configured: true,
    };

    it('should update SMS settings successfully', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(updatedSettings),
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      const result = await settingsService.updateSmsSettings(updateData);

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });
      expect(mockResponse.json).toHaveBeenCalled();
      expect(result).toEqual(updatedSettings);
    });

    it('should throw error when response is not ok', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        text: vi.fn().mockResolvedValue('Invalid phone number format'),
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      await expect(settingsService.updateSmsSettings(updateData)).rejects.toThrow(
        'Failed to update SMS settings: Invalid phone number format'
      );

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });
      expect(mockResponse.text).toHaveBeenCalled();
    });

    it('should throw error when fetch fails', async () => {
      const networkError = new Error('Network timeout');
      mockApiClient.fetch.mockRejectedValue(networkError);

      await expect(settingsService.updateSmsSettings(updateData)).rejects.toThrow('Network timeout');

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });
    });

    it('should handle empty phone number (null)', async () => {
      const updateDataWithNull: SMSSettingsUpdate = {
        phone_number: null,
        sms_notifications_enabled: true,
      };

      const updatedSettingsWithNull: SMSSettings = {
        phone_number: null,
        sms_notifications_enabled: true,
        twilio_configured: true,
      };

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(updatedSettingsWithNull),
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      const result = await settingsService.updateSmsSettings(updateDataWithNull);

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateDataWithNull),
      });
      expect(result).toEqual(updatedSettingsWithNull);
    });

    it('should handle response text error when response.text() fails', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        text: vi.fn().mockRejectedValue(new Error('Failed to read response')),
      };
      mockApiClient.fetch.mockResolvedValue(mockResponse as any);

      await expect(settingsService.updateSmsSettings(updateData)).rejects.toThrow(
        'Failed to read response'
      );

      expect(mockApiClient.fetch).toHaveBeenCalledWith('/api/settings/sms', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });
      expect(mockResponse.text).toHaveBeenCalled();
    });
  });
});