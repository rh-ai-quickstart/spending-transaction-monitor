import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SMTPSettingsPanel } from '../smtp-settings-panel';
import type { SMTPConfig } from '../../../schemas/settings';

describe('SMTPSettingsPanel', () => {
  const mockConfig: SMTPConfig = {
    host: 'smtp.example.com',
    port: 587,
    from_email: 'noreply@example.com',
    reply_to_email: 'support@example.com',
    use_tls: true,
    use_ssl: false,
    is_configured: true,
  };

  const defaultProps = {
    config: mockConfig,
    isLoading: false,
    error: null,
  };

  beforeEach(() => {
    // Clear any previous DOM state
    document.body.innerHTML = '';
  });

  describe('rendering states', () => {
    it('should render loading state', () => {
      render(<SMTPSettingsPanel {...defaultProps} config={null} isLoading={true} />);

      expect(screen.getByText('Email/SMTP Settings')).toBeInTheDocument();
      expect(screen.getByText('View current email configuration')).toBeInTheDocument();
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument(); // Loading spinner
    });

    it('should render error state', () => {
      const errorMessage = 'Failed to load SMTP config';
      render(
        <SMTPSettingsPanel
          {...defaultProps}
          config={null}
          isLoading={false}
          error={errorMessage}
        />,
      );

      expect(screen.getByText('Email/SMTP Settings')).toBeInTheDocument();
      expect(
        screen.getByText(`Error loading SMTP settings: ${errorMessage}`),
      ).toBeInTheDocument();
    });

    it('should render no config state', () => {
      render(
        <SMTPSettingsPanel
          {...defaultProps}
          config={null}
          isLoading={false}
          error={null}
        />,
      );

      expect(screen.getByText('Email/SMTP Settings')).toBeInTheDocument();
      expect(screen.getByText('No SMTP configuration found')).toBeInTheDocument();
    });

    it('should render config details when loaded', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      expect(screen.getByText('Email/SMTP Settings')).toBeInTheDocument();
      expect(screen.getByText('View current email configuration')).toBeInTheDocument();

      // Configuration status
      expect(screen.getByText('Configuration Status')).toBeInTheDocument();
      expect(screen.getByText('Configured')).toBeInTheDocument();

      // SMTP server settings
      expect(screen.getByText('SMTP Host')).toBeInTheDocument();
      expect(screen.getByText('SMTP Port')).toBeInTheDocument();

      // Email settings
      expect(screen.getByText('From Email')).toBeInTheDocument();
      expect(screen.getByText('Reply-To Email')).toBeInTheDocument();

      // Security settings
      expect(screen.getByText('TLS Encryption')).toBeInTheDocument();
      expect(screen.getByText('SSL Encryption')).toBeInTheDocument();

      // Info note
      expect(screen.getByText(/SMTP settings are read-only/)).toBeInTheDocument();
    });
  });

  describe('configuration status display', () => {
    it('should show configured status when SMTP is configured', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.queryByText('Not Configured')).not.toBeInTheDocument();
    });

    it('should show not configured status when SMTP is not configured', () => {
      const notConfiguredConfig: SMTPConfig = {
        ...mockConfig,
        is_configured: false,
      };

      render(<SMTPSettingsPanel {...defaultProps} config={notConfiguredConfig} />);

      expect(screen.getByText('Not Configured')).toBeInTheDocument();
      expect(screen.queryByText('Configured')).not.toBeInTheDocument();
    });
  });

  describe('SMTP server settings display', () => {
    it('should display host and port correctly', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      const hostInput = screen.getByDisplayValue('smtp.example.com');
      const portInput = screen.getByDisplayValue('587');

      expect(hostInput).toBeDisabled();
      expect(portInput).toBeDisabled();
    });

    it.skip('should handle missing host and port gracefully', () => {
      const configWithMissingData: SMTPConfig = {
        host: '',
        port: 0,
        from_email: '',
        reply_to_email: null,
        use_tls: false,
        use_ssl: false,
        is_configured: false,
      };

      render(<SMTPSettingsPanel {...defaultProps} config={configWithMissingData} />);

      expect(screen.getByDisplayValue('Not configured')).toBeInTheDocument();
      expect(screen.getAllByDisplayValue('Not configured')).toHaveLength(3); // host, port, from_email
    });
  });

  describe('email settings display', () => {
    it('should display from email correctly', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      const fromEmailInput = screen.getByDisplayValue('noreply@example.com');
      expect(fromEmailInput).toBeDisabled();
    });

    it('should display reply-to email when present', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      expect(screen.getByText('Reply-To Email')).toBeInTheDocument();
      const replyToInput = screen.getByDisplayValue('support@example.com');
      expect(replyToInput).toBeDisabled();
    });

    it('should not show reply-to field when not configured', () => {
      const configWithoutReplyTo: SMTPConfig = {
        ...mockConfig,
        reply_to_email: null,
      };

      render(<SMTPSettingsPanel {...defaultProps} config={configWithoutReplyTo} />);

      expect(screen.queryByText('Reply-To Email')).not.toBeInTheDocument();
      expect(screen.queryByDisplayValue('support@example.com')).not.toBeInTheDocument();
    });

    it('should not show reply-to field when empty string', () => {
      const configWithEmptyReplyTo: SMTPConfig = {
        ...mockConfig,
        reply_to_email: '',
      };

      render(<SMTPSettingsPanel {...defaultProps} config={configWithEmptyReplyTo} />);

      expect(screen.queryByText('Reply-To Email')).not.toBeInTheDocument();
    });
  });

  describe('security settings display', () => {
    it('should show TLS enabled when configured', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      const tlsSection = screen
        .getByText('TLS Encryption')
        .closest('div')?.parentElement;
      expect(tlsSection).toHaveTextContent('Enabled');
    });

    it('should show SSL disabled when not configured', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      const sslSection = screen
        .getByText('SSL Encryption')
        .closest('div')?.parentElement;
      expect(sslSection).toHaveTextContent('Disabled');
    });

    it('should show both TLS and SSL enabled correctly', () => {
      const configWithBothTlsSsl: SMTPConfig = {
        ...mockConfig,
        use_tls: true,
        use_ssl: true,
      };

      render(<SMTPSettingsPanel {...defaultProps} config={configWithBothTlsSsl} />);

      const tlsSection = screen
        .getByText('TLS Encryption')
        .closest('div')?.parentElement;
      const sslSection = screen
        .getByText('SSL Encryption')
        .closest('div')?.parentElement;

      expect(tlsSection).toHaveTextContent('Enabled');
      expect(sslSection).toHaveTextContent('Enabled');
    });

    it('should show both TLS and SSL disabled correctly', () => {
      const configWithoutSecurity: SMTPConfig = {
        ...mockConfig,
        use_tls: false,
        use_ssl: false,
      };

      render(<SMTPSettingsPanel {...defaultProps} config={configWithoutSecurity} />);

      const tlsSection = screen
        .getByText('TLS Encryption')
        .closest('div')?.parentElement;
      const sslSection = screen
        .getByText('SSL Encryption')
        .closest('div')?.parentElement;

      expect(tlsSection).toHaveTextContent('Disabled');
      expect(sslSection).toHaveTextContent('Disabled');
    });
  });

  describe('read-only behavior', () => {
    it('should have all form inputs disabled', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      const inputs = screen.getAllByRole('textbox');
      inputs.forEach((input) => {
        expect(input).toBeDisabled();
      });
    });

    it('should not have any submit buttons or form actions', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      expect(screen.queryByRole('button')).not.toBeInTheDocument();
      expect(screen.queryByRole('form')).not.toBeInTheDocument();
    });

    it('should display information note about read-only nature', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      expect(
        screen.getByText(
          /SMTP settings are read-only and managed by system administrators/,
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Contact your administrator to modify email configuration/),
      ).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it.skip('should have proper labels for all form fields', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      expect(screen.getByLabelText('SMTP Host')).toBeInTheDocument();
      expect(screen.getByLabelText('SMTP Port')).toBeInTheDocument();
      expect(screen.getByLabelText('From Email')).toBeInTheDocument();
      expect(screen.getByLabelText('Reply-To Email')).toBeInTheDocument();
      expect(screen.getByLabelText('TLS Encryption')).toBeInTheDocument();
      expect(screen.getByLabelText('SSL Encryption')).toBeInTheDocument();
    });

    it.skip('should have proper heading structure', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(
        'Email/SMTP Settings',
      );
    });

    it('should use semantic elements for status indicators', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      // Check for proper ARIA labels or semantic elements for status
      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.getByText('Enabled')).toBeInTheDocument();
      expect(screen.getByText('Disabled')).toBeInTheDocument();
    });
  });

  describe('visual styling and layout', () => {
    it('should render with proper card structure', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      // Check for card elements (assuming the Card component renders with proper roles or classes)
      expect(screen.getByText('Email/SMTP Settings')).toBeInTheDocument();
      expect(screen.getByText('View current email configuration')).toBeInTheDocument();
    });

    it('should group related settings appropriately', () => {
      render(<SMTPSettingsPanel {...defaultProps} />);

      // Check that related settings are present and grouped
      expect(screen.getByText('SMTP Host')).toBeInTheDocument();
      expect(screen.getByText('SMTP Port')).toBeInTheDocument();
      expect(screen.getByText('TLS Encryption')).toBeInTheDocument();
      expect(screen.getByText('SSL Encryption')).toBeInTheDocument();
    });
  });
});
