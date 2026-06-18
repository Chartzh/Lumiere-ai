<script>
  /**
   * routes/register/+page.svelte
   * Halaman Register — nama, email, password.
   * Setelah berhasil → redirect ke /onboarding untuk pilih genre.
   */
  import { goto }      from '$app/navigation';
  import { userStore } from '$lib/stores/user.js';
  import { register }  from '$lib/api.js';

  let name      = $state('');
  let email     = $state('');
  let password  = $state('');
  let confirm   = $state('');
  let loading   = $state(false);
  let error     = $state('');
  let showPass  = $state(false);

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  async function handleRegister(e) {
    if (e) e.preventDefault();
    error = '';
    if (!name.trim())         { error = 'Nama wajib diisi.'; return; }
    if (!emailRegex.test(email.trim())) { error = 'Format email tidak valid (contoh: nama@email.com).'; return; }
    if (password.length < 8)  { error = 'Password minimal 8 karakter.'; return; }
    if (password !== confirm)  { error = 'Password dan konfirmasi tidak cocok.'; return; }

    loading = true;
    try {
      const data = await register({ name: name.trim(), email: email.trim(), password });
      const nameFallback = data.name || data.username || data.display_name || name.trim() || 
        (data.email || email.trim()).split('@')[0].split(/[._-]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
      // Tandai isNewUser = true supaya layout guard arahkan ke /onboarding
      userStore.login({
        id:             data.user_id,
        name:           nameFallback,
        email:          data.email || email.trim(),
        favoriteGenres: [],
        token:          data.access_token,
        isNewUser:      true,
      });
      goto('/onboarding');
    } catch (e) {
      error = e.message ?? 'Gagal mendaftar, coba lagi.';
    } finally {
      loading = false;
    }
  }

  // Indikator kekuatan password
  const strength = $derived(
    password.length === 0 ? 0 :
    password.length < 8   ? 1 :
    /[A-Z]/.test(password) && /[0-9]/.test(password) && /[^A-Za-z0-9]/.test(password) ? 3 : 2
  );
  const strengthLabel = ['', 'Lemah', 'Sedang', 'Kuat'];
  const strengthColor = ['', '#e05252', '#c9a84c', '#52c07a'];
</script>

<div class="auth-page">
  <div class="glow" aria-hidden="true"></div>

  <a href="/" class="brand" tabindex="-1">
    <img src="/logo.webp" alt="Lumiere Logo" width="120" height="120" />
  </a>
  <p class="brand-tag">INTELLIGENT MOVIE DISCOVERY</p>

  <div class="card">
    <h1 class="card-title">Buat akun baru</h1>
    <p class="card-sub">Daftar dan kami akan mempelajari selera filmmu.</p>

    <form onsubmit={handleRegister} novalidate>
      <div class="field">
        <label for="name">Nama tampilan</label>
        <input id="name" type="text" placeholder="Nama kamu"
          bind:value={name}
          autocomplete="name" disabled={loading} />
      </div>

      <div class="field">
        <label for="email">Email</label>
        <input id="email" type="email" placeholder="nama@email.com"
          bind:value={email}
          autocomplete="email" disabled={loading} />
      </div>

      <div class="field">
        <label for="password">Password</label>
        <div class="input-wrap">
          <input id="password" type={showPass ? 'text' : 'password'}
            placeholder="Min. 8 karakter" bind:value={password}
            autocomplete="new-password" disabled={loading} />
          <button class="eye" type="button"
            onclick={() => showPass = !showPass}
            aria-label={showPass ? 'Sembunyikan' : 'Tampilkan'}>
            {showPass ? '🙈' : '👁️'}
          </button>
        </div>
        {#if password.length > 0}
          <div class="strength-row">
            <div class="strength-bars">
              {#each [1,2,3] as s}
                <div class="bar" class:active={strength >= s}
                  style="background: {strength >= s ? strengthColor[strength] : ''}"></div>
              {/each}
            </div>
            <span class="strength-label" style="color:{strengthColor[strength]}">
              {strengthLabel[strength]}
            </span>
          </div>
        {/if}
      </div>

      <div class="field">
        <label for="confirm">Konfirmasi password</label>
        <input id="confirm" type="password" placeholder="Ulangi password"
          bind:value={confirm}
          autocomplete="new-password" disabled={loading}
          class:mismatch={confirm.length > 0 && confirm !== password} />
        {#if confirm.length > 0 && confirm !== password}
          <span class="mismatch-hint">Password tidak cocok</span>
        {/if}
      </div>

      {#if error}
        <div class="error-box" role="alert">⚠ {error}</div>
      {/if}

      <button class="btn-gold" type="submit" disabled={loading}>
        {#if loading}<span class="spin"></span> Mendaftar...{:else}Daftar & Lanjut{/if}
      </button>
    </form>

    <p class="switch">Sudah punya akun? <a href="/login">Masuk</a></p>
  </div>

  <footer>Lumiere © 2026 · PJK-GM074 · Pijak × IBM SkillsBuild<br>
    <span>Lita · Rajif · Arghi · Zaky</span></footer>
</div>

<style>
.auth-page {
  min-height: 100vh; background: var(--noir-bg);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 2rem 1rem; position: relative; overflow: hidden;
}
.glow {
  position: absolute; top: -160px; left: 50%; transform: translateX(-50%);
  width: 600px; height: 500px;
  background: radial-gradient(ellipse, rgba(201,168,76,.07) 0%, transparent 68%);
  pointer-events: none;
}
.brand { display: flex; align-items: center; gap: 6px; text-decoration: none; margin-bottom: 2px; }
.brand-star { color: var(--gold); font-size: 1rem; }
.brand-name { color: var(--cream); font-size: 1.15rem; font-weight: 500; }
.brand-tag  { font-size: .65rem; color: var(--subtle); letter-spacing: .1em; margin-bottom: 1.75rem; }

.card {
  width: 100%; max-width: 400px;
  background: var(--noir-card); border: 1px solid var(--noir-border);
  border-radius: var(--radius-lg); padding: 2rem;
  box-shadow: 0 24px 64px rgba(0,0,0,.5);
}
.card-title { font-size: 1.3rem; font-weight: 500; color: var(--cream); margin-bottom: 4px; }
.card-sub   { font-size: .825rem; color: var(--muted); margin-bottom: 1.5rem; line-height: 1.5; }

.field { margin-bottom: 1rem; }
.field label {
  display: block; font-size: .75rem; font-weight: 500;
  color: var(--muted); margin-bottom: 6px; letter-spacing: .04em;
}
.field input, .input-wrap input {
  width: 100%; padding: 10px 14px;
  background: var(--noir-surface); border: 1px solid var(--noir-border);
  border-radius: var(--radius-sm); color: var(--cream); font-size: .9rem; outline: none;
}
.field input:focus, .input-wrap input:focus { border-color: var(--gold); }
.field input::placeholder { color: var(--subtle); }
.field input:disabled { opacity: .45; cursor: not-allowed; }
.field input.mismatch { border-color: #e05252; }
.mismatch-hint { font-size: .72rem; color: #e05252; margin-top: 4px; display: block; }

.input-wrap { position: relative; }
.input-wrap input { padding-right: 44px; }
.eye {
  position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
  background: none; border: none; cursor: pointer; font-size: .9rem; opacity: .45; padding: 0;
}
.eye:hover { opacity: 1; }

.strength-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.strength-bars { display: flex; gap: 4px; }
.bar { width: 32px; height: 3px; border-radius: 2px; background: var(--noir-soft); transition: background .3s; }
.bar.active { background: var(--gold); }
.strength-label { font-size: .7rem; font-weight: 500; }

.error-box {
  background: rgba(224,82,82,.1); border: 1px solid rgba(224,82,82,.25);
  border-radius: var(--radius-sm); padding: 8px 12px;
  font-size: .8rem; color: #ff8080; margin-bottom: 1rem;
}

.btn-gold {
  width: 100%; padding: 11px; margin-bottom: 1.25rem;
  background: var(--gold); border: none; border-radius: var(--radius-sm);
  color: #09090e; font-size: .9rem; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.btn-gold:hover:not(:disabled)  { opacity: .85; }
.btn-gold:active:not(:disabled) { transform: scale(.98); }
.btn-gold:disabled { opacity: .4; cursor: not-allowed; }

.spin {
  width: 13px; height: 13px;
  border: 2px solid rgba(9,9,14,.3); border-top-color: #09090e;
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.switch { font-size: .825rem; color: var(--muted); text-align: center; }
.switch a { color: var(--gold); text-decoration: none; font-weight: 500; }
.switch a:hover { text-decoration: underline; }

footer { margin-top: 1.5rem; font-size: .7rem; color: var(--subtle); text-align: center; line-height: 1.7; }
footer span { color: #444455; }

@media (max-width: 480px) { .card { padding: 1.5rem 1.25rem; } }
</style>
