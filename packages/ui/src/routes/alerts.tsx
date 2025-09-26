import { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { Card } from '../components/atoms/card/card';
import { Button } from '../components/atoms/button/button';
import { Badge } from '../components/atoms/badge/badge';
import { AlertRuleForm } from '../components/alert-rule-form/alert-rule-form';
import {
  AlertRuleValidation,
  type ValidationResult,
} from '../components/alert-rule-validation/alert-rule-validation';
import { AlertRecommendations } from '../components/alert-recommendations/alert-recommendations';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { LocationPermissionAlert } from '../components/location/LocationPermissionAlert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/atoms/dialog/dialog';
import { Bell, Pause, Play, Trash2, AlertTriangle, X } from 'lucide-react';
import {
  useAlertRules,
  useCreateAlertRuleFromValidation,
  useToggleAlertRule,
  useDeleteAlertRule,
  useValidateAlertRule,
  useAlertRecommendations,
  useCreateRuleFromRecommendation,
} from '../hooks/transactions';
import { cn } from '../lib/utils';
import { statusColors } from '../lib/colors';
import type { CreateAlertRuleInput } from '../schemas/alert-rule';

export const Route = createFileRoute('/alerts')({
  component: () => (
    <ProtectedRoute>
      <AlertsPage />
    </ProtectedRoute>
  ),
});

function AlertsPage() {
  const { data: rules, isLoading } = useAlertRules();
  const { data: recommendations, isLoading: isLoadingRecommendations } =
    useAlertRecommendations();
  const createRuleFromValidation = useCreateAlertRuleFromValidation();
  const createRuleFromRecommendation = useCreateRuleFromRecommendation();
  const validateRule = useValidateAlertRule();
  const toggleRule = useToggleAlertRule();
  const deleteRule = useDeleteAlertRule();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [ruleToDelete, setRuleToDelete] = useState<{ id: string; name: string } | null>(
    null,
  );
  const [createError, setCreateError] = useState<{
    rule: string;
    message: string;
  } | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(
    null,
  );
  const [pendingRule, setPendingRule] = useState<string | null>(null);

  const handleValidateRule = async (data: CreateAlertRuleInput) => {
    try {
      setCreateError(null);
      setValidationResult(null);
      setPendingRule(data.rule);

      const result = await validateRule.mutateAsync(data.rule);
      setValidationResult(result);
    } catch (error) {
      console.error('Failed to validate rule:', error);
      setCreateError({
        rule: data.rule,
        message: 'Failed to validate the alert rule. Please try again.',
      });
    }
  };

  const handleConfirmCreateRule = async () => {
    if (
      !pendingRule ||
      !validationResult ||
      !validationResult.alert_rule ||
      !validationResult.sql_query
    )
      return;

    try {
      setCreateError(null);
      await createRuleFromValidation.mutateAsync({
        alert_rule: validationResult.alert_rule,
        sql_query: validationResult.sql_query,
        natural_language_query: pendingRule,
      });
      setValidationResult(null);
      setPendingRule(null);
    } catch (error) {
      console.error('Failed to create rule:', error);
      setCreateError({
        rule: pendingRule,
        message: 'Failed to create the alert rule. Please try again.',
      });
    }
  };

  const handleDismissValidation = () => {
    setValidationResult(null);
    setPendingRule(null);
  };

  const dismissError = () => {
    setCreateError(null);
  };

  const handleToggleRule = (ruleId: string) => {
    toggleRule.mutate(ruleId);
  };

  const openDeleteDialog = (ruleId: string, ruleName: string) => {
    setRuleToDelete({ id: ruleId, name: ruleName });
    setDeleteDialogOpen(true);
  };

  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setRuleToDelete(null);
  };

  const handleDeleteRule = () => {
    if (!ruleToDelete) return;

    deleteRule.mutate(ruleToDelete.id, {
      onSuccess: () => {
        closeDeleteDialog();
      },
    });
  };

  const handleCreateRuleFromRecommendation = async (recommendation: {
    title: string;
    description: string;
    natural_language_query: string;
    category: string;
    priority: 'high' | 'medium' | 'low';
    reasoning: string;
  }) => {
    try {
      setCreateError(null);
      await createRuleFromRecommendation.mutateAsync(recommendation);
    } catch (error) {
      console.error('Failed to create rule from recommendation:', error);
      setCreateError({
        rule: recommendation.title,
        message:
          'Failed to create the alert rule from recommendation. Please try again.',
      });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="text-center mt-4 mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Alert Rules</h1>
        <p className="text-muted-foreground">
          Create and manage your transaction monitoring rules with natural language
        </p>
      </div>

      {/* Alert Rule Form */}
      <div className="mb-8">
        <AlertRuleForm
          onSubmit={handleValidateRule}
          isSubmitting={validateRule.isPending}
        />
      </div>

      {/* Alert Recommendations */}
      <AlertRecommendations
        recommendations={recommendations || null}
        isLoading={isLoadingRecommendations}
        onCreateRule={handleCreateRuleFromRecommendation}
      />

      {/* Validation Result Display */}
      {validationResult && (
        <AlertRuleValidation
          validationResult={validationResult}
          onConfirm={handleConfirmCreateRule}
          onDismiss={handleDismissValidation}
          isCreating={createRuleFromValidation.isPending}
        />
      )}

      {/* Error Display */}
      {createError && (
        <div className="mb-8">
          <Card
            className={cn('border-l-4 p-4', statusColors.error.card, 'border-red-500')}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="flex-shrink-0">
                  <AlertTriangle
                    className={cn('h-5 w-5 mt-0.5', statusColors.error.icon)}
                  />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-medium text-red-900 dark:text-red-100">
                      Alert Rule Failed
                    </p>
                  </div>

                  {/* Display the failed rule */}
                  <div className="mb-3 p-3 bg-red-100/50 dark:bg-red-950/30 rounded-md border border-red-200/50 dark:border-red-800/30">
                    <p className="text-sm font-mono text-red-800 dark:text-red-200 italic">
                      "{createError.rule}"
                    </p>
                  </div>

                  {/* User-friendly error message */}
                  <p className="text-sm text-red-700 dark:text-red-300 leading-relaxed">
                    {createError.message}
                  </p>

                  <div className="mt-3">
                    <Badge
                      variant="secondary"
                      className={cn('capitalize', statusColors.error.badge)}
                    >
                      Invalid Rule
                    </Badge>
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={dismissError}
                className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200 hover:bg-red-100 dark:hover:bg-red-950/50"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Active Rules */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">Active Rules</h2>
        </div>

        {/* Location Permission Alert - positioned under Active Rules with matching width */}
        <LocationPermissionAlert />

        {isLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="p-4">
                <div className="animate-pulse">
                  <div className="h-5 bg-muted rounded w-3/4 mb-2" />
                  <div className="h-4 bg-muted rounded w-1/2" />
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {rules?.map((rule) => (
              <Card
                key={rule.id}
                className={cn(
                  'border-l-4 p-4',
                  rule.status === 'active' ? 'border-l-primary' : 'border-l-muted',
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Bell className="h-4 w-4 text-muted-foreground" />
                      <p className="font-medium text-foreground">{rule.rule}</p>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>Triggered {rule.triggered} times</span>
                      <span>•</span>
                      <span>Last: {rule.last_triggered}</span>
                      {rule.status === 'inactive' && (
                        <span className="text-orange-600 font-medium">• Paused</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="secondary"
                      className={cn(
                        'capitalize',
                        statusColors[rule.status as keyof typeof statusColors]?.badge ||
                          'bg-muted text-muted-foreground',
                      )}
                    >
                      {rule.status}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleToggleRule(rule.id)}
                      disabled={toggleRule.isPending}
                      title={
                        rule.status === 'active'
                          ? 'Pause alert rule'
                          : 'Resume alert rule'
                      }
                    >
                      {rule.status === 'active' ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4 text-green-600" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openDeleteDialog(rule.id, rule.rule)}
                      disabled={deleteRule.isPending}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}

            {rules?.length === 0 && (
              <Card className="p-8 text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted mb-3">
                  <Bell className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground">No alert rules configured yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Start by creating your first rule above
                </p>
              </Card>
            )}
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Alert Rule</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the alert rule "{ruleToDelete?.name}"?
              This action cannot be undone and will also delete all associated
              notifications.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={closeDeleteDialog}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteRule}
              disabled={deleteRule.isPending}
            >
              {deleteRule.isPending ? 'Deleting...' : 'Delete Rule'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
