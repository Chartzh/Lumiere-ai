import { describe, test, expect, vi, beforeEach } from 'vitest';
import {
  request,
  register,
  login,
  fetchRecommendations,
  fetchPopular,
  fetchTrending,
  trackClick,
  trackRating,
  API_BASE
} from './api.js';

describe('src/lib/api.js - Helper Request & Endpoint API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
  });

  describe('request() helper', () => {
    test('Happy Path: Sukses melakukan GET request tanpa opsi tambahan', async () => {
      const mockData = { status: 'ok' };
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(mockData)
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request('/test-path');

      expect(globalThis.fetch).toHaveBeenCalledWith(`${API_BASE}/test-path`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: expect.any(AbortSignal)
      });
      expect(result).toEqual(mockData);
    });

    test('Happy Path: Sukses melakukan POST request dengan body dan token', async () => {
      const mockData = { id: 1 };
      const mockResponse = {
        ok: true,
        status: 201,
        json: vi.fn().mockResolvedValue(mockData)
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request('/test-post', {
        method: 'POST',
        body: { name: 'test' },
        token: 'mock-jwt-token'
      });

      expect(globalThis.fetch).toHaveBeenCalledWith(`${API_BASE}/test-post`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer mock-jwt-token'
        },
        signal: expect.any(AbortSignal),
        body: JSON.stringify({ name: 'test' })
      });
      expect(result).toEqual(mockData);
    });

    test('Error Handling: Mengeluarkan error ketika res.ok bernilai false', async () => {
      const errorDetail = { detail: 'Validasi gagal' };
      const mockResponse = {
        ok: false,
        status: 400,
        json: vi.fn().mockResolvedValue(errorDetail)
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      await expect(request('/invalid')).rejects.toThrow('Validasi gagal');
    });

    test('Error Handling: Mengeluarkan error default HTTP ketika response tidak memiliki JSON detail', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockRejectedValue(new Error('JSON parse error'))
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      await expect(request('/error-500')).rejects.toThrow('HTTP 500');
    });
  });

  describe('Fungsi-Fungsi Endpoint', () => {
    test('register() harus mengirim POST ke /api/v1/auth/register', async () => {
      const payload = { name: 'Tester', email: 'test@lumiere.com', password: 'password123' };
      const mockData = { user_id: 1, access_token: 'token' };
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockData)
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await register(payload);

      expect(globalThis.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/auth/register`, expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload)
      }));
      expect(result).toEqual(mockData);
    });

    test('login() harus mengirim POST ke /api/v1/auth/login', async () => {
      const payload = { email: 'test@lumiere.com', password: 'password123' };
      const mockData = { user_id: 1, access_token: 'token' };
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockData)
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await login(payload);

      expect(globalThis.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/auth/login`, expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload)
      }));
      expect(result).toEqual(mockData);
    });

    test('fetchRecommendations() harus mengirim POST dengan token ke /api/v1/recommend', async () => {
      const payload = { user_id: 1, top_k: 10 };
      const token = 'my-token';
      const mockData = { recommendations: [] };
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue(mockData)
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await fetchRecommendations(payload, token);

      expect(globalThis.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/recommend`, expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Authorization': `Bearer ${token}`
        }),
        body: JSON.stringify(payload)
      }));
      expect(result).toEqual(mockData);
    });

    test('fetchPopular() harus mengurai params menjadi query string', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ results: [] })
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      await fetchPopular({ limit: 5 });

      expect(globalThis.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/movies/popular?limit=5`, expect.any(Object));
    });

    test('fetchTrending() harus mengurai params menjadi query string', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ results: [] })
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      await fetchTrending({ limit: 5 });

      expect(globalThis.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/movies/trending?limit=5`, expect.any(Object));
    });

    test('trackClick() harus menangani error secara senyap (catch block coverage)', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ detail: 'Internal Server Error' })
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      // Pastikan tidak melempar error (catch block dijalankan)
      await expect(trackClick({ movie_id: 99 }, 'token')).resolves.not.toThrow();
    });

    test('trackRating() harus menangani error secara senyap (catch block coverage)', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ detail: 'Internal Server Error' })
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      // Pastikan tidak melempar error (catch block dijalankan)
      await expect(trackRating({ movie_id: 99, rating: 5 }, 'token')).resolves.not.toThrow();
    });
  });
});
