<!--
  LoadingSkeleton.svelte — Herlita
  Grid skeleton cards yang muncul saat data sedang di-fetch dari backend.
-->
<script>
  let { count = 10 } = $props();
</script>

<div class="skeleton-grid">
  {#each Array(count) as _, i}
    <div class="skeleton-card" style="animation-delay: {i * 0.05}s">
      <div class="skeleton-poster shimmer-bg"></div>
      <div class="skeleton-info">
        <div class="skeleton-line shimmer-bg" style="width:80%"></div>
        <div class="skeleton-line shimmer-bg" style="width:50%"></div>
      </div>
    </div>
  {/each}
</div>

<style>
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}
.skeleton-card {
  border-radius: 10px;
  overflow: hidden;
  background: var(--noir-card);
  border: 1px solid var(--noir-border);
  opacity: 0;
  animation: fadeUp 0.3s ease forwards;
}
.skeleton-poster {
  aspect-ratio: 2/3;
}
.skeleton-info {
  padding: 10px 12px 12px;
  display: flex; flex-direction: column; gap: 8px;
}
.skeleton-line {
  height: 10px;
  border-radius: 4px;
}
</style>
