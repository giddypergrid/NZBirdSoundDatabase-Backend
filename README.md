# NZ Bird Sound Database, backend API

**Live at [nzbirddatabase.com](https://nzbirddatabase.com)** · API at `api.nzbirddatabase.com`

Django REST API behind the site. You upload a bird call, it tells you what bird it is. You type a
description, it finds the closest match. That's the product.

| Repository | What it holds |
|---|---|
| [NZBirdSoundDatabase-AWS](https://github.com/giddypergrid/NZBirdSoundDatabase-AWS) | The deployed version: ECS Fargate, load shedding, 33 live tests. **Read that one for the production story.** |
| [NZBirdSoundDatabase-Prep](https://github.com/giddypergrid/NZBirdSoundDatabase-Prep) | Data preparation and model training |
| [NZBirdSoundDatabase-Frontend](https://github.com/giddypergrid/NZBirdSoundDatabase-Frontend) | The React client |
| this one | The application itself |

### Where to look

| File | Why |
|---|---|
| [`Bird_Sound/classifier.py`](Bird_Sound/classifier.py) | The audio pipeline. Singleton, loaded once, holds both models. |
| [`Bird_Sound/semantic_search.py`](Bird_Sound/semantic_search.py) | Description embeddings and the cosine ranking |
| [`Bird_Sound/views.py`](Bird_Sound/views.py) | Every endpoint, including the path-traversal guard on file serving |
| [`Bird_Sound/key_files.py`](Bird_Sound/key_files.py) | Every artifact path in one place |

---


---

## What this API does

**Reference data.** Birds, audio recordings, images. Standard REST reads.

**File serving.** Audio clips and bird photos, served safely with path traversal protection.

**Audio classification.** POST raw audio, get back an eBird species code and confidence score.  
Under the hood: BirdNET extracts a 1024-dimension audio fingerprint, AutoGluon classifies it.

**Semantic search.** GET a text query like *"loud screech at dawn"*, get back ranked bird matches.  
Under the hood: SentenceTransformers turn the query and all bird descriptions into vectors, then cosine similarity finds the closest ones.

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `classify/?ext=wav` | Upload audio → get eBird code + confidence |
| GET | `search-by-description/?query=...` | Semantic search over bird descriptions |
| GET | `birds/` | List all birds |
| GET | `birds/{eBird}/` | One bird by eBird code |
| GET | `audio/{eBird}/{filename}/` | Serve audio clip |
| GET | `image/{eBird}/{index}/` | Serve bird photo |
| GET | `sounds/bird-label/{eBird}/` | All recordings for a species |
| GET | `sounds/{id}/` | One recording by ID |
| GET | `healthz/` | Liveness check (DB + memory) |

---

## ML Pipeline

Both models are loaded once on first request and held in memory for the lifetime of the process.
If available RAM drops below 1 GB, `/classify/` returns 503 + `Retry-After` rather than crashing.

### Audio Classification

```
Raw audio bytes (.wav / .flac / .mp3 / .ogg / .m4a)
         │
         ▼
  ┌─────────────────┐
  │    BirdNET      │  TFLite neural network trained on bird audio.
  │  (TFLite model) │  Converts the waveform into a 1024-dimensional
  └────────┬────────┘  embedding — a fixed-size acoustic fingerprint.
           │
           │  1024-d vector
           ▼
  ┌─────────────────┐
  │   AutoGluon     │  AutoML framework — benchmarks LightGBM, XGBoost,
  │ (LightGBM core) │  CatBoost, random forests, and neural nets, then
  └────────┬────────┘  builds a weighted ensemble. LightGBM dominated here:
           │           gradient-boosted trees handle high-dimensional tabular
           │           features well, and outperformed the rest on NZ bird data.
           │
           ▼
  { "tui1": 0.94, "bellb1": 0.03, ... }   eBird codes + confidence scores
```

### Semantic Search

```
At startup — runs once, result cached in memory:

  All bird descriptions in DB
         │
         ▼
  SentenceTransformer  →  embedding matrix (N birds × D dimensions)


Per request:

  User query, e.g. "loud screech at dawn"
         │
         ▼
  SentenceTransformer  →  query vector (1 × D)
         │
         ▼
  Cosine similarity against the cached embedding matrix
         │
         ▼
  Ranked bird list, closest semantic match first
  Each result includes a strong_match flag (score above threshold)
```

---

## Data

> Assets (audio, images, embeddings) are not in this repo.  
> Upload them when ready. The seed script picks them up automatically on next container start.

---

## Stack

Django 5.2 · PostgreSQL 16 · BirdNET · AutoGluon · SentenceTransformers  
Gunicorn · Caddy · Docker · Prometheus + Grafana · Sentry

Caddy runs at the host level as a shared reverse proxy across services, so it is not part of this repo's compose stack.
