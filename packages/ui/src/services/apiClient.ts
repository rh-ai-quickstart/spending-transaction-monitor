/**
 * Centralized API client with location header support
 * Automatically includes user location in API requests for fraud detection
 */

import {
  getStoredLocation,
  createLocationHeaders,
  type LocationData,
} from '../hooks/useLocation';

export interface ApiClientConfig {
  baseUrl?: string;
  timeout?: number;
  includeLocation?: boolean;
  headers?: Record<string, string>;
}

export interface ApiResponse<T = unknown> {
  data: T;
  status: number;
  statusText: string;
  headers: globalThis.Headers;
}

export class ApiClient {
  private baseUrl: string;
  private timeout: number;
  private includeLocation: boolean;
  private defaultHeaders: Record<string, string>;

  constructor(config: ApiClientConfig = {}) {
    this.baseUrl = config.baseUrl || '/api';
    this.timeout = config.timeout || 30000;
    this.includeLocation = config.includeLocation ?? true;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      ...config.headers,
    };
  }

  /**
   * Create request headers including location if available
   */
  private createHeaders(
    customHeaders?: Record<string, string>,
  ): Record<string, string> {
    const headers = { ...this.defaultHeaders, ...customHeaders };

    // Add location headers if enabled
    if (this.includeLocation) {
      const location = getStoredLocation();
      if (location) {
        Object.assign(headers, createLocationHeaders(location));
      }
    }

    return headers;
  }

  /**
   * Make a request with timeout and error handling
   */
  private async makeRequest<T>(
    url: string,
    options: globalThis.RequestInit = {},
    customLocation?: LocationData | null,
  ): Promise<ApiResponse<T>> {
    const controller = new globalThis.AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      // Build full URL
      const fullUrl = url.startsWith('http') ? url : `${this.baseUrl}${url}`;

      // Create headers with optional custom location
      let headers = this.createHeaders(options.headers as Record<string, string>);

      // Override with custom location if provided
      if (customLocation) {
        Object.assign(headers, createLocationHeaders(customLocation));
      } else if (customLocation === null) {
        // Explicitly remove location headers if null is passed
        delete headers['X-User-Latitude'];
        delete headers['X-User-Longitude'];
        delete headers['X-User-Location-Accuracy'];
      }

      const response = await fetch(fullUrl, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const contentType = response.headers.get('content-type');
      let data: T;

      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = (await response.text()) as unknown as T;
      }

      if (!response.ok) {
        throw new ApiError(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          data,
        );
      }

      return {
        data,
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiError('Request timeout', 408);
      }

      throw error;
    }
  }

  /**
   * GET request
   */
  async get<T>(
    url: string,
    options?: {
      headers?: Record<string, string>;
      location?: LocationData | null;
    },
  ): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(
      url,
      {
        method: 'GET',
        headers: options?.headers,
      },
      options?.location,
    );
  }

  /**
   * POST request
   */
  async post<T>(
    url: string,
    data?: unknown,
    options?: {
      headers?: Record<string, string>;
      location?: LocationData | null;
    },
  ): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(
      url,
      {
        method: 'POST',
        headers: options?.headers,
        body: data ? JSON.stringify(data) : undefined,
      },
      options?.location,
    );
  }

  /**
   * PUT request
   */
  async put<T>(
    url: string,
    data?: unknown,
    options?: {
      headers?: Record<string, string>;
      location?: LocationData | null;
    },
  ): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(
      url,
      {
        method: 'PUT',
        headers: options?.headers,
        body: data ? JSON.stringify(data) : undefined,
      },
      options?.location,
    );
  }

  /**
   * DELETE request
   */
  async delete<T>(
    url: string,
    options?: {
      headers?: Record<string, string>;
      location?: LocationData | null;
    },
  ): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(
      url,
      {
        method: 'DELETE',
        headers: options?.headers,
      },
      options?.location,
    );
  }

  /**
   * Update location inclusion setting
   */
  setIncludeLocation(include: boolean): void {
    this.includeLocation = include;
  }

  /**
   * Set default headers
   */
  setDefaultHeaders(headers: Record<string, string>): void {
    this.defaultHeaders = { ...this.defaultHeaders, ...headers };
  }
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
  public status: number;
  public data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }

  /**
   * Check if error is due to authentication failure
   */
  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }

  /**
   * Check if error is due to network/server issues
   */
  get isNetworkError(): boolean {
    return this.status >= 500 || this.status === 408;
  }
}

// Default API client instance
export const apiClient = new ApiClient();

// Convenience function to create a client with custom config
export function createApiClient(config: ApiClientConfig): ApiClient {
  return new ApiClient(config);
}

// Legacy fetch wrapper for backward compatibility
export async function fetchWithLocation(
  url: string,
  options: globalThis.RequestInit = {},
  customLocation?: LocationData | null,
): Promise<globalThis.Response> {
  const headers = new globalThis.Headers(options.headers);

  // Add location headers if not explicitly disabled
  if (customLocation !== null) {
    const location = customLocation || getStoredLocation();
    if (location) {
      const locationHeaders = createLocationHeaders(location);
      Object.entries(locationHeaders).forEach(([key, value]) => {
        headers.set(key, value);
      });
    }
  }

  return fetch(url, {
    ...options,
    headers,
  });
}

/**
 * Hook for API client with location context
 */
export function useApiClient(location?: LocationData | null) {
  const client = new ApiClient({ includeLocation: location !== null });

  return {
    get: <T>(url: string, options?: { headers?: Record<string, string> }) =>
      client.get<T>(url, { ...options, location }),
    post: <T>(
      url: string,
      data?: unknown,
      options?: { headers?: Record<string, string> },
    ) => client.post<T>(url, data, { ...options, location }),
    put: <T>(
      url: string,
      data?: unknown,
      options?: { headers?: Record<string, string> },
    ) => client.put<T>(url, data, { ...options, location }),
    delete: <T>(url: string, options?: { headers?: Record<string, string> }) =>
      client.delete<T>(url, { ...options, location }),
  };
}
