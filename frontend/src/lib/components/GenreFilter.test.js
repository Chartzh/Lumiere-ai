import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, test, expect, vi } from 'vitest';
import GenreFilter from './GenreFilter.svelte';

describe('GenreFilter.svelte - Komponen Filter Genre', () => {
  test('Happy Path: Berhasil merender seluruh pill genre beserta opsi default All', () => {
    const genres = ['Action', 'Comedy', 'Sci-Fi'];
    render(GenreFilter, { props: { genres, activeGenre: 'All', onSelect: () => {} } });

    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getByText('Action')).toBeInTheDocument();
    expect(screen.getByText('Comedy')).toBeInTheDocument();
    expect(screen.getByText('Sci-Fi')).toBeInTheDocument();
  });

  test('Branch Coverage: Menyematkan class active dan aria-pressed=true pada activeGenre', () => {
    const genres = ['Action', 'Comedy'];
    render(GenreFilter, { props: { genres, activeGenre: 'Action', onSelect: () => {} } });

    const actionButton = screen.getByRole('button', { name: 'Action' });
    const comedyButton = screen.getByRole('button', { name: 'Comedy' });

    expect(actionButton).toHaveClass('active');
    expect(actionButton).toHaveAttribute('aria-pressed', 'true');

    expect(comedyButton).not.toHaveClass('active');
    expect(comedyButton).toHaveAttribute('aria-pressed', 'false');
  });

  test('Happy Path: Memanggil callback onSelect saat tombol diklik', async () => {
    const genres = ['Action', 'Comedy'];
    const onSelect = vi.fn();
    render(GenreFilter, { props: { genres, activeGenre: 'All', onSelect } });

    const actionButton = screen.getByRole('button', { name: 'Action' });
    await fireEvent.click(actionButton);

    expect(onSelect).toHaveBeenCalledWith('Action');
  });
});
