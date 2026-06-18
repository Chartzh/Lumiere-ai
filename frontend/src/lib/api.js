/**
 * lib/api.js
 * ─────────────────────────────────────────────────────────────────────
 * Semua komunikasi ke backend FastAPI terpusat di sini.
 * Import fungsi yang dibutuhkan di setiap komponen/halaman.
 *
 * Semua endpoint yang akan dipakai frontend:
 *   POST /api/v1/auth/register   — daftar akun baru
 *   POST /api/v1/auth/login      — login, dapat JWT
 *   POST /api/v1/recommend       — rekomendasi personal (butuh token)
 *   GET  /api/v1/movies/popular  — film populer (jumlah rating)
 *   POST /api/v1/events/click    — catat klik film (kebiasaan user)
 *   POST /api/v1/events/rating   — catat rating film
 */


export const API_BASE = 'https://lumiere-api-32400975992.asia-southeast2.run.app';

// ── Helper request ──────────────────────────────────────────────────────────

export async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    signal: AbortSignal.timeout(10000),
    ...(body ? { body: JSON.stringify(body) } : {})
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return data;
}

// ── Auth ────────────────────────────────────────────────────────────────────

/**
 * Daftar akun baru.
 * @param {{ name, email, password }} payload
 * @returns {{ user_id, name, email, access_token, is_new_user }}
 */
export function register(payload) {
  return request('/api/v1/auth/register', { method: 'POST', body: payload });
}

/**
 * Login dengan email + password.
 * @param {{ email, password }} payload
 * @returns {{ user_id, name, email, favorite_genres, access_token }}
 */
export function login(payload) {
  return request('/api/v1/auth/login', { method: 'POST', body: payload });
}

// ── Rekomendasi ─────────────────────────────────────────────────────────────

/**
 * Ambil rekomendasi personal untuk user yang login.
 * Jika user baru (belum punya history), backend pakai genre dari onboarding.
 * @param {{ user_id, top_k? }} payload
 * @param {string} token
 */
export function fetchRecommendations(payload, token) {
  const { top_k, ...body } = payload;
  const url = top_k ? `/api/v1/recommend?top_k=${top_k}` : '/api/v1/recommend';
  return request(url, { method: 'POST', body, token });
}

/**
 * Film populer berdasarkan jumlah rating di MovieLens + klik/view di sistem.
 * @param {{ limit? }} params
 */
export function fetchPopular(params = {}) {
  const top_k = params.limit ?? 10;
  return request(`/api/v1/recommend/trending?top_k=${top_k}`);
}

/**
 * Film di luar zona nyaman user — Serendipity via MMR.
 * @param {number} user_id
 * @param {string} token
 */
export function fetchSerendipity(user_id, token) {
  return request(`/api/v1/recommend/serendipity/${user_id}?top_k=12`, { token });
}

// ── Event tracking (kebiasaan user) ─────────────────────────────────────────

/**
 * Catat saat user mengklik / membuka detail film.
 * @param {{ movie_id }} payload
 * @param {string} token
 */
export function trackClick(payload, token) {
  return request('/api/v1/events/click', { method: 'POST', body: payload, token }).catch(() => {});
}

/**
 * Catat rating yang diberikan user terhadap film.
 * @param {{ movie_id, rating }} payload  — rating 1–5
 * @param {string} token
 */
export function trackRating(payload, token) {
  return request('/api/v1/events/rating', { method: 'POST', body: payload, token }).catch(() => {});
}
