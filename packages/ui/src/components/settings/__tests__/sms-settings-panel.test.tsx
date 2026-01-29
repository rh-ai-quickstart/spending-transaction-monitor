import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { SMSSettingsPanel } from '../sms-settings-panel';
import type { SMSSettings } from '../../../schemas/settings';

// Mock sonner
vi.mock('sonner');

const mockToast = vi.mocked(toast);

describe('SMSSettingsPanel', () => {
  const mockSettings: SMSSettings = {
    phone_number: '+1234567890',
    sms_notifications_enabled: true,
    twilio_configured: true,
  };

  const defaultProps = {
    settings: mockSettings,
    isLoading: false,
    error: null,
    isUpdating: false,
    onUpdateSettings: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering states', () => {
    it('should render loading state', () => {
      render(<SMSSettingsPanel {...defaultProps} settings={null} isLoading={true} />);

      expect(screen.getByText('SMS Settings')).toBeInTheDocument();
      expect(screen.getByText('Configure SMS notifications')).toBeInTheDocument();
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument(); // Loading spinner
    });

    it('should render error state', () => {
      const errorMessage = 'Failed to load settings';
      render(
        <SMSSettingsPanel
          {...defaultProps}
          settings={null}
          isLoading={false}
          error={errorMessage}
        />,
      );

      expect(screen.getByText('SMS Settings')).toBeInTheDocument();
      expect(
        screen.getByText(`Error loading SMS settings: ${errorMessage}`),
      ).toBeInTheDocument();
      expect(screen.queryByRole('form')).not.toBeInTheDocument();
    });

    it('should render form with settings when loaded', () => {
      render(<SMSSettingsPanel {...defaultProps} />);

      expect(screen.getByText('SMS Settings')).toBeInTheDocument();
      expect(screen.getByText('Configure SMS notifications')).toBeInTheDocument();

      // Twilio status
      expect(screen.getByText('Twilio Configuration')).toBeInTheDocument();
      expect(screen.getByText('Configured')).toBeInTheDocument();

      // Form fields
      expect(screen.getByLabelText('Phone Number')).toBeInTheDocument();
      expect(screen.getByLabelText('Enable SMS Notifications')).toBeInTheDocument();

      // Submit button
      expect(
        screen.getByRole('button', { name: /save sms settings/i }),
      ).toBeInTheDocument();
    });
  });

  describe('form initialization', () => {
    it('should initialize form with current settings values', () => {
      render(<SMSSettingsPanel {...defaultProps} />);

      const phoneInput = screen.getByLabelText('Phone Number') as HTMLInputElement;
      const notificationsCheckbox = screen.getByLabelText(
        'Enable SMS Notifications',
      ) as HTMLInputElement;

      expect(phoneInput.value).toBe(mockSettings.phone_number);
      expect(notificationsCheckbox.checked).toBe(
        mockSettings.sms_notifications_enabled,
      );
    });

    it('should handle settings with null phone number', () => {
      const settingsWithNullPhone: SMSSettings = {
        phone_number: null,
        sms_notifications_enabled: false,
        twilio_configured: false,
      };

      render(<SMSSettingsPanel {...defaultProps} settings={settingsWithNullPhone} />);

      const phoneInput = screen.getByLabelText('Phone Number') as HTMLInputElement;
      const notificationsCheckbox = screen.getByLabelText(
        'Enable SMS Notifications',
      ) as HTMLInputElement;

      expect(phoneInput.value).toBe('');
      expect(notificationsCheckbox.checked).toBe(false);
    });

    it('should update form values when settings prop changes', async () => {
      const { rerender } = render(<SMSSettingsPanel {...defaultProps} />);

      const phoneInput = screen.getByLabelText('Phone Number') as HTMLInputElement;
      expect(phoneInput.value).toBe('+1234567890');

      // Update with new settings
      const newSettings: SMSSettings = {
        phone_number: '+9876543210',
        sms_notifications_enabled: false,
        twilio_configured: true,
      };

      rerender(<SMSSettingsPanel {...defaultProps} settings={newSettings} />);

      await waitFor(() => {
        expect(phoneInput.value).toBe('+9876543210');
      });

      const notificationsCheckbox = screen.getByLabelText(
        'Enable SMS Notifications',
      ) as HTMLInputElement;
      expect(notificationsCheckbox.checked).toBe(false);
    });
  });

  describe('twilio configuration display', () => {
    it('should show configured status when twilio is configured', () => {
      render(<SMSSettingsPanel {...defaultProps} />);

      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.queryByText('Not Configured')).not.toBeInTheDocument();
      expect(
        screen.queryByText(/SMS notifications require Twilio configuration/),
      ).not.toBeInTheDocument();
    });

    it('should show not configured status and warning when twilio is not configured', () => {
      const settingsWithoutTwilio: SMSSettings = {
        phone_number: '+1234567890',
        sms_notifications_enabled: true,
        twilio_configured: false,
      };

      render(<SMSSettingsPanel {...defaultProps} settings={settingsWithoutTwilio} />);

      expect(screen.getByText('Not Configured')).toBeInTheDocument();
      expect(screen.queryByText('Configured')).not.toBeInTheDocument();
      expect(
        screen.getByText(/SMS notifications require Twilio configuration/),
      ).toBeInTheDocument();
    });
  });

  describe('form interactions', () => {
    it('should update phone number field', async () => {
      const user = userEvent.setup();
      render(<SMSSettingsPanel {...defaultProps} />);

      const phoneInput = screen.getByLabelText('Phone Number');

      await user.clear(phoneInput);
      await user.type(phoneInput, '+9876543210');

      expect(phoneInput).toHaveValue('+9876543210');
    });

    it('should toggle SMS notifications checkbox', async () => {
      const user = userEvent.setup();
      render(<SMSSettingsPanel {...defaultProps} />);

      const checkbox = screen.getByLabelText(
        'Enable SMS Notifications',
      ) as HTMLInputElement;
      expect(checkbox.checked).toBe(true);

      await user.click(checkbox);
      expect(checkbox.checked).toBe(false);

      await user.click(checkbox);
      expect(checkbox.checked).toBe(true);
    });

    it.skip('should show validation error for invalid phone number', async () => {
      const user = userEvent.setup();
      render(<SMSSettingsPanel {...defaultProps} />);

      const phoneInput = screen.getByLabelText('Phone Number');
      const submitButton = screen.getByRole('button', { name: /save sms settings/i });

      await user.clear(phoneInput);
      await user.type(phoneInput, '0123456789'); // Invalid: starts with 0

      // Trigger validation by blurring
      await user.tab();

      // Also try clicking the submit button to trigger form validation
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(
            /Please enter a valid phone number \(E\.164 format, e\.g\., \+1234567890\)/,
          ),
        ).toBeInTheDocument();
      });

      expect(submitButton).toBeDisabled();
    });

    it('should allow empty phone number', async () => {
      const user = userEvent.setup();
      render(<SMSSettingsPanel {...defaultProps} />);

      const phoneInput = screen.getByLabelText('Phone Number');
      const submitButton = screen.getByRole('button', { name: /save sms settings/i });

      await user.clear(phoneInput);
      await user.tab(); // Trigger validation

      expect(
        screen.queryByText(
          /Please enter a valid phone number \(E\.164 format, e\.g\., \+1234567890\)/,
        ),
      ).not.toBeInTheDocument();
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe('form submission', () => {
    it.skip('should submit form with updated values and show success toast', async () => {
      const user = userEvent.setup();
      const mockOnUpdateSettings = vi.fn().mockResolvedValue(undefined);

      render(
        <SMSSettingsPanel {...defaultProps} onUpdateSettings={mockOnUpdateSettings} />,
      );

      const phoneInput = screen.getByLabelText('Phone Number');
      const checkbox = screen.getByLabelText('Enable SMS Notifications');
      const submitButton = screen.getByRole('button', { name: /save sms settings/i });

      // Update form values
      await user.clear(phoneInput);
      await user.type(phoneInput, '+9876543210');
      await user.click(checkbox); // Toggle to false

      // Submit form
      await user.click(submitButton);

      expect(mockOnUpdateSettings).toHaveBeenCalledWith({
        phone_number: '+9876543210',
        sms_notifications_enabled: false,
      });

      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith(
          'SMS settings updated successfully!',
        );
      });
    });

    it.skip('should submit form with null phone number when empty', async () => {
      const user = userEvent.setup();
      const mockOnUpdateSettings = vi.fn().mockResolvedValue(undefined);

      render(
        <SMSSettingsPanel {...defaultProps} onUpdateSettings={mockOnUpdateSettings} />,
      );

      const phoneInput = screen.getByLabelText('Phone Number');
      const submitButton = screen.getByRole('button', { name: /save sms settings/i });

      // Clear phone number
      await user.clear(phoneInput);

      // Submit form
      await user.click(submitButton);

      expect(mockOnUpdateSettings).toHaveBeenCalledWith({
        phone_number: null,
        sms_notifications_enabled: true,
      });

      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith(
          'SMS settings updated successfully!',
        );
      });
    });

    it.skip('should handle submission error and show error toast', async () => {
      const user = userEvent.setup();
      const mockOnUpdateSettings = vi
        .fn()
        .mockRejectedValue(new Error('Network error'));

      render(
        <SMSSettingsPanel {...defaultProps} onUpdateSettings={mockOnUpdateSettings} />,
      );

      const submitButton = screen.getByRole('button', { name: /save sms settings/i });

      await user.click(submitButton);

      expect(mockOnUpdateSettings).toHaveBeenCalled();

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith(
          'Failed to update SMS settings. Please try again.',
        );
      });
    });

    it('should disable submit button when updating', () => {
      render(<SMSSettingsPanel {...defaultProps} isUpdating={true} />);

      const submitButton = screen.getByRole('button', { name: /saving/i });
      expect(submitButton).toBeDisabled();
      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });

    it.skip('should disable submit button when form is invalid', async () => {
      const user = userEvent.setup();
      render(<SMSSettingsPanel {...defaultProps} />);

      const phoneInput = screen.getByLabelText('Phone Number');
      const submitButton = screen.getByRole('button', { name: /save sms settings/i });

      // Enter invalid phone number
      await user.clear(phoneInput);
      await user.type(phoneInput, 'invalid');
      await user.tab(); // Trigger validation

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });
    });
  });

  describe('accessibility', () => {
    it.skip('should have proper form labels and structure', () => {
      render(<SMSSettingsPanel {...defaultProps} />);

      // Check form labels
      expect(screen.getByLabelText('Phone Number')).toBeInTheDocument();
      expect(screen.getByLabelText('Enable SMS Notifications')).toBeInTheDocument();

      // Check form structure
      expect(screen.getByRole('form')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /save sms settings/i }),
      ).toBeInTheDocument();
    });

    it.skip('should show validation messages with proper accessibility', async () => {
      const user = userEvent.setup();
      render(<SMSSettingsPanel {...defaultProps} />);

      const phoneInput = screen.getByLabelText('Phone Number');

      await user.clear(phoneInput);
      await user.type(phoneInput, 'invalid');
      await user.tab();

      await waitFor(() => {
        const errorMessage = screen.getByText(/Please enter a valid phone number/);
        expect(errorMessage).toBeInTheDocument();
      });
    });
  });
});
