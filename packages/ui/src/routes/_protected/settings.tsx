import { createFileRoute } from '@tanstack/react-router';
import { Settings as SettingsIcon } from 'lucide-react';
import { SMTPSettingsPanel } from '../../components/settings/smtp-settings-panel';
import { SMSSettingsPanel } from '../../components/settings/sms-settings-panel';
import { useSettings } from '../../hooks/useSettings';

export const Route = createFileRoute('/_protected/settings')({
  component: SettingsPage,
});

function SettingsPage() {
  const {
    smtpConfig,
    smtpLoading,
    smtpError,
    smsSettings,
    smsLoading,
    smsError,
    smsUpdating,
    updateSmsSettings,
  } = useSettings();

  return (
    <div className="container mx-auto max-w-7xl p-6 space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <SettingsIcon className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        </div>
        <p className="text-lg text-muted-foreground">
          Manage your email and SMS notification preferences
        </p>
      </div>

      {/* Settings Panels */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* SMTP Settings Panel (Read-only) */}
        <SMTPSettingsPanel
          config={smtpConfig}
          isLoading={smtpLoading}
          error={smtpError}
        />

        {/* SMS Settings Panel (Editable) */}
        <SMSSettingsPanel
          settings={smsSettings}
          isLoading={smsLoading}
          error={smsError}
          isUpdating={smsUpdating}
          onUpdateSettings={updateSmsSettings}
        />
      </div>
    </div>
  );
}
