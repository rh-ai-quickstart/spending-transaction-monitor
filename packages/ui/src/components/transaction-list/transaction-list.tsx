import { useState, useEffect } from 'react';
import { Button } from '../atoms/button/button';
import { cn } from '../../lib/utils';
import { useRecentTransactions, useTransactionSearch } from '../../hooks/transactions';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { TransactionCard } from '../transaction-card/transaction-card';
import type { Transaction } from '../../schemas/transaction';

export interface TransactionListProps {
  className?: string;
  onTransactionClick?: (transaction: Transaction) => void;
  itemsPerPage?: number;
  searchQuery?: string;
  sortBy?: 'date' | 'amount' | 'merchant';
  sortOrder?: 'asc' | 'desc';
  statusFilter?: string;
  selectedTransactionId?: string;
}

export function TransactionList({
  className,
  onTransactionClick,
  itemsPerPage = 10,
  searchQuery = '',
  sortBy = 'date',
  sortOrder = 'desc',
  statusFilter = '',
  selectedTransactionId,
}: TransactionListProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const { data: recentData, isLoading: isRecentLoading } = useRecentTransactions(
    currentPage,
    itemsPerPage,
  );
  const { data: searchData, isLoading: isSearchLoading } =
    useTransactionSearch(searchQuery);

  // Determine which data to use
  const isSearching = searchQuery.length > 2;
  const rawData = isSearching
    ? {
        transactions: searchData || [],
        total: searchData?.length || 0,
        page: 1,
        totalPages: 1,
      }
    : recentData;
  const isLoading = isSearching ? isSearchLoading : isRecentLoading;

  // Sort and filter transactions
  const data = rawData
    ? {
        ...rawData,
        transactions: [...rawData.transactions]
          .filter((transaction) => {
            // Apply status filter
            if (statusFilter && transaction.status !== statusFilter) {
              return false;
            }
            return true;
          })
          .sort((a, b) => {
            let comparison = 0;

            switch (sortBy) {
              case 'date':
                comparison =
                  new Date(a.transaction_date).getTime() -
                  new Date(b.transaction_date).getTime();
                break;
              case 'amount':
                comparison = a.amount - b.amount;
                break;
              case 'merchant':
                comparison = a.merchant_name.localeCompare(b.merchant_name);
                break;
            }

            return sortOrder === 'asc' ? comparison : -comparison;
          }),
      }
    : rawData;

  // Update total count after filtering
  if (data && statusFilter) {
    data.total = data.transactions.length;
    data.totalPages = Math.ceil(data.transactions.length / itemsPerPage);
  }

  // Reset page when searching or filtering
  useEffect(() => {
    if (isSearching || statusFilter) {
      setCurrentPage(1);
    }
  }, [isSearching, statusFilter]);

  if (isLoading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="flex items-center justify-between p-4 rounded-lg border border-border">
              <div className="space-y-2">
                <div className="h-4 bg-muted rounded w-48" />
                <div className="h-3 bg-muted rounded w-32" />
              </div>
              <div className="flex items-center gap-3">
                <div className="h-6 bg-muted rounded w-20" />
                <div className="h-5 bg-muted rounded w-24" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className={cn('', className)}>
      <div className="space-y-2">
        {data.transactions.length === 0 ? (
          <div className="text-center py-8">
            <Search className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground">
              {isSearching
                ? `No transactions found for "${searchQuery}"`
                : statusFilter
                  ? `No ${statusFilter} transactions found`
                  : 'No transactions available'}
            </p>
          </div>
        ) : (
          data.transactions.map((transaction) => (
            <TransactionCard
              key={transaction.id}
              transaction={transaction}
              onClick={onTransactionClick}
              isSelected={selectedTransactionId === transaction.id}
            />
          ))
        )}
      </div>

      {/* Pagination - only show for non-search results */}
      {!isSearching && data.totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 pt-6 border-t border-border">
          <p className="text-sm text-muted-foreground">
            Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
            {Math.min(currentPage * itemsPerPage, data.total)} of {data.total}{' '}
            transactions
          </p>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, data.totalPages) }, (_, i) => {
                const pageNum = i + 1;
                return (
                  <Button
                    key={pageNum}
                    variant={currentPage === pageNum ? 'default' : 'ghost'}
                    size="sm"
                    className="w-8 h-8 p-0"
                    onClick={() => setCurrentPage(pageNum)}
                  >
                    {pageNum}
                  </Button>
                );
              })}
              {data.totalPages > 5 && (
                <>
                  <span className="text-muted-foreground px-1">...</span>
                  <Button
                    variant={currentPage === data.totalPages ? 'default' : 'ghost'}
                    size="sm"
                    className="w-8 h-8 p-0"
                    onClick={() => setCurrentPage(data.totalPages)}
                  >
                    {data.totalPages}
                  </Button>
                </>
              )}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(data.totalPages, p + 1))}
              disabled={currentPage === data.totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
