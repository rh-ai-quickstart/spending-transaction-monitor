import type { Meta, StoryObj } from '@storybook/react';
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { Alert, AlertDescription } from './alert';

const meta: Meta<typeof Alert> = {
  title: 'Atoms/Alert',
  component: Alert,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: { type: 'select' },
      options: ['default', 'destructive', 'secondary'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: (args) => (
    <Alert {...args}>
      <Info className="h-4 w-4" />
      <AlertDescription>
        Your session will expire in 5 minutes. Please save your work.
      </AlertDescription>
    </Alert>
  ),
};

export const Destructive: Story = {
  render: (args) => (
    <Alert variant="destructive" {...args}>
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>
        Error: Unable to process transaction. Please try again.
      </AlertDescription>
    </Alert>
  ),
};

export const Secondary: Story = {
  render: (args) => (
    <Alert variant="secondary" {...args}>
      <CheckCircle2 className="h-4 w-4" />
      <AlertDescription>
        Your preferences have been saved successfully.
      </AlertDescription>
    </Alert>
  ),
};

export const WithoutIcon: Story = {
  render: (args) => (
    <Alert {...args}>
      <AlertDescription>This is an alert without an icon.</AlertDescription>
    </Alert>
  ),
};
