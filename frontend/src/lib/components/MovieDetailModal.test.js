import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';

// 1. Mock store dan api menggunakan standard vi.mock factory
vi.mock('$lib/stores/user.js', async () => {
  const { writable } = await import('svelte/store');
  const userStore = writable({
    id: 99,
    name: 'Herlita',
    email: 'herlita@lumiere.com',
    token: 'mock-jwt-token-123'
  });
  return {
    userStore
  };
});

vi.mock('$lib/api.js', () => ({
  request: vi.fn()
}));

// Mock global alert
vi.stubGlobal('alert', vi.fn());

// 2. Impor modul asli yang telah di-mock
import { userStore } from '$lib/stores/user.js';
import { request } from '$lib/api.js';
import MovieDetailModal from './MovieDetailModal.svelte';

describe('MovieDetailModal.svelte - Modal Detail & Interaksi Film', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(request).mockReset();
    userStore.set({
      id: 99,
      name: 'Herlita',
      email: 'herlita@lumiere.com',
      token: 'mock-jwt-token-123'
    });
  });

  test('Happy Path: Berhasil mengambil detail film dan data interaksi saat modal dibuka', async () => {
    mockRequestImplementation();

    render(MovieDetailModal, {
      props: { movieId: 101, isOpen: true, onClose: () => {} }
    });

    expect(screen.getByText('Memuat detail film...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Inception')).toBeInTheDocument();
      expect(screen.getByText('(2010)')).toBeInTheDocument();
      expect(screen.getByText('Sebuah mimpi di dalam mimpi.')).toBeInTheDocument();
      expect(screen.getByText('Christopher Nolan')).toBeInTheDocument();
    });
  });

  test('Error Handling: Menampilkan pesan kesalahan jika request detail film gagal', async () => {
    vi.mocked(request).mockRejectedValue(new Error('Gagal mengambil data dari server'));

    render(MovieDetailModal, {
      props: { movieId: 101, isOpen: true, onClose: () => {} }
    });

    await waitFor(() => {
      expect(screen.getByText('⚠️ Gagal memuat detail film.')).toBeInTheDocument();
    });
  });

  test('Happy Path: Berhasil menambahkan film ke daftar favorit', async () => {
    mockRequestImplementation();

    const onInteractionComplete = vi.fn();

    render(MovieDetailModal, {
      props: {
        movieId: 101,
        isOpen: true,
        onClose: () => {},
        onInteractionComplete
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Inception')).toBeInTheDocument();
    });

    const favButton = screen.getByRole('button', { name: '🤍 Tambah Favorit', hidden: true });
    await fireEvent.click(favButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '❤️ Difavoritkan', hidden: true })).toBeInTheDocument();
      expect(onInteractionComplete).toHaveBeenCalled();
    });
  });

  test('Happy Path: Berhasil mengirimkan rating bintang baru', async () => {
    mockRequestImplementation();

    const onInteractionComplete = vi.fn();

    render(MovieDetailModal, {
      props: {
        movieId: 101,
        isOpen: true,
        onClose: () => {},
        onInteractionComplete
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Inception')).toBeInTheDocument();
    });

    const stars = screen.getAllByRole('button', { name: '★', hidden: true });
    await fireEvent.click(stars[3]);

    await waitFor(() => {
      expect(request).toHaveBeenCalledWith('/api/v1/interactions', expect.objectContaining({
        method: 'POST',
        body: expect.objectContaining({
          type: 'rating',
          rating: 4
        })
      }));
      expect(onInteractionComplete).toHaveBeenCalled();
    });
  });

  test('Happy Path: Berhasil mengirim ulasan teks', async () => {
    mockRequestImplementation();

    const onInteractionComplete = vi.fn();

    render(MovieDetailModal, {
      props: {
        movieId: 101,
        isOpen: true,
        onClose: () => {},
        onInteractionComplete
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Inception')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText('Bagikan pendapatmu tentang film ini...');
    await fireEvent.input(textarea, { target: { value: 'Film yang sangat luar biasa!' } });

    const submitBtn = screen.getByRole('button', { name: 'Kirim Ulasan', hidden: true });
    await fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(request).toHaveBeenCalledWith('/api/v1/interactions', expect.objectContaining({
        method: 'POST',
        body: expect.objectContaining({
          type: 'review',
          review: 'Film yang sangat luar biasa!'
        })
      }));
      expect(globalThis.alert).toHaveBeenCalledWith('Review berhasil disimpan!');
      expect(onInteractionComplete).toHaveBeenCalled();
    });
  });

  test('Happy Path: Modal tidak me-render elemen apa pun ketika isOpen bernilai false', async () => {
    mockRequestImplementation();

    const { container, rerender } = render(MovieDetailModal, {
      props: { movieId: 101, isOpen: true, onClose: () => {} }
    });

    await waitFor(() => {
      expect(screen.getByText('Inception')).toBeInTheDocument();
    });

    // Rerender dengan isOpen: false
    await rerender({ movieId: 101, isOpen: false, onClose: () => {} });

    // Gunakan queryByText untuk memastikan konten modal bersih
    expect(screen.queryByText('Inception')).toBeNull();
  });
});

function mockRequestImplementation() {
  vi.mocked(request).mockImplementation((path, options) => {
    if (path.includes('/api/v1/movie/101')) {
      return Promise.resolve({
        movie: {
          movie_id: 101,
          title: 'Inception',
          year: 2010,
          avg_rating: 4.8,
          rating_count: 120,
          synopsis: 'Sebuah mimpi di dalam mimpi.',
          genres: ['Sci-Fi', 'Action'],
          directors: ['Christopher Nolan'],
          cast: [{ name: 'Leonardo DiCaprio', profile_url: '' }]
        }
      });
    }
    if (path.includes('/interactions')) {
      if (options?.method === 'POST') {
        return Promise.resolve({ status: 'success' });
      }
      return Promise.resolve([]);
    }
    return Promise.reject(new Error('Unknown path'));
  });
}
