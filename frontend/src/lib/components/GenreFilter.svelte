<!--
  GenreFilter.svelte — Herlita
  Komponen filter genre: pill buttons untuk memfilter MovieCard di grid.
  Props: genres (list string), activeGenre (string), onSelect (callback).
-->
<script>
  let { genres = [], activeGenre = 'All', onSelect } = $props();
</script>

<div class="genre-filter" role="group" aria-label="Filter by genre">
  {#each ['All', ...genres] as genre}
    <button
      class="genre-pill"
      class:active={activeGenre === genre}
      onclick={() => onSelect(genre)}
      aria-pressed={activeGenre === genre}
    >
      {genre}
    </button>
  {/each}
</div>

<style>
.genre-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 4px 0;
}
.genre-pill {
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid var(--noir-border);
  background: transparent;
  color: var(--muted);
  font-family: var(--font-body);
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.genre-pill:hover {
  border-color: var(--gold-dim);
  color: var(--gold-soft);
}
.genre-pill.active {
  background: var(--gold);
  border-color: var(--gold);
  color: var(--noir);
  font-weight: 500;
}
</style>
