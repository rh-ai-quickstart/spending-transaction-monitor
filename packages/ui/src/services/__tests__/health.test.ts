import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getHealth } from '../health';

globalThis.fetch = vi.fn();

describe('getHealth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch health data successfully', async () => {
    const mockHealthData = [
      {
        name: 'api',
        status: 'healthy' as const,
        message: 'API is healthy',
        version: '1.0.0',
        start_time: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockHealthData,
    } as Response);

    const result = await getHealth();

    expect(globalThis.fetch).toHaveBeenCalledWith('/health/');
    expect(result).toEqual(mockHealthData);
  });

  it('should throw error when response is not ok', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: false,
      status: 500,
    } as Response);

    await expect(getHealth()).rejects.toThrow('Failed to fetch health');
  });

  it('should parse response with schema', async () => {
    const mockHealthData = [
      {
        name: 'database',
        status: 'healthy' as const,
        message: 'DB is up',
        version: '1.0.0',
        start_time: '2024-01-01T00:00:00Z',
      },
      {
        name: 'cache',
        status: 'degraded' as const,
        message: 'Cache is slow',
        version: '1.0.0',
        start_time: '2024-01-01T00:00:00Z',
      },
    ];

    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockHealthData,
    } as Response);

    const result = await getHealth();

    expect(Array.isArray(result)).toBe(true);
    expect(result).toHaveLength(2);
    expect(result[0].name).toBe('database');
    expect(result[0].status).toBe('healthy');
  });
});
