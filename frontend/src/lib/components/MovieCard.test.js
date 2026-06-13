import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, test, expect } from 'vitest';
import MovieCard from './MovieCard.svelte';

describe('MovieCard.svelte - Komponen Kartu Film', () => {
  test('Happy Path: Sukses merender MovieCard dengan rating kecocokan tinggi (★ Perfect Match)', () => {
    render(MovieCard, {
      props: {
        movie_id: '101',
        title: 'Lumiere: Interstellar AI',
        confidence: 0.92,
        poster_url: 'https://placeholder.jpg',
        genre: 'Sci-Fi'
      }
    });

    expect(screen.getByText('Lumiere: Interstellar AI')).toBeInTheDocument();
    expect(screen.getByText('Sci-Fi')).toBeInTheDocument();
    
    // Verifikasi derived matchPercent (0.92 * 100 = 92%)
    expect(screen.getByText('92%')).toBeInTheDocument();
    
    // Verifikasi derived match-label (>= 85 -> ★ Perfect Match)
    expect(screen.getByText('★ Perfect Match')).toBeInTheDocument();
  });

  test('Branch Coverage: Rating kecocokan sedang (✦ Great Match)', () => {
    render(MovieCard, {
      props: {
        movie_id: '102',
        title: 'Great Movie',
        confidence: 0.78,
        poster_url: 'https://placeholder.jpg',
        genre: 'Drama'
      }
    });

    expect(screen.getByText('78%')).toBeInTheDocument();
    expect(screen.getByText('✦ Great Match')).toBeInTheDocument();
  });

  test('Branch Coverage: Rating kecocokan rendah (· Good Pick)', () => {
    render(MovieCard, {
      props: {
        movie_id: '103',
        title: 'Average Movie',
        confidence: 0.45,
        poster_url: 'https://placeholder.jpg',
        genre: 'Action'
      }
    });

    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(screen.getByText('· Good Pick')).toBeInTheDocument();
  });

  test('Null/Empty Parameter: Penanganan confidence bernilai null/undefined', () => {
    render(MovieCard, {
      props: {
        movie_id: '104',
        title: 'No Confidence Movie',
        confidence: null,
        poster_url: 'https://placeholder.jpg',
        genre: 'Mystery'
      }
    });

    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByText('· Good Pick')).toBeInTheDocument();
  });

  test('Error Handling: Mengaktifkan mode poster-fallback saat pemuatan poster gagal', async () => {
    render(MovieCard, {
      props: {
        movie_id: '105',
        title: 'Broken Poster Movie',
        confidence: 0.8,
        poster_url: 'https://broken-link.jpg',
        genre: 'Horror'
      }
    });

    // Cari elemen img
    const img = screen.getByRole('img');
    expect(img).toBeInTheDocument();

    // Trigger error event pada gambar
    await fireEvent.error(img);

    // Setelah error, img dihilangkan dan .poster-fallback dirender
    expect(img).not.toBeInTheDocument();
    expect(screen.getByText('🎬')).toBeInTheDocument();
    
    // Karena judul dicetak di fallback-title dan card-title, pastikan keduanya ada
    const titles = screen.getAllByText('Broken Poster Movie');
    expect(titles.length).toBe(2);
  });

  test('Null Parameter: Berhasil menggunakan poster-fallback sejak awal jika poster_url absen', () => {
    render(MovieCard, {
      props: {
        movie_id: '106',
        title: 'No Poster Movie',
        confidence: 0.8,
        poster_url: null,
        genre: 'Adventure'
      }
    });

    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByText('🎬')).toBeInTheDocument();
    
    const titles = screen.getAllByText('No Poster Movie');
    expect(titles.length).toBe(2);
  });

  test('Branch Coverage: Perhitungan numericId dan fallbackBg untuk non-numeric movie_id', () => {
    const { container } = render(MovieCard, {
      props: {
        movie_id: 'abc', // parsing parseInt("abc") -> NaN -> fallback 0
        title: 'Non Numeric ID Movie',
        confidence: 0.8,
        poster_url: null,
        genre: 'Comedy'
      }
    });

    // fallbackBg untuk indeks 0 adalah '#1a1a2e'
    const fallbackDiv = container.querySelector('.poster-fallback');
    expect(fallbackDiv).toHaveStyle('background: #1a1a2e');
  });
});
