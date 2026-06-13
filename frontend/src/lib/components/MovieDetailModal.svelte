<script>
  import { request } from '$lib/api.js'; // 1. Ubah apiRequest menjadi request asli tim
  import { userStore } from '$lib/stores/user.js';

  // Props menggunakan Svelte 5 Runes
  let { movieId, isOpen, onClose, onInteractionComplete } = $props();

  let movie = $state(null);
  let loading = $state(false);
  let error = $state('');

  // State untuk form interaksi
  let isFavorite = $state(false);
  let rating = $state(0);
  let reviewText = $state('');
  let submittingInteraction = $state(false);

  // Ambil detail film setiap kali movieId berubah dan modal terbuka
  $effect(() => {
    if (isOpen && movieId) {
      fetchMovieDetail();
      fetchUserInteractions();
    }
  });

  async function fetchMovieDetail() {
    loading = true;
    error = '';
    try {
      // 2. Sesuaikan ke request() dengan prefix /api/v1 (Butuh token/tidak tergantung kebijakan backend, amannya pasang jika user login)
      const user = $userStore;
      const data = await request(`/api/v1/movie/${movieId}?include_credits=true`, { 
        token: user?.token 
      });
      movie = data.movie;
    } catch (e) {
      error = 'Gagal memuat detail film.';
    } finally {
      loading = false;
    }
  }

  async function fetchUserInteractions() {
    try {
      const user = $userStore;
      // 3. Sesuaikan ke request() dengan prefix /api/v1 dan teruskan token
      const data = await request(`/api/v1/users/${user.id}/interactions`, { 
        token: user.token 
      });
      const interactions = Array.isArray(data) ? data : (data.results ?? []);
      
      const fav = interactions.find(i => i.movie_id === movieId && i.type === 'favorite'); 
      const rat = interactions.find(i => i.movie_id === movieId && i.type === 'rating'); 
      const rev = interactions.find(i => i.movie_id === movieId && i.type === 'review'); 

      isFavorite = !!fav;
      rating = rat ? rat.rating : 0;
      reviewText = rev ? rev.review : '';
    } catch {
      // Gagal senyap jika data interaksi belum ada
    }
  }

  async function handleFavorite() {
    submittingInteraction = true; 
    try {
      const user = $userStore; 
      // 4. Sesuaikan ke request() dengan signature POST, body, dan token kelompokmu
      await request('/api/v1/interactions', {
        method: 'POST',
        body: {
          user_id: parseInt(user.id),
          movie_id: movieId,
          type: 'favorite'
        },
        token: user.token
      });
      isFavorite = !isFavorite; 
      if (onInteractionComplete) onInteractionComplete();
    } catch (e) {
      alert('Gagal memperbarui favorit');
    } finally {
      submittingInteraction = false; 
    }
  }

  async function handleRating(score) {
    submittingInteraction = true; 
    try {
      const user = $userStore; 
      // 5. Sesuaikan ke request() untuk pencatatan rating bintang
      await request('/api/v1/interactions', {
        method: 'POST',
        body: {
          user_id: parseInt(user.id),
          movie_id: movieId,
          type: 'rating',
          rating: score
        },
        token: user.token
      });
      rating = score; 
      if (onInteractionComplete) onInteractionComplete();
    } catch (e) {
      alert('Gagal mengirim rating');
    } finally {
      submittingInteraction = false; 
    }
  }

  async function handleReviewSubmit(e) {
    e.preventDefault();
    if (!reviewText.trim()) return;
    
    submittingInteraction = true;
    try {
      const user = $userStore; 
      // 6. Sesuaikan ke request() untuk submisi ulasan teks tertulis
      await request('/api/v1/interactions', {
        method: 'POST',
        body: {
          user_id: parseInt(user.id),
          movie_id: movieId,
          type: 'review',
          rating: rating || 5,
          review: reviewText.trim()
        },
        token: user.token
      });
      alert('Review berhasil disimpan!'); 
      if (onInteractionComplete) onInteractionComplete();
    } catch (e) {
      alert('Gagal mengirim review');
    } finally {
      submittingInteraction = false; 
    }
  }
</script>

{#if isOpen}
  <div class="modal-backdrop" onclick={onClose} aria-hidden="true">
    <div class="modal-card" onclick={(e) => e.stopPropagation()} aria-hidden="true">
      
      <button class="close-btn" onclick={onClose}>✕</button>

      {#if loading}
        <div class="modal-loading">Memuat detail film...</div>
      {:else if error}
        <div class="modal-error">⚠️ {error}</div>
      {:else if movie}
        <div class="modal-grid">
          
          <div class="poster-side">
            <img class="modal-poster" src={movie.poster_url || 'https://via.placeholder.com/300x450'} alt={movie.title} />
            
            <div class="action-buttons">
              <button class="btn-fav" class:active={isFavorite} onclick={handleFavorite} disabled={submittingInteraction}>
                {isFavorite ? '❤️ Difavoritkan' : '🤍 Tambah Favorit'}
              </button>

              <div class="rating-box">
                <span class="label">Beri Rating:</span>
                <div class="stars">
                  {#each [1, 2, 3, 4, 5] as star}
                    <button class="star" class:filled={rating >= star} onclick={() => handleRating(star)} disabled={submittingInteraction}>
                      ★
                    </button>
                  {/each}
                </div>
              </div>
            </div>
          </div>

          <div class="info-side">
            <h1 class="movie-title">{movie.title} <span class="year">({movie.year})</span></h1>
            
            <div class="metadata">
              <span class="avg-rating">⭐ {movie.avg_rating?.toFixed(1) || '0.0'} ({movie.rating_count} ulasan)</span>
              <div class="genres">
                {#each movie.genres || [] as g}
                  <span class="genre-tag">{g}</span>
                {/each}
              </div>
            </div>

            <div class="synopsis-box">
              <h3>Sinopsis</h3>
              <p>{movie.synopsis || 'Sinopsis tidak tersedia untuk film ini.'}</p>
            </div>

            {#if movie.directors?.length}
              <div class="credits-box">
                <h3>Sutradara</h3>
                <p class="director-name">{movie.directors.join(', ')}</p>
              </div>
            {/if}

            {#if movie.cast?.length}
              <div class="credits-box">
                <h3>Pemeran Utama</h3>
                <div class="cast-scroll">
                  {#each movie.cast as actor}
                    <div class="actor-card">
                      <img src={actor.profile_url || 'https://via.placeholder.com/100'} alt={actor.name} />
                      <span>{actor.name}</span>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <div class="review-section">
              <h3>Tulis Ulasan Teks</h3>
              <form onsubmit={handleReviewSubmit}>
                <textarea bind:value={reviewText} placeholder="Bagikan pendapatmu tentang film ini..." rows="3" disabled={submittingInteraction}></textarea>
                <button type="submit" class="btn-submit-review" disabled={submittingInteraction || !reviewText.trim()}>
                  {submittingInteraction ? 'Mengirim...' : 'Kirim Ulasan'}
                </button>
              </form>
            </div>

          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed; inset: 0; background: rgba(0, 0, 0, 0.85);
    display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1rem;
    backdrop-filter: blur(8px);
  }
  .modal-card {
    background: var(--noir-card, #121218); border: 1px solid var(--noir-border, #222230);
    width: 100%; max-width: 850px; max-height: 90vh; overflow-y: auto;
    border-radius: var(--radius-lg, 12px); position: relative; padding: 2rem;
    box-shadow: 0 20px 50px rgba(0,0,0,0.6); color: var(--cream, #f3f3f6);
  }
  .close-btn {
    position: absolute; right: 1.5rem; top: 1.5rem; background: none; border: none;
    color: var(--muted, #88889c); font-size: 1.25rem; cursor: pointer; transition: color 0.2s;
  }
  .close-btn:hover { color: #ffffff; }
  
  .modal-grid { display: grid; grid-template-columns: 280px 1fr; gap: 2rem; }
  
  .modal-poster { width: 100%; border-radius: var(--radius-md, 8px); border: 1px solid var(--noir-border, #222230); }
  .action-buttons { margin-top: 1.25rem; display: flex; flex-direction: column; gap: 1rem; }
  
  .btn-fav {
    width: 100%; padding: 10px; background: transparent; border: 1px solid var(--noir-border, #222230);
    color: var(--cream, #f3f3f6); border-radius: var(--radius-sm, 4px); cursor: pointer; font-size: 0.85rem;
  }
  .btn-fav.active { background: rgba(224, 82, 82, 0.15); border-color: #e05252; color: #ff8080; }
  
  .rating-box { background: var(--noir-surface, #181824); padding: 10px; border-radius: var(--radius-sm, 4px); }
  .rating-box .label { font-size: 0.75rem; color: var(--muted, #88889c); display: block; margin-bottom: 4px; }
  .stars { display: flex; gap: 4px; }
  .star { background: none; border: none; color: #333344; font-size: 1.5rem; cursor: pointer; padding: 0; }
  .star.filled { color: var(--gold, #c9a84c); }
  
  .movie-title { font-size: 1.75rem; font-weight: 500; margin-bottom: 0.5rem; }
  .movie-title .year { color: var(--muted, #88889c); font-weight: 400; }
  
  .metadata { display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1.5rem; font-size: 0.85rem; }
  .avg-rating { color: var(--gold, #c9a84c); font-weight: 500; }
  .genres { display: flex; gap: 6px; }
  .genre-tag { background: var(--noir-soft, #222232); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; color: var(--muted, #88889c); }
  
  .synopsis-box h3, .credits-box h3, .review-section h3 { font-size: 0.95rem; color: var(--gold, #c9a84c); margin-bottom: 6px; font-weight: 500; }
  .synopsis-box p { font-size: 0.9rem; color: var(--muted, #88889c); line-height: 1.6; }
  
  .credits-box { margin-top: 1.5rem; }
  .director-name { font-size: 0.9rem; color: var(--cream, #f3f3f6); }
  
  .cast-scroll { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px; margin-top: 8px; }
  .actor-card { display: flex; flex-direction: column; align-items: center; text-align: center; width: 70px; flex-shrink: 0; }
  .actor-card img { width: 60px; height: 60px; border-radius: 50%; object-fit: cover; background: #222; border: 1px solid var(--noir-border, #222230); }
  .actor-card span { font-size: 0.7rem; color: var(--muted, #88889c); margin-top: 4px; line-height: 1.2; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  
  .review-section { margin-top: 1.5rem; border-top: 1px solid var(--noir-border, #222230); padding-top: 1.25rem; }
  .review-section textarea { width: 100%; background: var(--noir-surface, #181824); border: 1px solid var(--noir-border, #222230); border-radius: var(--radius-sm, 4px); color: white; padding: 10px; font-size: 0.85rem; outline: none; resize: none; margin-top: 6px; }
  .review-section textarea:focus { border-color: var(--gold, #c9a84c); }
  .btn-submit-review { margin-top: 8px; background: var(--gold, #c9a84c); border: none; color: #09090e; padding: 8px 16px; font-size: 0.8rem; font-weight: 500; border-radius: var(--radius-sm, 4px); cursor: pointer; float: right; }
  .btn-submit-review:disabled { opacity: 0.4; cursor: not-allowed; }
  
  .modal-loading, .modal-error { text-align: center; padding: 3rem 0; color: var(--muted, #88889c); }

  @media (max-width: 640px) {
    .modal-grid { grid-template-columns: 1fr; gap: 1.5rem; }
    .modal-card { padding: 1.25rem; }
  }
</style>