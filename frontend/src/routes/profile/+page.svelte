<script>
  /**
   * routes/profile/+page.svelte
   * Dashboard Profil Selera & Grafik Evolusi Selera Pengguna.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { userStore, isLoggedIn } from '$lib/stores/user.js';
  import { request } from '$lib/api.js'; // Menggunakan fungsi request bawaan asli tim

  // ── State (Svelte 5 Runes) ─────────────────────────────────────────────
  let profile = $state(null);
  let evolution = $state([]);
  let realLikedCount = $state(0); // Fallback riil untuk jumlah film favorit
  let fallbackGenresDistribution = $state(null); // Fallback riil untuk distribusi genre
  let fallbackDirectors = $state([]); // Fallback riil untuk sutradara favorit
  let fallbackActors = $state([]); // Fallback riil untuk aktor favorit
  let loading = $state(true);
  let refreshing = $state(false);
  let error = $state('');

  const user = $derived($userStore);

  onMount(async () => {
    if (!$isLoggedIn) {
      goto('/login');
      return;
    }
    await loadProfileData();
  });

  async function loadProfileData() {
    loading = true;
    error = '';
    try {
      // 1. Ambil Ringkasan Profil Selera v5 (Gunakan fungsi request asli dengan prefix /api/v1)
      const profileRes = await request(`/api/v1/profile/${user.id}?include_credits=true`, { token: user.token });
      // Deteksi envelope .data dan fallback ke objek kosong jika tidak ada data valid
      const profileData = profileRes?.data ?? profileRes;
      profile = profileData && typeof profileData === 'object' ? profileData : {};

      // 2. Ambil Deret Snapshot Evolusi v5
      const evolutionRes = await request(`/api/v1/profile/${user.id}/evolution`, { token: user.token });
      // Menangani pembungkus .data secara aman dengan fallback array kosong
      const evolutionData = evolutionRes?.data ?? evolutionRes;
      evolution = Array.isArray(evolutionData) ? evolutionData : (evolutionData?.results ?? []);

      // 3. Mengambil data interaksi favorit secara langsung untuk jaminan fallback yang akurat
      const favsRes = await request(`/api/v1/users/${user.id}/interactions?type=favorite`, { token: user.token });
      const favsData = favsRes?.data ?? favsRes;
      const favsArray = Array.isArray(favsData) ? favsData : (favsData?.interactions ?? favsData?.results ?? []);
      realLikedCount = favsArray.length;

      // 4. Hitung fallback distribusi genre, sutradara, dan aktor jika kosong dari backend
      const backendGenres = profile?.genre_distribution;
      const backendDirectors = profile?.favorite_directors;
      const backendActors = profile?.favorite_actors;

      const needsFallback = realLikedCount > 0 && (
        (!backendGenres || Object.keys(backendGenres).length === 0) ||
        (!backendDirectors || backendDirectors.length === 0) ||
        (!backendActors || backendActors.length === 0)
      );

      if (needsFallback) {
        const genreCounts = {};
        const directorCounts = {};
        const actorCounts = {};
        let totalGenresCount = 0;

        // Ambil detail film (termasuk credits) secara paralel
        const movieDetails = await Promise.allSettled(
          favsArray.map(item => request(`/api/v1/movie/${item.movie_id}?include_credits=true`, { token: user.token }))
        );

        movieDetails.forEach(res => {
          if (res.status === 'fulfilled') {
            const movie = res.value?.movie ?? res.value;
            
            // Proses Genre
            const genres = movie?.genres ?? (movie?.genre ? [movie.genre] : []);
            genres.forEach(g => {
              if (g) {
                genreCounts[g] = (genreCounts[g] || 0) + 1;
                totalGenresCount++;
              }
            });

            // Proses Sutradara
            const directors = movie?.directors ?? [];
            directors.forEach(d => {
              if (d) {
                directorCounts[d] = (directorCounts[d] || 0) + 1;
              }
            });

            // Proses Aktor/Pemeran
            const cast = movie?.cast ?? [];
            cast.forEach(actor => {
              if (actor?.name) {
                actorCounts[actor.name] = (actorCounts[actor.name] || 0) + 1;
              }
            });
          }
        });

        // Simpan data ke state fallback jika data backend kosong
        if (totalGenresCount > 0 && (!backendGenres || Object.keys(backendGenres).length === 0)) {
          const computedDist = {};
          Object.entries(genreCounts).forEach(([genre, count]) => {
            computedDist[genre] = Math.round((count / totalGenresCount) * 100);
          });
          fallbackGenresDistribution = computedDist;
        }

        if (!backendDirectors || backendDirectors.length === 0) {
          fallbackDirectors = Object.entries(directorCounts)
            .sort((a, b) => b[1] - a[1])
            .map(entry => entry[0])
            .slice(0, 3);
        }

        if (!backendActors || backendActors.length === 0) {
          fallbackActors = Object.entries(actorCounts)
            .sort((a, b) => b[1] - a[1])
            .map(entry => entry[0])
            .slice(0, 5);
        }
      }
    } catch (e) {
      error = e.message || 'Gagal memuat profil selera.';
    } finally {
      loading = false;
    }
  }

  // Pemicu Hitung Ulang Snapshot Selera Manual v5
  async function handleRefreshProfile() {
    refreshing = true;
    try {
      await request(`/api/v1/profile/${user.id}/refresh?include_credits=true`, { method: 'POST', token: user.token });
      await loadProfileData(); // Reload data setelah refresh berhasil
      alert('Profil selera berhasil diperbarui secara real-time!');
    } catch (e) {
      alert('Gagal menyegarkan profil selera.');
    } finally {
      refreshing = false;
    }
  }

  // Transformasi objek genre_distribution menjadi array terurut untuk Bar Chart
  const sortedGenres = $derived(
    (profile?.genre_distribution && Object.keys(profile.genre_distribution).length > 0)
      ? Object.entries(profile.genre_distribution)
          .map(([name, value]) => ({ name, value }))
          .sort((a, b) => b.value - a.value)
      : (fallbackGenresDistribution
          ? Object.entries(fallbackGenresDistribution)
              .map(([name, value]) => ({ name, value }))
              .sort((a, b) => b.value - a.value)
          : [])
  );

  // Cari genre dominan terbesar secara aman
  const dominantGenres = $derived(
    profile?.dominant_genres && profile.dominant_genres.length > 0
      ? profile.dominant_genres
      : (sortedGenres.length > 0 ? [sortedGenres[0].name] : [])
  );

  // Cari sutradara terfavorit secara aman
  const displayDirectors = $derived(
    profile?.favorite_directors && profile.favorite_directors.length > 0
      ? profile.favorite_directors
      : fallbackDirectors
  );

  // Cari aktor terfavorit secara aman
  const displayActors = $derived(
    profile?.favorite_actors && profile.favorite_actors.length > 0
      ? profile.favorite_actors
      : fallbackActors
  );
</script>

<div class="page">
  <nav class="navbar">
    <div class="nav-brand">
      <img src="/logo.webp" alt="Lumiere Logo" width="80" height="80" />
      <span class="brand-tag">TASTE PROFILE ANALYTICS</span>
    </div>
    <div class="nav-right">
      {#if user}
        <span class="nav-user">Halo, <strong>{user.name}</strong></span>
        <button
          class="btn-ghost"
          onclick={() => {
            userStore.logout();
            goto('/login');
          }}>Keluar</button
        >
      {/if}
    </div>
  </nav>

  <main class="content">
    {#if loading}
      <div class="loading-state">Menganalisis matriks selera filmmu...</div>
    {:else if error}
      <div class="error-state">
        <span class="error-icon">⚠</span>
        <div>
          <div class="error-title">Analisis Gagal</div>
          <div class="error-msg">{error}</div>
          <button class="btn-gold-sm" onclick={loadProfileData}>Coba Lagi</button>
        </div>
      </div>
    {:else if (profile && Object.keys(profile).length > 0) || realLikedCount > 0}
      <header class="profile-header">
        <div>
          <h1 class="title">DNA Seleramu</h1>
          <p class="sub">
            Metrik preferensi yang diekstraksi dari riwayat interaksi dan onboarding.
          </p>
        </div>
        <button class="btn-gold" onclick={handleRefreshProfile} disabled={refreshing}>
          {refreshing ? '🔄 Sinkronisasi...' : '⚡ Refresh Selera'}
        </button>
      </header>

      <div class="dashboard-grid">
        <div class="metrics-card">
          <h3 class="card-title">📊 Distribusi Minat Genre</h3>
          <div class="bar-chart-container">
            {#each sortedGenres as genre}
              <div class="bar-row">
                <span class="genre-label">{genre.name}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="width: {Math.min(100, genre.value)}%"></div>
                </div>
                <span class="genre-value">{genre.value}%</span>
              </div>
            {/each}
          </div>
        </div>

        <div class="side-panel">
          <div class="metrics-card highlight">
            <h4 class="card-meta">Dominant Genre & Mood</h4>
            <div class="highlight-val">{dominantGenres?.[0] || 'N/A'}</div>
            <p class="highlight-sub">
              Suasana Favorit: <span>{profile.favorite_mood || 'Universal'}</span>
            </p>
            <div class="confidence-badge">
              Tingkat Akurasi AI: {((profile.confidence ?? 0.8) * 100).toFixed(0)}%
            </div>
          </div>

          <div class="metrics-card">
            <h3 class="card-title">🎬 Sutradara & Aktor Favorit</h3>
            <div class="meta-list">
              <div class="meta-item">
                <strong>Sutradara:</strong>
                <span>{displayDirectors.join(', ') || 'Belum terdeteksi'}</span>
              </div>
              <div class="meta-item">
                <strong>Aktor/Aktris:</strong>
                <span>{displayActors.join(', ') || 'Belum terdeteksi'}</span>
              </div>
              <div class="meta-item border-top">
                <strong>Total Film Disukai:</strong>
                <span class="gold-text">
                  {profile.stats?.interaction_liked_count || profile.interaction_liked_count || realLikedCount} Judul
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="metrics-card wide">
        <h3 class="card-title">📈 Grafik Evolusi Kedalaman Selera</h3>
        <p class="card-sub">
          Visualisasi akumulasi ketajaman preferensi seleramu yang meningkat seiring aktivitas
          onboarding dan interaksi ulasan.
        </p>

        {#if evolution.length > 1}
          {@const points = evolution.map((snap, i) => {
            const x = (i / (evolution.length - 1)) * 460 + 20;
            
            // Cek apakah data bertipe persentase (taste_depth, depth_score, confidence)
            const isPercentage = (snap.taste_depth !== undefined) || 
                                 (snap.depth_score !== undefined) || 
                                 (snap.confidence !== undefined);
            
            // Ekstraksi nilai secara dinamis
            const value = snap.taste_depth || 
                          snap.depth_score || 
                          (snap.confidence ? (snap.confidence <= 1 ? Math.round(snap.confidence * 100) : snap.confidence) : null) || 
                          snap.stats?.interaction_liked_count || 
                          snap.interaction_liked_count || 
                          0;
            
            // Penskalaan sumbu Y: Jika persentase langsung dipetakan 0-100, jika hitungan film dikali faktor skala 15
            const y = 130 - Math.min(100, isPercentage ? value : value * 15);
            const unit = isPercentage ? '%' : ' Film';
            
            return { x, y, value, unit, label: `Snap ${i + 1}` };
          })}

          <div class="svg-chart-wrap">
            <svg viewBox="0 0 500 150" class="line-chart">
              <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stop-color="var(--gold)" stop-opacity="0.2" />
                  <stop offset="100%" stop-color="var(--gold)" stop-opacity="0" />
                </linearGradient>
              </defs>

              <path
                d="M {points[0].x} 130 L {points.map((p) => `${p.x} ${p.y}`).join(' L ')} L {points[
                  points.length - 1
                ].x} 130 Z"
                fill="url(#grad)"
              />

              <polyline
                fill="none"
                stroke="var(--gold)"
                stroke-width="3"
                points={points.map((p) => `${p.x},${p.y}`).join(' ')}
              />

              {#each points as pt}
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r="4"
                  fill="#09090e"
                  stroke="var(--gold)"
                  stroke-width="2"
                />
                <text x={pt.x} y={pt.y - 10} text-anchor="middle" class="chart-text-val"
                  >{pt.value}{pt.unit}</text
                >
                <text x={pt.x} y="145" text-anchor="middle" class="chart-text-label"
                  >{pt.label}</text
                >
              {/each}
            </svg>
          </div>
        {:else}
          <div class="section-empty">
            Grafik memerlukan minimal 2 snapshot riwayat. Terus lakukan interaksi (rating/favorite)
            pada film untuk menumbuhkan snapshot baru!
          </div>
        {/if}
      </div>
    {:else}
      <div class="error-state">
        <span class="error-icon">⚠</span>
        <div>
          <div class="error-title">Profil Belum Siap</div>
          <div class="error-msg">
            Data profil Anda kosong atau belum terhitung oleh AI. Silakan klik tombol di bawah untuk memicu hitung ulang.
          </div>
          <button class="btn-gold-sm" onclick={handleRefreshProfile} disabled={refreshing}>
            {refreshing ? '🔄 Memproses...' : '⚡ Hitung Selera Baru'}
          </button>
        </div>
      </div>
    {/if}
  </main>

  <nav
    class="navbar"
    style="position: static; border-top: 1px solid var(--noir-border); border-bottom: none; justify-content: center; background: transparent; padding: 1rem;"
  >
    <div class="nav-right" style="gap: 1.5rem;">
      <a
        href="/"
        class="brand-name"
        style="text-decoration: none; font-size: 0.85rem; color: var(--muted);">Beranda</a
      >
      <a
        href="/favorites"
        class="brand-name"
        style="text-decoration: none; font-size: 0.85rem; color: var(--muted);">Favorit Saya</a
      >
      <a
        href="/profile"
        class="brand-name"
        style="text-decoration: none; font-size: 0.85rem; color: var(--gold);">Profil Selera</a
      >
    </div>
  </nav>

  <footer class="site-footer">
    Lumiere © 2026 · PJK-GM074 · Pijak × IBM SkillsBuild ·
    <span>Lita · Rajif · Arghi · Zaky</span>
  </footer>
</div>

<style>
  /* Keselarasan Token Desain Antarmuka Noir & Emas */
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
    padding: 0 1.5rem 3rem;
  }

  .navbar {
    position: sticky;
    top: 0;
    z-index: 50;
    background: rgba(10, 10, 15, 0.88);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--noir-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.9rem 1.5rem;
    gap: 1rem;
  }
  .nav-brand {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .brand-name {
    color: var(--cream);
    font-size: 1rem;
    font-weight: 500;
  }
  .brand-tag {
    font-size: 0.6rem;
    color: #444455;
    letter-spacing: 0.08em;
  }
  .nav-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .nav-user {
    font-size: 0.8rem;
    color: var(--muted);
  }
  .nav-user strong {
    color: var(--cream);
  }

  .profile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 2.5rem;
    margin-bottom: 1.5rem;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .profile-header .title {
    font-size: 1.6rem;
    font-weight: 500;
    color: var(--cream);
  }
  .profile-header .sub {
    font-size: 0.85rem;
    color: var(--muted);
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .metrics-card {
    background: var(--noir-card, #121218);
    border: 1px solid var(--noir-border, #222230);
    border-radius: var(--radius-lg, 12px);
    padding: 1.5rem;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  }
  .metrics-card.wide {
    grid-column: span 2;
  }
  .metrics-card.highlight {
    background: radial-gradient(circle at top right, rgba(201, 168, 76, 0.08), transparent);
    border-color: rgba(201, 168, 76, 0.2);
    text-align: center;
    padding: 2rem 1.5rem;
  }

  .card-title {
    font-size: 1rem;
    font-weight: 500;
    color: var(--cream);
    margin-bottom: 1.25rem;
  }
  .card-sub {
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 1rem;
  }
  .card-meta {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--subtle, #555566);
    margin-bottom: 6px;
  }

  .highlight-val {
    font-size: 2rem;
    font-weight: 600;
    color: var(--gold);
  }
  .highlight-sub {
    font-size: 0.85rem;
    color: var(--muted);
    margin-top: 4px;
  }
  .highlight-sub span {
    color: white;
    font-weight: 500;
  }

  .confidence-badge {
    display: inline-block;
    margin-top: 12px;
    background: rgba(82, 192, 122, 0.1);
    color: #52c07a;
    border: 1px solid rgba(82, 122, 122, 0.2);
    font-size: 0.7rem;
    padding: 2px 10px;
    border-radius: 99px;
  }

  /* Bar Chart Layout */
  .bar-chart-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .bar-row {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.85rem;
  }
  .genre-label {
    width: 100px;
    color: var(--muted);
    text-align: right;
    flex-shrink: 0;
  }
  .bar-track {
    flex: 1;
    height: 8px;
    background: var(--noir-surface, #181824);
    border-radius: 4px;
    overflow: hidden;
  }
  .bar-fill {
    height: 100%;
    background: var(--gold);
    border-radius: 4px;
  }
  .genre-value {
    width: 45px;
    color: var(--cream);
    font-weight: 500;
  }

  /* Metadata List */
  .meta-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    font-size: 0.85rem;
  }
  .meta-item strong {
    color: var(--muted);
    font-weight: 400;
  }
  .meta-item span {
    color: var(--cream);
    margin-left: 4px;
  }
  .meta-item.border-top {
    border-top: 1px solid var(--noir-border);
    padding-top: 10px;
    margin-top: 4px;
  }
  .gold-text {
    color: var(--gold) !important;
    font-weight: 500;
  }

  /* Native SVG Chart */
  .svg-chart-wrap {
    background: var(--noir-surface, #181824);
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1rem;
    border: 1px solid var(--noir-border);
  }
  .line-chart {
    width: 100%;
    height: auto;
    display: block;
    overflow: visible;
  }
  .chart-text-val {
    font-size: 7px;
    fill: var(--cream);
    font-weight: 500;
  }
  .chart-text-label {
    font-size: 7px;
    fill: var(--subtle, #555566);
  }

  .loading-state {
    text-align: center;
    padding: 5rem 0;
    color: var(--muted);
    font-size: 0.9rem;
  }
  .error-state {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background: var(--noir-card, #121218);
    border: 1px solid var(--noir-border, #222230);
    border-radius: var(--radius-lg, 12px);
    padding: 2.5rem 1.5rem;
    max-width: 600px;
    margin: 3rem auto;
    text-align: left;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  }
  .error-icon {
    font-size: 2.5rem;
    color: #e05252;
  }
  .error-title {
    font-size: 1.15rem;
    font-weight: 500;
    color: var(--cream);
    margin-bottom: 0.5rem;
  }
  .error-msg {
    font-size: 0.85rem;
    color: var(--muted);
    margin-bottom: 1rem;
    line-height: 1.5;
  }
  .btn-gold-sm {
    padding: 6px 14px;
    background: var(--gold);
    border: none;
    color: #09090e;
    font-size: 0.8rem;
    font-weight: 500;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }
  .btn-gold-sm:hover:not(:disabled) {
    opacity: 0.85;
  }
  .btn-gold-sm:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .section-empty {
    font-size: 0.825rem;
    color: var(--subtle);
    text-align: center;
    padding: 2rem 0;
  }

  .btn-ghost {
    padding: 6px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--noir-border);
    background: transparent;
    color: var(--muted);
    font-size: 0.8rem;
    cursor: pointer;
  }
  .btn-ghost:hover {
    border-color: var(--subtle);
    color: var(--cream);
  }

  .btn-gold {
    padding: 10px 20px;
    background: var(--gold);
    border: none;
    color: #09090e;
    font-size: 0.85rem;
    font-weight: 500;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .btn-gold:hover:not(:disabled) {
    opacity: 0.85;
  }
  .btn-gold:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .site-footer {
    border-top: 1px solid var(--noir-border);
    padding: 1.25rem 1.5rem;
    font-size: 0.7rem;
    color: var(--subtle);
    text-align: center;
  }
  .site-footer span {
    color: #444455;
  }

  @media (max-width: 850px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
    }
    .metrics-card.wide {
      grid-column: span 1;
    }
  }
</style>