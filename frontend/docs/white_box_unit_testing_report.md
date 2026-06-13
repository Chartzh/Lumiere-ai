# Laporan Analisis White Box Unit Testing Komprehensif
### Proyek: Lumiere-ai Frontend (Intelligent Movie Discovery)
**Peran:** Senior QA Engineer  
**Tanggal:** 13 Juni 2026  
**Status:** DRAFT UNTUK IMPLEMENTASI  

---

## 1. Pendahuluan & Ringkasan Eksekutif

Sebagai Senior QA Engineer, laporan ini disusun setelah melakukan analisis statis mendalam (*static analysis*) terhadap seluruh basis kode di direktori `src` pada repositori `Lumiere-ai/frontend`. Aplikasi ini dikembangkan menggunakan **Svelte 5** dengan pemanfaatan Svelte Runes (`$state`, `$derived`, `$effect`, `$props`) dan **Svelte Stores** untuk mengelola session autentikasi pengguna secara reaktif.

Tujuan utama dari pengujian *White Box* ini adalah memastikan seluruh alur logika internal, percabangan keputusan (*decision branches*), penanganan error (*exception handling*), dan pembaruan state reaktif berjalan dengan benar dan aman dari kegagalan senyap (*silent failures*).

---

## 2. Pemetaan Unit Kode Layak Uji (Testable Units Mapping)

Berikut adalah pemetaan seluruh unit kode yang diidentifikasi memiliki logika bisnis, manipulasi data, pembaruan state, atau efek samping jaringan (*network side-effects*) yang wajib dicakup dalam pengujian unit:

### A. Utilitas Jaringan & Helper API (`src/lib/api.js`)
File ini memusatkan seluruh komunikasi HTTP ke backend FastAPI. Semua fungsi di sini bergantung pada helper `request()`.

| Nama Unit (Fungsi) | Tipe | Deskripsi | Aspek Kritis yang Diuji |
| :--- | :--- | :--- | :--- |
| `request(path, options)` | Async Helper | Wrapper `fetch` dengan pengaturan header auth dan timeout. | Penanganan HTTP error, penanganan JSON parsing error, penyematan header `Authorization`. |
| `register(payload)` | Wrapper Function | Mengirim payload registrasi ke `/api/v1/auth/register`. | Pengiriman metode `POST` dan parameter body yang sesuai. |
| `login(payload)` | Wrapper Function | Mengirim payload login ke `/api/v1/auth/login`. | Pengiriman metode `POST` dan parameter body yang sesuai. |
| `fetchRecommendations` | Wrapper Function | Mengambil rekomendasi NCF di `/api/v1/recommend`. | Penyematan JWT token dan format payload `user_id` + `top_k`. |
| `fetchPopular(params)` | Wrapper Function | Mengambil film populer terpopuler. | Transformasi objek parameter ke *query string* (`URLSearchParams`). |
| `fetchTrending(params)` | Wrapper Function | Mengambil film terbaru. | Transformasi objek parameter ke *query string* (`URLSearchParams`). |
| `trackClick(payload, token)` | Event Tracker | Mengirim sinyal klik film ke `/api/v1/events/click`. | Penanganan *silent error* (`.catch(() => {})`) agar kegagalan jaringan tidak memblokir UI. |
| `trackRating(payload, token)` | Event Tracker | Mengirim rating film (1–5) ke `/api/v1/events/rating`. | Penanganan *silent error* dan kesesuaian payload rating. |

### B. State Autentikasi & Svelte Stores (`src/lib/stores/user.js`)
Mengelola data sesi lokal (`localStorage`) dan mengekspos state reaktif ke seluruh aplikasi.

| Nama Unit (Store / Derived) | Tipe | Deskripsi | Aspek Kritis yang Diuji |
| :--- | :--- | :--- | :--- |
| `userStore` | Writable Store | Menyimpan objek profil user yang terautentikasi. | Inisialisasi awal dari `localStorage`, pembaruan data via `login()`, penghapusan via `logout()`, dan modifikasi parsial via `patch()`. |
| `isLoggedIn` | Derived Store | Memantau keberadaan JWT token di dalam `userStore`. | Menghasilkan nilai boolean reaktif (`true` jika token ada, `false` jika sebaliknya). |
| `needsOnboarding` | Derived Store | Memantau apakah user baru perlu masuk ke fase onboarding. | Menghasilkan boolean reaktif berdasarkan flag `isNewUser === true`. |

### C. Komponen UI & Svelte 5 Runes (`src/lib/components/`)
Komponen-komponen ini memanfaatkan dekorator reaktif Svelte 5 untuk sinkronisasi antarmuka.

*   **`MovieCard.svelte`**
    *   `$props()`: Properti input `movie_id`, `title`, `confidence` (alias `confidence_score`), `poster_url`, dan `genre`.
    *   `$derived(matchPercent)`: Menghitung persentase kecocokan rekomendasi AI (berkisar antara `0%` hingga `100%`).
    *   `$derived(ringColor)`: Logika multi-kondisi penentuan warna sirkular berdasarkan ambang batas (`matchPercent >= 85`, `>= 70`, `>= 50`, `< 50`).
    *   `$state(imgError)` & `$state(imgLoaded)`: Mengontrol transisi skeleton poster dan penggantian gambar rusak (*fallback background*).
    *   `$derived(numericId)`: Melakukan parsing `movie_id` string ke integer dengan fallback `0`.
    *   `$derived(fallbackBg)`: Menghitung warna latar belakang poster konsisten menggunakan modulo (`numericId % fallbackColors.length`).
*   **`GenreFilter.svelte`**
    *   `$props()`: `genres` (array), `activeGenre` (string), dan callback `onSelect`.
    *   Percabangan visual: `active` class binding jika `activeGenre === genre`.
*   **`MovieDetailModal.svelte`**
    *   `$state(movie)`, `$state(loading)`, `$state(error)`: State siklus hidup data detail film.
    *   `$state(isFavorite)`, `$state(rating)`, `$state(reviewText)`: State penampung form interaksi pengguna.
    *   `$effect`: Reaktivitas pengumpulan data detail film dan interaksi lama ketika `isOpen` dan `movieId` berubah.

### D. Logika Bisnis Halaman Utama (`src/routes/+page.svelte`)
*   `enrichMovies(raw)`: Fungsi transformasi data krusial yang menormalisasi representasi genre dari API backend (baik dalam bentuk array maupun string terpisah koma) menjadi array bersih terstandarisasi.
*   `loadPersonal()`, `loadMoodOptions()`, `handleMoodChange()`, `loadPopular()`, `loadTrending()`: Manajemen pemuatan data paralel dengan penanganan error adaptif.

---

## 3. Matriks Skenario Uji Detail & Branch Coverage

Berikut adalah matriks pengujian unit *white box* untuk melacak seluruh kemungkinan percabangan (*if/else, catch block*) guna memastikan cakupan kode maksimal (*high branch coverage*).

| ID Tes | Target Kode | Skenario Pengujian | Input Uji | Alur Percabangan / Branch yang Dilalui | Hasil yang Diharapkan (Expected Output) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-API-01** | `request` (`api.js`) | Happy Path request dengan token | `path = "/api/v1/movies"`, `options = { token: "valid_jwt" }` | `if (token)` dievaluasi `true`. `res.ok` dievaluasi `true`. | Header `Authorization` tersemat, mengembalikan objek data JSON ter-decode. |
| **TC-API-02** | `request` (`api.js`) | Request tanpa menyematkan token | `path = "/api/v1/movies"`, `options = {}` | `if (token)` dievaluasi `false`. | Header `Authorization` tidak dikirim, request berjalan normal. |
| **TC-API-03** | `request` (`api.js`) | Penanganan kegagalan HTTP (Non-2xx) | `path = "/api/v1/error"`, Mock API melempar status `400` dengan detail. | `if (!res.ok)` dievaluasi `true`. `data.detail` ada. | Melempar `Error` dengan pesan dari payload backend (`data.detail`). |
| **TC-API-04** | `request` (`api.js`) | Penanganan kegagalan HTTP tanpa pesan detail | Mock API melempar status `500` tanpa payload JSON valid. | `if (!res.ok)` dievaluasi `true`. `data.detail` is `null`/`undefined`. | Melempar `Error` dengan pesan fallback `"HTTP 500"`. `res.json().catch()` terpanggil. |
| **TC-STORE-01** | `createUserStore` | Inisialisasi awal tanpa data di storage | `localStorage.getItem` mengembalikan `null`. | Ternary `typeof localStorage` dievaluasi `true`, `stored` dievaluasi `null`. | Store diinisialisasi dengan nilai `null`. |
| **TC-STORE-02** | `userStore.login` | Proses penyimpanan sesi login baru | `userData = { id: 99, token: "JWT_TOKEN" }` | Memanggil `set()` dan `localStorage.setItem()`. | State store berubah dan data ter-persis ke `localStorage` dengan format JSON string. |
| **TC-STORE-03** | `userStore.patch` | Pembaruan sebagian data sesi | `partialData = { favoriteGenres: ["Action"] }` | `update()` terpanggil, melakukan penggabungan `{...current, ...partial}`. | State lama dipertahankan, nilai baru ditambahkan, dan `localStorage` diperbarui. |
| **TC-DERIVED-01**| `isLoggedIn` | Pengecekan reaktivitas status login | `userStore` berisi objek dengan `token: "abc"`. | Ekspresi `!!$u?.token` dievaluasi. | Mengembalikan `true`. |
| **TC-DERIVED-02**| `isLoggedIn` | Pengecekan status login jika data kosong | `userStore` bernilai `null` atau tanpa properti `token`. | Ekspresi `!!$u?.token` menangani *optional chaining*. | Mengembalikan `false` (tanpa menyebabkan *crash*). |
| **TC-RUNE-01** | `MovieCard` | Perhitungan match percent dari pecahan desimal | `confidence_score = 0.854` | `$derived(matchPercent)` menghitung `Math.round(0.854 * 100)`. | `matchPercent` bernilai `85`. |
| **TC-RUNE-02** | `MovieCard` | Pembatasan nilai batas atas match percent | `confidence_score = 1.5` | `Math.min(100, Math.max(0, 150))` | `matchPercent` mentok di nilai `100`. |
| **TC-RUNE-03** | `MovieCard` | Penanganan nilai kosong / undefined pada confidence | `confidence_score = null` | `(confidence_score || 0)` mengevaluasi nilai fallback ke `0`. | `matchPercent` bernilai `0`. |
| **TC-RUNE-04** | `MovieCard` | Penentuan warna ring - Sangat Cocok (Gold) | `matchPercent = 85` | `matchPercent >= 85` dievaluasi `true`. | `ringColor` bernilai `"#c9a84c"` (Gold). |
| **TC-RUNE-05** | `MovieCard` | Penentuan warna ring - Cukup Cocok (Blue) | `matchPercent = 65` | `matchPercent >= 85` (false), `>= 70` (false), `>= 50` (true). | `ringColor` bernilai `"#6a9fd8"` (Blue). |
| **TC-RUNE-06** | `MovieCard` | Penanganan parsing numeric ID film gagal | `movie_id = "abc"` | `parseInt("abc") || 0` dievaluasi menjadi `0`. | `numericId` bernilai `0`, `fallbackBg` memilih indeks ke-0. |
| **TC-RUNE-07** | `MovieCard` | Penanganan gambar poster error / rusak | `poster_url` valid tetapi gagal dimuat (memicu `onerror`). | `handleImgError()` dijalankan, mengubah `imgError` menjadi `true`. | Render beralih ke blok `{:else}` menampilkan `.poster-fallback` berlatar belakang `fallbackBg`. |
| **TC-UTIL-01** | `enrichMovies` | Normalisasi film dengan genre bertipe Array | `[{ movie_id: 1, genres: ["Drama", "Sci-Fi"] }]` | `Array.isArray(m.genres)` dievaluasi `true`. | Mengembalikan array genre asli tanpa modifikasi. |
| **TC-UTIL-02** | `enrichMovies` | Normalisasi film dengan genre bertipe String koma | `[{ movie_id: 2, genre: "Action, Thriller, " }]` | `Array.isArray` (false), string dipecah (`.split(',')`), di-trim, dan di-filter. | Properti `genres` ditambahkan dengan isi `["Action", "Thriller"]` (spasi dibersihkan). |
| **TC-UTIL-03** | `enrichMovies` | Normalisasi film tanpa informasi genre sama sekali | `[{ movie_id: 3 }]` | `m.genre ?? m.genres ?? ''` mengevaluasi string kosong `""`. | Properti `genres` ditambahkan berupa array kosong `[]`. |

---

## 4. Strategi Mocking Lokal (Local Mocking Strategy)

Dalam pengujian unit *White Box*, kita harus mengisolasi modul dari ketergantungan luar seperti server API riil atau variabel lingkungan peramban (*browser environment*). Vitest menyediakan utilitas handal untuk melakukan ini secara lokal.

### A. Mocking Utilitas Jaringan `request` (`$lib/api.js`)
Kita perlu menguji modul halaman (seperti `+page.svelte` atau `MovieDetailModal.svelte`) tanpa melakukan panggilan HTTP aktual ke FastAPI.

```javascript
import { vi } from 'vitest';

// 1. Definisikan mock secara global untuk lib/api.js
vi.mock('$lib/api.js', async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    // Kita tiru fungsi request agar mengembalikan data tiruan sesuai path-nya
    request: vi.fn().mockImplementation((path, options = {}) => {
      if (path.includes('/auth/login')) {
        return Promise.resolve({
          user_id: 42,
          name: 'QA Tester',
          email: 'tester@lumiere.com',
          access_token: 'mocked_jwt_token'
        });
      }
      if (path.includes('/movie/101')) {
        return Promise.resolve({
          movie: {
            movie_id: 101,
            title: 'Mocked Movie Title',
            year: 2026,
            poster_url: 'https://placeholder.jpg',
            avg_rating: 4.5,
            genres: ['Sci-Fi', 'Action']
          }
        });
      }
      // Fallback jika endpoint tidak dikenal
      return Promise.reject(new Error('Endpoint mock tidak ditemukan'));
    }),
    
    // Kita juga bisa membungkus wrapper API jika ingin di-mock secara spesifik
    fetchRecommendations: vi.fn().mockResolvedValue({
      recommendations: [{ movie_id: 99, title: 'Inception', genres: ['Sci-Fi'] }]
    })
  };
});
```

### B. Mocking Svelte Auth Stores (`$lib/stores/user.js`)
Svelte Store adalah objek bernilai yang dapat di-subscribe. Dalam pengujian unit, kita perlu menyimulasikan berbagai skenario pengguna: tamu (*guest*), pengguna baru (*new user*), dan pengguna terautentikasi (*logged in*).

```javascript
import { writable } from 'svelte/store';
import { vi } from 'vitest';

// Definisikan state writable penampung data user lokal untuk pengujian
const mockUserStore = writable(null);

vi.mock('$lib/stores/user.js', () => {
  return {
    userStore: {
      subscribe: mockUserStore.subscribe,
      login: vi.fn((data) => mockUserStore.set(data)),
      logout: vi.fn(() => mockUserStore.set(null)),
      patch: vi.fn((partial) => {
        mockUserStore.update((current) => ({ ...current, ...partial }));
      })
    },
    // Mock derived store secara manual agar nilainya reaktif mengikuti mockUserStore
    isLoggedIn: {
      subscribe: (run) => {
        return mockUserStore.subscribe((user) => {
          run(!!user?.token);
        });
      }
    },
    needsOnboarding: {
      subscribe: (run) => {
        return mockUserStore.subscribe((user) => {
          run(user?.isNewUser === true);
        });
      }
    }
  };
});

// Helper untuk menyetel status auth sebelum setiap kasus uji berjalan
function setMockSession(userObj) {
  mockUserStore.set(userObj);
}

function clearMockSession() {
  mockUserStore.set(null);
}
```

### C. Mocking Global `localStorage` & `AbortSignal`
Karena kode pada `src/lib/stores/user.js` langsung mengakses `localStorage` pada tingkat inisialisasi modul, kita harus menyediakan mock API global agar tidak terjadi *runtime error* di lingkungan Node.js/jsdom.

```javascript
import { vi, beforeEach } from 'vitest';

const mockStorage = new Map();

vi.stubGlobal('localStorage', {
  getItem: vi.fn((key) => mockStorage.get(key) || null),
  setItem: vi.fn((key, val) => mockStorage.set(key, String(val))),
  removeItem: vi.fn((key) => mockStorage.delete(key)),
  clear: vi.fn(() => mockStorage.clear()),
});

// Tambahkan pollyfill AbortSignal.timeout jika menggunakan node versi lama di lingkungan CI/CD
if (typeof AbortSignal.timeout !== 'function') {
  AbortSignal.timeout = (ms) => {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), ms);
    return controller.signal;
  };
}
```

---

## 5. Blueprint Cetak Biru Kode Pengujian (Vitest Unit Test Suite)

Cetak biru berikut ditulis dalam Javascript murni menggunakan API Vitest dan memuat unit test untuk menguji fungsi pengolahan data `enrichMovies` serta siklus hidup status autentikasi di dalam `userStore` secara menyeluruh.

```javascript
/**
 * src/test/lumiere_core.test.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Vitest Unit Test Suite untuk menguji fungsi transformasi data 
 * dan pengelolaan state reaktif (store & derived store).
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';

// ── MOCKING LOCAL STORAGE ──────────────────────────────────────────────────
const mockStorage = new Map();
vi.stubGlobal('localStorage', {
  getItem: vi.fn((key) => mockStorage.get(key) || null),
  setItem: vi.fn((key, val) => mockStorage.set(key, String(val))),
  removeItem: vi.fn((key) => mockStorage.delete(key)),
  clear: vi.fn(() => mockStorage.clear()),
});

// ── IMPORT UNIT DIBAWAH PENGUJIAN ──────────────────────────────────────────
// Catatan: Impor dilakukan setelah mock global disematkan
import { userStore, isLoggedIn, needsOnboarding } from '../lib/stores/user.js';

// ── PENGUJIAN FUNGSI TRANSFORMASI DATA: enrichMovies ───────────────────────
// Karena enrichMovies berada di dalam file +page.svelte (komponen), kita salin
// definisinya ke lingkungan pengujian untuk memverifikasi logika murni fungsinya.
function enrichMovies(raw) {
  return raw.map((m) => ({
    ...m,
    genres: Array.isArray(m.genres)
      ? m.genres
      : (m.genre ?? m.genres ?? '')
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
  }));
}

describe('Fungsi Transformasi Data - enrichMovies()', () => {
  
  test('Happy Path: Tetap menggunakan array genre jika sudah dalam format array', () => {
    const rawMovies = [
      { movie_id: '101', title: 'Inception', genres: ['Action', 'Sci-Fi'] }
    ];
    const result = enrichMovies(rawMovies);
    
    expect(result[0].genres).toEqual(['Action', 'Sci-Fi']);
    expect(result[0].title).toBe('Inception');
  });

  test('Normalisasi: Memecah string genre berpemisah koma menjadi array bersih', () => {
    const rawMovies = [
      { movie_id: '102', title: 'Interstellar', genre: 'Sci-Fi, Adventure, Drama' }
    ];
    const result = enrichMovies(rawMovies);
    
    expect(result[0].genres).toEqual(['Sci-Fi', 'Adventure', 'Drama']);
    // Pastikan properti "genres" baru terbentuk tanpa merusak properti "genre" asli
    expect(result[0].genre).toBe('Sci-Fi, Adventure, Drama');
  });

  test('Normalisasi: Mengabaikan nilai kosong, spasi berlebih, dan string kotor', () => {
    const rawMovies = [
      { movie_id: '103', title: 'Tenet', genre: ' Action , , Sci-Fi ' }
    ];
    const result = enrichMovies(rawMovies);
    
    // Nilai kosong dari double koma (", ,") dan spasi harus dihilangkan
    expect(result[0].genres).toEqual(['Action', 'Sci-Fi']);
  });

  test('Edge Case: Menangani parameter kosong / absennya nilai genre', () => {
    const rawMovies = [
      { movie_id: '104', title: 'Film Misterius' } // Tidak ada properti genre atau genres
    ];
    const result = enrichMovies(rawMovies);
    
    expect(result[0].genres).toEqual([]);
  });

  test('Edge Case: Mengembalikan array kosong jika input kosong', () => {
    const result = enrichMovies([]);
    expect(result).toEqual([]);
  });
});

// ── PENGUJIAN SIKLUS HIDUP STATE REAKTIF - userStore ───────────────────────
describe('Siklus Hidup Autentikasi & Reaktivitas Store', () => {
  
  beforeEach(() => {
    mockStorage.clear();
    userStore.logout();
    vi.clearAllMocks();
  });

  test('Inisialisasi Awal: Sesi kosong secara default', () => {
    expect(get(userStore)).toBeNull();
    expect(get(isLoggedIn)).toBe(false);
    expect(get(needsOnboarding)).toBe(false);
  });

  test('Proses Login: Menyimpan data user dan memicu reaktivitas store', () => {
    const fakeUserData = {
      id: 99,
      name: 'Herlita',
      email: 'herlita@lumiere.com',
      favoriteGenres: [],
      token: 'jwt_mock_token_123',
      isNewUser: true
    };

    userStore.login(fakeUserData);

    // Verifikasi pembaruan state reaktif pada store utama
    expect(get(userStore)).toEqual(fakeUserData);
    
    // Verifikasi persistensi ke localStorage
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'lumiere_user',
      JSON.stringify(fakeUserData)
    );

    // Verifikasi reaktivitas derived stores
    expect(get(isLoggedIn)).toBe(true);
    expect(get(needsOnboarding)).toBe(true);
  });

  test('Proses Patch: Memperbarui sebagian state (misal: setelah onboarding selesai)', () => {
    const fakeUserData = {
      id: 99,
      name: 'Herlita',
      email: 'herlita@lumiere.com',
      favoriteGenres: [],
      token: 'jwt_mock_token_123',
      isNewUser: true
    };
    userStore.login(fakeUserData);

    // Lakukan patch pembaruan genre favorit dan status pengguna baru
    userStore.patch({
      favoriteGenres: ['Sci-Fi', 'Action'],
      isNewUser: false
    });

    const updated = get(userStore);
    expect(updated.favoriteGenres).toEqual(['Sci-Fi', 'Action']);
    expect(updated.isNewUser).toBe(false);
    expect(updated.name).toBe('Herlita'); // Data lama tidak boleh hilang

    // Derived store untuk onboarding harus bernilai false sekarang
    expect(get(needsOnboarding)).toBe(false);
    expect(get(isLoggedIn)).toBe(true); // Status login tetap aktif
  });

  test('Proses Logout: Membersihkan store dan penyimpanan lokal', () => {
    const fakeUserData = {
      id: 99,
      name: 'Herlita',
      token: 'jwt_mock_token_123'
    };
    userStore.login(fakeUserData);

    // Lakukan logout
    userStore.logout();

    expect(get(userStore)).toBeNull();
    expect(localStorage.removeItem).toHaveBeenCalledWith('lumiere_user');
    expect(get(isLoggedIn)).toBe(false);
  });
});
