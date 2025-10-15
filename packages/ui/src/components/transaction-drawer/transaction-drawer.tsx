import { Badge } from '../atoms/badge/badge';
import { Button } from '../atoms/button/button';
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '../atoms/drawer/drawer';
import { statusColors } from '../../lib/colors';
import { cn } from '../../lib/utils';
import { getCategoryIcon } from '../../lib/category-icons';
import { Copy, Calendar, CreditCard, MapPin } from 'lucide-react';
import type { Transaction } from '../../schemas/transaction';

export interface TransactionDrawerProps {
  transaction: Transaction | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TransactionDrawer({
  transaction,
  open,
  onOpenChange,
}: TransactionDrawerProps) {
  if (!transaction) return null;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(transaction.id);
    console.log('Transaction ID copied');
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-h-[80vh]">
        <DrawerHeader className="text-left">
          <DrawerTitle className="sr-only">Transaction Details</DrawerTitle>
        </DrawerHeader>
        <div className="px-6 pb-6 overflow-y-auto">
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>
                  {new Date(transaction.transaction_date).toLocaleDateString('en-US', {
                    weekday: 'long',
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </span>
              </div>
              <Badge
                variant="secondary"
                className={cn(
                  'capitalize',
                  statusColors[
                    transaction.status.toLowerCase() as keyof typeof statusColors
                  ]?.badge,
                )}
              >
                {transaction.status}
              </Badge>
            </div>

            {/* Main Info */}
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <h2 className="text-2xl font-bold text-foreground leading-tight">
                  {transaction.merchant_name}
                </h2>
                <p className="text-2xl font-bold text-foreground">
                  {formatCurrency(transaction.amount)}
                </p>
              </div>

              {/* Pills */}
              <div className="flex flex-wrap gap-3">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-info-muted text-info-muted-foreground rounded-full">
                  <div className="text-sm">
                    {getCategoryIcon(transaction.merchant_category)}
                  </div>
                  <span className="text-sm font-medium uppercase tracking-wide">
                    {transaction.merchant_category || transaction.transaction_type}
                  </span>
                </div>

                <div
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full"
                  style={{ backgroundColor: 'var(--chart-1)' }}
                >
                  <CreditCard className="h-4 w-4 text-white" />
                  <span className="text-sm font-medium text-white">Primary Card</span>
                </div>
              </div>

              {/* Details */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border/50">
                <div className="text-center">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                    Time
                  </p>
                  <p className="text-sm font-medium text-foreground">
                    {new Date(transaction.transaction_date).toLocaleTimeString(
                      'en-US',
                      {
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true,
                      },
                    )}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                    ID
                  </p>
                  <div className="flex items-center justify-center gap-1">
                    <p className="text-xs font-medium text-foreground font-mono">
                      {transaction.id}
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyId}
                      className="h-5 w-5 p-0"
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Description */}
            {transaction.description && (
              <div className="p-4 bg-muted/30 rounded-lg">
                <p className="text-sm text-foreground leading-relaxed">
                  {transaction.description}
                </p>
              </div>
            )}

            {/* Location Info */}
            {(transaction.merchant_city ||
              transaction.merchant_state ||
              transaction.merchant_country) && (
              <div className="pt-4 border-t border-border/50">
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-3">
                  Location
                </p>
                <div className="flex items-start gap-3 p-3 bg-muted/30 rounded-lg">
                  <MapPin className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    {transaction.merchant_city && (
                      <p className="text-sm font-medium text-foreground">
                        {transaction.merchant_city}
                      </p>
                    )}
                    {(transaction.merchant_state || transaction.merchant_country) && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {[transaction.merchant_state, transaction.merchant_country]
                          .filter(Boolean)
                          .join(', ')}
                      </p>
                    )}
                    {transaction.merchant_zipcode && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {transaction.merchant_zipcode}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
