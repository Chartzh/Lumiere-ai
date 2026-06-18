<script>
  import './layout.css';

  let { children } = $props();
</script>

<svelte:head>
  <title>Lumiere — Intelligent Movie Discovery</title>
  <meta name="description" content="Rekomendasi film personal dengan Neural Collaborative Filtering" />
</svelte:head>

{@render children()}
