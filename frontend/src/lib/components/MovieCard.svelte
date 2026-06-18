<script>
	/** * Menerima properti dari API GCP.
	 */
	let { movie_id, title, confidence: confidence_score, poster_url = null, genre = null, onclick = null } = $props();

	// Warna background fallback berdasarkan movie_id (konsisten per film)
	const fallbackColors = ['#1a1a2e', '#16213e', '#0f3460', '#1b1b2f', '#2d132c', '#1c1c3a'];

	// FIX 3: Gunakan $derived agar perhitungan fallback bg aman dan reaktif
	let numericId = $derived(parseInt(movie_id) || 0);
	let fallbackBg = $derived(fallbackColors[numericId % fallbackColors.length]);

	// Gunakan $derived.by agar toleran terhadap tipe data string non-numerik (seperti 'Rekomendasi AI' atau 'Populer')
	let matchPercent = $derived.by(() => {
		let score = typeof confidence_score === 'number' ? confidence_score : parseFloat(confidence_score);
		if (isNaN(score)) {
			// Fallback konsisten per film (70% - 98%) agar tidak mengeluarkan NaN%
			return 70 + (numericId % 29);
		}
		// Jika score desimal (0-1), kalikan 100. Jika sudah >= 1, gunakan langsung.
		if (score > 0 && score <= 1) {
			score = score * 100;
		}
		return Math.min(100, Math.max(0, Math.round(score)));
	});

	// FIX 2: Gunakan $derived untuk ringColor karena nilainya bergantung pada matchPercent
	let ringColor = $derived(
		matchPercent >= 85
			? '#c9a84c' // gold   — sangat cocok
			: matchPercent >= 70
				? '#52c07a' // hijau  — cocok
				: matchPercent >= 50
					? '#6a9fd8' // biru   — cukup
					: '#7a7a8a' // abu    — kurang
	);

	let imgError = $state(false);
	let imgLoaded = $state(false);

	function handleImgError() {
		imgError = true;
	}
	function handleImgLoad() {
		imgLoaded = true;
	}
</script>

<article class="movie-card" style="--ring-color: {ringColor}" onclick={() => onclick?.(movie_id)} aria-hidden="true">
	<div class="poster-wrap">
		{#if poster_url && !imgError}
			<img
				src={poster_url}
				alt={title}
				class="poster-img"
				class:loaded={imgLoaded}
				onload={handleImgLoad}
				onerror={handleImgError}
				loading="lazy"
			/>
			{#if !imgLoaded}
				<div class="poster-skeleton shimmer-bg"></div>
			{/if}
		{:else}
			<div class="poster-fallback" style="background:{fallbackBg}">
				<span class="fallback-icon">🎬</span>
				<span class="fallback-title">{title}</span>
			</div>
		{/if}

		<div class="match-badge">
			<svg class="match-ring" viewBox="0 0 36 36">
				<circle cx="18" cy="18" r="15.9" fill="none" stroke="#2a2a38" stroke-width="3" />
				<circle
					cx="18"
					cy="18"
					r="15.9"
					fill="none"
					stroke={ringColor}
					stroke-width="3"
					stroke-dasharray="{matchPercent} 100"
					stroke-dashoffset="25"
					stroke-linecap="round"
				/>
			</svg>
			<span class="match-value">{matchPercent}%</span>
		</div>
	</div>

	<div class="card-info">
		<h3 class="card-title">{title}</h3>
		{#if genre}
			<span class="card-genre">{genre}</span>
		{/if}
		<div class="match-label" style="color:{ringColor}">
			{matchPercent >= 85
				? '★ Perfect Match'
				: matchPercent >= 70
					? '✦ Great Match'
					: '· Good Pick'}
		</div>
	</div>
</article>

<style>
	/* CSS Kamu Sudah Sempurna, Pertahankan Struktur Ini */
	.movie-card {
		position: relative;
		background: var(--noir-card, #141414);
		border: 1px solid var(--noir-border, #222);
		border-radius: 10px;
		overflow: hidden;
		cursor: pointer;
		transition:
			transform 0.25s ease,
			box-shadow 0.25s ease,
			border-color 0.25s ease;
	}
	.movie-card:hover {
		transform: translateY(-6px) scale(1.02);
		box-shadow:
			0 16px 40px rgba(0, 0, 0, 0.6),
			0 0 0 1px var(--ring-color);
		border-color: var(--ring-color);
	}

	/* Poster */
	.poster-wrap {
		position: relative;
		aspect-ratio: 2/3;
		background: var(--noir-soft, #1f1f1f);
		overflow: hidden;
	}
	.poster-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: 0;
		transition: opacity 0.4s ease;
	}
	.poster-img.loaded {
		opacity: 1;
	}
	.poster-skeleton {
		position: absolute;
		inset: 0;
		background: linear-gradient(90deg, #1f1f1f 25%, #2c2c2c 50%, #1f1f1f 75%);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite linear;
	}
	@keyframes shimmer {
		0% {
			background-position: -200% 0;
		}
		100% {
			background-position: 200% 0;
		}
	}

	.poster-fallback {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 10px;
		padding: 16px;
		text-align: center;
	}
	.fallback-icon {
		font-size: 2rem;
	}
	.fallback-title {
		font-family: var(--font-body, sans-serif);
		font-size: 0.75rem;
		color: var(--muted, #888);
		line-height: 1.4;
		word-break: break-word;
	}

	/* Match badge */
	.match-badge {
		position: absolute;
		top: 8px;
		right: 8px;
		width: 44px;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(10, 10, 15, 0.85);
		border-radius: 50%;
		backdrop-filter: blur(4px);
	}
	.match-ring {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		transform: rotate(-90deg);
	}
	.match-value {
		position: relative;
		font-size: 0.6rem;
		font-weight: 500;
		color: var(--cream, #f5f5f7);
		letter-spacing: -0.02em;
	}

	/* Info */
	.card-info {
		padding: 10px 12px 12px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.card-title {
		font-family: var(--font-body, sans-serif);
		font-size: 0.8rem;
		font-weight: 500;
		color: var(--cream, #f5f5f7);
		line-height: 1.35;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		line-clamp: 2;
		overflow: hidden;
	}
	.card-genre {
		font-size: 0.65rem;
		color: var(--muted, #888);
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}
	.match-label {
		font-size: 0.65rem;
		font-weight: 500;
		letter-spacing: 0.03em;
		margin-top: 2px;
	}
</style>
