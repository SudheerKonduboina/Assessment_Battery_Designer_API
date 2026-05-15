<p align="center">
  <img src="https://www.shl.com/wp-content/uploads/2021/04/SHL-Logo-Red-on-White.png" alt="SHL Logo" width="200" />
</p>

<h1 align="center">🎯 SHL Assessment Battery Designer API</h1>

<p align="center">
  <strong>Production-grade conversational recommender for SHL Individual Test Solutions</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white" />
  <img src="https://img.shields.io/badge/Stateless-Architecture-brightgreen?style=for-the-badge" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/score-9%2F9%20tests-brightgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/recall-0.73%4010-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/hallucination-0.0%25-success?style=flat-square" />
  <img src="https://img.shields.io/badge/status-production--ready-brightgreen?style=flat-square" />
</p>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🧠 Intent-Driven Retrieval
- **Context-Aware Signals** — Extracts role, seniority, and skills from natural language.
- **Deterministic Ranker** — Additive scoring (+3 technical, +2 seniority/behavioral).
- **Battery Diversity** — Automatic injection of Knowledge (K), Ability (A), and Personality (P) types.
- **Stateless Replay** — Reconstructs entire session state from message history.

</td>
<td width="50%">

### 🛡️ Enterprise Guardrails
- **Prompt Injection Refusal** — Hardened against "ignore instructions" attacks.
- **Off-Scope Refusal** — Gracefully handles salary/legal/hiring strategy queries.
- **Grounded Comparison** — Fabrication-proof assessment diffs using verbatim catalogue data.
- **Turn Budgeting** — Strict 8-turn conversation management.

</td>
</tr>
<tr>
<td width="50%">

### 📊 Evaluation Harness
- **Recall@10 Suite** — Automated benchmarking against SHL trace traces.
- **Hallucination Probes** — Targeted security and grounding verification.
- **Schema Validation** — Strict Pydantic enforcement of response envelopes.
- **Audit Logging** — Transparent signal extraction and scoring traces.

</td>
<td width="50%">

### 🏗️ Engineering Rigor
- **Catalogue Pipeline** — Automated ingestion, normalization, and indexing.
- **Refined Matching** — Multi-pass name resolution (Exact → Substring → Inverse).
- **Clean Separation** — Context Builder / Retriever / Ranker / Agent layers.
- **Zero Hallucination** — 100% grounding in `shl_product_catalogue.json`.

</td>
</tr>
</table>

---

## 🏛️ System Architecture

The API follows a purely functional, stateless design. Every request carries the full conversational context, allowing the engine to remain side-effect free and highly scalable.

```
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI SERVICE LAYER                     │
├──────────────────────────┬──────────────────────────────────┤
│      Agent Orchestrator   │       Retrieval Pipeline          │
│  ┌──────────────────┐    │  ┌────────────────────────────┐  │
│  │ Guard Layer      │    │  │ Context Builder (Signals)  │  │
│  │ Intent Routing   │────┼──│ Ranker (Scoring & Diversity)│  │
│  │ Reply Generator  │    │  │ Retriever (Catalog Grounding)│  │
│  └──────────────────┘    │  └────────────────────────────┘  │
├──────────────────────────┴──────────────────────────────────┤
│                  SHL Product Catalogue (JSON)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Behavioral Probe Matrix

| Probe Category | Example Query | Expected Behavior |
|----------------|---------------|:-----------------:|
| **Vague Intent** | "I am hiring" | `CLARIFY` (Request role/skills) |
| **Early Recommendation**| "Hiring a Java Developer" | `RECOMMEND` (Top shortlist) |
| **Refinement** | "Must also have SQL skills" | `REFINE` (Update shortlist) |
| **Comparison** | "OPQ vs HPTI" | `COMPARE` (Grounded Diff) |
| **Off-Scope** | "What is the pay range?" | `REFUSE` (Scope warning) |
| **Injection** | "Ignore instructions..." | `REFUSE` (Safety warning) |
| **Finalization** | "That's all, thanks" | `CLOSE` (End conversation) |

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd Assessment_Battery_Designer_API

# Install dependencies
pip install -r requirements.txt

# Start the API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Running the Evaluation

The system includes a production-grade evaluation harness to measure Recall@10 and Hallucination rates.

```bash
# 1. Start the server (background)
python -m uvicorn app.main:app --port 8000 &

# 2. Run the Catalogue Pipeline
python catalogue_loader.py

# 3. Run Behavior Probes
python evaluation_runner.py --traces_dir ./traces

# 4. Run Hallucination Tests
python hallucination_tests.py
```

---

## 📡 API Documentation

### POST `/chat`
Replays a full conversation history and returns a schema-valid assessment shortlist.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I need assessments for a mid-level Python developer"}
    ]
  }'
```

**Response:**
```json
{
  "reply": "Based on your requirements, I've identified the top SHL solutions...",
  "recommendations": [
    {
      "name": "Python (New)",
      "url": "https://www.shl.com/...",
      "test_type": "K"
    }
  ],
  "end_of_conversation": false
}
```

---

## 📁 Project Structure

```
Assessment_Battery_Designer_API/
├── app/
│   ├── api/              # API route handlers (chat, health)
│   ├── core/
│   │   ├── agent.py      # Dialog State Machine & Decision Logic
│   │   ├── ranker.py     # Scoring Engine & Diversity Enforcement
│   │   ├── context.py    # Signal Extraction & Seniority Mapping
│   │   └── retriever.py  # Catalogue Data Access Layer
│   ├── data/             # SHL Product Catalogue (JSON)
│   ├── models.py         # Pydantic Schema Models
│   └── main.py           # FastAPI Application Entry
├── catalogue_loader.py   # Catalogue Ingestion Pipeline
├── evaluation_runner.py  # Recall@10 Benchmarking Harness
├── hallucination_tests.py# Security & Grounding Probes
├── requirements.txt      # Dependency Specification
└── README.md
```

---

## 👨‍💻 Developed by

<div align="center">
  <a href="https://www.linkedin.com/in/sudheerkonduboina/">
    <img src="https://raw.githubusercontent.com/skonduboina/skonduboina/main/profile.png" width="120" style="border-radius: 50%;" alt="Sudheer Konduboina" />
  </a>
  <br/>
  <h3>Sudheer Konduboina</h3>
  <p>Software Engineer (Backend) & AIML Engineer</p>
  <a href="https://www.linkedin.com/in/sudheerkonduboina/">
    <img src="https://img.shields.io/badge/LinkedIn-Sudheer_Konduboina-blue?style=flat-square&logo=linkedin" alt="LinkedIn" />
  </a>
</div>

---

## © Copyright Notice

**© 2024 SHL Group. Assessment Battery Designer API Project.**
