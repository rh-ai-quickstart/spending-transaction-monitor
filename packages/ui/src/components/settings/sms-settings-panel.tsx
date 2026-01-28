import * as React from 'react';
import { useForm } from '@tanstack/react-form';
import { CheckCircle, XCircle, Smartphone, Send, Loader2 } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '../atoms/card/card';
import { Button } from '../atoms/button/button';
import { FormItem, FormLabel, FormMessage } from '../atoms/form/form';
import { Input } from '../atoms/input/input';
import { Badge } from '../atoms/badge/badge';
import { toast } from 'sonner';
import type { SMSSettings, SMSSettingsUpdate } from '../../schemas/settings';

export interface SMSSettingsPanelProps {
  settings: SMSSettings | null;
  isLoading: boolean;
  error: string | null;
  isUpdating: boolean;
  onUpdateSettings: (settings: SMSSettingsUpdate) => Promise<void>;
}

export function SMSSettingsPanel({
  settings,
  isLoading,
  error,
  isUpdating,
  onUpdateSettings,
}: SMSSettingsPanelProps) {
  const form = useForm({
    defaultValues: {
      phone_number: settings?.phone_number || '',
      sms_notifications_enabled: settings?.sms_notifications_enabled ?? true,
    },
    onSubmit: async ({ value }) => {
      try {
        await onUpdateSettings({
          phone_number: value.phone_number || null,
          sms_notifications_enabled: value.sms_notifications_enabled,
        });
        toast.success('SMS settings updated successfully!');
      } catch (err) {
        console.error('Failed to update SMS settings:', err);
        toast.error('Failed to update SMS settings. Please try again.');
      }
    },
  });

  // Update form values when settings change
  React.useEffect(() => {
    if (settings) {
      form.setFieldValue('phone_number', settings.phone_number || '');
      form.setFieldValue(
        'sms_notifications_enabled',
        () => settings.sms_notifications_enabled,
      );
    }
  }, [settings, form]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smartphone className="h-5 w-5" />
            SMS Settings
          </CardTitle>
          <CardDescription>Configure SMS notifications</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-center py-8">
            <div
              className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"
              data-testid="loading-spinner"
            ></div>
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
            <Smartphone className="h-5 w-5" />
            SMS Settings
          </CardTitle>
          <CardDescription>Configure SMS notifications</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-destructive">
            <XCircle className="h-4 w-4" />
            <span>Error loading SMS settings: {error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Smartphone className="h-5 w-5" />
          SMS Settings
        </CardTitle>
        <CardDescription>Configure SMS notifications</CardDescription>
      </CardHeader>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          e.stopPropagation();
          form.handleSubmit();
        }}
      >
        <CardContent className="space-y-6">
          {/* Twilio Configuration Status */}
          <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-2">
              {settings?.twilio_configured ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-red-600" />
              )}
              <span className="font-medium">Twilio Configuration</span>
            </div>
            <Badge variant={settings?.twilio_configured ? 'default' : 'destructive'}>
              {settings?.twilio_configured ? 'Configured' : 'Not Configured'}
            </Badge>
          </div>

          {/* Phone Number Field */}
          <form.Field name="phone_number">
            {(field) => (
              <FormItem>
                <FormLabel htmlFor="phone-number-input">Phone Number</FormLabel>
                <Input
                  id="phone-number-input"
                  type="tel"
                  placeholder="+1234567890"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                />
                {field.state.meta.errors && (
                  <FormMessage>{field.state.meta.errors.join(', ')}</FormMessage>
                )}
                <p className="text-sm text-muted-foreground">
                  Enter your phone number in international format (e.g., +1234567890)
                </p>
              </FormItem>
            )}
          </form.Field>

          {/* SMS Notifications Enabled Toggle */}
          <form.Field name="sms_notifications_enabled">
            {(field) => (
              <FormItem>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="sms-notifications"
                    className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                    checked={field.state.value}
                    onChange={(e) => field.handleChange(e.target.checked)}
                    onBlur={field.handleBlur}
                  />
                  <FormLabel
                    htmlFor="sms-notifications"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    Enable SMS Notifications
                  </FormLabel>
                </div>
                <p className="text-sm text-muted-foreground ml-6">
                  Receive SMS alerts for important transactions and account activity
                </p>
              </FormItem>
            )}
          </form.Field>

          {/* Warning if Twilio not configured */}
          {!settings?.twilio_configured && (
            <div className="p-3 bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <p className="text-sm text-yellow-700 dark:text-yellow-300">
                <strong>Warning:</strong> SMS notifications require Twilio
                configuration. Contact your administrator to set up SMS functionality.
              </p>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between">
          <p className="text-sm text-muted-foreground">
            Changes will be saved immediately
          </p>
          <Button
            type="submit"
            disabled={isUpdating || !form.state.isFormValid}
            className="flex items-center gap-2"
          >
            {isUpdating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {isUpdating ? 'Saving...' : 'Save SMS Settings'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
