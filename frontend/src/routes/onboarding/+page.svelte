<script>
  /**
   * routes/onboarding/+page.svelte
   * Halaman onboarding genre — muncul sekali untuk user baru.
   * User pilih minimal 3 genre, lalu disimpan ke backend dan profil lokal.
   * Setelah selesai → isNewUser = false → redirect ke halaman utama.
   */
  import { goto }      from '$app/navigation';
  import { userStore } from '$lib/stores/user.js';
  import { request }   from '$lib/api.js';

  // Semua genre dari MovieLens + TMDB yang ada di dataset
  const ALL_GENRES = [
    'Action', 'Adventure', 'Animation', 'Children\'s', 'Comedy',
    'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir',
    'Horror', 'Musical', 'Mystery', 'Romance', 'Sci-Fi',
    'Thriller', 'War', 'Western'
  ];

  // Emoji representatif tiap genre
  const GENRE_EMOJI = {
    'Action': '💥', 'Adventure': '🧭', 'Animation': '🎨',
    "Children's": '🧸', 'Comedy': '😄', 'Crime': '🔫',
    'Documentary': '📽️', 'Drama': '🎭', 'Fantasy': '🧙',
    'Film-Noir': '🕵️', 'Horror': '👻', 'Musical': '🎵',
    'Mystery': '🔍', 'Romance': '❤️', 'Sci-Fi': '🚀',
    'Thriller': '😰', 'War': '⚔️', 'Western': '🤠'
  };

  let selected  = $state(new Set());
  let loading   = $state(false);
  let error     = $state('');

  const MIN = 3;
  const canContinue = $derived(selected.size >= MIN);
  const progress    = $derived(Math.min(1, selected.size / MIN));

  function toggle(genre) {
    const next = new Set(selected);
    next.has(genre) ? next.delete(genre) : next.add(genre);
    selected = next;
  }

  async function handleContinue() {
    if (!canContinue) return;
    error = '';
    loading = true;

    const genres = [...selected];

    try {
      // Kirim ke backend supaya NCF bisa pakai saat cold-start
      // Endpoint ini akan dibuat oleh Arghi
      const user = $userStore;
      await fetch(`https://lumiere-api-32400975992.asia-southeast2.run.app/api/v1/auth/onboarding`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({ favorite_genres: genres })
      });
    } catch {
      // Tidak blokir user jika backend belum siap
    }

    // Simpan ke store lokal & tandai onboarding selesai
    userStore.patch({ favoriteGenres: genres, isNewUser: false });
    goto('/');
  }
</script>

<div class="ob-page">
  <div class="glow" aria-hidden="true"></div>

  <div class="ob-header">
    <div class="brand">
      <span class="brand-star">✦</span>
      <span class="brand-name">Lumiere</span>
    </div>

    <div class="step-wrap">
      <div class="step-bar">
        <div class="step-fill" style="width: {progress * 100}%"></div>
      </div>
      <span class="step-label">
        {selected.size} / {MIN} dipilih
        {#if selected.size >= MIN} ✓{/if}
      </span>
    </div>
  </div>

  <div class="ob-content">
    <h1 class="ob-title">Genre apa yang kamu suka?</h1>
    <p class="ob-sub">
      Pilih minimal <strong>{MIN} genre</strong>. Model kami akan mempelajari
      selera filmmu dan memberi rekomendasi yang makin personal seiring waktu.
    </p>

    <div class="genre-grid">
      {#each ALL_GENRES as genre}
        {@const active = selected.has(genre)}
        <button
          class="genre-pill"
          class:active
          onclick={() => toggle(genre)}
          aria-pressed={active}
        >
          <span class="genre-emoji">{GENRE_EMOJI[genre] ?? '🎬'}</span>
          <span class="genre-name">{genre}</span>
          {#if active}
            <span class="genre-check" aria-hidden="true">✓</span>
          {/if}
        </button>
      {/each}
    </div>

    {#if error}
      <div class="error-box" role="alert">⚠ {error}</div>
    {/if}

    <div class="ob-footer">
      {#if !canContinue}
        <p class="hint">Pilih {MIN - selected.size} genre lagi untuk melanjutkan</p>
      {:else}
        <p class="hint ready">Siap! Klik lanjut untuk lihat rekomendasimu</p>
      {/if}

      <button class="btn-gold" onclick={handleContinue} disabled={!canContinue || loading}>
        {#if loading}
          <span class="spin"></span> Menyimpan...
        {:else}
          Lanjut ke Lumiere →
        {/if}
      </button>
    </div>
  </div>
</div>

<style>
.ob-page {
  min-height: 100vh; background: var(--noir-bg);
  padding: 0 1rem 3rem; position: relative; overflow: hidden;
}
.glow {
  position: fixed; top: -200px; left: 50%; transform: translateX(-50%);
  width: 700px; height: 600px;
  background: radial-gradient(ellipse, rgba(201,168,76,.06) 0%, transparent 68%);
  pointer-events: none;
}

/* ── Header ── */
.ob-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.25rem 0 1rem; max-width: 700px; margin: 0 auto;
  gap: 1rem; flex-wrap: wrap;
}
.brand { display: flex; align-items: center; gap: 6px; }
.brand-star { color: var(--gold); }
.brand-name { color: var(--cream); font-size: 1.1rem; font-weight: 500; }

.step-wrap { display: flex; align-items: center; gap: 10px; }
.step-bar {
  width: 120px; height: 4px;
  background: var(--noir-soft); border-radius: 9px; overflow: hidden;
}
.step-fill {
  height: 100%; background: var(--gold);
  border-radius: 9px; transition: width .3s ease;
}
.step-label { font-size: .75rem; color: var(--muted); min-width: 80px; }

/* ── Content ── */
.ob-content { max-width: 700px; margin: 0 auto; }
.ob-title { font-size: 1.6rem; font-weight: 500; color: var(--cream); margin-bottom: 8px; }
.ob-sub {
  font-size: .875rem; color: var(--muted); margin-bottom: 2rem;
  line-height: 1.6; max-width: 500px;
}
.ob-sub strong { color: var(--gold); }

/* ── Genre grid ── */
.genre-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 2rem;
}

.genre-pill {
  position: relative;
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px;
  background: var(--noir-card);
  border: 1px solid var(--noir-border);
  border-radius: var(--radius-md);
  color: var(--muted); font-size: .875rem;
  cursor: pointer; text-align: left;
  transition: border-color .2s, background .2s, transform .15s, color .2s;
  width: 100%;
}
.genre-pill:hover:not(.active) {
  border-color: var(--subtle); color: var(--cream); transform: translateY(-1px);
}
.genre-pill.active {
  border-color: var(--gold);
  background: rgba(201,168,76,.1);
  color: var(--cream);
  box-shadow: 0 0 0 1px rgba(201,168,76,.2);
}
.genre-pill:active { transform: scale(.97); }
.genre-emoji { font-size: 1.1rem; flex-shrink: 0; }
.genre-name  { flex: 1; }
.genre-check {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  width: 18px; height: 18px;
  background: var(--gold); color: #09090e;
  border-radius: 50%; font-size: .6rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}

/* ── Footer ── */
.ob-footer {
  position: sticky; bottom: 0;
  background: linear-gradient(to top, var(--noir-bg) 70%, transparent);
  padding: 1.5rem 0 .5rem;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.hint { font-size: .825rem; color: var(--muted); }
.hint.ready { color: #52c07a; }

.error-box {
  background: rgba(224,82,82,.1); border: 1px solid rgba(224,82,82,.25);
  border-radius: var(--radius-sm); padding: 8px 12px;
  font-size: .8rem; color: #ff8080; margin-bottom: 1rem;
}

.btn-gold {
  padding: 12px 2.5rem; min-width: 220px;
  background: var(--gold); border: none; border-radius: var(--radius-sm);
  color: #09090e; font-size: .9rem; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.btn-gold:hover:not(:disabled)  { opacity: .85; }
.btn-gold:active:not(:disabled) { transform: scale(.98); }
.btn-gold:disabled { opacity: .35; cursor: not-allowed; }

.spin {
  width: 13px; height: 13px;
  border: 2px solid rgba(9,9,14,.3); border-top-color: #09090e;
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 480px) {
  .genre-grid { grid-template-columns: repeat(2, 1fr); }
  .ob-title   { font-size: 1.3rem; }
}
</style>
