/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { userService, currentUserService } from '../user';
import { apiClient } from '../apiClient';

vi.mock('../apiClient');

describe('userService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getUsers', () => {
    it('should fetch all users', async () => {
      const mockUsers = [
        { id: '1', first_name: 'John', email: 'john@example.com' },
        { id: '2', first_name: 'Jane', email: 'jane@example.com' },
      ];
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockUsers,
      } as any);

      const result = await userService.getUsers();

      expect(result).toEqual(mockUsers);
      expect(apiClient.fetch).toHaveBeenCalledWith('/api/users/');
    });

    it('should throw error on failed fetch', async () => {
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: false,
        status: 500,
      } as any);

      await expect(userService.getUsers()).rejects.toThrow('Failed to fetch users');
    });
  });

  describe('getCurrentUser', () => {
    it('should fetch current user', async () => {
      const mockUser = { id: '1', first_name: 'John', email: 'john@example.com' };
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockUser,
      } as any);

      const result = await userService.getCurrentUser();

      expect(result).toEqual(mockUser);
      expect(apiClient.fetch).toHaveBeenCalledWith('/api/users/profile');
    });

    it('should return null for 404', async () => {
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: false,
        status: 404,
      } as any);

      const result = await userService.getCurrentUser();

      expect(result).toBeNull();
    });

    it('should throw error for other failures', async () => {
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: false,
        status: 500,
      } as any);

      await expect(userService.getCurrentUser()).rejects.toThrow(
        'Failed to fetch current user profile',
      );
    });
  });

  describe('getUserById', () => {
    it('should fetch user by id', async () => {
      const mockUser = { id: '1', first_name: 'John' };
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockUser,
      } as any);

      const result = await userService.getUserById('1');

      expect(result).toEqual(mockUser);
      expect(apiClient.fetch).toHaveBeenCalledWith('/api/users/1');
    });

    it('should return null for 404', async () => {
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: false,
        status: 404,
      } as any);

      const result = await userService.getUserById('999');

      expect(result).toBeNull();
    });
  });

  describe('getUserTransactions', () => {
    it('should fetch user transactions', async () => {
      const mockTransactions = [{ id: 'txn-1', amount: 100 }];
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockTransactions,
      } as any);

      const result = await userService.getUserTransactions('user-1', 50, 0);

      expect(result).toEqual(mockTransactions);
      expect(apiClient.fetch).toHaveBeenCalledWith(
        '/api/users/user-1/transactions?limit=50&offset=0',
      );
    });

    it('should use default parameters', async () => {
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: true,
        json: async () => [],
      } as any);

      await userService.getUserTransactions('user-1');

      expect(apiClient.fetch).toHaveBeenCalledWith(
        '/api/users/user-1/transactions?limit=50&offset=0',
      );
    });
  });

  describe('getUserCreditCards', () => {
    it('should fetch user credit cards', async () => {
      const mockCards = [{ id: 'card-1', card_type: 'VISA' }];
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockCards,
      } as any);

      const result = await userService.getUserCreditCards('user-1');

      expect(result).toEqual(mockCards);
      expect(apiClient.fetch).toHaveBeenCalledWith('/api/users/user-1/credit-cards');
    });
  });

  describe('getUserAlertRules', () => {
    it('should fetch user alert rules', async () => {
      const mockRules = [{ id: 'rule-1', name: 'High Spending' }];
      vi.mocked(apiClient.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockRules,
      } as any);

      const result = await userService.getUserAlertRules('user-1');

      expect(result).toEqual(mockRules);
      expect(apiClient.fetch).toHaveBeenCalledWith('/api/users/user-1/rules');
    });
  });
});

describe('currentUserService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('getCurrentUser', () => {
    it('should get user from localStorage', () => {
      const mockUser = { id: '1', name: 'John', email: 'john@example.com' };
      localStorage.setItem('spending-monitor-current-user', JSON.stringify(mockUser));

      const result = currentUserService.getCurrentUser();

      expect(result).toEqual(mockUser);
    });

    it('should return null if no user in storage', () => {
      const result = currentUserService.getCurrentUser();

      expect(result).toBeNull();
    });

    it('should return null on invalid JSON', () => {
      localStorage.setItem('spending-monitor-current-user', 'invalid json');

      const result = currentUserService.getCurrentUser();

      expect(result).toBeNull();
    });
  });

  describe('setCurrentUser', () => {
    it('should store user in localStorage', () => {
      const mockUser = { id: '1', name: 'John', email: 'john@example.com' };

      currentUserService.setCurrentUser(mockUser as any);

      const stored = localStorage.getItem('spending-monitor-current-user');
      expect(JSON.parse(stored!)).toEqual(mockUser);
    });
  });

  describe('clearCurrentUser', () => {
    it('should remove user from localStorage', () => {
      const mockUser = { id: '1', name: 'John', email: 'john@example.com' };
      localStorage.setItem('spending-monitor-current-user', JSON.stringify(mockUser));

      currentUserService.clearCurrentUser();

      const stored = localStorage.getItem('spending-monitor-current-user');
      expect(stored).toBeNull();
    });
  });

  describe('initializeDemoUser', () => {
    it('should use stored user if available', async () => {
      const mockUser = {
        id: '1',
        firstName: 'John',
        lastName: 'Doe',
        email: 'john@example.com',
        fullName: 'John Doe',
      };
      localStorage.setItem('spending-monitor-current-user', JSON.stringify(mockUser));

      const result = await currentUserService.initializeDemoUser();

      expect(result).toEqual(mockUser);
    });

    it('should create fallback demo user if API fails', async () => {
      vi.mocked(apiClient.fetch).mockRejectedValue(new Error('API Error'));

      const result = await currentUserService.initializeDemoUser();

      expect(result.id).toBeDefined();
      expect(result.email).toBeDefined();
      expect(result.fullName).toBeDefined();
    });
  });
});
