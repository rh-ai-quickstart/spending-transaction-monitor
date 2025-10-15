/**
 * Authentication constants
 */
import type { User } from '../types/auth';

export const DEV_USER: User = {
  id: 'u-merchant-high-001',
  email: 'alex.thompson@example.com',
  username: 'alexthompson',
  name: 'Alex Thompson',
  roles: ['user', 'admin'],
  isDevMode: true,
} as const;
