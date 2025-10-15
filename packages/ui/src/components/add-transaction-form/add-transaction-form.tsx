import { useForm } from '@tanstack/react-form';
import {
  CreateTransaction,
  CreateTransactionSchema,
  TRANSACTION_CATEGORIES,
  ACCOUNT_TYPES,
} from '../../schemas/transaction';
import { Button } from '../atoms/button/button';
import { Input } from '../atoms/input/input';
import { Label } from '../atoms/label/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../atoms/select/select';
import { Textarea } from '../atoms/textarea/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../atoms/dialog/dialog';
import { useState, useEffect } from 'react';
import { useCreateTransaction } from '../../hooks/transactions';
import { PlusIcon, MapPinIcon } from 'lucide-react';
import { toast } from 'sonner';
import { getCurrentLocation } from '../../services/geolocation';

// Nominatim API response types
interface NominatimAddress {
  city?: string;
  town?: string;
  village?: string;
  county?: string;
  state?: string;
  country?: string;
  postcode?: string;
}

interface NominatimSearchResult {
  place_id: number;
  lat: string;
  lon: string;
  display_name: string;
  address: NominatimAddress;
  name?: string;
}

interface NominatimReverseResult {
  place_id: number;
  lat: string;
  lon: string;
  display_name: string;
  address: NominatimAddress;
}

export function AddTransactionDialog() {
  const [open, setOpen] = useState(false);
  const [isFetchingLocation, setIsFetchingLocation] = useState(false);
  const [citySuggestions, setCitySuggestions] = useState<
    Array<{
      display_name: string;
      name: string;
      state?: string;
      country?: string;
      lat: string;
      lon: string;
    }>
  >([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchTimeout, setSearchTimeout] = useState<ReturnType<
    typeof setTimeout
  > | null>(null);
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number } | null>(
    null,
  );
  const createTransactionMutation = useCreateTransaction();

  const form = useForm({
    defaultValues: {
      date: new Date().toISOString().split('T')[0], // Today's date in YYYY-MM-DD format
      description: '',
      amount: 0,
      category: '',
      account: '',
      type: 'debit',
      merchant: '',
      merchant_city: '',
      merchant_state: '',
      merchant_country: '',
      tags: [] as string[],
      notes: '',
    } as CreateTransaction,
    onSubmit: async ({ value }) => {
      // Use the mutation to create the transaction
      createTransactionMutation.mutate(value);
    },
    validators: {
      onSubmit: CreateTransactionSchema,
    },
  });

  const handleCancel = () => {
    setOpen(false);
    form.reset();
    setCitySuggestions([]);
    setShowSuggestions(false);
  };

  // Get user's location when dialog opens (for biased search)
  useEffect(() => {
    if (open && !userLocation) {
      getCurrentLocation()
        .then((loc) => {
          setUserLocation({ lat: loc.latitude, lon: loc.longitude });
        })
        .catch(() => {
          // Silently fail - autocomplete will work without location bias
        });
    }
  }, [open, userLocation]);

  // Search for cities with autocomplete
  const searchCities = async (query: string) => {
    if (!query || query.length < 2) {
      setCitySuggestions([]);
      return;
    }

    try {
      // Build URL with optional location bias
      let url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`;

      // Bias results towards user's location if available
      if (userLocation) {
        url += `&viewbox=${userLocation.lon - 0.5},${userLocation.lat + 0.5},${userLocation.lon + 0.5},${userLocation.lat - 0.5}&bounded=0`;
      }

      const response = await fetch(url, {
        headers: {
          Accept: 'application/json',
          'User-Agent': 'SpendingMonitor/1.0',
        },
      });

      if (!response.ok) return;

      const data: NominatimSearchResult[] = await response.json();

      // Filter and format results
      const suggestions = data
        .filter(
          (item) => item.address?.city || item.address?.town || item.address?.village,
        )
        .map((item) => ({
          display_name: item.display_name,
          name:
            item.address?.city ||
            item.address?.town ||
            item.address?.village ||
            item.name ||
            'Unknown',
          state: item.address?.state,
          country: item.address?.country,
          lat: item.lat,
          lon: item.lon,
        }));

      setCitySuggestions(suggestions);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error searching cities:', error);
    }
  };

  // Debounced search
  const handleCityInputChange = (value: string) => {
    form.setFieldValue('merchant_city', value);

    // Clear previous timeout
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    // Set new timeout for search
    const timeout = setTimeout(() => {
      searchCities(value);
    }, 300); // 300ms debounce

    setSearchTimeout(timeout);
  };

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion: (typeof citySuggestions)[0]) => {
    form.setFieldValue('merchant_city', suggestion.name);
    form.setFieldValue('merchant_state', suggestion.state || '');
    form.setFieldValue('merchant_country', suggestion.country || '');
    setCitySuggestions([]);
    setShowSuggestions(false);
  };

  // Get city from current GPS location using Nominatim (free, no API key)
  const handleUseCurrentLocation = async () => {
    setIsFetchingLocation(true);
    try {
      // Get GPS coordinates
      const location = await getCurrentLocation();

      // Reverse geocode using Nominatim (OpenStreetMap)
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${location.latitude}&lon=${location.longitude}`,
        {
          headers: {
            Accept: 'application/json',
            'User-Agent': 'SpendingMonitor/1.0', // Required by Nominatim
          },
        },
      );

      if (!response.ok) {
        throw new Error('Failed to fetch location data');
      }

      const data: NominatimReverseResult = await response.json();
      const city =
        data.address?.city ||
        data.address?.town ||
        data.address?.village ||
        data.address?.county;

      if (city) {
        form.setFieldValue('merchant_city', city);
        form.setFieldValue('merchant_state', data.address?.state || '');
        form.setFieldValue('merchant_country', data.address?.country || '');
        toast.success(`Location set to ${city}`);
        setCitySuggestions([]);
        setShowSuggestions(false);
      } else {
        toast.error('Could not determine city from your location');
      }
    } catch (error) {
      console.error('Error getting location:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to get location');
    } finally {
      setIsFetchingLocation(false);
    }
  };

  // Cleanup search timeout on unmount
  useEffect(() => {
    return () => {
      if (searchTimeout) {
        clearTimeout(searchTimeout);
      }
    };
  }, [searchTimeout]);

  // Handle mutation success/error with useEffect
  useEffect(() => {
    if (createTransactionMutation.isSuccess) {
      setOpen(false);
      form.reset();
      toast.success('Transaction created successfully');
      setCitySuggestions([]);
      setShowSuggestions(false);
    }
  }, [createTransactionMutation.isSuccess, form]);

  useEffect(() => {
    if (createTransactionMutation.isError) {
      console.error('Failed to create transaction:', createTransactionMutation.error);
      toast.error(
        createTransactionMutation.error?.message || 'Failed to create transaction',
      );
    }
  }, [createTransactionMutation.isError, createTransactionMutation.error]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="flex items-center gap-2 w-full md:w-auto">
          <PlusIcon className="h-4 w-4" />
          Add Transaction
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add New Transaction</DialogTitle>
          <DialogDescription>
            Enter the details for the new transaction below.
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            {/* Date */}
            <form.Field
              name="date"
              validators={{
                onChange: CreateTransactionSchema.shape.date,
              }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Date *</Label>
                  <Input
                    id={field.name}
                    type="date"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                  />
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">
                      {field.state.meta.errors[0]?.message.toString()}
                    </p>
                  )}
                </div>
              )}
            </form.Field>

            {/* Amount */}
            <form.Field
              name="amount"
              validators={{
                onChange: CreateTransactionSchema.shape.amount,
              }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Amount *</Label>
                  <Input
                    id={field.name}
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={field.state.value || ''}
                    onChange={(e) =>
                      field.handleChange(parseFloat(e.target.value) || 0)
                    }
                    onBlur={field.handleBlur}
                  />
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">
                      {field.state.meta.errors[0]?.message.toString()}
                    </p>
                  )}
                </div>
              )}
            </form.Field>
          </div>

          {/* Description */}
          <form.Field
            name="description"
            validators={{
              onChange: CreateTransactionSchema.shape.description,
            }}
          >
            {(field) => (
              <div className="space-y-2">
                <Label htmlFor={field.name}>Description *</Label>
                <Input
                  id={field.name}
                  placeholder="Enter transaction description"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                />
                {field.state.meta.errors.length > 0 && (
                  <p className="text-sm text-destructive">
                    {field.state.meta.errors[0]?.message.toString()}
                  </p>
                )}
              </div>
            )}
          </form.Field>

          <div className="grid grid-cols-2 gap-4">
            {/* Category */}
            <form.Field
              name="category"
              validators={{
                onChange: CreateTransactionSchema.shape.category,
              }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Category *</Label>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) => field.handleChange(value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {TRANSACTION_CATEGORIES.map((category) => (
                        <SelectItem key={category} value={category}>
                          {category}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">
                      {field.state.meta.errors[0]?.message.toString()}
                    </p>
                  )}
                </div>
              )}
            </form.Field>

            {/* Account */}
            <form.Field
              name="account"
              validators={{
                onChange: CreateTransactionSchema.shape.account,
              }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Account *</Label>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) => field.handleChange(value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select account" />
                    </SelectTrigger>
                    <SelectContent>
                      {ACCOUNT_TYPES.map((account) => (
                        <SelectItem key={account} value={account}>
                          {account}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">
                      {field.state.meta.errors[0]?.message.toString()}
                    </p>
                  )}
                </div>
              )}
            </form.Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Type */}
            <form.Field
              name="type"
              validators={{
                onChange: CreateTransactionSchema.shape.type,
              }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Type *</Label>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) =>
                      field.handleChange(value as 'debit' | 'credit')
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="debit">Debit</SelectItem>
                      <SelectItem value="credit">Credit</SelectItem>
                    </SelectContent>
                  </Select>
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">
                      {field.state.meta.errors[0]?.message.toString()}
                    </p>
                  )}
                </div>
              )}
            </form.Field>

            {/* Merchant */}
            <form.Field
              name="merchant"
              validators={{
                onChange: CreateTransactionSchema.shape.merchant,
              }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Merchant</Label>
                  <Input
                    id={field.name}
                    placeholder="Enter merchant name"
                    value={field.state.value || ''}
                    onChange={(e) => field.handleChange(e.target.value || '')}
                    onBlur={field.handleBlur}
                  />
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">
                      {field.state.meta.errors[0]?.message.toString()}
                    </p>
                  )}
                </div>
              )}
            </form.Field>
          </div>

          {/* Merchant City (optional) with Autocomplete */}
          <form.Field
            name="merchant_city"
            validators={{
              onChange: CreateTransactionSchema.shape.merchant_city,
            }}
          >
            {(field) => (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor={field.name}>Merchant City (optional)</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleUseCurrentLocation}
                    disabled={isFetchingLocation}
                    className="h-7 px-2 text-xs"
                  >
                    <MapPinIcon className="h-3 w-3 mr-1" />
                    {isFetchingLocation ? 'Getting location...' : 'Use my location'}
                  </Button>
                </div>
                <div className="relative">
                  <Input
                    id={field.name}
                    placeholder="e.g., San Francisco"
                    value={field.state.value || ''}
                    onChange={(e) => handleCityInputChange(e.target.value || '')}
                    onBlur={() => {
                      field.handleBlur();
                      // Delay hiding suggestions to allow click
                      setTimeout(() => setShowSuggestions(false), 200);
                    }}
                    onFocus={() => {
                      if (citySuggestions.length > 0) {
                        setShowSuggestions(true);
                      }
                    }}
                    autoComplete="off"
                  />
                  {showSuggestions && citySuggestions.length > 0 && (
                    <div className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-md max-h-60 overflow-auto">
                      {citySuggestions.map((suggestion, index) => (
                        <button
                          key={index}
                          type="button"
                          className="w-full px-3 py-2 text-left hover:bg-accent hover:text-accent-foreground text-sm cursor-pointer border-b last:border-b-0"
                          onClick={() => handleSuggestionSelect(suggestion)}
                        >
                          <div className="font-medium">{suggestion.name}</div>
                          <div className="text-xs text-muted-foreground truncate">
                            {suggestion.display_name}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {field.state.meta.errors.length > 0 && (
                  <p className="text-sm text-destructive">
                    {field.state.meta.errors[0]?.message.toString()}
                  </p>
                )}
              </div>
            )}
          </form.Field>

          {/* Notes */}
          <form.Field
            name="notes"
            validators={{
              onChange: CreateTransactionSchema.shape.notes,
            }}
          >
            {(field) => (
              <div className="space-y-2">
                <Label htmlFor={field.name}>Notes</Label>
                <Textarea
                  id={field.name}
                  placeholder="Additional notes (optional)"
                  value={field.state.value || ''}
                  onChange={(e) => field.handleChange(e.target.value || '')}
                  onBlur={field.handleBlur}
                  rows={3}
                />
                {field.state.meta.errors.length > 0 && (
                  <p className="text-sm text-destructive">
                    {field.state.meta.errors[0]?.message.toString()}
                  </p>
                )}
              </div>
            )}
          </form.Field>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={createTransactionMutation.isPending}
            >
              Cancel
            </Button>
            <form.Subscribe selector={(state) => [state.canSubmit]}>
              {([canSubmit]) => (
                <Button
                  type="submit"
                  disabled={!canSubmit || createTransactionMutation.isPending}
                >
                  {createTransactionMutation.isPending
                    ? 'Adding...'
                    : 'Add Transaction'}
                </Button>
              )}
            </form.Subscribe>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
