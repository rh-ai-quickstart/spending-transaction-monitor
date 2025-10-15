import { useForm } from '@tanstack/react-form';
import { Button } from '../atoms/button/button';
import { Input } from '../atoms/input/input';
import {
  CreateAlertRuleSchema,
  type CreateAlertRuleInput,
} from '../../schemas/alert-rule';
import { cn } from '../../lib/utils';
import { Sparkles, ArrowRight, Loader2 } from 'lucide-react';

export interface AlertRuleFormProps {
  className?: string;
  onSubmit?: (data: CreateAlertRuleInput) => void | Promise<void>;
  isSubmitting?: boolean;
}

export function AlertRuleForm({
  className,
  onSubmit,
  isSubmitting = false,
}: AlertRuleFormProps) {
  const form = useForm({
    defaultValues: {
      rule: '',
    },
    onSubmit: async ({ value }) => {
      console.log('Form submitted:', value);
      await onSubmit?.(value);
      form.reset();
    },
    validators: {
      onChange: CreateAlertRuleSchema,
    },
  });

  return (
    <form
      className={cn('space-y-4', className)}
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
    >
      <div className="relative max-w-2xl mx-auto">
        <form.Field name="rule">
          {(field) => (
            <>
              <div className="relative">
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <Input
                  id={field.name}
                  name={field.name}
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  placeholder="Describe your alert rule in plain English..."
                  className={cn(
                    'px-10 py-6 text-lg z-10',
                    'border-2 border-primary/20 focus:border-primary rounded-xl',
                    'focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    field.state.meta.errors.length > 0 &&
                      'border-destructive focus:border-destructive',
                  )}
                  disabled={isSubmitting}
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={
                    !field.state.value.trim() ||
                    isSubmitting ||
                    field.state.meta.errors.length > 0
                  }
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 h-8 w-8 p-1 rounded-lg z-20"
                >
                  {isSubmitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <ArrowRight className="h-4 w-4" />
                  )}
                </Button>
              </div>

              {field.state.meta.errors.length > 0 && (
                <div className="text-center py-2">
                  <p className="text-sm text-destructive">
                    {field.state.meta.errors[0]?.message?.toString()}
                  </p>
                </div>
              )}
            </>
          )}
        </form.Field>
      </div>
    </form>
  );
}
