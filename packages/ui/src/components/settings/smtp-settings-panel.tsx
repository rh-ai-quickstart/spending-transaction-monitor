import { CheckCircle, XCircle, Mail, Server, Shield } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../atoms/card/card';
import { FormItem, FormLabel } from '../atoms/form/form';
import { Input } from '../atoms/input/input';
import { Badge } from '../atoms/badge/badge';
import type { SMTPConfig } from '../../schemas/settings';

export interface SMTPSettingsPanelProps {
  config: SMTPConfig | null;
  isLoading: boolean;
  error: string | null;
}

export function SMTPSettingsPanel({ config, isLoading, error }: SMTPSettingsPanelProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Email/SMTP Settings
          </CardTitle>
          <CardDescription>View current email configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" data-testid="loading-spinner"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Email/SMTP Settings
          </CardTitle>
          <CardDescription>View current email configuration</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-destructive">
            <XCircle className="h-4 w-4" />
            <span>Error loading SMTP settings: {error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!config) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Email/SMTP Settings
          </CardTitle>
          <CardDescription>View current email configuration</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground">No SMTP configuration found</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-5 w-5" />
          Email/SMTP Settings
        </CardTitle>
        <CardDescription>View current email configuration</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Configuration Status */}
        <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            {config.is_configured ? (
              <CheckCircle className="h-4 w-4 text-green-600" />
            ) : (
              <XCircle className="h-4 w-4 text-red-600" />
            )}
            <span className="font-medium">Configuration Status</span>
          </div>
          <Badge variant={config.is_configured ? "default" : "destructive"}>
            {config.is_configured ? "Configured" : "Not Configured"}
          </Badge>
        </div>

        {/* SMTP Server Settings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormItem>
            <FormLabel className="flex items-center gap-2">
              <Server className="h-4 w-4" />
              SMTP Host
            </FormLabel>
            <Input value={config.host || 'Not configured'} disabled />
          </FormItem>

          <FormItem>
            <FormLabel>SMTP Port</FormLabel>
            <Input value={config.port?.toString() || 'Not configured'} disabled />
          </FormItem>
        </div>

        {/* Email Settings */}
        <FormItem>
          <FormLabel>From Email</FormLabel>
          <Input value={config.from_email || 'Not configured'} disabled />
        </FormItem>

        {config.reply_to_email && (
          <FormItem>
            <FormLabel>Reply-To Email</FormLabel>
            <Input value={config.reply_to_email} disabled />
          </FormItem>
        )}

        {/* Security Settings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormItem>
            <FormLabel className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              TLS Encryption
            </FormLabel>
            <div className="flex items-center gap-2 p-2 bg-muted/30 rounded-md">
              {config.use_tls ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-red-600" />
              )}
              <span className="text-sm">
                {config.use_tls ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </FormItem>

          <FormItem>
            <FormLabel className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              SSL Encryption
            </FormLabel>
            <div className="flex items-center gap-2 p-2 bg-muted/30 rounded-md">
              {config.use_ssl ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-red-600" />
              )}
              <span className="text-sm">
                {config.use_ssl ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </FormItem>
        </div>

        {/* Info Message */}
        <div className="mt-6 p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>Note:</strong> SMTP settings are read-only and managed by system administrators.
            Contact your administrator to modify email configuration.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}