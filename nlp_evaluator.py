"""
NLP-based evaluation: content quality, grammar proxy, communication,
confidence proxy (via sentiment + subjectivity), response time factor.
"""
import difflib
import re
from typing import Any, Dict, List, Optional

from textblob import TextBlob
import textstat

# Reasonable bounds for spoken/written interview answers (seconds)
MIN_GOOD_SECONDS = 15
MAX_IDEAL_SECONDS = 240
TOO_FAST_SECONDS = 5


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _grammar_proxy(text: str) -> float:
    """Spelling/grammar proxy: compare sample to TextBlob-corrected text + basic hygiene."""
    if not text or not text.strip():
        return 0.0
    sample = text[:2000]
    base = 72.0
    if re.search(r"(.)\1{5,}", sample):
        base -= 12
    if re.search(r"[!?]{3,}", sample):
        base -= 8
    try:
        blob = TextBlob(sample)
        corrected = str(blob.correct())
        ratio = difflib.SequenceMatcher(None, sample.lower(), corrected.lower()).ratio()
        base = 0.55 * base + 0.45 * (45 + 55 * ratio)
    except Exception:
        pass
    return _clamp(base)


def _content_quality(text: str, job_role: str) -> float:
    if not text or len(text.strip()) < 20:
        return 25.0
    words = len(text.split())
    # Readability — not too shallow, not unreadable
    try:
        fre = textstat.flesch_reading_ease(text)
    except Exception:
        fre = 50.0
    # Target moderate readability for professional answers
    read_score = _clamp(100 - abs(fre - 55) * 1.2, 30, 100)
    length_score = _clamp(30 + min(words / 3.0, 50), 30, 100)
    role_lower = (job_role or "").lower()
    overlap = sum(1 for tok in re.findall(r"[a-zA-Z]+", role_lower) if tok in text.lower() and len(tok) > 2)
    relevance = _clamp(40 + min(overlap * 8, 40))
    return _clamp(0.35 * read_score + 0.35 * length_score + 0.3 * relevance)


def _communication_score(text: str) -> float:
    if not text.strip():
        return 0.0
    blob = TextBlob(text[:8000])
    sentences = blob.sentences
    n = len(sentences)
    if n == 0:
        return 45.0
    avg_len = sum(len(s.words) for s in sentences) / max(n, 1)
    # Prefer multiple sentences, moderate length
    structure = _clamp(40 + min(n * 8, 40) + (10 if 8 <= avg_len <= 35 else 0))
    return _clamp(structure)


def _confidence_proxy(text: str) -> float:
    """
    Proxy: polarity (positive steadiness) and lower subjectivity = more factual/assertive.
    Calibrated heuristically for interview-style answers.
    """
    if not text.strip():
        return 0.0
    blob = TextBlob(text[:8000])
    pol = float(blob.sentiment.polarity)  # -1..1
    subj = float(blob.sentiment.subjectivity)  # 0..1
    # Map polarity 0..1-ish for professional tone
    pol_score = _clamp(50 + pol * 35, 20, 95)
    # Slight subjectivity ok for behavioral; penalize extreme subjectivity only
    subj_penalty = _clamp((1.0 - abs(subj - 0.45)) * 40, 0, 40)
    return _clamp(0.65 * pol_score + 0.35 * (40 + subj_penalty))


def _response_time_score(elapsed_seconds: float) -> float:
    if elapsed_seconds is None or elapsed_seconds <= 0:
        return 50.0
    if elapsed_seconds < TOO_FAST_SECONDS:
        return 35.0
    if elapsed_seconds < MIN_GOOD_SECONDS:
        return _clamp(45 + (elapsed_seconds / MIN_GOOD_SECONDS) * 25)
    if elapsed_seconds <= MAX_IDEAL_SECONDS:
        return 92.0
    # Very long — slight penalty (rambling)
    over = elapsed_seconds - MAX_IDEAL_SECONDS
    return _clamp(92 - min(over / 10.0, 25))


def evaluate_answer(
    text: str,
    job_role: str,
    elapsed_seconds: float,
    question_tag: Optional[str] = None,
) -> Dict[str, Any]:
    text = (text or "").strip()
    cq = _content_quality(text, job_role)
    gram = _grammar_proxy(text) if len(text) > 15 else (30.0 if text else 0.0)
    comm = _communication_score(text)
    conf = _confidence_proxy(text)
    rt = _response_time_score(float(elapsed_seconds or 0))

    # Weighted overall (per-answer)
    weights = {
        "content": 0.28,
        "grammar": 0.18,
        "communication": 0.22,
        "confidence": 0.17,
        "response_time": 0.15,
    }
    overall = (
        weights["content"] * cq
        + weights["grammar"] * gram
        + weights["communication"] * comm
        + weights["confidence"] * conf
        + weights["response_time"] * rt
    )
    return {
        "content_quality": round(cq, 1),
        "grammar": round(gram, 1),
        "communication": round(comm, 1),
        "confidence_level": round(conf, 1),
        "response_time_score": round(rt, 1),
        "overall_answer_score": round(overall, 1),
        "word_count": len(text.split()),
        "question_tag": question_tag,
    }


def aggregate_session(answers_eval: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not answers_eval:
        return {
            "interview_performance_score": 0,
            "strengths": [],
            "weaknesses": [],
            "confidence_analysis": "No answers recorded.",
            "averages": {},
        }

    keys = ["content_quality", "grammar", "communication", "confidence_level", "response_time_score"]
    avgs = {k: round(sum(a[k] for a in answers_eval) / len(answers_eval), 1) for k in keys}
    perf = round(sum(a["overall_answer_score"] for a in answers_eval) / len(answers_eval), 1)

    strengths = []
    weaknesses = []
    if avgs["content_quality"] >= 75:
        strengths.append("Strong content depth and relevance in your answers.")
    elif avgs["content_quality"] < 55:
        weaknesses.append("Answers could include more specific detail and role-related examples.")

    if avgs["communication"] >= 75:
        strengths.append("Clear structure and good articulation across responses.")
    elif avgs["communication"] < 55:
        weaknesses.append("Try organizing answers with a short setup, actions, and outcome.")

    if avgs["grammar"] >= 75:
        strengths.append("Consistent language quality and readability.")
    elif avgs["grammar"] < 55:
        weaknesses.append("Watch grammar and spelling; brief pauses to compose can help.")

    if avgs["confidence_level"] >= 72:
        strengths.append("Steady, professional tone suggesting confidence.")
    elif avgs["confidence_level"] < 55:
        weaknesses.append("Tone reads as tentative; practice stating outcomes assertively.")

    if avgs["response_time_score"] >= 80:
        strengths.append("Response pacing suggests thoughtful preparation.")
    else:
        weaknesses.append("Some answers may be too rushed or overly long; aim for concise depth.")

    if not strengths:
        strengths.append("You completed the full interview — good persistence.")
    if not weaknesses:
        weaknesses.append("No major weak areas flagged; continue refining examples with metrics.")

    low = min(avgs, key=lambda k: avgs[k])
    conf_text = (
        f"Average confidence proxy score: {avgs['confidence_level']}/100. "
        f"The lowest dimension was {low.replace('_', ' ')} ({avgs[low]}). "
        "Confidence here combines sentiment steadiness and how factual vs. vague the language reads — "
        "not camera-based detection."
    )

    return {
        "interview_performance_score": perf,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "confidence_analysis": conf_text,
        "averages": avgs,
    }
