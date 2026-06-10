<script>
  /**
   * routes/+layout.svelte
   * Root layout: import CSS global, pasang route guard.
   * - User belum login      → redirect ke /login
   * - User baru (isNewUser) → redirect ke /onboarding
   * - /login & /register    → bebas diakses tanpa login
   */
  import './layout.css';
  import { page }          from '$app/stores';
  import { goto }          from '$app/navigation';
  import { onMount }       from 'svelte';
  import { isLoggedIn, needsOnboarding } from '$lib/stores/user.js';

  let { children } = $props();

  const PUBLIC = ['/login', '/register'];

  onMount(() => {
    const path = $page.url.pathname;
    const pub  = PUBLIC.some(r => path.startsWith(r));
    if (!pub && !$isLoggedIn)     { goto('/login');      return; }
    if (!pub && $needsOnboarding) { goto('/onboarding'); return; }
  });
</script>

<svelte:head>
  <title>Lumiere — Intelligent Movie Discovery</title>
  <meta name="description" content="Rekomendasi film personal dengan Neural Collaborative Filtering" />
</svelte:head>

{@render children()}
