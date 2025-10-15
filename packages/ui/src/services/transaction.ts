import {
  CreateTransaction,
  Transaction,
  TransactionStats,
  ApiTransactionResponse,
  TRANSACTION_TYPES,
  TRANSACTION_STATUSES,
} from '../schemas/transaction';
import { apiClient } from './apiClient';

export class TransactionService {
  private static baseUrl = '/transactions';

  /**
   * Fetch all transactions
   */
  static async getTransactions(): Promise<Transaction[]> {
    const response = await apiClient.get<Transaction[]>(this.baseUrl);
    return response.data;
  }

  /**
   * Get recent transactions with pagination
   */
  static async getRecentTransactions(
    page = 1,
    limit = 10,
  ): Promise<{
    transactions: Transaction[];
    total: number;
    page: number;
    totalPages: number;
  }> {
    const response = await apiClient.fetch('/api/transactions/');
    if (!response.ok) {
      throw new Error('Failed to fetch transactions');
    }

    const allTransactions = await response.json();

    // Transform API data to match UI schema
    const transformedTransactions: Transaction[] = allTransactions.map(
      (tx: ApiTransactionResponse) => ({
        id: tx.id,
        user_id: tx.user_id,
        credit_card_num: '1234', // Default since not in API response
        amount: tx.amount,
        currency: tx.currency,
        description: tx.description,
        merchant_name: tx.merchant_name,
        merchant_category: tx.merchant_category,
        transaction_date: tx.transaction_date,
        transaction_type: tx.transaction_type as (typeof TRANSACTION_TYPES)[number],
        status: tx.status as (typeof TRANSACTION_STATUSES)[number],
        merchant_city: tx.merchant_city || undefined,
        merchant_state: tx.merchant_state || undefined,
        merchant_country: tx.merchant_country || undefined,
        merchant_zipcode: tx.merchant_zipcode || undefined,
        merchant_latitude: tx.merchant_latitude || undefined,
        merchant_longitude: tx.merchant_longitude || undefined,
        authorization_code: tx.authorization_code || undefined,
        trans_num: tx.trans_num || undefined,
        created_at: new Date().toISOString(), // Default since not in API response
        updated_at: new Date().toISOString(), // Default since not in API response
      }),
    );

    // Sort by time descending
    transformedTransactions.sort(
      (a, b) =>
        new Date(b.transaction_date).getTime() - new Date(a.transaction_date).getTime(),
    );

    // Apply pagination
    const start = (page - 1) * limit;
    const end = start + limit;
    const transactions = transformedTransactions.slice(start, end);

    return {
      transactions,
      total: transformedTransactions.length,
      page,
      totalPages: Math.ceil(transformedTransactions.length / limit),
    };
  }

  /**
   * Get transaction by ID
   */
  static async getTransactionById(id: string): Promise<Transaction | null> {
    const response = await apiClient.fetch(`/api/transactions/${id}`);
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error('Failed to fetch transaction');
    }

    const tx = await response.json();

    // Transform API data to match UI schema
    return {
      id: tx.id,
      user_id: tx.user_id,
      credit_card_num: '1234', // Default since not in API response
      amount: tx.amount,
      currency: tx.currency,
      description: tx.description,
      merchant_name: tx.merchant_name,
      merchant_category: tx.merchant_category,
      transaction_date: tx.transaction_date,
      transaction_type: tx.transaction_type as (typeof TRANSACTION_TYPES)[number],
      status: tx.status as (typeof TRANSACTION_STATUSES)[number],
      merchant_city: tx.merchant_city || undefined,
      merchant_state: tx.merchant_state || undefined,
      merchant_country: tx.merchant_country || undefined,
      merchant_zipcode: tx.merchant_zipcode || undefined,
      merchant_latitude: tx.merchant_latitude || undefined,
      merchant_longitude: tx.merchant_longitude || undefined,
      authorization_code: tx.authorization_code || undefined,
      trans_num: tx.trans_num || undefined,
      created_at: new Date().toISOString(), // Default since not in API response
      updated_at: new Date().toISOString(), // Default since not in API response
    };
  }

  /**
   * Get transaction statistics
   */
  static async getTransactionStats(): Promise<TransactionStats> {
    // For now, calculate stats from the transactions data
    // In the future, you could create a dedicated stats endpoint
    const { transactions } = await this.getRecentTransactions(1, 1000);

    const totalTransactions = transactions.length;
    const totalVolume = transactions.reduce((sum, t) => sum + t.amount, 0);
    const flaggedCount = transactions.filter((t) => t.status === 'DECLINED').length;

    return {
      totalTransactions,
      totalVolume,
      activeAlerts: flaggedCount,
      avgProcessingTime: 1.2,
      previousPeriod: {
        totalTransactions: Math.floor(totalTransactions * 0.88),
        totalVolume: totalVolume * 0.92,
        activeAlerts: Math.floor(flaggedCount * 1.15),
        avgProcessingTime: 1.27,
      },
    };
  }

  /**
   * Search transactions
   */
  static async searchTransactions(query: string): Promise<Transaction[]> {
    const { transactions } = await this.getRecentTransactions(1, 1000);

    const lowercaseQuery = query.toLowerCase();
    return transactions.filter(
      (t) =>
        t.merchant_name.toLowerCase().includes(lowercaseQuery) ||
        t.id.toLowerCase().includes(lowercaseQuery) ||
        t.transaction_type.includes(lowercaseQuery) ||
        t.merchant_category?.toLowerCase().includes(lowercaseQuery),
    );
  }

  /**
   * Get chart data for transaction volume over time
   */
  static async getTransactionChartData(timeRange: '7d' | '30d' | '90d' | '1y'): Promise<
    Array<{
      date: string;
      volume: number;
      transactions: number;
      formattedDate: string;
    }>
  > {
    const { transactions } = await this.getRecentTransactions(1, 1000);

    const days =
      timeRange === '7d'
        ? 7
        : timeRange === '30d'
          ? 30
          : timeRange === '90d'
            ? 90
            : 365;

    const data = [];
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    // Group transactions by date
    const transactionsByDate = new Map<string, { volume: number; count: number }>();

    transactions
      .filter((tx) => new Date(tx.transaction_date) >= cutoffDate)
      .forEach((tx) => {
        const date = new Date(tx.transaction_date).toISOString().split('T')[0];
        const existing = transactionsByDate.get(date) || { volume: 0, count: 0 };
        transactionsByDate.set(date, {
          volume: existing.volume + tx.amount,
          count: existing.count + 1,
        });
      });

    // Fill in missing dates with zeros
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];

      const dayData = transactionsByDate.get(dateStr) || { volume: 0, count: 0 };

      data.push({
        date: dateStr,
        volume: Math.floor(dayData.volume),
        transactions: dayData.count,
        formattedDate: date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        }),
      });
    }

    return data;
  }

  /**
   * Create a new transaction
   * Transforms the frontend form data to match backend API schema
   */
  static async createTransaction(
    formData: CreateTransaction,
    userId: string,
  ): Promise<Transaction> {
    // Transform form data to backend API format
    const backendPayload = {
      id: globalThis.crypto.randomUUID(), // Generate client-side ID
      user_id: userId,
      credit_card_num: 'demo-card-1234', // Default demo card
      amount: formData.amount,
      currency: 'USD',
      description: formData.description,
      merchant_name: formData.merchant || 'Unknown Merchant',
      merchant_category: formData.category,
      transaction_date: new Date(formData.date).toISOString(),
      transaction_type: formData.type === 'credit' ? 'REFUND' : 'PURCHASE',
      status: 'PENDING',
      // Optional fields
      merchant_city: formData.merchant_city || null,
      merchant_state: formData.merchant_state || null,
      merchant_country: formData.merchant_country || null,
      merchant_zipcode: null,
      merchant_latitude: null,
      merchant_longitude: null,
      authorization_code: null,
      trans_num: null,
    };

    const response = await apiClient.post<Transaction>(this.baseUrl, backendPayload);
    return response.data;
  }

  /**
   * Update an existing transaction
   */
  static async updateTransaction(
    id: string,
    transaction: Partial<CreateTransaction>,
  ): Promise<Transaction> {
    const response = await apiClient.put<Transaction>(
      `${this.baseUrl}/${id}`,
      transaction,
    );
    return response.data;
  }

  /**
   * Delete a transaction
   */
  static async deleteTransaction(id: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`);
  }
}
