// Type definitions for API responses
export interface ApiUserResponse {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  created_at: string;
}

export interface ApiCreditCardResponse {
  id: string;
  user_id: string;
  card_number: string;
  card_type: string;
  expiry_date: string;
  credit_limit: number;
  current_balance: number;
  available_credit: number;
}

export interface ApiAlertRuleResponse {
  id: string;
  name: string;
  natural_language_query: string;
  sql_query: string;
  alert_type: string;
  is_active: boolean;
  trigger_count: number;
  created_at: string;
  updated_at: string;
  last_triggered?: string;
}

// Current user interface for session management
export interface CurrentUser {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  fullName: string;
}

// Storage key constant
const CURRENT_USER_STORAGE_KEY = 'spending-monitor-current-user';

import { apiClient } from './apiClient';
import { type ApiTransactionResponse } from '../schemas/transaction';

// User service for real API data
export const userService = {
  // Get all users
  async getUsers(): Promise<ApiUserResponse[]> {
    const response = await apiClient.fetch('/api/users/');
    if (!response.ok) {
      throw new Error('Failed to fetch users');
    }
    return response.json();
  },

  // Get current logged-in user
  async getCurrentUser(): Promise<ApiUserResponse | null> {
    const response = await apiClient.fetch('/api/users/profile');
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error('Failed to fetch current user profile');
    }
    return response.json();
  },

  // Get user by ID
  async getUserById(id: string): Promise<ApiUserResponse | null> {
    const response = await apiClient.fetch(`/api/users/${id}`);
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error('Failed to fetch user');
    }
    return response.json();
  },

  // Get user transactions
  async getUserTransactions(
    user_id: string,
    limit = 50,
    offset = 0,
  ): Promise<ApiTransactionResponse[]> {
    const response = await apiClient.fetch(
      `/api/users/${user_id}/transactions?limit=${limit}&offset=${offset}`,
    );
    if (!response.ok) {
      throw new Error('Failed to fetch user transactions');
    }
    return response.json();
  },

  // Get user credit cards
  async getUserCreditCards(user_id: string): Promise<ApiCreditCardResponse[]> {
    const response = await apiClient.fetch(`/api/users/${user_id}/credit-cards`);
    if (!response.ok) {
      throw new Error('Failed to fetch user credit cards');
    }
    return response.json();
  },

  // Get user alert rules
  async getUserAlertRules(user_id: string): Promise<ApiAlertRuleResponse[]> {
    const response = await apiClient.fetch(`/api/users/${user_id}/rules`);
    if (!response.ok) {
      throw new Error('Failed to fetch user alert rules');
    }
    return response.json();
  },
};

// Current user session management service
export const currentUserService = {
  // Get current logged-in user from storage
  getCurrentUser(): CurrentUser | null {
    try {
      const userData = localStorage.getItem(CURRENT_USER_STORAGE_KEY);
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      console.error('Error getting current user:', error);
      return null;
    }
  },

  // Set current user (for login/session initialization)
  setCurrentUser(user: CurrentUser): void {
    try {
      localStorage.setItem(CURRENT_USER_STORAGE_KEY, JSON.stringify(user));
    } catch (error) {
      console.error('Error setting current user:', error);
    }
  },

  // Get current user ID (commonly needed for API calls)
  getCurrentUserId(): string | null {
    const user = this.getCurrentUser();
    return user?.id || null;
  },

  // Check if user is logged in
  isLoggedIn(): boolean {
    return this.getCurrentUser() !== null;
  },

  // Clear current user (for logout)
  clearCurrentUser(): void {
    try {
      localStorage.removeItem(CURRENT_USER_STORAGE_KEY);
    } catch (error) {
      console.error('Error clearing current user:', error);
    }
  },

  // Initialize demo user (temporary until proper auth is implemented)
  async initializeDemoUser(): Promise<CurrentUser> {
    let user = this.getCurrentUser();

    if (!user) {
      // Try to get the current user from the API (returns first user as demo)
      try {
        const apiUser = await userService.getCurrentUser();
        if (apiUser) {
          user = {
            id: apiUser.id,
            firstName: apiUser.first_name,
            lastName: apiUser.last_name,
            email: apiUser.email,
            phone: apiUser.phone_number,
            fullName: `${apiUser.first_name} ${apiUser.last_name}`,
          };
          this.setCurrentUser(user);
        } else {
          // Fallback demo user if no users in API
          user = {
            id: 'u-merchant-high-001',
            firstName: 'Alex',
            lastName: 'Thompson',
            email: 'alex.thompson@example.com',
            fullName: 'Alex Thompson',
          };
          this.setCurrentUser(user);
        }
      } catch (error) {
        console.warn(
          'Failed to fetch current user from API, using fallback demo user:',
          error,
        );
        // Fallback demo user
        user = {
          id: 'u-merchant-high-001',
          firstName: 'Alex',
          lastName: 'Thompson',
          email: 'alex.thompson@example.com',
          fullName: 'Alex Thompson',
        };
        this.setCurrentUser(user);
      }
    }

    return user;
  },

  // Login with user ID (temporary method until proper auth)
  async loginWithUserId(userId: string): Promise<CurrentUser | null> {
    try {
      const apiUser = await userService.getUserById(userId);
      if (apiUser) {
        const user: CurrentUser = {
          id: apiUser.id,
          firstName: apiUser.first_name,
          lastName: apiUser.last_name,
          email: apiUser.email,
          phone: apiUser.phone_number,
          fullName: `${apiUser.first_name} ${apiUser.last_name}`,
        };
        this.setCurrentUser(user);
        return user;
      }
      return null;
    } catch (error) {
      console.error('Error logging in user:', error);
      return null;
    }
  },
};
