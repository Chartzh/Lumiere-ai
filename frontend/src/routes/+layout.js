import { redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { isLoggedIn, needsOnboarding } from '$lib/stores/user.js';

// Nonaktifkan SSR agar pemeriksaan localStorage berjalan sinkron di sisi klien
// dan mencegah Flash of Unauthenticated Content (FOUC).
export const ssr = false;

/** @type {import('./$types').LayoutLoad} */
export async function load({ url }) {
  const path = url.pathname;
  const isPublicRoute = ['/login', '/register'].some(r => path.startsWith(r));

  const loggedIn = get(isLoggedIn);
  const onboardingNeeded = get(needsOnboarding);

  // Jika mencoba mengakses rute terproteksi tanpa status login
  if (!isPublicRoute && !loggedIn) {
    throw redirect(307, '/login');
  }

  // Jika sudah login tetapi belum menyelesaikan onboarding
  if (!isPublicRoute && onboardingNeeded && path !== '/onboarding') {
    throw redirect(307, '/onboarding');
  }

  // Jika sudah login dan mencoba mengakses login/register, alihkan ke home
  if (isPublicRoute && loggedIn) {
    throw redirect(307, '/');
  }

  return {};
}
