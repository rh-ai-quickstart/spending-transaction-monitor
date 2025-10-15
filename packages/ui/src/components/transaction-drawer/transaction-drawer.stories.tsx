import type { Meta, StoryObj } from '@storybook/react';
import { TransactionDrawer } from './transaction-drawer';
import { useState } from 'react';
import { Button } from '../atoms/button/button';
import type { Transaction } from '../../schemas/transaction';

const mockTransaction: Transaction = {
  id: 'TXN-0042',
  user_id: 'u-test-001',
  credit_card_num: '1234',
  amount: 1234.56,
  currency: 'USD',
  description:
    'Monthly subscription for AWS hosting services including EC2, S3, and CloudFront usage.',
  merchant_name: 'Amazon Web Services',
  merchant_category: 'Cloud Services',
  transaction_date: '2024-01-15T14:30:00.000Z',
  transaction_type: 'PURCHASE',
  status: 'APPROVED',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const flaggedTransaction: Transaction = {
  id: 'TXN-0043',
  user_id: 'u-test-001',
  credit_card_num: '1234',
  amount: 2500.0,
  currency: 'USD',
  description:
    'Large wire transfer flagged for manual review due to amount exceeding daily limit.',
  merchant_name: 'Wire Transfer',
  merchant_category: 'Transfer',
  transaction_date: '2024-01-15T09:15:00.000Z',
  transaction_type: 'PAYMENT',
  status: 'DECLINED',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const meta = {
  title: 'Components/TransactionDrawer',
  component: TransactionDrawer,
  decorators: [
    (Story) => (
      <div className="p-8 bg-background">
        <Story />
      </div>
    ),
  ],
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof TransactionDrawer>;

export default meta;
type Story = StoryObj<typeof meta>;

const DefaultComponent = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Open Transaction Drawer</Button>
      <TransactionDrawer
        transaction={mockTransaction}
        open={isOpen}
        onOpenChange={setIsOpen}
      />
    </>
  );
};

export const Default: Story = {
  args: {
    transaction: mockTransaction,
    open: false,
    onOpenChange: () => {},
  },
  render: () => <DefaultComponent />,
};

const FlaggedComponent = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button variant="destructive" onClick={() => setIsOpen(true)}>
        Open Flagged Transaction
      </Button>
      <TransactionDrawer
        transaction={flaggedTransaction}
        open={isOpen}
        onOpenChange={setIsOpen}
      />
    </>
  );
};

export const FlaggedTransaction: Story = {
  args: {
    transaction: flaggedTransaction,
    open: false,
    onOpenChange: () => {},
  },
  render: () => <FlaggedComponent />,
};

export const AlwaysOpen: Story = {
  args: {
    transaction: mockTransaction,
    open: true,
    onOpenChange: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          'Drawer always open for design review. In real usage, the drawer would be controlled by state.',
      },
    },
  },
};
