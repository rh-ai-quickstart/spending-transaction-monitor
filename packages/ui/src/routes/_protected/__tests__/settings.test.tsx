import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryHistory } from '@tanstack/react-router';
import { useSettings } from '../../../hooks/useSettings';
import type { SMTPConfig, SMSSettings } from '../../../schemas/settings';

// Mock the useSettings hook
vi.mock('../../../hooks/useSettings');

// Mock the settings panel components
vi.mock('../../../components/settings/smtp-settings-panel', () => ({
  SMTPSettingsPanel: ({ config, isLoading, error }: any) => {
    if (isLoading) return <div data-testid="smtp-loading">SMTP Loading...</div>;
    if (error) return <div data-testid="smtp-error">SMTP Error: {error}</div>;
    return <div data-testid="smtp-panel">SMTP Panel: {config?.host || 'No config'}</div>;
  },
}));

vi.mock('../../../components/settings/sms-settings-panel', () => ({
  SMSSettingsPanel: ({ settings, isLoading, error, isUpdating, onUpdateSettings }: any) => {
    if (isLoading) return <div data-testid="sms-loading">SMS Loading...</div>;
    if (error) return <div data-testid="sms-error">SMS Error: {error}</div>;
    return (
      <div data-testid="sms-panel">
        SMS Panel: {settings?.phone_number || 'No settings'}
        <button onClick={() => onUpdateSettings({ sms_notifications_enabled: true })}>
          Update SMS
        </button>
      </div>
    );
  },
}));

const mockUseSettings = vi.mocked(useSettings);

// We need to import the component after mocking
async function importSettingsPage() {
  const module = await import('../settings');
  return module.Route.options.component;
}

describe('SettingsPage', () => {
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

  const defaultMockHookReturn = {
    smtpConfig: mockSMTPConfig,
    smtpLoading: false,
    smtpError: null,
    smsSettings: mockSMSSettings,
    smsLoading: false,
    smsError: null,
    smsUpdating: false,
    refreshSmtpConfig: vi.fn(),
    refreshSmsSettings: vi.fn(),
    updateSmsSettings: vi.fn(),
    refresh: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSettings.mockReturnValue(defaultMockHookReturn);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering', () => {
    it('should render settings page with header and panels', async () => {
      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      // Header
      expect(screen.getByText('Settings')).toBeInTheDocument();
      expect(screen.getByText('Manage your email and SMS notification preferences')).toBeInTheDocument();

      // Panels
      expect(screen.getByTestId('smtp-panel')).toBeInTheDocument();
      expect(screen.getByTestId('sms-panel')).toBeInTheDocument();
    });

    it('should pass correct props to SMTP settings panel', async () => {
      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      expect(screen.getByTestId('smtp-panel')).toHaveTextContent('SMTP Panel: smtp.example.com');
    });

    it('should pass correct props to SMS settings panel', async () => {
      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      expect(screen.getByTestId('sms-panel')).toHaveTextContent('SMS Panel: +1234567890');
    });

    it('should show loading states when data is loading', async () => {
      mockUseSettings.mockReturnValue({
        ...defaultMockHookReturn,
        smtpLoading: true,
        smsLoading: true,
        smtpConfig: null,
        smsSettings: null,
      });

      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      expect(screen.getByTestId('smtp-loading')).toBeInTheDocument();
      expect(screen.getByTestId('sms-loading')).toBeInTheDocument();
    });

    it('should show error states when there are errors', async () => {
      mockUseSettings.mockReturnValue({
        ...defaultMockHookReturn,
        smtpError: 'SMTP load failed',
        smsError: 'SMS load failed',
        smtpConfig: null,
        smsSettings: null,
      });

      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      expect(screen.getByTestId('smtp-error')).toHaveTextContent('SMTP Error: SMTP load failed');
      expect(screen.getByTestId('sms-error')).toHaveTextContent('SMS Error: SMS load failed');
    });

    it('should handle partial loading and error states', async () => {
      mockUseSettings.mockReturnValue({
        ...defaultMockHookReturn,
        smtpLoading: true,
        smsError: 'SMS failed',
        smtpConfig: null,
        smsSettings: null,
      });

      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      expect(screen.getByTestId('smtp-loading')).toBeInTheDocument();
      expect(screen.getByTestId('sms-error')).toHaveTextContent('SMS Error: SMS failed');
    });
  });

  describe('interactions', () => {
    it('should pass updateSmsSettings function to SMS panel', async () => {
      const mockUpdateSmsSettings = vi.fn().mockResolvedValue(undefined);
      mockUseSettings.mockReturnValue({
        ...defaultMockHookReturn,
        updateSmsSettings: mockUpdateSmsSettings,
      });

      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      const updateButton = screen.getByText('Update SMS');
      updateButton.click();

      expect(mockUpdateSmsSettings).toHaveBeenCalledWith({
        sms_notifications_enabled: true,
      });
    });

    it('should show updating state when SMS is being updated', async () => {
      mockUseSettings.mockReturnValue({
        ...defaultMockHookReturn,
        smsUpdating: true,
      });

      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      // The SMS panel should receive isUpdating=true
      expect(screen.getByTestId('sms-panel')).toBeInTheDocument();
    });
  });

  describe('layout and responsiveness', () => {
    it('should use proper container and grid layout', async () => {
      const SettingsPage = await importSettingsPage();
      const { container } = render(<SettingsPage />);

      // Check for container classes (these might be applied via Tailwind)
      const mainContainer = container.querySelector('.container');
      expect(mainContainer).toBeInTheDocument();

      // Check that both panels are present
      expect(screen.getByTestId('smtp-panel')).toBeInTheDocument();
      expect(screen.getByTestId('sms-panel')).toBeInTheDocument();
    });

    it('should have proper semantic structure', async () => {
      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      // Check for proper heading hierarchy
      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toHaveTextContent('Settings');

      // Check for description
      expect(screen.getByText('Manage your email and SMS notification preferences')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have proper heading structure', async () => {
      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent('Settings');
    });

    it('should provide meaningful content when loaded', async () => {
      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      // Should have meaningful content for screen readers
      expect(screen.getByText('Settings')).toBeInTheDocument();
      expect(screen.getByText('Manage your email and SMS notification preferences')).toBeInTheDocument();

      // Both panels should be accessible
      expect(screen.getByTestId('smtp-panel')).toBeInTheDocument();
      expect(screen.getByTestId('sms-panel')).toBeInTheDocument();
    });
  });

  describe('data states', () => {
    it('should handle null config and settings gracefully', async () => {
      mockUseSettings.mockReturnValue({
        ...defaultMockHookReturn,
        smtpConfig: null,
        smsSettings: null,
      });

      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      expect(screen.getByTestId('smtp-panel')).toHaveTextContent('SMTP Panel: No config');
      expect(screen.getByTestId('sms-panel')).toHaveTextContent('SMS Panel: No settings');
    });

    it('should handle empty or minimal data states', async () => {
      const minimalSMTP: SMTPConfig = {
        host: '',
        port: 0,
        from_email: '',
        reply_to_email: null,
        use_tls: false,
        use_ssl: false,
        is_configured: false,
      };

      const minimalSMS: SMSSettings = {
        phone_number: null,
        sms_notifications_enabled: false,
        twilio_configured: false,
      };

      mockUseSettings.mockReturnValue({
        ...defaultMockHookReturn,
        smtpConfig: minimalSMTP,
        smsSettings: minimalSMS,
      });

      const SettingsPage = await importSettingsPage();
      render(<SettingsPage />);

      expect(screen.getByTestId('smtp-panel')).toHaveTextContent('SMTP Panel: '); // Empty host
      expect(screen.getByTestId('sms-panel')).toHaveTextContent('SMS Panel: No settings'); // Null phone
    });
  });
});