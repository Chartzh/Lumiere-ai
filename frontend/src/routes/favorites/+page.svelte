<script>
  /**
   * routes/favorites/+page.svelte
   * Halaman Favorit Saya — Menampilkan daftar film yang disukai user.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { userStore, isLoggedIn } from '$lib/stores/user.js';
  import { request } from '$lib/api.js'; // 1. Menggunakan fungsi request asli bawaan tim
  import MovieCard from '$lib/components/MovieCard.svelte';
  import MovieDetailModal from '$lib/components/MovieDetailModal.svelte';
  import LoadingSkeleton from '$lib/components/LoadingSkeleton.svelte';

  // ── State (Svelte 5 Runes) ─────────────────────────────────────────────
  let favorites = $state([]);
  let loading = $state(true);
  let error = $state('');
  
  // State untuk Modal Detail
  let selectedMovieId = $state(null);
  let isModalOpen = $state(false);

  const user = $derived($userStore);

  onMount(async () => {
    if (!$isLoggedIn) { goto('/login'); return; }
    await loadFavorites();
  });

  // ── Ambil Daftar Favorit v5 ────────────────────────────────────────────
  async function loadFavorites() {
    loading = true;
    error = '';
    try {
      // 2. Path wajib menyertakan prefix /api/v1 dan token dikirim dalam objek opsi
      const data = await request(`/api/v1/users/${user.id}/interactions?type=favorite`, { 
        token: user.token 
      });
      // Antisipasi jika response langsung berupa array atau dibungkus objek results
      const interactions = Array.isArray(data) ? data : (data.interactions ?? data.results ?? []);
      
      // Fetch detail film untuk setiap interaksi secara paralel
      favorites = await Promise.all(
        interactions.map(async (item) => {
          try {
            const detailData = await request(`/api/v1/movie/${item.movie_id}`, { token: user.token });
            return {
              ...item,
              movie: detailData.movie
            };
          } catch (err) {
            return {
              ...item,
              movie: {
                movie_id: item.movie_id,
                title: `Film #${item.movie_id}`,
                poster_url: '',
                genres: ['Movie']
              }
            };
          }
        })
      );
    } catch (e) {
      error = e.message || 'Gagal memuat daftar favorit.';
    } finally {
      loading = false;
    }
  }

  // ── Hapus dari Favorit v5 ──────────────────────────────────────────────
  async function handleRemoveFavorite(e, interactionId) {
    e.stopPropagation(); // Mencegah modal terbuka saat mengklik tombol hapus
    
    if (!confirm('Hapus film ini dari favorit?')) return;

    try {
      // 3. Menghapus dengan signature objek opsi { method: 'DELETE', token } sesuai dengan api.js tim
      await request(`/api/v1/interactions/${interactionId}`, { 
        method: 'DELETE', 
        token: user.token 
      });
      
      // Update state lokal secara berkala agar responsif tanpa refresh full page
      favorites = favorites.filter(item => item.id !== interactionId && item.interaction_id !== interactionId);
    } catch (e) {
      alert('Gagal menghapus favorit, coba lagi.');
    }
  }

  function handleCardClick(movieId) {
    selectedMovieId = movieId;
    isModalOpen = true;
  }
</script>

<div class="page">
  <nav class="navbar">
    <div class="nav-brand">
      <img src="/logo.webp" alt="Lumiere Logo" width="100" height="100" style="object-fit: contain;" />
      <span class="brand-tag">MY FAVORITES</span>
    </div>
    <div class="nav-right">
      {#if user}
        <a href="/" class="nav-link">Beranda</a>
        <a href="/favorites" class="nav-link active">Favorit Saya</a>
        <a href="/profile" class="nav-link">Profil Selera</a>
        <span class="nav-user">Halo, <strong>{user.name}</strong></span>
        <button class="btn-ghost" onclick={() => { userStore.logout(); goto('/login'); }}>Keluar</button>
      {/if}
    </div>
  </nav>

  <main class="content">
    <section class="section">
      <div class="section-head">
        <div>
          <h1 class="section-title">❤️ Favorit Saya</h1>
          <p class="section-sub">
            Koleksi film yang kamu sukai. Film di sini otomatis memperkuat benih algoritma 
            content-based boosting untuk memberikan rekomendasi yang lebih tajam.
          </p>
        </div>
        <button class="btn-ghost-sm" onclick={loadFavorites} disabled={loading}>
          {loading ? '...' : '↺ Refresh'}
        </button>
      </div>

      {#if loading}
        <div class="movie-grid">
          <LoadingSkeleton count={8} />
        </div>

      {:else if error}
        <div class="error-state">
          <span class="error-icon">⚠</span>
          <div>
            <div class="error-title">Gagal memuat data</div>
            <div class="error-msg">{error}</div>
            <button class="btn-gold-sm" onclick={loadFavorites}>Coba lagi</button>
          </div>
        </div>

      {:else if favorites.length === 0}
        <div class="empty-state">
          <span class="empty-icon">🍿</span>
          <p>Belum ada film di daftar favoritmu.</p>
          <a href="/" class="btn-gold-sm" style="text-decoration: none; display: inline-block; margin-top: 10px;">
            Jelajahi Film
          </a>
        </div>

      {:else}
        <div class="movie-grid">
          {#each favorites as item (item.id || item.interaction_id)}
            {@const film = item.movie || item}
            <div class="fav-card-wrapper" style="position: relative;">
              <MovieCard
                movie_id={film.movie_id}
                title={film.title}
                confidence={film.year ? `Tahun ${film.year}` : 'Film Favorit'}
                poster_url={film.poster_url}
                genre={Array.isArray(film.genres) ? film.genres[0] : (film.genre || 'Movie')}
                synopsis={film.synopsis}
                onclick={handleCardClick}
              />
              <button 
                class="remove-fav-badge" 
                onclick={(e) => handleRemoveFavorite(e, item.id || item.interaction_id)}
                aria-label="Hapus dari favorit"
                title="Hapus dari favorit"
              >
                ✕
              </button>
            </div>
          {/each}
        </div>
      {/if}
    </section>
  </main>



  <footer class="site-footer">
    Lumiere © 2026 · PJK-GM074 · Pijak × IBM SkillsBuild ·
    <span>Lita · Rajif · Arghi · Zaky</span>
  </footer>
</div>

<MovieDetailModal 
  movieId={selectedMovieId} 
  isOpen={isModalOpen} 
  onClose={() => isModalOpen = false} 
  onInteractionComplete={loadFavorites} 
/>

<style>
  /* Menggunakan Token Desain Utama agar Inkonsistensi Visual 0% */
  .page { min-height: 100vh; background: var(--noir-bg); display: flex; flex-direction: column; }
  .content { flex: 1; max-width: 1200px; width: 100%; margin: 0 auto; padding: 0 1.5rem 3rem; }

  .navbar {
    position: sticky; top: 0; z-index: 50;
    background: rgba(10,10,15,.88); backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--noir-border);
    display: flex; align-items: center; justify-content: space-between;
    padding: .9rem 1.5rem; gap: 1rem;
  }
  .nav-brand   { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .brand-name  { color: var(--cream); font-size: 1rem; font-weight: 500; }
  .brand-tag   { font-size: .6rem; color: #444455; letter-spacing: .08em; }
  .nav-right   { display: flex; align-items: center; gap: 10px; }
  .nav-user    { font-size: .8rem; color: var(--muted); }
  .nav-user strong { color: var(--cream); }
  .nav-link {
    font-size: 0.85rem; color: var(--muted); text-decoration: none;
    padding: 4px 6px; border-radius: var(--radius-sm); transition: color 0.2s;
  }
  .nav-link:hover { color: var(--cream); }
  .nav-link.active { color: var(--gold); }

  .section { margin-top: 2.5rem; }
  .section-head {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap;
  }
  .section-title { font-size: 1.5rem; font-weight: 500; color: var(--cream); margin-bottom: 4px; }
  .section-sub { font-size: 0.85rem; color: var(--muted); line-height: 1.5; max-width: 600px; }

  .movie-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 16px;
    margin-top: 1.5rem;
  }

  /* Badge Silang Floating untuk Hapus Favorit */
  .remove-fav-badge {
    position: absolute; top: -6px; right: -6px;
    width: 22px; height: 22px; background: #e05252; color: #ffffff;
    border: none; border-radius: 50%; font-size: 0.65rem; font-weight: bold;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.5); z-index: 10;
    transition: transform 0.15s ease;
  }
  .remove-fav-badge:hover { transform: scale(1.15); background: #ff5c5c; }

  .error-state {
    display: flex; align-items: flex-start; gap: 12px;
    background: rgba(224,82,82,.08); border: 1px solid rgba(224,82,82,.2);
    border-radius: var(--radius-md); padding: 1rem 1.25rem;
  }
  .error-icon  { font-size: 1.25rem; color: #e05252; flex-shrink: 0; }
  .error-title { font-size: .9rem; color: #ff8080; font-weight: 500; margin-bottom: 2px; }
  .error-msg   { font-size: .8rem; color: var(--muted); margin-bottom: .5rem; }

  .empty-state { text-align: center; padding: 4rem 1rem; display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .empty-icon { font-size: 3rem; color: var(--subtle); }
  .empty-state p { font-size: .9rem; color: var(--muted); }

  .btn-ghost {
    padding: 6px 14px; border-radius: var(--radius-sm);
    border: 1px solid var(--noir-border); background: transparent; color: var(--muted); font-size: .8rem; cursor: pointer;
  }
  .btn-ghost:hover { border-color: var(--subtle); color: var(--cream); }

  .btn-ghost-sm {
    padding: 5px 12px; border-radius: var(--radius-sm);
    border: 1px solid var(--noir-border); background: transparent; color: var(--muted); font-size: .75rem; cursor: pointer;
  }
  .btn-ghost-sm:hover:not(:disabled) { border-color: var(--gold-dim); color: var(--gold); }

  .btn-gold-sm {
    padding: 6px 16px; border-radius: var(--radius-sm); background: var(--gold); border: none; color: #09090e; font-size: .8rem; font-weight: 500; cursor: pointer;
  }
  .btn-gold-sm:hover { opacity: .85; }

  .site-footer { border-top: 1px solid var(--noir-border); padding: 1.25rem 1.5rem; font-size: .7rem; color: var(--subtle); text-align: center; }
  .site-footer span { color: #444455; }

  @media (max-width: 640px) {
    .movie-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .brand-tag { display: none; }
    .nav-link { display: none; }
    .content { padding: 0 1rem 2rem; }
  }
  @media (min-width: 1024px) {
    .movie-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  }
</style>