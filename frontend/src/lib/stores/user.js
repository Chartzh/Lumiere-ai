/**
 * lib/stores/user.js
 * ─────────────────────────────────────────────────────────────────────
 * Svelte store untuk session user yang sedang login.
 * Dipakai di seluruh aplikasi untuk cek auth, simpan profil, dan token.
 *
 * Struktur data user:
 * {
 *   id             : number    — user_id di backend
 *   name           : string    — nama tampilan
 *   email          : string
 *   favoriteGenres : string[]  — dipilih saat onboarding
 *   token          : string    — JWT dari backend
 *   isNewUser      : boolean   — true jika belum selesai onboarding
 * }
 */

import { writable, derived } from 'svelte/store';

const STORAGE_KEY = 'lumiere_user';

function createUserStore() {
  // Ambil session dari localStorage supaya tetap login setelah refresh
  const stored = typeof localStorage !== 'undefined'
    ? localStorage.getItem(STORAGE_KEY)
    : null;

  const initial = stored ? JSON.parse(stored) : null;
  const { subscribe, set, update } = writable(initial);

  return {
    subscribe,

    /** Simpan data user setelah login berhasil */
    login(userData) {
      set(userData);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userData));
    },

    /** Hapus session saat logout */
    logout() {
      set(null);
      localStorage.removeItem(STORAGE_KEY);
    },

    /** Update sebagian data — misal setelah onboarding selesai */
    patch(partial) {
      update(current => {
        const updated = { ...current, ...partial };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        return updated;
      });
    }
  };
}

export const userStore      = createUserStore();

/** true jika user sudah login (ada token) */
export const isLoggedIn     = derived(userStore, $u => !!$u?.token);

/** true jika user baru yang belum selesai onboarding */
export const needsOnboarding = derived(userStore, $u => $u?.isNewUser === true);
