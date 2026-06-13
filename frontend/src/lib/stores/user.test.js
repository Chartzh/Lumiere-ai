import { describe, test, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

// Mock localStorage sebelum modul diimpor
const mockStorage = new Map();
vi.stubGlobal('localStorage', {
  getItem: vi.fn((key) => mockStorage.get(key) || null),
  setItem: vi.fn((key, val) => mockStorage.set(key, String(val))),
  removeItem: vi.fn((key) => mockStorage.delete(key)),
  clear: vi.fn(() => mockStorage.clear()),
});

// Impor store setelah mock localStorage disematkan
const { userStore, isLoggedIn, needsOnboarding } = await import('./user.js');

describe('src/lib/stores/user.js - Svelte Stores & Session Auth', () => {
  beforeEach(() => {
    mockStorage.clear();
    userStore.logout();
    vi.clearAllMocks();
  });

  test('Inisialisasi Awal: Store kosong secara default jika localStorage kosong', () => {
    expect(get(userStore)).toBeNull();
    expect(get(isLoggedIn)).toBe(false);
    expect(get(needsOnboarding)).toBe(false);
  });

  test('login(): Menyimpan data user ke store dan localStorage', () => {
    const fakeUserData = {
      id: 99,
      name: 'Herlita',
      email: 'herlita@lumiere.com',
      favoriteGenres: ['Sci-Fi'],
      token: 'mock-jwt-token-123',
      isNewUser: true
    };

    userStore.login(fakeUserData);

    expect(get(userStore)).toEqual(fakeUserData);
    expect(localStorage.setItem).toHaveBeenCalledWith('lumiere_user', JSON.stringify(fakeUserData));
    expect(get(isLoggedIn)).toBe(true);
    expect(get(needsOnboarding)).toBe(true);
  });

  test('logout(): Membersihkan data store dan menghapus localStorage', () => {
    const fakeUserData = {
      id: 99,
      name: 'Herlita',
      token: 'mock-jwt-token-123'
    };
    userStore.login(fakeUserData);

    userStore.logout();

    expect(get(userStore)).toBeNull();
    expect(localStorage.removeItem).toHaveBeenCalledWith('lumiere_user');
    expect(get(isLoggedIn)).toBe(false);
  });

  test('patch(): Memperbarui sebagian data sesi tanpa menghapus properti lainnya', () => {
    const fakeUserData = {
      id: 99,
      name: 'Herlita',
      email: 'herlita@lumiere.com',
      favoriteGenres: [],
      token: 'mock-jwt-token-123',
      isNewUser: true
    };
    userStore.login(fakeUserData);

    // Patch untuk menyelesaikan onboarding
    userStore.patch({
      favoriteGenres: ['Sci-Fi', 'Action'],
      isNewUser: false
    });

    const currentData = get(userStore);
    expect(currentData.name).toBe('Herlita');
    expect(currentData.favoriteGenres).toEqual(['Sci-Fi', 'Action']);
    expect(currentData.isNewUser).toBe(false);

    expect(get(needsOnboarding)).toBe(false);
    expect(get(isLoggedIn)).toBe(true);
  });
});
