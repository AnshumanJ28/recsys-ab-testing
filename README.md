# recsys-ab-testing

A production-style recommendation system with a full A/B testing pipeline — from model training and variant assignment to statistical significance testing and a live monitoring dashboard.

---

## Overview

Two recommendation algorithms are tested head-to-head using a rigorous A/B framework:

- **Control** — Collaborative filtering via Alternating Least Squares (ALS)
- **Treatment** — Content-based filtering with FAISS approximate nearest neighbour search

Users are assigned to variants deterministically via MD5 hash, ensuring stable assignment across sessions without a database lookup. Every impression and click is logged to SQLite and exposed through a FastAPI backend consumed by a Streamlit dashboard.

---

## Architecture

```
Synthetic Interaction Data (10k users · 1k items · 500k interactions)
        |
        v
  ┌─────────────┐        ┌──────────────────────┐
  │  ALS Model  │        │  Content-Based Model  │
  │ (implicit)  │        │  (FAISS + embeddings) │
  └──────┬──────┘        └──────────┬────────────┘
         │                          │
         └──────────┬───────────────┘
                    │
             A/B Router
      MD5 hash → control / treatment
                    │
             SQLite Event Logger
          impressions + clicks per variant
                    │
              FastAPI Backend
                    │
          Streamlit Dashboard
```

---

## Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/recommend` | GET | Serve top-N recommendations, auto-log impression |
| `/event` | POST | Log a click event |
| `/experiment/stats` | GET | Live CTR per variant |
| `/experiment/significance` | GET | Run two-proportion z-test on demand |
| `/variant` | GET | Check user's variant without logging |

---

## Statistical Testing

- Two-proportion z-test with pooled standard error
- Absolute lift, relative lift, 95% confidence interval
- Winner declaration at configurable α (default 0.05)
- Minimum sample size calculator via power analysis (default 80% power, 5% MDE)

---

## Stack

| Layer | Tools |
|---|---|
| Models | implicit ALS, FAISS, scikit-learn |
| Tracking | MLflow + DagsHub |
| Serving | FastAPI, Uvicorn |
| Event store | SQLite |
| Dashboard | Streamlit, Altair |
| Experiment | Custom A/B router, z-test, power analysis |
| Deployment | Cloudflare Tunnel (Colab) |

---

## Project Structure

```
recsys-ab-testing/
├── notebooks/
│   └── recsys_ab_testing.ipynb   # end-to-end pipeline
├── dashboard/
│   └── dashboard.py              # Streamlit dashboard
└── experiments/
    └── exp_001.json              # experiment config
```

---

## Results

Experiment `exp_001` — ALS vs Content-Based, 50/50 split, 2000 impressions per variant:

| Variant | Impressions | CTR |
|---|---|---|
| Control (ALS) | 2,000 | 7.50% |
| Treatment (Content-Based) | 2,000 | 9.70% |

Absolute lift: **+2.20%** · Statistically significant at α = 0.05

---

## Running in Colab

1. Open `notebooks/recsys_ab_testing.ipynb` and run all cells
2. FastAPI starts on port 8000
3. Run the tunnel + dashboard cell — Cloudflare exposes both ports publicly
4. Open the Streamlit URL printed in the output
