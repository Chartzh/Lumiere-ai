<<<<<<< HEAD
<script>
  import MovieCard       from '$lib/components/MovieCard.svelte';
  import GenreFilter     from '$lib/components/GenreFilter.svelte';
  import LoadingSkeleton from '$lib/components/LoadingSkeleton.svelte';

  // ── CONFIG ─────────────────────────────────────────────────────────
  const API_BASE = 'https://lumiere-api-32400975992.asia-southeast2.run.app';
  const TMDB_KEY = import.meta.env.VITE_TMDB_API_KEY ?? '';
  const TMDB_IMG = 'https://image.tmdb.org/t/p/w500';

  // ── STATE ───────────────────────────────────────────────────────────
  let userId      = $state('');
  let inputValue  = $state('');
  let enriched    = $state([]);   // hasil API + data TMDB (poster, genre)
  let loading     = $state(false);
  let error       = $state('');
  let activeGenre = $state('All');
  let hasSearched = $state(false);
  let totalResults = $state(0);

  // ── COMPUTED ────────────────────────────────────────────────────────
  const allGenres = $derived(
    [...new Set(enriched.flatMap(m => m.genres ?? []))].sort()
  );

  const displayed = $derived(
    activeGenre === 'All'
      ? enriched
      : enriched.filter(m => m.genres?.includes(activeGenre))
  );

  // ── FETCH TMDB METADATA ─────────────────────────────────────────────
  async function fetchTMDB(movieId) {
    if (!TMDB_KEY) return { poster_url: null, genres: [] };
    try {
      const res = await fetch(
        `https://api.themoviedb.org/3/movie/${movieId}?api_key=${TMDB_KEY}&language=en-US`,
        { signal: AbortSignal.timeout(5000) }
      );
      if (!res.ok) return { poster_url: null, genres: [] };
      const d = await res.json();
      return {
        poster_url: d.poster_path ? `${TMDB_IMG}${d.poster_path}` : null,
        genres:     d.genres?.map(g => g.name) ?? []
      };
    } catch {
      return { poster_url: null, genres: [] };
    }
  }

  // ── FETCH REKOMENDASI ───────────────────────────────────────────────
  async function fetchRecommendations() {
    const uid = String(inputValue).trim();
    if (!uid) { error = 'Masukkan User ID terlebih dahulu.'; return; }

    const uidNum = Number(uid);
    if (!Number.isInteger(uidNum) || uidNum < 1 || uidNum > 6040) {
      error = 'User ID harus berupa angka antara 1 sampai 6040.';
      return;
    }

    loading      = true;
    error        = '';
    enriched     = [];
    hasSearched  = true;
    activeGenre  = 'All';
    userId       = uid;
    totalResults = 0;

    try {
      const res = await fetch(`${API_BASE}/api/v1/recommend/${uid}?top_k=20`);

      if (res.status === 404) {
        error = `User ID "${uid}" tidak ditemukan. Coba angka lain (1–6040).`;
        loading = false;
        return;
      }
      if (!res.ok) {
        error = `Server error ${res.status}: ${res.statusText}`;
        loading = false;
        return;
      }

      const data = await res.json();
      const movies = data.results ?? [];
      totalResults = data.total_results ?? movies.length;

      if (movies.length === 0) {
        error = 'Tidak ada rekomendasi untuk user ini.';
        loading = false;
        return;
      }

      const enrichedResults = await Promise.all(
        movies.map(async (m) => {
          const tmdb = await fetchTMDB(m.movie_id);
          return { ...m, ...tmdb };
        })
      );

      enriched = enrichedResults;

    } catch (e) {
      if (e.name === 'TypeError' && e.message.includes('fetch')) {
        error = 'Tidak bisa terhubung ke server. Pastikan koneksi internet aktif.';
      } else {
        error = `Error: ${e.message}`;
      }
    } finally {
      loading = false;
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter') fetchRecommendations();
  }

  function selectGenre(genre) { activeGenre = genre; }

  function reset() {
    inputValue = ''; userId = '';
    enriched = []; error = '';
    hasSearched = false; activeGenre = 'All'; totalResults = 0;
  }
</script>

<svelte:head>
  <title>Lumiere — Intelligent Movie Discovery</title>
</svelte:head>

<div class="page">

  <header class="site-header">
    <div class="header-inner">
      <div class="logo-wrap">
        <span class="logo-icon">✦</span>
        <span class="logo-text">Lumiere</span>
      </div>
      <p class="tagline">Intelligent Movie Discovery · Neural Collaborative Filtering</p>
    </div>
  </header>

  <section class="hero">
    <div class="hero-bg-text" aria-hidden="true">LUMIERE</div>

    <div class="hero-content">
      <h1 class="hero-title">
        Discover films<br/>
        <em>made for you</em>
      </h1>
      <p class="hero-sub">
        Enter your User ID and our Neural Collaborative Filtering model
        will surface the films that match your hidden taste profile.
      </p>

      <div class="search-wrap">
        <div class="search-box" class:has-error={!!error}>
          <label class="search-label" for="uid-input">User ID</label>
          <input
            id="uid-input"
            class="search-input"
            type="number"
            min="1" max="6040"
            placeholder="e.g. 1, 42, 999 …"
            bind:value={inputValue}
            onkeydown={handleKey}
            disabled={loading}
            autocomplete="off"
          />
          <button
            class="search-btn"
            onclick={fetchRecommendations}
            disabled={loading || !inputValue.toString().trim()}
          >
            {#if loading}
              <span class="spinner"></span>
            {:else}
              <span>Discover</span>
              <span class="btn-arrow">→</span>
            {/if}
          </button>
        </div>

        {#if error}
          <p class="error-msg" role="alert">⚠ {error}</p>
        {/if}

        <p class="search-hint">
          Valid User IDs: <strong>1 – 6040</strong> · MovieLens 1M dataset
        </p>
      </div>
    </div>
  </section>

  {#if loading}
    <section class="results-section">
      <div class="results-header">
        <div class="skel-line shimmer-bg" style="width:240px;height:26px;border-radius:6px"></div>
      </div>
      <LoadingSkeleton count={10} />
    </section>

  {:else if hasSearched && enriched.length > 0}
    <section class="results-section fade-up">

      <div class="results-header">
        <div>
          <h2 class="results-title">
            Picks for User <span class="user-chip">#{userId}</span>
          </h2>
          <p class="results-meta">
            Showing {displayed.length} of {totalResults} recommendations
            {#if activeGenre !== 'All'}· filtered by <strong>{activeGenre}</strong>{/if}
          </p>
        </div>
        <button class="reset-btn" onclick={reset}>← New Search</button>
      </div>

      {#if allGenres.length > 0}
        <div class="filter-wrap">
          <GenreFilter genres={allGenres} {activeGenre} onSelect={selectGenre} />
        </div>
      {/if}

      <div class="movie-grid">
        {#each displayed as movie, i (movie.movie_id)}
          <div style="animation-delay:{i * 0.04}s" class="fade-up">
            <MovieCard
              movie_id={movie.movie_id}
              title={movie.title}
              confidence={movie.confidence_score} poster_url={movie.poster_url ?? null}
              genre={movie.genres?.[0] ?? null}
            />
          </div>
        {/each}
      </div>

    </section>

  {:else}
    {#if displayed.length === 0 && hasSearched}
      <div class="empty-state">
        <span class="empty-icon">🔍</span>
        <p>No films match the <strong>{activeGenre}</strong> genre filter.</p>
        <button class="ghost-btn" onclick={() => activeGenre = 'All'}>
          Show all genres
        </button>
      </div>
    {/if}
  {/if}

  {#if hasSearched && !loading && !error && enriched.length === 0}
    <div class="empty-state fade-up" style="flex:1">
      <span class="empty-icon">🎬</span>
      <p>No recommendations found for User #{userId}.</p>
      <button class="ghost-btn" onclick={reset}>Try another User ID</button>
    </div>
  {/if}

  <footer class="site-footer">
    <p>Lumiere &copy; 2026 · PJK-GM074 · Pijak × IBM SkillsBuild</p>
    <p class="footer-team">Lita · Rajif · Arghi · Zaky</p>
  </footer>

</div>

<style>
/* ── INJEKSI TEMA GELAP GLOBAL & VARIABEL WARNA ──────────────── */
:global(body) {
  background-color: #09090e !important; /* Hitam pekat sinematik */
  color: #f5f5f7 !important;            /* Teks default putih krem lembut */
  margin: 0;
  font-family: var(--font-body, 'Inter', sans-serif);
  -webkit-font-smoothing: antialiased;
}

:root {
  /* Palet Utama Noir-Gold */
  --noir-bg: #09090e;
  --noir-card: #13131a;       /* Abu-abu gelap pekat untuk background komponen */
  --noir-soft: #1c1c24;       /* Sedikit lebih terang untuk placeholder/skeleton */
  --noir-border: #252532;     /* Garis batas tipis yang elegan */
  
  --gold: #c9a84c;            /* Emas aksen utama */
  --gold-soft: #dfc26b;       /* Emas terang saat hover */
  --gold-dim: #a58734;        /* Emas redup untuk border kontras */
  
  --cream: #eef0f5;           /* Putih cerah kontras tinggi untuk judul */
  --muted: #8e8e9f;           /* Abu-abu pudar untuk sub-teks/genre */
  --error: #e05252;           /* Merah tegas pesan error */
}

/* ── PAGE LAYOUT ─────────────────────────────────────────── */
.page {
  min-height: 100vh;
  display: flex; 
  flex-direction: column;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  background-color: var(--noir-bg);
}

/* ── SITE HEADER ─────────────────────────────────────────── */
.site-header {
  padding: 28px 0 20px;
  border-bottom: 1px solid var(--noir-border);
}
.header-inner {
  display: flex; 
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap; 
  gap: 16px;
}
.logo-wrap { display: flex; align-items: center; gap: 10px; }
.logo-icon {
  color: var(--gold);
  font-size: 1.4rem;
  text-shadow: 0 0 12px rgba(201,168,76,0.4);
}
.logo-text {
  font-size: 1.6rem; 
  font-weight: 800;
  color: var(--cream); 
  letter-spacing: -0.01em;
}
.tagline {
  font-size: 0.7rem; 
  color: var(--muted);
  letter-spacing: 0.06em; 
  text-transform: uppercase;
}

/* ── HERO SECTION ────────────────────────────────────────── */
.hero {
  position: relative;
  padding: 80px 0 64px;
  text-align: center;
}
.hero-bg-text {
  position: absolute; 
  top: 45%; 
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: clamp(100px, 20vw, 220px);
  font-weight: 900;
  color: rgba(201,168,76,0.025);
  white-space: nowrap;
  pointer-events: none; 
  user-select: none;
  letter-spacing: 0.05em;
}
.hero-content {
  position: relative;
  display: flex; 
  flex-direction: column; 
  align-items: center; 
  gap: 16px;
  z-index: 2;
}
.hero-title {
  font-size: clamp(2.4rem, 5vw, 4rem);
  font-weight: 700; 
  line-height: 1.15; 
  color: var(--cream);
  letter-spacing: -0.02em;
}
.hero-title em { 
  font-style: italic; 
  color: var(--gold); 
  font-weight: 600;
}
.hero-sub {
  font-size: 1rem; 
  color: var(--muted);
  max-width: 520px; 
  line-height: 1.6;
}

/* ── SEARCH CONTAINER ────────────────────────────────────── */
.search-wrap {
  width: 100%; 
  max-width: 480px;
  margin-top: 12px;
  display: flex; 
  flex-direction: column; 
  gap: 12px;
}
.search-box {
  display: flex; 
  align-items: center;
  background: var(--noir-card);
  border: 1px solid var(--noir-border);
  border-radius: 14px; 
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  transition: all 0.25s ease;
}
.search-box:focus-within {
  border-color: var(--gold);
  box-shadow: 0 0 0 3px rgba(201,168,76,0.15), 0 12px 40px rgba(0,0,0,0.6);
}
.search-box.has-error { 
  border-color: var(--error); 
  box-shadow: 0 0 0 3px rgba(224,82,82,0.1);
}
.search-label {
  padding-left: 18px;
  font-size: 0.75rem; 
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase; 
  color: var(--gold); 
  white-space: nowrap;
}
.search-input {
  flex: 1; 
  padding: 16px 12px;
  background: transparent; 
  border: none; 
  outline: none;
  color: var(--cream); 
  font-size: 1rem;
}
.search-input::placeholder { color: rgba(142,142,159,0.5); }
.search-input:disabled { opacity: 0.4; }

.search-btn {
  display: flex; 
  align-items: center; 
  gap: 8px;
  padding: 16px 24px;
  background: var(--gold); 
  color: #09090e; 
  border: none;
  font-size: 0.9rem; 
  font-weight: 600;
  cursor: pointer; 
  transition: all 0.2s ease;
}
.search-btn:hover:not(:disabled) { 
  background: var(--gold-soft);
  transform: translateX(2px);
}
.search-btn:disabled { 
  background: var(--noir-soft); 
  color: var(--muted); 
  cursor: not-allowed; 
}

.spinner {
  display: inline-block; 
  width: 16px; 
  height: 16px;
  border: 2.5px solid var(--muted); 
  border-top-color: var(--gold);
  border-radius: 50%; 
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  100% { transform: rotate(360deg); }
}

.error-msg {
  font-size: 0.85rem; 
  color: #ff8080;
  padding: 10px 16px; 
  text-align: left;
  background: rgba(224,82,82,0.12);
  border: 1px solid rgba(224,82,82,0.25); 
  border-radius: 10px;
}
.search-hint { font-size: 0.75rem; color: var(--muted); }
.search-hint strong { color: var(--gold-soft); }

/* ── RESULTS LAYOUT ──────────────────────────────────────── */
.results-section { flex: 1; padding: 24px 0 64px; }
.results-header {
  display: flex; 
  align-items: center; 
  justify-content: space-between;
  flex-wrap: wrap; 
  gap: 16px; 
  margin-bottom: 28px;
}
.results-title {
  font-size: 1.6rem; 
  font-weight: 600; 
  color: var(--cream);
}
.user-chip {
  display: inline-block; 
  padding: 2px 12px;
  background: rgba(201,168,76,0.12);
  border: 1px solid var(--gold-dim); 
  border-radius: 999px;
  font-size: 0.95rem; 
  color: var(--gold); 
  font-weight: 700;
}
.results-meta { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
.results-meta strong { color: var(--gold-soft); }

.reset-btn {
  padding: 8px 16px; 
  background: var(--noir-card);
  border: 1px solid var(--noir-border); 
  border-radius: 8px;
  color: var(--cream); 
  font-size: 0.8rem; 
  font-weight: 500;
  cursor: pointer; 
  transition: all 0.2s;
}
.reset-btn:hover { 
  border-color: var(--gold); 
  color: var(--gold);
  background: rgba(201,168,76,0.05);
}

.filter-wrap { 
  margin-bottom: 28px; 
  border-bottom: 1px solid var(--noir-border);
  padding-bottom: 12px;
}

/* ── MOVIE SELECTION GRID ────────────────────────────────── */
.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 24px;
}

/* ── EMPTY STATE LAYOUT ──────────────────────────────────── */
.empty-state {
  display: flex; 
  flex-direction: column;
  align-items: center; 
  justify-content: center;
  gap: 16px; 
  padding: 80px 20px; 
  text-align: center;
}
.empty-icon { font-size: 3.5rem; }
.empty-state p { font-size: 0.95rem; color: var(--muted); }
.empty-state strong { color: var(--cream); }

.ghost-btn {
  padding: 10px 22px; 
  border-radius: 999px;
  border: 1px solid var(--gold-dim); 
  background: transparent;
  color: var(--gold); 
  font-size: 0.85rem; 
  font-weight: 600;
  cursor: pointer; 
  transition: all 0.2s;
}
.ghost-btn:hover { 
  background: rgba(201,168,76,0.1); 
  border-color: var(--gold);
}

/* ── SITE FOOTER ─────────────────────────────────────────── */
.site-footer {
  margin-top: auto;
  border-top: 1px solid var(--noir-border);
  padding: 24px 0; 
  text-align: center;
  color: var(--muted); 
  font-size: 0.75rem;
  line-height: 1.8;
}
.footer-team { 
  color: var(--gold-dim); 
  font-weight: 500; 
  letter-spacing: 0.05em;
}

/* ── RESPONSIVE RESPONSIVITAS ────────────────────────────── */
@media (max-width: 640px) {
  .hero { padding: 48px 0 40px; }
  .header-inner { flex-direction: column; align-items: center; gap: 8px; text-align: center; }
  .search-box { flex-direction: column; align-items: stretch; }
  .search-label { padding: 14px 18px 0; }
  .search-input { padding: 12px 18px; }
  .search-btn { width: 100%; justify-content: center; padding: 14px; border-radius: 0 0 12px 12px; }
  .movie-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 16px; }
  .results-header { flex-direction: column; align-items: flex-start; }
}
</style>
=======
<h1>Welcome to SvelteKit</h1>
<p>Visit <a href="https://svelte.dev/docs/kit">svelte.dev/docs/kit</a> to read the documentation</p>
>>>>>>> 0d15c6f9ad05a9a3286e42cf539958efa22b677b
