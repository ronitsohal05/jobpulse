from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


Mode = Literal["lexical", "semantic", "hybrid"]


def tokenize(text: str) -> list[str]:
    return [t for t in "".join([c.lower() if c.isalnum() else " " for c in text]).split() if t]


def minmax(xs: list[float]) -> list[float]:
    if not xs:
        return xs
    lo, hi = min(xs), max(xs)
    if math.isclose(lo, hi):
        return [0.0 for _ in xs]
    return [(x - lo) / (hi - lo) for x in xs]


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str | None
    description: str
    skills: list[str]
    category: str

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.company}\n{self.location or ''}\n\n{self.description}"


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    top = ranked[:k]
    if not top:
        return 0.0
    return sum(1 for x in top if x in relevant) / float(len(top))


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = ranked[:k]
    return sum(1 for x in top if x in relevant) / float(len(relevant))


def mrr(ranked: list[str], relevant: set[str]) -> float:
    for i, x in enumerate(ranked):
        if x in relevant:
            return 1.0 / float(i + 1)
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    def dcg(items: list[str]) -> float:
        s = 0.0
        for i, x in enumerate(items[:k]):
            rel = 1.0 if x in relevant else 0.0
            s += rel / math.log2(i + 2)
        return s

    ideal = list(relevant)
    return dcg(ranked) / max(dcg(ideal), 1e-12)


def rank_jobs(jobs: list[Job], query: str, mode: Mode, model: SentenceTransformer, index: faiss.Index) -> list[str]:
    docs = [tokenize(j.text) for j in jobs]
    bm25 = BM25Okapi(docs)
    bm25_scores = bm25.get_scores(tokenize(query)).tolist()
    bm25_n = minmax([float(s) for s in bm25_scores])

    qvec = model.encode([query]).astype("float32")
    faiss.normalize_L2(qvec)
    sem_scores, sem_ids = index.search(qvec, k=len(jobs))
    sem_rank = sem_ids[0].tolist()
    sem_score_map = {jobs[i].id: float(sem_scores[0][pos]) for pos, i in enumerate(sem_rank)}
    sem_n = minmax([sem_score_map[j.id] for j in jobs])

    scores: dict[str, float] = {}
    for i, j in enumerate(jobs):
        if mode == "lexical":
            scores[j.id] = bm25_n[i]
        elif mode == "semantic":
            scores[j.id] = sem_n[i]
        else:
            # A simple hybrid like the backend’s default weights.
            skill_hit = 1.0 if any(s.lower() in query.lower() for s in j.skills) else 0.0
            scores[j.id] = 0.35 * bm25_n[i] + 0.35 * sem_n[i] + 0.20 * skill_hit + 0.10 * 0.5

    return [jid for jid, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def main() -> None:
    data = json.loads(Path(__file__).with_name("sample_jobs.json").read_text())
    jobs = [Job(**j) for j in data["jobs"]]
    queries = data["queries"]

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    vecs = model.encode([j.text for j in jobs]).astype("float32")
    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)

    metrics: dict[str, dict[str, float]] = {}
    for mode in ("lexical", "semantic", "hybrid"):
        p5 = r5 = m = n5 = 0.0
        for q in queries:
            relevant = {j.id for j in jobs if j.category in set(q["relevant_categories"])}
            ranked = rank_jobs(jobs, q["text"], mode=mode, model=model, index=index)
            p5 += precision_at_k(ranked, relevant, 5)
            r5 += recall_at_k(ranked, relevant, 5)
            m += mrr(ranked, relevant)
            n5 += ndcg_at_k(ranked, relevant, 5)
        n = float(len(queries))
        metrics[mode] = {
            "Precision@5": p5 / n,
            "Recall@5": r5 / n,
            "MRR": m / n,
            "NDCG@5": n5 / n,
        }

    out_path = Path(__file__).with_name("results.json")
    out_path.write_text(json.dumps({"metrics": metrics}, indent=2))
    print(json.dumps({"metrics": metrics}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

