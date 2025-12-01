import { z } from 'zod';

/**
 * User Schema
 * Represents an authenticated user with roles and mode information
 */
export const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  username: z.string().optional(),
  name: z.string().optional(),
  roles: z.array(z.string()),
  isDevMode: z.boolean(),
});

/**
 * Auth Context Type Schema
 * Defines the authentication context structure
 * Note: Functions are added to the type but not in the schema
 */
export const AuthContextSchema = z.object({
  user: UserSchema.nullable(),
  isAuthenticated: z.boolean(),
  isLoading: z.boolean(),
  error: z.instanceof(Error).nullable(),
});

// Export types
export type User = z.infer<typeof UserSchema>;

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  signinRedirect: () => void;
  error: Error | null;
}
