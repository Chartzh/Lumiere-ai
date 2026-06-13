<script>
  /**
   * routes/movie/[id]/+page.svelte
   * ───────────────────────────────────────────────────────────────────────────
   * Halaman Detail Film Resmi Lumiere — Noir & Gold Premium Design
   * Menggunakan Svelte 5 Runes untuk pembaruan state reaktif secara penuh.
   */
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { request, fetchPopular } from '$lib/api.js';
  import { userStore, isLoggedIn } from '$lib/stores/user.js';
  import MovieCard from '$lib/components/MovieCard.svelte';
  import LoadingSkeleton from '$lib/components/LoadingSkeleton.svelte';

  // ── Svelte 5 Runes State ──────────────────────────────────────────────────
  let movieId = $derived($page.params.id);
  const user = $derived($userStore);

  let movie = $state(null);
  let loading = $state(true);
  let error = $state('');

  // State untuk form interaksi (ML loops)
  let isFavorite = $state(false);
  let favoriteInteraction = $state(null);
  let rating = $state(0);
  let reviewText = $state('');
  let submittingInteraction = $state(false);
  let hoveredStar = $state(0);

  // State ulasan & film serupa
  let similarMovies = $state([]);
  let loadingSimilar = $state(false);
  let historicalReviews = $state([]);
  let loadingReviews = $state(false);

  // ── Reactive Fetching saat movieId berubah ─────────────────────────────────
  $effect(() => {
    if (movieId && $isLoggedIn) {
      loadAllMovieData(movieId);
    }
  });

  // Proteksi rute pada tingkat browser
  onMount(() => {
    if (!$isLoggedIn) {
      goto('/login');
    }
  });

  async function loadAllMovieData(id) {
    loading = true;
    error = '';
    try {
      // 1. Ambil detail film (IMDb-style)
      const data = await request(`/api/v1/movie/${id}?include_credits=true`, { token: user?.token });
      movie = data.movie;

      // Ambil data historis dan interaksi secara paralel untuk kecepatan pemuatan halaman
      await Promise.all([
        loadHistoricalReviews(id),
        loadSimilarMovies(id)
      ]);
      
      // Ambil interaksi pengguna saat ini setelah ulasan historis terisi agar dapat digabungkan secara dinamis
      await loadUserInteractions(id);
    } catch (e) {
      error = e.message || 'Gagal memuat detail film.';
    } finally {
      loading = false;
    }
  }

  // Ambil data interaksi user lama terhadap film ini langsung dari API/Database
  async function loadUserInteractions(id) {
    try {
      const data = await request(`/api/v1/users/${user.id}/interactions`, { token: user.token });
      const interactions = Array.isArray(data) ? data : (data.results ?? []);
      
      const numericId = parseInt(id) || 0;
      const fav = interactions.find(i => i.movie_id === numericId && i.type === 'favorite'); 
      const rat = interactions.find(i => i.movie_id === numericId && i.type === 'rating'); 
      const rev = interactions.find(i => i.movie_id === numericId && i.type === 'review'); 

      favoriteInteraction = fav;
      isFavorite = !!fav;
      rating = rat ? rat.rating : 0;
      reviewText = rev ? rev.review : '';

      // Tampilkan ulasan pengguna ini secara dinamis pada daftar jika ada ulasan aktif dari database
      if (rev) {
        const reviewExists = historicalReviews.some(
          r => r.id === rev.id || r.id === rev.interaction_id || r.user_name === (user?.name || 'Kamu')
        );
        if (!reviewExists) {
          historicalReviews = [
            {
              id: rev.id || rev.interaction_id || `user-review-${id}`,
              user_name: user?.name || 'Kamu',
              rating: rat ? rat.rating : 5,
              review: rev.review,
              created_at: rev.created_at || new Date().toISOString()
            },
            ...historicalReviews
          ];
        }
      }
    } catch {
      // Gagal senyap jika belum ada interaksi lama
    }
  }

  // Ambil film serupa (More Like This) dari API
  async function loadSimilarMovies(id) {
    loadingSimilar = true;
    try {
      const data = await request(`/api/v1/movies/${id}/similar`, { token: user?.token });
      similarMovies = data.recommendations ?? data.results ?? (Array.isArray(data) ? data : []);
    } catch {
      // Fallback ke popular film dari API jika endpoint item-similarity gagal/tidak tersedia
      try {
        const data = await fetchPopular({ limit: 6 });
        similarMovies = data.recommendations ?? data.results ?? (Array.isArray(data) ? data : []);
      } catch {
        similarMovies = [];
      }
    } finally {
      loadingSimilar = false;
    }
  }

  // Ambil riwayat komentar/ulasan film dari seluruh user dari API
  async function loadHistoricalReviews(id) {
    loadingReviews = true;
    try {
      const data = await request(`/api/v1/movie/${id}/reviews`, { token: user?.token });
      historicalReviews = Array.isArray(data) ? data : (data.results || data.reviews || []);
    } catch {
      // Bebas hardcode: jika API gagal/tidak ditemukan, atur ke array kosong
      historicalReviews = [];
    } finally {
      loadingReviews = false;
    }
  }

  // ── Handler Interaksi ML Loops ─────────────────────────────────────────────
  async function handleFavorite() {
    submittingInteraction = true; 
    try {
      const numericMovieId = parseInt(movieId) || 0;
      if (isFavorite && favoriteInteraction) {
        // Unfavorite: Hapus interaksi dari database
        const favId = favoriteInteraction.id || favoriteInteraction.interaction_id;
        await request(`/api/v1/interactions/${favId}`, {
          method: 'DELETE',
          token: user.token
        });
        isFavorite = false;
        favoriteInteraction = null;
      } else {
        // Favorite: Tambahkan ke database
        const data = await request('/api/v1/interactions', {
          method: 'POST',
          body: {
            user_id: parseInt(user.id),
            movie_id: numericMovieId,
            type: 'favorite'
          },
          token: user.token
        });
        isFavorite = true;
        // Simpan data interaksi baru agar bisa dihapus nanti
        favoriteInteraction = data.interaction ?? data;
      }
    } catch {
      alert('Gagal memperbarui status favorit.');
    } finally {
      submittingInteraction = false; 
    }
  }

  async function handleRating(score) {
    submittingInteraction = true; 
    try {
      const numericMovieId = parseInt(movieId) || 0;
      await request('/api/v1/interactions', {
        method: 'POST',
        body: {
          user_id: parseInt(user.id),
          movie_id: numericMovieId,
          type: 'rating',
          rating: score
        },
        token: user.token
      });
      rating = score;
    } catch {
      alert('Gagal mengirim ulasan rating.');
    } finally {
      submittingInteraction = false; 
    }
  }

  async function handleReviewSubmit(e) {
    e.preventDefault();
    if (!reviewText.trim()) return;
    
    submittingInteraction = true;
    try {
      const numericMovieId = parseInt(movieId) || 0;
      await request('/api/v1/interactions', {
        method: 'POST',
        body: {
          user_id: parseInt(user.id),
          movie_id: numericMovieId,
          type: 'review',
          rating: rating || 5,
          review: reviewText.trim()
        },
        token: user.token
      });

      // Tambahkan ulasan baru secara reaktif di sisi atas ulasan historis (local update)
      historicalReviews = [
        {
          id: Date.now().toString(),
          user_name: user?.name || 'Kamu',
          rating: rating || 5,
          review: reviewText.trim(),
          created_at: new Date().toISOString()
        },
        ...historicalReviews
      ];
      
      alert('Ulasan teks berhasil disimpan ke database!');
      reviewText = '';
    } catch {
      alert('Gagal mengirimkan ulasan teks.');
    } finally {
      submittingInteraction = false; 
    }
  }
</script>

<div class="page">
  <!-- Navbar Header -->
  <nav class="navbar">
    <div class="nav-brand" onclick={() => goto('/')} style="cursor: pointer;">
      <span class="brand-star">✦</span>
      <span class="brand-name">Lumiere</span>
    </div>
    <div class="nav-right">
      {#if user}
        <span class="nav-user">Halo, <strong>{user.name}</strong></span>
        <button class="btn-ghost" onclick={() => { userStore.logout(); goto('/login'); }}>Keluar</button>
      {/if}
    </div>
  </nav>

  <main class="content">
    <div class="back-nav-container">
      <button class="btn-back-home" onclick={() => goto('/')}>
        <span class="back-icon">←</span> Kembali ke Beranda
      </button>
    </div>

    {#if loading}
      <div class="loader-wrap">
        <LoadingSkeleton count={1} />
        <p class="loader-text">Mengekstraksi Metadata Film...</p>
      </div>
    {:else if error}
      <div class="error-state">
        <span class="error-icon">⚠</span>
        <div>
          <div class="error-title">Gagal Memuat Detail Film</div>
          <div class="error-msg">{error}</div>
          <button class="btn-gold-sm" onclick={() => loadAllMovieData(movieId)}>Muat Ulang</button>
        </div>
      </div>
    {:else if movie}
      <!-- 1. IMDb-style Info Header -->
      <section class="movie-backdrop" style="background-image: linear-gradient(to bottom, rgba(10,10,15,0.3), var(--noir-bg)), url({movie.poster_url || 'https://via.placeholder.com/1200x500'})">
        <div class="backdrop-content">
          <span class="movie-meta-year">{movie.year || 'N/A'}</span>
          <h1 class="movie-title">{movie.title}</h1>
          {#if movie.genres}
            <div class="genres-row">
              {#each movie.genres as g}
                <span class="genre-badge">{g}</span>
              {/each}
            </div>
          {/if}
        </div>
      </section>

      <div class="details-grid">
        <!-- Kolom Kiri: Poster dan Tombol Aksi Cepat -->
        <div class="left-col">
          <div class="poster-wrap-detail">
            <img class="poster-img-detail" src={movie.poster_url || 'https://via.placeholder.com/300x450'} alt={movie.title} />
          </div>
          
          <button class="btn-favorite" class:favorited={isFavorite} onclick={handleFavorite} disabled={submittingInteraction}>
            {isFavorite ? '❤️ Difavoritkan' : '🤍 Tambah ke Favorit'}
          </button>
        </div>

        <!-- Kolom Kanan: Detail IMDb, Rating & XAI Panel -->
        <div class="right-col">
          <!-- Rating Box -->
          <div class="rating-header-box">
            <div class="rating-item">
              <span class="rating-label">Rating Rata-rata</span>
              <div class="rating-val-wrap">
                <span class="gold-star-large">★</span>
                <span class="rating-num">{movie.avg_rating?.toFixed(1) || '0.0'}</span>
                <span class="rating-scale">/5.0</span>
              </div>
            </div>
            <div class="rating-item border-left">
              <span class="rating-label">Total Ulasan</span>
              <span class="rating-count">{movie.rating_count || 0} pengguna</span>
            </div>
          </div>

          <!-- Sinopsis -->
          <div class="info-section">
            <h3 class="info-title">Sinopsis</h3>
            <p class="synopsis-text">{movie.synopsis || 'Sinopsis tidak tersedia untuk film ini.'}</p>
          </div>

          <!-- Credits -->
          <div class="credits-grid">
            {#if movie.directors?.length}
              <div class="credit-item">
                <span class="credit-label">Sutradara</span>
                <span class="credit-value">{movie.directors.join(', ')}</span>
              </div>
            {/if}
            {#if movie.cast?.length}
              <div class="credit-item">
                <span class="credit-label">Pemeran Utama</span>
                <div class="cast-names">
                  {movie.cast.map(c => c.name).join(', ')}
                </div>
              </div>
            {/if}
          </div>

          <!-- 2. AI Transparency Panel (XAI) -->
          <div class="xai-panel">
            <div class="xai-header">
              <span class="xai-spark">🔮</span>
              <h4>Transparansi AI Lumiere</h4>
            </div>
            <p class="xai-reason">
              <strong>Alasan Rekomendasi:</strong> "{movie.xai_reason?.primary_factor || 'Disarankan berdasarkan kecocokan DNA seleramu dengan preferensi genre sejenis.'}"
            </p>
            <div class="xai-footer">
              Model Neural Collaborative Filtering (NCF) kami mendeteksi film ini memiliki kecocokan tinggi dengan selera historis Anda.
            </div>
          </div>
        </div>
      </div>

      <!-- 3. ML loops interaction box (Kotak Interaksi User) -->
      <section class="section interaction-section">
        <h3 class="section-title-custom">⚡ Kotak Interaksi Loops ML</h3>
        <p class="section-sub-custom">Beri masukan langsung untuk mengoptimalkan model rekomendasi personal AI Anda secara real-time.</p>

        <div class="interaction-card">
          <div class="rating-form-group">
            <span class="form-label">Berikan Rating Bintang Anda:</span>
            <div class="stars-interactive">
              {#each [1,2,3,4,5] as star}
                <button
                  class="star-btn"
                  class:hovered={hoveredStar >= star}
                  class:filled={rating >= star && hoveredStar === 0}
                  onmouseenter={() => hoveredStar = star}
                  onmouseleave={() => hoveredStar = 0}
                  onclick={() => handleRating(star)}
                  disabled={submittingInteraction}
                >
                  ★
                </button>
              {/each}
            </div>
            {#if rating > 0}
              <span class="rating-applied-label">Rating Anda: {rating} Bintang</span>
            {/if}
          </div>

          <form class="review-form" onsubmit={handleReviewSubmit}>
            <label for="review-textarea" class="form-label">Tulis Ulasan Sinematik Anda:</label>
            <textarea
              id="review-textarea"
              placeholder="Bagikan ulasan mendalam Anda tentang film ini agar AI kami mengenali minat Anda..."
              bind:value={reviewText}
              rows="4"
              disabled={submittingInteraction}
            ></textarea>
            <button class="btn-submit-review" type="submit" disabled={submittingInteraction || !reviewText.trim()}>
              {submittingInteraction ? 'Mengirim...' : 'Kirim Ulasan Teks'}
            </button>
          </form>
        </div>
      </section>

      <!-- 4. More Like This Section (Item Similarity) -->
      <section class="section">
        <h3 class="section-title-custom">🎬 Film Serupa (More Like This)</h3>
        <p class="section-sub-custom">Rekomendasi berbasis kemiripan konten (*item-similarity*) dalam database Lumiere.</p>
        
        {#if loadingSimilar}
          <LoadingSkeleton count={4} />
        {:else if similarMovies.length === 0}
          <p class="empty-similar">Tidak ada film serupa yang ditemukan.</p>
        {:else}
          <div class="similar-scroller">
            {#each similarMovies.slice(0, 6) as film}
              <div class="similar-card-wrap">
                <MovieCard
                  movie_id={film.movie_id}
                  title={film.title}
                  confidence={film.confidence ?? film.xai_reason?.primary_factor ?? 'Kemiripan 90%'}
                  poster_url={film.poster_url}
                  genre={Array.isArray(film.genres) ? film.genres[0] : (film.genre || 'Movie')}
                  synopsis={film.synopsis}
                  onclick={(id) => goto(`/movie/${id}`)}
                />
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <!-- 5. Seksi Daftar Komentar & Ulasan Historis -->
      <section class="section reviews-section">
        <h3 class="section-title-custom">💬 Ulasan & Komentar Pengguna ({historicalReviews.length})</h3>
        
        {#if loadingReviews}
          <div class="loader-comments">Memuat Ulasan Historis...</div>
        {:else if historicalReviews.length === 0}
          <div class="empty-reviews">Belum ada komentar untuk film ini. Jadilah yang pertama memberikan ulasan!</div>
        {:else}
          <div class="reviews-list">
            {#each historicalReviews as review (review.id)}
              <div class="review-card-detail">
                <div class="review-card-header">
                  <div class="user-info">
                    <span class="user-avatar">🍿</span>
                    <span class="user-name">{review.user_name}</span>
                  </div>
                  <div class="user-rating-badge">
                    {#each Array(5) as _, i}
                      <span class="star-mini" class:active={review.rating > i}>★</span>
                    {/each}
                  </div>
                </div>
                <p class="review-body">"{review.review}"</p>
                <span class="review-time">Diulas pada {new Date(review.created_at).toLocaleDateString('id-ID')}</span>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    {/if}
  </main>

  <footer class="site-footer">
    Lumiere © 2026 · PJK-GM074 · Pijak × IBM SkillsBuild
  </footer>
</div>

<style>
  /* ── Layout & Core ── */
  .page {
    min-height: 100vh;
    background: var(--noir-bg);
    display: flex;
    flex-direction: column;
  }
  .content {
    flex: 1;
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    padding: 0 1.5rem 4rem;
  }

  .back-nav-container {
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
  }
  .btn-back-home {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: transparent;
    border: 1px solid var(--noir-border, #222);
    color: var(--muted, #888);
    padding: 8px 16px;
    border-radius: var(--radius-sm, 4px);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .btn-back-home:hover {
    border-color: var(--gold, #c9a84c);
    color: var(--cream, #f5f5f7);
    background: rgba(201, 168, 76, 0.05);
  }
  .back-icon {
    font-size: 1rem;
    transition: transform 0.2s ease;
  }
  .btn-back-home:hover .back-icon {
    transform: translateX(-4px);
  }

  /* ── Navbar ── */
  .navbar {
    position: sticky; top: 0; z-index: 50;
    background: rgba(10, 10, 15, 0.88); backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--noir-border);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.9rem 1.5rem; gap: 1rem;
  }
  .brand-star { color: var(--gold); }
  .brand-name { color: var(--cream); font-size: 1.15rem; font-weight: 500; letter-spacing: 0.05em; }
  .nav-right { display: flex; align-items: center; gap: 10px; }
  .nav-user { font-size: 0.8rem; color: var(--muted); }
  .nav-user strong { color: var(--cream); }

  /* ── Loader ── */
  .loader-wrap { text-align: center; padding: 5rem 0; }
  .loader-text { margin-top: 1rem; color: var(--muted); font-size: 0.85rem; }

  /* ── Section Titles ── */
  .section-title-custom { font-size: 1.1rem; color: var(--cream); font-weight: 500; margin-bottom: 4px; }
  .section-sub-custom { font-size: 0.8rem; color: var(--muted); margin-bottom: 1.5rem; }

  /* ── Backdrop Area ── */
  .movie-backdrop {
    position: relative;
    height: 380px;
    background-size: cover;
    background-position: center;
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-top: 1.5rem;
    display: flex;
    align-items: flex-end;
    padding: 2rem;
  }
  .backdrop-content {
    z-index: 10;
    max-width: 800px;
  }
  .movie-meta-year {
    background: rgba(201, 168, 76, 0.15);
    border: 1px solid var(--gold);
    color: var(--gold);
    font-size: 0.75rem;
    padding: 2px 10px;
    border-radius: 99px;
    font-weight: 500;
  }
  .movie-title {
    font-size: 2.2rem;
    font-weight: 600;
    color: var(--cream);
    margin: 8px 0;
    text-shadow: 0 4px 12px rgba(0,0,0,0.8);
  }
  .genres-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .genre-badge {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    color: var(--muted);
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  /* ── Grid Detail ── */
  .details-grid {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 2rem;
    margin-top: 2rem;
  }
  .poster-wrap-detail {
    width: 100%;
    aspect-ratio: 2/3;
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--noir-border);
    box-shadow: 0 16px 32px rgba(0,0,0,0.6);
  }
  .poster-img-detail {
    width: 100%; height: 100%;
    object-fit: cover;
  }
  .btn-favorite {
    width: 100%;
    margin-top: 1rem;
    padding: 12px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--noir-border);
    background: var(--noir-card);
    color: var(--cream);
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s ease;
  }
  .btn-favorite:hover:not(:disabled) {
    border-color: #e05252;
    background: rgba(224, 82, 82, 0.06);
    color: #ff8080;
  }
  .btn-favorite.favorited {
    background: rgba(224, 82, 82, 0.15);
    border-color: #e05252;
    color: #ff8080;
  }

  /* ── Right Column Details ── */
  .rating-header-box {
    display: flex;
    background: var(--noir-card);
    border: 1px solid var(--noir-border);
    border-radius: var(--radius-md);
    padding: 1.25rem;
    margin-bottom: 1.5rem;
  }
  .rating-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    justify-content: center;
  }
  .rating-item.border-left {
    border-left: 1px solid var(--noir-border);
    padding-left: 1.5rem;
  }
  .rating-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .rating-val-wrap { display: flex; align-items: center; gap: 6px; }
  .gold-star-large { color: var(--gold); font-size: 1.5rem; line-height: 1; }
  .rating-num { font-size: 1.8rem; font-weight: 600; color: var(--cream); }
  .rating-scale { color: var(--muted); font-size: 0.9rem; align-self: flex-end; margin-bottom: 4px; }
  .rating-count { font-size: 1rem; font-weight: 500; color: var(--cream); margin-top: 4px; }

  .info-section { margin-bottom: 1.5rem; }
  .info-title { font-size: 0.9rem; color: var(--gold); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; font-weight: 500; }
  .synopsis-text { font-size: 0.9rem; color: var(--muted); line-height: 1.6; }

  .credits-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    background: var(--noir-surface);
    border: 1px solid var(--noir-border);
    border-radius: var(--radius-md);
    padding: 1.25rem;
    margin-bottom: 1.5rem;
  }
  .credit-item { display: flex; flex-direction: column; gap: 4px; }
  .credit-label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .credit-value, .cast-names { font-size: 0.85rem; color: var(--cream); }

  /* ── XAI Panel ── */
  .xai-panel {
    background: radial-gradient(circle at top right, rgba(201, 168, 76, 0.06), transparent);
    border: 1px solid rgba(201, 168, 76, 0.15);
    border-radius: var(--radius-md);
    padding: 1.25rem;
  }
  .xai-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .xai-spark { font-size: 1rem; }
  .xai-header h4 { font-size: 0.85rem; font-weight: 500; color: var(--gold); }
  .xai-reason { font-size: 0.85rem; color: var(--cream); line-height: 1.5; }
  .xai-footer { font-size: 0.7rem; color: var(--muted); margin-top: 10px; border-top: 1px solid rgba(201, 168, 76, 0.1); padding-top: 8px; }

  /* ── Interaction Card ── */
  .interaction-card {
    background: var(--noir-card);
    border: 1px solid var(--noir-border);
    border-radius: var(--radius-lg);
    padding: 2rem;
  }
  .form-label { display: block; font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px; }
  
  .rating-form-group {
    margin-bottom: 1.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--noir-border);
  }
  .stars-interactive { display: flex; gap: 8px; }
  .star-btn {
    background: none; border: none; color: var(--subtle); font-size: 2.2rem; cursor: pointer; padding: 0;
    transition: color 0.15s ease, transform 0.1s ease;
  }
  .star-btn:hover { transform: scale(1.15); }
  .star-btn.hovered, .star-btn.filled { color: var(--gold); }
  .rating-applied-label { font-size: 0.75rem; color: var(--gold); display: block; margin-top: 8px; font-weight: 500; }

  .review-form textarea {
    width: 100%;
    background: var(--noir-surface);
    border: 1px solid var(--noir-border);
    border-radius: var(--radius-sm);
    color: var(--cream);
    padding: 12px;
    font-size: 0.9rem;
    outline: none;
    resize: none;
    margin-bottom: 1rem;
    font-family: var(--font-body);
  }
  .review-form textarea:focus { border-color: var(--gold); }
  .btn-submit-review {
    background: var(--gold);
    color: var(--noir-bg);
    border: none;
    padding: 10px 24px;
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    float: right;
  }
  .btn-submit-review:disabled { opacity: 0.45; cursor: not-allowed; }

  /* ── Similar Scroller ── */
  .similar-scroller {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 1rem;
  }
  .similar-card-wrap {
    width: 155px;
    flex-shrink: 0;
  }

  /* ── Reviews Section ── */
  .reviews-list { display: flex; flex-direction: column; gap: 1rem; }
  .review-card-detail {
    background: var(--noir-card);
    border: 1px solid var(--noir-border);
    border-radius: var(--radius-md);
    padding: 1.25rem;
  }
  .review-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .user-info { display: flex; align-items: center; gap: 8px; }
  .user-avatar { font-size: 1rem; }
  .user-name { font-size: 0.85rem; font-weight: 500; color: var(--cream); }
  .user-rating-badge { display: flex; gap: 2px; }
  .star-mini { color: var(--subtle); font-size: 0.75rem; }
  .star-mini.active { color: var(--gold); }
  .review-body { font-size: 0.9rem; color: var(--muted); line-height: 1.5; font-style: italic; }
  .review-time { font-size: 0.7rem; color: var(--subtle); display: block; margin-top: 8px; }

  /* ── Common Styles ── */
  .section { margin-top: 3.5rem; }
  .site-footer {
    border-top: 1px solid var(--noir-border);
    padding: 1.5rem;
    text-align: center;
    font-size: 0.7rem;
    color: var(--subtle);
    background: transparent;
  }
  .btn-ghost {
    padding: 6px 14px; border-radius: var(--radius-sm);
    border: 1px solid var(--noir-border); background: transparent; color: var(--muted); font-size: .8rem; cursor: pointer;
  }
  .btn-ghost:hover { border-color: var(--subtle); color: var(--cream); }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .details-grid { grid-template-columns: 1fr; }
    .left-col { display: flex; gap: 1rem; align-items: flex-start; }
    .poster-wrap-detail { width: 140px; }
    .movie-title { font-size: 1.8rem; }
    .movie-backdrop { height: 280px; padding: 1rem; }
  }
</style>
