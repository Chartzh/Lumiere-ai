<script>
	/**
	 * routes/+page.svelte
	 * ─────────────────────────────────────────────────────────────────────
	 * Halaman utama Lumiere — dashboard rekomendasi film & Mood Discovery.
	 */

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import MovieCard from '$lib/components/MovieCard.svelte';
	import GenreFilter from '$lib/components/GenreFilter.svelte';
	import LoadingSkeleton from '$lib/components/LoadingSkeleton.svelte';
	import { userStore, isLoggedIn } from '$lib/stores/user.js';
	// Import request tambahan untuk mengamankan panggilan custom endpoint mood v5
	import { fetchRecommendations, fetchPopular, fetchTrending, trackClick, request } from '$lib/api.js';

	// ── State ──────────────────────────────────────────────────────────────
	let personal = $state([]); // rekomendasi personal dari NCF
	let popular = $state([]); // film populer (jumlah rating + klik)
	let trending = $state([]); // film terbaru

	// State Tambahan untuk Mood Discovery v5
	let moods = $state([]);
	let selectedMood = $state('');
	let moodMovies = $state([]);

	const moodEmojis = {
		'santai': '🍃',
		'ringan': '🍿',
		'bahagia': '😊',
		'menegangkan': '⚡',
		'menantang': '🧗',
		'mengharukan': '🥺',
		'penasaran': '🕵️',
		'nostalgia': '📻',
		'berpikir': '🧠',
		'epik': '⚔️',
		'romantis': '💖',
		'seram': '👻'
	};

	async function selectMoodHandler(moodValue) {
		if (selectedMood === moodValue) {
			selectedMood = '';
		} else {
			selectedMood = moodValue;
		}
		await handleMoodChange();
	}

	let loadingPersonal = $state(true);
	let loadingPopular = $state(true);
	let loadingTrending = $state(true);
	let loadingMood = $state(false);

	let errorPersonal = $state('');
	let activeGenre = $state('All');
	let showGreeting = $state(true);

	// ── Computed ───────────────────────────────────────────────────────────
	const user = $derived($userStore);

	// Ambil semua genre unik dari hasil personal
	const allGenres = $derived([...new Set(personal.flatMap((m) => m.genres ?? []))].sort());
	// Filter personal berdasarkan genre yang dipilih
	const displayed = $derived(
		activeGenre === 'All' ? personal : personal.filter((m) => m.genres?.includes(activeGenre))
	);

	// ── Load data saat mount ───────────────────────────────────────────────
	onMount(async () => {
		if (!$isLoggedIn) {
			goto('/login');
			return;
		}

		// Sembunyikan greeting setelah 3 detik
		setTimeout(() => (showGreeting = false), 3000);

		// Load seksi paralel bawaan dan opsi mood discovery v5
		loadPersonal();
		loadPopular();
		loadTrending();
		loadMoodOptions();
	});

	// ── Fetch personal rekomendasi ─────────────────────────────────────────
	async function loadPersonal() {
		loadingPersonal = true;
		errorPersonal = '';
		try {
			const data = await fetchRecommendations({ user_id: user.id, top_k: 20 }, user.token);
			personal = enrichMovies(data.recommendations ?? []);
		} catch (e) {
			errorPersonal = e.message ?? 'Gagal memuat rekomendasi.';
		} finally {
			loadingPersonal = false;
		}
	}

	// ── Fetch daftar opsi mood resmi v5 ────────────────────────────────────
	async function loadMoodOptions() {
		try {
			const data = await request('/api/v1/moods', { token: user.token });
			moods = Array.isArray(data) ? data : (data.moods || []);
		} catch {
			// Gagal senyap agar tidak merusak seksi utama lain
		}
	}

	// ── Fetch film berdasarkan mood yang dipilih v5 ────────────────────────
	async function handleMoodChange() {
		if (!selectedMood) {
			moodMovies = [];
			return;
		}
		loadingMood = true;
		try {
			const data = await request(`/api/v1/recommend/mood/${selectedMood}?top_k=15&user_id=${user.id}`, {
				token: user.token
			});
			moodMovies = enrichMovies(Array.isArray(data) ? data : (data.recommendations ?? data.results ?? data ?? []));
		} catch {
			// Gagal senyap
		} finally {
			loadingMood = false;
		}
	}

	// ── Fetch populer ──────────────────────────────────────────────────────
	async function loadPopular() {
		loadingPopular = true;
		try {
			const data = await fetchPopular({ limit: 10 });
			popular = enrichMovies(data.recommendations ?? data.results ?? data ?? []);
		} catch {
			// Gagal senyap — seksi ini tidak kritis
		} finally {
			loadingPopular = false;
		}
	}

	// ── Fetch trending ─────────────────────────────────────────────────────
	async function loadTrending() {
		loadingTrending = true;
		try {
			const data = await fetchTrending({ limit: 10 });
			trending = enrichMovies(data.recommendations ?? data.results ?? data ?? []);
		} catch {
			// Gagal senyap
		} finally {
			loadingTrending = false;
		}
	}

	/**
	 * Normalisasi response API ke format yang dipakai MovieCard.
	 */
	function enrichMovies(raw) {
		return raw.map((m) => {
			const genresSource = m.genres ?? m.genre ?? m.xai_reason?.matched_features ?? [];
			return {
				...m,
				genres: Array.isArray(genresSource)
					? genresSource
					: genresSource
							.toString()
							.split(',')
							.map((s) => s.trim())
							.filter(Boolean)
			};
		});
	}

	// ── Tracking klik (catat kebiasaan user) ──────────────────────────────
	function handleCardClick(movieId) {
		if (user?.token) trackClick({ movie_id: movieId }, user.token);
		goto(`/movie/${movieId}`);
	}

	// ── Logout ─────────────────────────────────────────────────────────────
	function handleLogout() {
		userStore.logout();
		goto('/login');
	}
</script>

<div class="page">
	<nav class="navbar">
		<div class="nav-brand">
			<img src="/logo.webp" alt="Lumiere Logo" width="80" height="80" />
			<span class="brand-tag">INTELLIGENT MOVIE DISCOVERY · NEURAL COLLABORATIVE FILTERING</span>
		</div>
		<div class="nav-right">
			{#if user}
				<span class="nav-user">Halo, <strong>{user.name}</strong></span>
				<button class="btn-ghost" onclick={handleLogout}>Keluar</button>
			{/if}
		</div>
	</nav>

	{#if showGreeting && user}
		<div class="greeting-banner">
			<span class="greeting-emoji">👋</span>
			<div>
				<div class="greeting-title">Selamat datang, {user.name}!</div>
				<div class="greeting-sub">
					Berikut rekomendasi film yang dipilih khusus untukmu berdasarkan seleramu terhadap
					<strong>{user.favoriteGenres?.join(', ') || 'berbagai genre'}</strong>.
				</div>
			</div>
		</div>
	{/if}

	<main class="content">
		<section class="section">
			<div class="section-head">
				<div>
					<h2 class="section-title">
						Dipilih untuk kamu
						{#if user?.favoriteGenres?.length}
							<span class="section-badge">
								{user.favoriteGenres.slice(0, 2).join(' · ')}
							</span>
						{/if}
					</h2>
					<p class="section-sub">
						Rekomendasi personal dari model Neural Collaborative Filtering, semakin akurat seiring
						kamu menonton dan memberi rating.
					</p>
				</div>
				<button class="btn-ghost-sm" onclick={loadPersonal} disabled={loadingPersonal}>
					{loadingPersonal ? '...' : '↺ Refresh'}
				</button>
			</div>

			{#if !loadingPersonal && personal.length > 0}
				<GenreFilter genres={allGenres} {activeGenre} onSelect={(g) => (activeGenre = g)} />
			{/if}

			{#if loadingPersonal}
				<LoadingSkeleton count={10} />
			{:else if errorPersonal}
				<div class="error-state">
					<span class="error-icon">⚠</span>
					<div>
						<div class="error-title">Gagal memuat rekomendasi</div>
						<div class="error-msg">{errorPersonal}</div>
						<button class="btn-gold-sm" onclick={loadPersonal}>Coba lagi</button>
					</div>
				</div>
			{:else if displayed.length === 0 && personal.length > 0}
				<div class="empty-state">
					<span class="empty-icon">🔍</span>
					<p>Tidak ada film yang cocok dengan filter <strong>{activeGenre}</strong>.</p>
					<button class="btn-ghost-sm" onclick={() => (activeGenre = 'All')}>
						Tampilkan semua genre
					</button>
				</div>
			{:else if personal.length === 0}
				<div class="empty-state">
					<span class="empty-icon">🎬</span>
					<p>Model sedang mempersiapkan rekomendasimu.</p>
					<button class="btn-ghost-sm" onclick={loadPersonal}>Muat ulang</button>
				</div>
			{:else}
				<div class="movie-grid">
					{#each displayed as film (film.movie_id)}
						<MovieCard
							movie_id={film.movie_id}
							title={film.title}
							confidence={film.confidence ?? film.xai_reason?.primary_factor ?? 'Rekomendasi AI'}
							poster_url={film.poster_url}
							genre={film.genres?.[0] ?? film.genre}
							synopsis={film.synopsis}
							onclick={handleCardClick}
						/>
					{/each}
				</div>
			{/if}
		</section>

		<section class="section mood-section">
			<div class="section-head">
				<div>
					<h2 class="section-title">🔮 Mood Discovery</h2>
					<p class="section-sub">Bagaimana suasana hatimu hari ini? Pilih mood untuk menyesuaikan rekomendasi sinematik AI.</p>
				</div>
			</div>

			<div class="mood-chips-container">
				{#each moods as m}
					{@const moodValue = typeof m === 'object' ? (m.name || m.mood || m.value || '') : m}
					{@const moodLabel = typeof m === 'object' ? (m.name || m.mood || m.label || moodValue) : m}
					{@const emoji = moodEmojis[moodValue.toLowerCase()] || '🎬'}
					
					<button
						class="mood-chip"
						class:active={selectedMood === moodValue}
						onclick={() => selectMoodHandler(moodValue)}
					>
						<span class="mood-emoji">{emoji}</span>
						<span class="mood-label">{moodLabel}</span>
					</button>
				{/each}
			</div>

			{#if loadingMood}
				<LoadingSkeleton count={5} />
			{:else if moodMovies.length > 0}
				<div class="movie-grid">
					{#each moodMovies as film (film.movie_id)}
						<MovieCard
							movie_id={film.movie_id}
							title={film.title}
							confidence={film.xai_reason?.primary_factor || `Nuansa ${selectedMood}`}
							poster_url={film.poster_url}
							genre={Array.isArray(film.genres) ? film.genres[0] : (film.genre || 'Movie')}
							synopsis={film.synopsis}
							onclick={handleCardClick}
						/>
					{/each}
				</div>
			{:else if selectedMood}
				<div class="section-empty" style="text-align: center; padding: 2rem 0;">Tidak ada rekomendasi khusus untuk mood {selectedMood}.</div>
			{/if}
		</section>

		<section class="section">
			<div class="section-head">
				<div>
					<h2 class="section-title">🔥 Film Populer</h2>
					<p class="section-sub">
						Berdasarkan jumlah rating di dataset MovieLens dan klik/view pengguna sistem ini.
					</p>
				</div>
			</div>

			{#if loadingPopular}
				<div class="row-scroll">
					<LoadingSkeleton count={6} />
				</div>
			{:else if popular.length > 0}
				<div class="movie-row">
					{#each popular as film (film.movie_id)}
						<MovieCard
							movie_id={film.movie_id}
							title={film.title}
							confidence={film.xai_reason?.primary_factor || 'Populer'}
							poster_url={film.poster_url}
							genre={film.genres?.[0] ?? film.genre}
							synopsis={film.synopsis}
							onclick={handleCardClick}
						/>
					{/each}
				</div>
			{:else}
				<div class="section-empty">Data populer belum tersedia.</div>
			{/if}
		</section>

		<section class="section">
			<div class="section-head">
				<div>
					<h2 class="section-title">✨ Film Terbaru</h2>
					<p class="section-sub">Film yang baru-baru ini ditambahkan ke dataset.</p>
				</div>
			</div>

			{#if loadingTrending}
				<div class="row-scroll">
					<LoadingSkeleton count={6} />
				</div>
			{:else if trending.length > 0}
				<div class="movie-row">
					{#each trending as film (film.movie_id)}
						<MovieCard
							movie_id={film.movie_id}
							title={film.title}
							confidence={film.xai_reason?.primary_factor || 'Baru Ditambahkan'}
							poster_url={film.poster_url}
							genre={film.genres?.[0] ?? film.genre}
							synopsis={film.synopsis}
							onclick={handleCardClick}
						/>
					{/each}
				</div>
			{:else}
				<div class="section-empty">Data trending belum tersedia.</div>
			{/if}
		</section>
	</main>

	<nav class="navbar" style="position: static; border-top: 1px solid var(--noir-border); border-bottom: none; justify-content: center; background: transparent; padding: 1rem;">
		<div class="nav-right" style="gap: 1.5rem;">
			<a href="/" class="brand-name" style="text-decoration: none; font-size: 0.85rem; color: var(--gold);">Beranda</a>
			<a href="/favorites" class="brand-name" style="text-decoration: none; font-size: 0.85rem; color: var(--muted);">Favorit Saya</a>
			<a href="/profile" class="brand-name" style="text-decoration: none; font-size: 0.85rem; color: var(--muted);">Profil Selera</a>
		</div>
	</nav>

	<footer class="site-footer">
		Lumiere © 2026 · PJK-GM074 · Pijak × IBM SkillsBuild ·
		<span>Lita · Rajif · Arghi · Zaky</span>
	</footer>
</div>

<style>
	/* ── Layout ── */
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

	/* ── Navbar ── */
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
		flex-wrap: wrap;
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

	/* ── Greeting banner ── */
	.greeting-banner {
		max-width: 1200px;
		margin: 1.25rem auto 0;
		padding: 0 1.5rem;
		display: flex;
		align-items: flex-start;
		gap: 12px;
	}
	.greeting-emoji {
		font-size: 1.5rem;
		flex-shrink: 0;
		margin-top: 2px;
	}
	.greeting-title {
		font-size: 1rem;
		font-weight: 500;
		color: var(--cream);
		margin-bottom: 2px;
	}
	.greeting-sub {
		font-size: 0.825rem;
		color: var(--muted);
		line-height: 1.5;
	}
	.greeting-sub strong {
		color: var(--gold);
	}

	/* ── Sections ── */
	.section {
		margin-top: 2.5rem;
	}
	.section-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1.25rem;
		flex-wrap: wrap;
	}
	.section-title {
		font-size: 1.15rem;
		font-weight: 500;
		color: var(--cream);
		margin-bottom: 4px;
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}
	.section-badge {
		background: rgba(201, 168, 76, 0.12);
		border: 1px solid var(--gold-dim, #a58734);
		border-radius: 999px;
		padding: 1px 10px;
		font-size: 0.7rem;
		color: var(--gold);
		font-weight: 400;
	}
	.section-sub {
		font-size: 0.8rem;
		color: var(--muted);
		line-height: 1.5;
		max-width: 540px;
	}

	/* Mood Chips Layout */
	.mood-chips-container {
		display: flex;
		gap: 10px;
		overflow-x: auto;
		padding: 4px 4px 14px;
		margin-bottom: 1rem;
		scrollbar-width: thin;
		scrollbar-color: var(--noir-border) transparent;
	}
	.mood-chips-container::-webkit-scrollbar {
		height: 6px;
	}
	.mood-chips-container::-webkit-scrollbar-thumb {
		background: var(--noir-border, #222);
		border-radius: 99px;
	}
	.mood-chips-container::-webkit-scrollbar-track {
		background: transparent;
	}

	.mood-chip {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		background: var(--noir-card, #121218);
		border: 1px solid var(--noir-border, #222230);
		color: var(--muted, #888);
		padding: 10px 18px;
		border-radius: 999px;
		font-size: 0.85rem;
		font-weight: 500;
		cursor: pointer;
		white-space: nowrap;
		transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
		user-select: none;
	}
	.mood-chip:hover {
		border-color: var(--subtle, #444);
		color: var(--cream, #f5f5f7);
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
	}
	.mood-chip.active {
		background: radial-gradient(circle at center, rgba(201, 168, 76, 0.15), rgba(201, 168, 76, 0.05));
		border-color: var(--gold, #c9a84c);
		color: var(--gold, #c9a84c);
		box-shadow: 0 0 15px rgba(201, 168, 76, 0.2);
		font-weight: 600;
	}
	.mood-emoji {
		font-size: 1.15rem;
		transition: transform 0.2s ease;
	}
	.mood-chip:hover .mood-emoji {
		transform: scale(1.2) rotate(5deg);
	}
	.mood-label {
		text-transform: capitalize;
	}

	/* ── Grids ── */
	.movie-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
		gap: 12px;
		margin-top: 14px;
	}
	.movie-row {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
		gap: 12px;
	}

	/* ── States ── */
	.error-state {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		background: rgba(224, 82, 82, 0.08);
		border: 1px solid rgba(224, 82, 82, 0.2);
		border-radius: var(--radius-md);
		padding: 1rem 1.25rem;
		margin-top: 0.75rem;
	}
	.error-icon {
		font-size: 1.25rem;
		color: #e05252;
		flex-shrink: 0;
	}
	.error-title {
		font-size: 0.9rem;
		color: #ff8080;
		font-weight: 500;
		margin-bottom: 2px;
	}
	.error-msg {
		font-size: 0.8rem;
		color: var(--muted);
		margin-bottom: 0.5rem;
	}

	.empty-state {
		text-align: center;
		padding: 3rem 1rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 10px;
	}
	.empty-icon {
		font-size: 2.5rem;
		color: var(--subtle);
	}
	.empty-state p {
		font-size: 0.9rem;
		color: var(--muted);
	}
	.empty-state strong {
		color: var(--cream);
	}

	.section-empty {
		font-size: 0.825rem;
		color: var(--subtle);
		padding: 0.75rem 0;
	}

	/* ── Buttons ── */
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

	.btn-ghost-sm {
		padding: 5px 12px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--noir-border);
		background: transparent;
		color: var(--muted);
		font-size: 0.75rem;
		cursor: pointer;
		white-space: nowrap;
	}
	.btn-ghost-sm:hover:not(:disabled) {
		border-color: var(--gold-dim);
		color: var(--gold);
	}
	.btn-ghost-sm:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.btn-gold-sm {
		padding: 6px 16px;
		border-radius: var(--radius-sm);
		background: var(--gold);
		border: none;
		color: #09090e;
		font-size: 0.8rem;
		font-weight: 500;
		cursor: pointer;
		margin-top: 0.25rem;
	}
	.btn-gold-sm:hover {
		opacity: 0.85;
	}

	/* ── Footer ── */
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

	/* ── Responsive ── */
	@media (max-width: 640px) {
		.movie-grid,
		.movie-row {
			grid-template-columns: repeat(2, 1fr);
			gap: 8px;
		}
		.brand-tag {
			display: none;
		}
		.content {
			padding: 0 1rem 2rem;
		}
		.navbar {
			padding: 0.75rem 1rem;
		}
	}
	@media (min-width: 1024px) {
		.movie-grid {
			grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		}
		.movie-row {
			grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		}
	}
</style>