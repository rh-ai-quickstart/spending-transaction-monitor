import { createFileRoute } from '@tanstack/react-router';
import { TransactionList } from '../../components/transaction-list/transaction-list';
import { TransactionSidebar } from '../../components/transaction-sidebar/transaction-sidebar';
import { TransactionDrawer } from '../../components/transaction-drawer/transaction-drawer';
import { Card } from '../../components/atoms/card/card';
import { Button } from '../../components/atoms/button/button';
import { StatsList } from '../../components/stats-list/stats-list';
import { AddTransactionDialog } from '../../components/add-transaction-form/add-transaction-form';
import {
  Search,
  Filter,
  Download,
  Calendar,
  TrendingUp,
  TrendingDown,
  ArrowUpDown,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTransactionStats } from '../../hooks/transactions';
import { cn } from '../../lib/utils';
import type { Transaction } from '../../schemas/transaction';
import type { Stat } from '../../components/stats-list/stats-list';

export const Route = createFileRoute('/_protected/transactions')({
  component: TransactionsPage,
});

function TransactionsPage() {
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(
    null,
  );
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy] = useState<'date' | 'amount' | 'merchant'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const { data: stats } = useTransactionStats();

  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < 1024 : false,
  );

  useEffect(() => {
    function handleResize() {
      setIsMobile(window.innerWidth < 1024); // Tailwind 'lg' breakpoint is 1024px
    }
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleTransactionClick = (transaction: Transaction) => {
    setSelectedTransaction(transaction);
    // Only open drawer on mobile screens
    if (window.innerWidth < 1024) {
      setIsDrawerOpen(true);
    }
  };

  const handleCloseSidebar = () => {
    setSelectedTransaction(null);
  };

  const handleCloseDrawer = (open: boolean) => {
    setIsDrawerOpen(open);
    if (!open) {
      setSelectedTransaction(null);
    }
  };

  const handleReviewFlagged = () => {
    setStatusFilter('flagged');
    setShowFilters(true);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Create stats array for the stats list
  const transactionStats: Stat[] = stats
    ? [
        {
          id: 'volume',
          title: "Today's Volume",
          value: formatCurrency(stats.totalVolume * 0.05),
          icon: <TrendingUp className="h-8 w-8 text-success" />,
        },
        {
          id: 'total',
          title: 'Total Transactions',
          value: stats.totalTransactions.toLocaleString(),
          icon: <Calendar className="h-8 w-8 text-primary" />,
        },
        {
          id: 'flagged',
          title: 'Flagged',
          value: stats.activeAlerts,
          action:
            stats.activeAlerts > 0 ? (
              <Button variant="destructive" size="sm" onClick={handleReviewFlagged}>
                Review
              </Button>
            ) : undefined,
        },
        {
          id: 'success',
          title: 'Success Rate',
          value: '98.5%',
          icon: <TrendingDown className="h-8 w-8 text-error" />,
        },
      ]
    : [];

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Main Content */}
      <div
        className={cn(
          'flex-1 overflow-y-auto',
          selectedTransaction ? 'lg:w-2/3' : 'w-full',
        )}
      >
        <div className="container mx-auto px-4 py-6">
          {/* Page Header */}
          <div className="mb-6">
            <div className="flex items-start justify-between mb-4 md:mb-0">
              <div>
                <h1 className="text-2xl font-bold text-foreground mb-2">
                  Transactions
                </h1>
                <p className="text-muted-foreground">
                  View and manage all your transaction history
                </p>
              </div>
              <div className="hidden md:block">
                <AddTransactionDialog />
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          {stats && (
            <div className="mb-6">
              <StatsList stats={transactionStats} variant="compact" columns={4} />
            </div>
          )}

          {/* Search and Filters */}
          <div className="mb-6 space-y-4">
            {/* Search and Sort Row */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by merchant, ID, or category..."
                  className="w-full pl-10 pr-4 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                />
              </div>
              {/* Sort and buttons for md and above */}
              <div className="hidden md:flex gap-2">
                <div className="relative">
                  <select
                    value={`${sortBy}-${sortOrder}`}
                    onChange={(e) => {
                      const [field, order] = e.target.value.split('-') as [
                        'date' | 'amount' | 'merchant',
                        'asc' | 'desc',
                      ];
                      setSortBy(field);
                      setSortOrder(order);
                    }}
                    className="appearance-none pl-10 pr-8 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 cursor-pointer"
                  >
                    <option value="date-desc">Date (Newest)</option>
                    <option value="date-asc">Date (Oldest)</option>
                    <option value="amount-desc">Amount (High to Low)</option>
                    <option value="amount-asc">Amount (Low to High)</option>
                    <option value="merchant-asc">Merchant (A-Z)</option>
                    <option value="merchant-desc">Merchant (Z-A)</option>
                  </select>
                  <ArrowUpDown className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4 pointer-events-none" />
                  <div className="absolute right-2 top-1/2 transform -translate-y-1/2 pointer-events-none">
                    <svg
                      className="h-4 w-4 text-muted-foreground"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </div>
                <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                </Button>
                <Button variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </div>
            </div>

            {/* Mobile Layout: Sort on its own row */}
            <div className="md:hidden">
              <div className="relative">
                <select
                  value={`${sortBy}-${sortOrder}`}
                  onChange={(e) => {
                    const [field, order] = e.target.value.split('-') as [
                      'date' | 'amount' | 'merchant',
                      'asc' | 'desc',
                    ];
                    setSortBy(field);
                    setSortOrder(order);
                  }}
                  className="appearance-none w-full pl-10 pr-8 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 cursor-pointer"
                >
                  <option value="date-desc">Date (Newest)</option>
                  <option value="date-asc">Date (Oldest)</option>
                  <option value="amount-desc">Amount (High to Low)</option>
                  <option value="amount-asc">Amount (Low to High)</option>
                  <option value="merchant-asc">Merchant (A-Z)</option>
                  <option value="merchant-desc">Merchant (Z-A)</option>
                </select>
                <ArrowUpDown className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4 pointer-events-none" />
                <div className="absolute right-2 top-1/2 transform -translate-y-1/2 pointer-events-none">
                  <svg
                    className="h-4 w-4 text-muted-foreground"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </div>
              </div>
            </div>

            {/* Mobile Layout: Filter and Export buttons - 50% each */}
            <div className="md:hidden grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className="w-full"
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
              </Button>
              <Button variant="outline" className="w-full">
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>

            {/* Mobile Layout: Add Transaction button - 100% width */}
            <div className="md:hidden">
              <AddTransactionDialog />
            </div>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <Card className="p-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="text-sm font-medium text-foreground mb-1 block">
                    Status
                  </label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    <option value="">All Statuses</option>
                    <option value="completed">Completed</option>
                    <option value="pending">Pending</option>
                    <option value="flagged">Flagged</option>
                    <option value="failed">Failed</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1 block">
                    Type
                  </label>
                  <select className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring">
                    <option value="">All Types</option>
                    <option value="subscription">Subscription</option>
                    <option value="payment">Payment</option>
                    <option value="transfer">Transfer</option>
                    <option value="purchase">Purchase</option>
                    <option value="refund">Refund</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1 block">
                    Date Range
                  </label>
                  <select className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring">
                    <option value="">All Time</option>
                    <option value="today">Today</option>
                    <option value="week">This Week</option>
                    <option value="month">This Month</option>
                    <option value="custom">Custom Range</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1 block">
                    Amount Range
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      className="w-1/2 px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      className="w-1/2 px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setStatusFilter('');
                    setShowFilters(false);
                  }}
                >
                  Clear Filters
                </Button>
                <Button>Apply Filters</Button>
              </div>
            </Card>
          )}

          {/* Transactions List */}
          <TransactionList
            onTransactionClick={handleTransactionClick}
            itemsPerPage={20}
            searchQuery={searchQuery}
            sortBy={sortBy}
            sortOrder={sortOrder}
            statusFilter={statusFilter}
            selectedTransactionId={selectedTransaction?.id}
          />
        </div>
      </div>

      {/* Desktop Sidebar */}
      <TransactionSidebar
        transaction={selectedTransaction}
        onClose={handleCloseSidebar}
      />

      {/* Mobile Drawer */}
      {isMobile && (
        <TransactionDrawer
          transaction={selectedTransaction}
          open={isDrawerOpen}
          onOpenChange={handleCloseDrawer}
        />
      )}
    </div>
  );
}
