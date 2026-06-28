# 🎬 Lumiere — Intelligent Movie Discovery

> An AI-powered movie recommendation system that doesn't just tell you *what* to watch, but **why** — combining personalization, diversity, and transparency.
>
> **Capstone Project `PJK-GM074`** · Pijak by Dicoding × IBM SkillsBuild · Theme: *AI for Smart Recommendation Systems*

<p align="center">
  <a href="#">🌐 Live Demo</a> ·
  <a href="#">🎥 Demo Video</a> ·
  <a href="#-api-reference">📡 API Reference</a> ·
  <a href="#-how-to-replicate-locally">⚙️ Replicate Locally</a>
</p>

---

## 📖 Overview

Choosing a film today is harder than watching one. Endless catalogs cause **choice overload**, most recommenders are opaque **black boxes** ("recommended for you" — but why?), and new users face the **cold-start** problem.

**Lumiere** solves all three:

| Problem | Lumiere's Solution |
|---|---|
| 🤯 Choice Overload | Personalized **Neural Collaborative Filtering (NCF)** trained from scratch |
| 🔍 Black Box | **Explainable AI (XAI)** — every recommendation states *why* it fits you |
| ❄️ Cold Start | Genre + film **onboarding** for brand-new users |
| 🔁 Filter Bubble | **MMR re-ranking** ("Beyond Your Comfort Zone") for serendipitous diversity |

---

## ✨ Key Features

- **Personalized recommendations** via a NeuMF (GMF + MLP) deep learning model.
- **Explainable AI** — each card explains the primary factor behind the match.
- **Mood-based discovery** — recommendations adapt to your current mood.
- **Serendipity engine** — surfaces hidden gems outside your usual taste (MMR).
- **Cold-start onboarding** — relevant picks from your very first session.
- **Taste DNA profile** — a visual summary of your cinematic preferences.
- **JWT authentication** — register, login, and personalized sessions.

---

## 🏗️ Architecture

```
┌─────────────┐     HTTPS/JSON      ┌──────────────────┐     SQL      ┌──────────────┐
│  Frontend   │ ──────────────────> │     Backend      │ ──────────> │   Supabase   │
│  SvelteKit  │ <────────────────── │  FastAPI (REST)  │ <────────── │  PostgreSQL  │
│  (Vercel)   │                     │  (Cloud Run)     │             └──────────────┘
└─────────────┘                     │       │          │
                                    │       ▼          │
                                    │  NCF Model (.h5) │  <── downloaded at startup
                                    │  TensorFlow/Keras│      from Supabase Storage
                                    └──────────────────┘
```

The frontend **never** touches the database directly — all CRUD flows through the FastAPI backend, keeping database credentials secure on the server.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | SvelteKit 2, Svelte 5 (Runes), TailwindCSS 4, Vite 8 |
| **Backend** | FastAPI, Uvicorn, Python 3.10, Pydantic, SQLAlchemy |
| **Machine Learning** | TensorFlow / Keras, NumPy, Pandas, Scikit-learn, TMDB API |
| **Database & Storage** | Supabase (PostgreSQL + Object Storage) |
| **Infrastructure** | Docker, Google Cloud Run, Vercel, GitHub |

---

## 📁 Repository Structure

```
Lumiere-ai/
├── frontend/          # SvelteKit web app (deployed to Vercel)
│   ├── src/
│   │   ├── routes/    # Pages: home, login, register, onboarding, movie/[id], profile, favorites
│   │   └── lib/       # api.js, components, stores
│   ├── static/
│   ├── .env.example
│   └── package.json
├── backend/           # FastAPI REST API (deployed to Cloud Run)
│   ├── app/
│   │   ├── main.py            # App entrypoint + startup (model download, catalog warm-up)
│   │   ├── api/endpoints/     # auth, movies, onboarding, profile, mood, interactions
│   │   ├── core/              # config, recommender logic (NCF, MMR, exploration)
│   │   └── db/                # SQLAlchemy session, models, migrations
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
└── ml-model/          # Model training & experiments
    ├── src/           # architecture.py, dataset.py, train.py
    ├── notebooks/     # Jupyter/Colab exploration (.ipynb)
    └── requirements.txt
```

---

## 🤖 The Model

Lumiere's recommender is a **Neural Collaborative Filtering (NeuMF)** network combining a Generalized Matrix Factorization (GMF) branch and a Multi-Layer Perceptron (MLP) branch, trained **from scratch** (no pre-trained embeddings).

| Detail | Value |
|---|---|
| Dataset | MovieLens 1M (1,000,209 ratings) |
| Train / Test split | 800,167 / 200,042 (80/20, `random_state=42`) |
| Users × Movies | 6,040 × 3,706 |
| Embedding size | 32 |
| MLP head | Dense(64) → Dropout(0.3) → Dense(32) → Dropout(0.2) → Dense(1, sigmoid) |
| Optimizer / Loss | Adam (lr=0.001) / MSE |
| Regularization | L2 (1e-4), EarlyStopping, ReduceLROnPlateau |

## 📦 Model Access

The trained NCF model (`lumiere_ncf.h5`) is hosted on Google Drive.
Access has been granted to `pijak@student.devacademy.id` (Viewer) for review.

- **Download link:** https://drive.google.com/drive/folders/1-OdS4JOwHswj9SZ7zyxqZ7-zdvU8GoRQ?usp=sharing
- **How to load:** download the `.h5` file and load it via
  `tensorflow.keras.models.load_model("lumiere_ncf.h5")`, or let the backend
  fetch it automatically at startup (see `backend/app/main.py`).

Model specs: NeuMF (GMF + MLP), input = (user_id, movie_id), output = predicted
rating (sigmoid, scaled 1–5). Trained on MovieLens 1M.

### 📊 Results

| Metric | Score |
|---|---|
| **Test RMSE** (scale 1–5) | **0.8776** |
| Test MSE (normalized loss) | 0.0498 |

> On a 1–5 rating scale, the model's predictions are off by **less than one star** on average — strong baseline accuracy for a from-scratch NCF.

---

## ⚙️ How to Replicate Locally

### Prerequisites

- **Python 3.10**
- **Node.js 18+** and npm
- A **Supabase** project (PostgreSQL database + Storage bucket)
- A **TMDB API key** ([themoviedb.org](https://www.themoviedb.org/) → free account → API)
- (Optional) **Docker** for containerized backend

---

### 1️⃣ Clone the repository

```bash
git clone https://github.com/<your-username>/Lumiere-ai.git
cd Lumiere-ai
```

---

### 2️⃣ Train the model (optional — a pre-trained `.h5` is hosted on Supabase Storage)

```bash
cd ml-model
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Place the MovieLens 1M dataset in ./data, then train:
python src/train.py
```

This produces `lumiere_ncf.h5`. Upload it to a **public** Supabase Storage bucket (e.g. `models/lumiere_ncf.h5`) so the backend can download it at startup.

> ⚠️ **Version note:** train and serve with **matching TensorFlow versions**. The backend pins `tensorflow-cpu==2.15.0`. If your `.h5` was trained on a newer version and fails to load, rebuild the architecture and use `load_weights()` instead of `load_model()`.

---

### 3️⃣ Run the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy the provided template and fill in your values:

```bash
cp .env.example .env
```

`backend/.env.example`:

```env
TMDB_API_KEY=ISI_TMDB_KEY
TMDB_ACCESS_TOKEN=ISI_TMDB_TOKEN
DATABASE_URL=ISI_DATABASE_URL
```

- **`DATABASE_URL`** — your PostgreSQL connection string. Use the Supabase **Session Pooler** URL for IPv4 compatibility:<br>`postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
- **`TMDB_API_KEY`** / **`TMDB_ACCESS_TOKEN`** — from your TMDB account (for posters & metadata).

The model URL is read in `app/main.py` and downloaded to `/tmp/lumiere_ncf.h5` on startup — update it to point to your own Supabase Storage object if needed.

Start the server:

```bash
uvicorn app.main:app --reload --port 8080
```

Visit **http://localhost:8080/docs** for the interactive Swagger API documentation.

> On startup the backend (1) ensures the DB schema, (2) warms the movie catalog cache from Supabase, and (3) downloads + loads the NCF model. Watch the logs — if you see `Mengaktifkan MOCK_MODE`, the model failed to load and recommendations will be degraded.

---

### 4️⃣ Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
```

`frontend/.env.example`:

```env
PUBLIC_API_BASE=ISI_API_BACKEND
```

Set `PUBLIC_API_BASE` to your backend URL (e.g. `http://localhost:8080` for local development, or your Cloud Run URL).

```bash
npm run dev
```

Open **http://localhost:5173** in your browser.

> In SvelteKit, browser-exposed environment variables **must** be prefixed with `PUBLIC_`.

---

## 🐳 Run the backend with Docker

```bash
cd backend
docker build -t lumiere-backend .
docker run -p 8080:8080 -e PORT=8080 --env-file .env lumiere-backend
```

---

## ☁️ Deployment

### Backend → Google Cloud Run

```bash
gcloud config set project <your-gcp-project>
gcloud builds submit --tag gcr.io/<your-gcp-project>/lumiere-backend
gcloud run deploy lumiere-api \
  --image gcr.io/<your-gcp-project>/lumiere-backend \
  --region asia-southeast2 --port 8080 \
  --memory 2Gi --cpu 2 --timeout 600 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=...,TMDB_API_KEY=...,TMDB_ACCESS_TOKEN=..."
```

### Frontend → Vercel

1. Import the GitHub repo into Vercel.
2. Set **Root Directory** to `frontend` (this is a monorepo).
3. Framework preset: **SvelteKit** (auto-detected; uses `adapter-auto`).
4. Add `PUBLIC_API_BASE` = your Cloud Run URL under **Settings → Environment Variables**.
5. Deploy 🚀

---

## 📡 API Reference

All endpoints are prefixed with `/api/v1`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new account |
| `POST` | `/auth/login` | Login, returns JWT |
| `GET` | `/auth/me/{user_id}` | Get current user |
| `POST` | `/onboarding` | Submit cold-start preferences (≥3 genres + 5 films) |
| `POST` | `/recommend` | Personalized recommendations (NCF) |
| `GET` | `/recommend/foryou/{user_id}` | Personalized feed |
| `GET` | `/recommend/trending` | Popular films |
| `GET` | `/recommend/genre/{genre}` | Recommendations by genre |
| `GET` | `/recommend/serendipity/{user_id}` | "Beyond your comfort zone" (MMR) |
| `GET` | `/recommend/mood/{mood}` | Mood-based recommendations |
| `GET` | `/moods` | List available moods |
| `GET` | `/movie/{movie_id}` | Movie detail |
| `POST` | `/interactions` | Create interaction (favorite / rating / review) |
| `DELETE` | `/interactions/{interaction_id}` | Remove an interaction |
| `GET` | `/users/{user_id}/interactions` | List a user's interactions |
| `GET` | `/profile/{user_id}` | Taste profile |
| `POST` | `/profile/{user_id}/refresh` | Recompute taste profile |
| `GET` | `/profile/{user_id}/evolution` | Taste evolution over time |

---

## 🗺️ Roadmap

**Short term**
- LLM-generated natural-language explanations (XAI)
- Multi-dimensional evaluation: Intra-list Diversity, Catalog Coverage, Novelty
- Automated retraining pipeline + monitoring / A-B testing

**Long term**
- *Lumiere Agent* — conversational recommendations
- Mood detection from camera / wearables
- Group "Taste DNA" blending (date-night mode)
- Cross-domain recommendations (music & books)
- Federated learning for privacy
- B2B white-label offering

---

## 👥 Team

| Name | Role |
|---|---|
| **Muhammad Rajif Raditya** | Machine Learning Engineering & Cloud Infrastructure |
| **Muhamad Arghi Trianda Vianuri** | Data Engineering & Backend |
| **Herlita** | Frontend |
| **Zaky Ramadhan** | Frontend |

---

## 📜 License & Acknowledgements

Developed as a Capstone Project (`PJK-GM074`) for **Pijak by Dicoding** in collaboration with **IBM SkillsBuild**.

Dataset: [MovieLens 1M](https://grouplens.org/datasets/movielens/1m/) (GroupLens). Movie metadata & posters: [TMDB](https://www.themoviedb.org/). This product uses the TMDB API but is not endorsed or certified by TMDB.
