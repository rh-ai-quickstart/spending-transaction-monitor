/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TransactionService } from '../transaction';
import { apiClient } from '../apiClient';

// Mock the apiClient
vi.mock('../apiClient', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    fetch: vi.fn(),
  },
}));

describe('Transaction Service', () => {
  const mockTransaction = {
    id: 'tx-123',
    user_id: 'user-456',
    amount: 150.5,
    currency: 'USD',
    merchant_name: 'Test Store',
    merchant_category: 'Shopping',
    credit_card_num: '1234',
    transaction_date: '2024-01-15T14:30:00Z',
    trans_num: 'trans-789',
    description: 'Test transaction',
    transaction_type: 'PURCHASE',
    status: 'COMPLETED',
    created_at: '2024-01-15T14:30:00Z',
    updated_at: '2024-01-15T14:30:00Z',
  };

  const mockTransactions = [
    mockTransaction,
    {
      ...mockTransaction,
      id: 'tx-124',
      amount: 75.0,
      merchant_name: 'Coffee Shop',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getTransactions', () => {
    it('should fetch transactions successfully', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: mockTransactions,
        status: 200,
        statusText: 'OK',
        headers: new Headers(),
      });

      const result = await TransactionService.getTransactions();

      expect(apiClient.get).toHaveBeenCalledWith('/transactions');
      expect(result).toEqual(mockTransactions);
    });
  });

  describe('getRecentTransactions', () => {
    it('should fetch and transform recent transactions', async () => {
      const mockApiTransactions = [
        {
          id: 'tx-123',
          user_id: 'user-456',
          amount: 150.5,
          currency: 'USD',
          merchant_name: 'Test Store',
          merchant_category: 'Shopping',
          transaction_date: '2024-01-15T14:30:00Z',
          description: 'Test transaction',
          transaction_type: 'PURCHASE',
          status: 'COMPLETED',
        },
      ];

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockApiTransactions),
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result = await TransactionService.getRecentTransactions(1, 10);

      expect(apiClient.fetch).toHaveBeenCalledWith('/api/transactions/');
      expect(result).toHaveProperty('transactions');
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('page', 1);
      expect(result).toHaveProperty('totalPages');
      expect(result.transactions[0]).toHaveProperty('id', 'tx-123');
    });

    it('should handle pagination correctly', async () => {
      const mockApiTransactions = Array.from({ length: 25 }, (_, i) => ({
        id: `tx-${i}`,
        user_id: 'user-456',
        amount: 100,
        currency: 'USD',
        merchant_name: 'Store',
        merchant_category: 'Shopping',
        transaction_date: '2024-01-15T14:30:00Z',
        description: 'Test',
        transaction_type: 'PURCHASE',
        status: 'COMPLETED',
      }));

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockApiTransactions),
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result = await TransactionService.getRecentTransactions(2, 10);

      expect(result.page).toBe(2);
      expect(result.transactions.length).toBe(10);
      expect(result.total).toBe(25);
      expect(result.totalPages).toBe(3);
    });

    it('should handle errors when fetching transactions', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      await expect(TransactionService.getRecentTransactions()).rejects.toThrow(
        'Failed to fetch transactions',
      );
    });
  });

  describe('getTransactionById', () => {
    it('should fetch a single transaction by ID', async () => {
      const mockApiTransaction = {
        id: 'tx-123',
        user_id: 'user-456',
        amount: 150.5,
        currency: 'USD',
        merchant_name: 'Test Store',
        merchant_category: 'Shopping',
        transaction_date: '2024-01-15T14:30:00Z',
        description: 'Test transaction',
        transaction_type: 'PURCHASE',
        status: 'COMPLETED',
      };

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockApiTransaction),
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result = await TransactionService.getTransactionById('tx-123');

      expect(apiClient.fetch).toHaveBeenCalledWith('/api/transactions/tx-123');
      expect(result).toHaveProperty('id', 'tx-123');
    });

    it('should return null for 404 errors', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result = await TransactionService.getTransactionById('nonexistent');

      expect(result).toBeNull();
    });

    it('should throw error for other failures', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      await expect(TransactionService.getTransactionById('tx-123')).rejects.toThrow(
        'Failed to fetch transaction',
      );
    });
  });

  describe('createTransaction', () => {
    const formData = {
      amount: 99.99,
      merchant: 'New Store',
      category: 'Shopping',
      account: 'Checking',
      date: '2024-01-20',
      description: 'New purchase',
      type: 'debit' as const,
      tags: ['test'],
      notes: '',
    };

    it('should create a transaction successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: mockTransaction,
        status: 201,
        statusText: 'Created',
        headers: new Headers(),
      });

      const result = await TransactionService.createTransaction(formData, 'user-456');

      expect(apiClient.post).toHaveBeenCalledWith(
        '/transactions',
        expect.objectContaining({
          user_id: 'user-456',
          amount: 99.99,
          merchant_name: 'New Store',
          merchant_category: 'Shopping',
          description: 'New purchase',
          transaction_type: 'PURCHASE',
        }),
      );
      expect(result).toEqual(mockTransaction);
    });

    it('should handle credit transactions', async () => {
      const creditFormData = { ...formData, type: 'credit' as const };
      vi.mocked(apiClient.post).mockResolvedValue({
        data: mockTransaction,
        status: 201,
        statusText: 'Created',
        headers: new Headers(),
      });

      await TransactionService.createTransaction(creditFormData, 'user-456');

      const callArgs = vi.mocked(apiClient.post).mock.calls[0][1];
      expect(callArgs).toHaveProperty('transaction_type', 'REFUND');
    });

    it('should include optional location fields', async () => {
      const formDataWithLocation = {
        ...formData,
        merchant_city: 'San Francisco',
        merchant_state: 'CA',
        merchant_country: 'USA',
      };
      vi.mocked(apiClient.post).mockResolvedValue({
        data: mockTransaction,
        status: 201,
        statusText: 'Created',
        headers: new Headers(),
      });

      await TransactionService.createTransaction(formDataWithLocation, 'user-456');

      const callArgs = vi.mocked(apiClient.post).mock.calls[0][1];
      expect(callArgs).toHaveProperty('merchant_city', 'San Francisco');
      expect(callArgs).toHaveProperty('merchant_state', 'CA');
      expect(callArgs).toHaveProperty('merchant_country', 'USA');
    });
  });

  describe('updateTransaction', () => {
    const updates = {
      description: 'Updated description',
      category: 'Updated Category',
    };

    it('should update a transaction successfully', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        data: mockTransaction,
        status: 200,
        statusText: 'OK',
        headers: new Headers(),
      });

      const result = await TransactionService.updateTransaction('tx-123', updates);

      expect(apiClient.put).toHaveBeenCalledWith('/transactions/tx-123', updates);
      expect(result).toEqual(mockTransaction);
    });
  });

  describe('deleteTransaction', () => {
    it('should delete a transaction successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        data: undefined,
        status: 204,
        statusText: 'No Content',
        headers: new Headers(),
      });

      await TransactionService.deleteTransaction('tx-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/transactions/tx-123');
    });
  });

  describe('getTransactionStats', () => {
    it('should calculate transaction statistics', async () => {
      const mockApiTransactions = [
        {
          id: 'tx-1',
          user_id: 'user-456',
          amount: 100,
          currency: 'USD',
          merchant_name: 'Store 1',
          merchant_category: 'Shopping',
          transaction_date: '2024-01-15T14:30:00Z',
          description: 'Purchase 1',
          transaction_type: 'PURCHASE',
          status: 'COMPLETED',
        },
        {
          id: 'tx-2',
          user_id: 'user-456',
          amount: 200,
          currency: 'USD',
          merchant_name: 'Store 2',
          merchant_category: 'Food',
          transaction_date: '2024-01-16T14:30:00Z',
          description: 'Purchase 2',
          transaction_type: 'PURCHASE',
          status: 'DECLINED',
        },
      ];

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockApiTransactions),
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result = await TransactionService.getTransactionStats();

      expect(result).toHaveProperty('totalTransactions', 2);
      expect(result).toHaveProperty('totalVolume', 300);
      expect(result).toHaveProperty('activeAlerts', 1);
      expect(result).toHaveProperty('previousPeriod');
    });
  });

  describe('searchTransactions', () => {
    it('should search transactions by merchant name', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockTransactions),
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result = await TransactionService.searchTransactions('coffee');

      expect(result.length).toBe(1);
      expect(result[0].merchant_name).toBe('Coffee Shop');
    });
  });

  describe('getTransactionChartData', () => {
    it('should generate chart data for 7 days', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockTransactions),
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result = await TransactionService.getTransactionChartData('7d');

      expect(result.length).toBe(7);
      expect(result[0]).toHaveProperty('date');
      expect(result[0]).toHaveProperty('volume');
      expect(result[0]).toHaveProperty('transactions');
      expect(result[0]).toHaveProperty('formattedDate');
    });

    it('should generate chart data for different time ranges', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue([]),
      };

      vi.mocked(apiClient.fetch).mockResolvedValue(mockResponse as unknown as Response);

      const result30d = await TransactionService.getTransactionChartData('30d');
      expect(result30d.length).toBe(30);

      const result90d = await TransactionService.getTransactionChartData('90d');
      expect(result90d.length).toBe(90);

      const result1y = await TransactionService.getTransactionChartData('1y');
      expect(result1y.length).toBe(365);
    });
  });
});
