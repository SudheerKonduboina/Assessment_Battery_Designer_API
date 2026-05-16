# SHL Conversational Assessment Recommender — Approach Document

## What I Built and Why

The system is a production-hardened FastAPI service that helps hiring managers convert role descriptions into a structured shortlist of relevant SHL assessments. It is stateless, scalable, and designed for fast inference in cloud environments.

I transitioned from a heavier semantic embedding approach to a lightweight TF-IDF based retrieval system using scikit-learn. This change was made to ensure stability and low memory usage on constrained deployments like Render.

The architecture follows a Guard-First design philosophy, where inputs are validated and normalized before entering the retrieval pipeline to ensure consistent output quality.

## How Retrieval Works

The system follows a multi-stage retrieval pipeline:

### 1. TF-IDF Based Retrieval

The SHL catalog (377 assessments) is transformed into a TF-IDF vector space. User queries are vectorized and compared using cosine similarity to identify the most relevant assessments.

### 2. Hybrid Scoring Layer

A lightweight scoring system boosts results based on:

- keyword matches (e.g., Java, SQL, Leadership)
- role-skill alignment

This ensures domain-relevant assessments rank higher.

### 3. Signal-Based Clarification

If the user query is too vague, the system requests clarification instead of returning low-confidence recommendations.

### 4. Diversity Filtering

Results are balanced across assessment types (Knowledge, Ability, Personality) to ensure a well-rounded assessment battery.

### 5. Output Sanitization

Final outputs are strictly validated to ensure:

- only catalog-approved assessments are returned
- consistent schema formatting (name, url, test_type)

## What Didn't Work

Several iterations were required to stabilize the system:

- Heavier embedding models (SentenceTransformers) were removed due to memory constraints in deployment environments.
- Initial rule-based matching failed to handle indirect queries like “coding test”, which was resolved using TF-IDF with query expansion.
- Early versions produced overly biased results toward knowledge-based assessments, which was fixed using diversity balancing logic.
- Strict filtering rules initially blocked valid queries; this was resolved by introducing a weighted scoring system for input signals.

## Evaluation Approach

The system was evaluated using manual test queries across multiple job roles such as:

- Java Developer
- Data Analyst
- QA Engineer
- Backend Developer

Evaluation focused on:

- relevance of recommendations
- diversity of assessment types
- correctness of structured output
- robustness across vague and detailed inputs

## AI Tools Used

AI coding assistants such as ChatGPT were used during development for:

- debugging retrieval logic
- designing scoring heuristics
- refining API structure
- improving system reliability

## Deployment
- **Backend:** FastAPI
- **Retrieval:** TF-IDF (scikit-learn)
- **Hosting:** Render
- **API Endpoints:**
  - `/health`
  - `/chat`
