/**
 * Settings-related TypeScript schemas
 */

export interface SMTPConfig {
  host: string;
  port: number;
  from_email: string;
  reply_to_email?: string | null;
  use_tls: boolean;
  use_ssl: boolean;
  is_configured: boolean; // True if username/password exist
}

export interface SMSSettings {
  phone_number?: string | null;
  sms_notifications_enabled: boolean;
  twilio_configured: boolean; // True if Twilio credentials exist
}

export interface SMSSettingsUpdate {
  phone_number?: string | null;
  sms_notifications_enabled: boolean;
}

// Form validation schemas
export interface SMSSettingsFormData {
  phone_number: string;
  sms_notifications_enabled: boolean;
}

// Zod validation schemas
import { z } from 'zod';

export const SMSSettingsSchema = z.object({
  phone_number: z
    .string()
    .optional()
    .refine((val) => !val || /^\+?[1-9]\d{1,14}$/.test(val), {
      message: 'Please enter a valid phone number (E.164 format, e.g., +1234567890)',
    }),
  sms_notifications_enabled: z.boolean(),
});
