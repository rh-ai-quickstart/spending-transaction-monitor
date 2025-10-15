import type { Meta, StoryObj } from '@storybook/react';
import { TransactionCard } from './transaction-card';
import type { Transaction } from '../../schemas/transaction';

const meta: Meta<typeof TransactionCard> = {
  title: 'Components/TransactionCard',
  component: TransactionCard,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
  argTypes: {
    onClick: { action: 'clicked' },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

const sampleTransaction: Transaction = {
  id: 'txn_1234567890',
  user_id: 'u-test-001',
  credit_card_num: '1234',
  amount: 45.67,
  currency: 'USD',
  description: 'Morning coffee and pastry',
  merchant_name: 'Coffee Shop Downtown',
  merchant_category: 'dining',
  transaction_date: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 minutes ago
  transaction_type: 'PURCHASE',
  status: 'APPROVED',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export const Default: Story = {
  args: {
    transaction: sampleTransaction,
  },
};

export const Selected: Story = {
  args: {
    transaction: sampleTransaction,
    isSelected: true,
  },
};

export const Pending: Story = {
  args: {
    transaction: {
      ...sampleTransaction,
      status: 'PENDING',
      merchant: 'Online Store',
      category: 'shopping',
      amount: 129.99,
      transaction_type: 'PURCHASE',
    },
  },
};

export const Failed: Story = {
  args: {
    transaction: {
      ...sampleTransaction,
      status: 'failed',
      merchant: 'Gas Station',
      category: 'transport',
      amount: 65.43,
      transaction_type: 'PURCHASE',
    },
  },
};

export const LargeAmount: Story = {
  args: {
    transaction: {
      ...sampleTransaction,
      merchant: 'Electronics Store',
      category: 'shopping',
      amount: 1299.99,
      transaction_type: 'PURCHASE',
    },
  },
};

export const LongMerchantName: Story = {
  args: {
    transaction: {
      ...sampleTransaction,
      merchant: 'Very Long Business Name That Should Truncate Properly',
      category: 'business',
      amount: 234.56,
      type: 'payment',
    },
  },
};

export const CloudService: Story = {
  args: {
    transaction: {
      ...sampleTransaction,
      merchant: 'AWS Services',
      category: 'cloud software',
      amount: 89.23,
      type: 'subscription',
    },
  },
};

export const Travel: Story = {
  args: {
    transaction: {
      ...sampleTransaction,
      merchant: 'Airline Booking',
      category: 'travel',
      amount: 456.78,
      transaction_type: 'PURCHASE',
    },
  },
};

export const Multiple: Story = {
  render: () => (
    <div className="space-y-2 max-w-2xl">
      <TransactionCard transaction={sampleTransaction} />
      <TransactionCard
        transaction={{
          ...sampleTransaction,
          id: 'txn_0987654321',
          merchant_name: 'Uber Ride',
          merchant_category: 'transport',
          amount: 23.45,
          status: 'PENDING',
          transaction_type: 'PAYMENT',
        }}
      />
      <TransactionCard
        transaction={{
          ...sampleTransaction,
          id: 'txn_1122334455',
          merchant_name: 'Netflix Subscription',
          merchant_category: 'entertainment',
          amount: 15.99,
          status: 'APPROVED',
          transaction_type: 'PURCHASE',
        }}
        isSelected
      />
    </div>
  ),
};

export const MobileView: Story = {
  parameters: {
    viewport: {
      defaultViewport: 'mobile1',
    },
  },
  args: {
    transaction: sampleTransaction,
  },
};
