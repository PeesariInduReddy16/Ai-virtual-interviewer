"""
AI Virtual Interviewer — Flask API + static SPA.
Run: python app.py  →  http://127.0.0.1:5000
"""
import secrets
import time
from typing import Any, Dict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from question_bank import INTERVIEW_TYPES, build_questions
from nlp_evaluator import aggregate_session, evaluate_answer

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
)
CORS(app)

sessions: Dict[str, Dict[str, Any]] = {}


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/types", methods=["GET"])
def api_types():
    return jsonify({"interview_types": INTERVIEW_TYPES})


@app.route("/api/session", methods=["POST"])
def create_session():
    data = request.get_json(force=True, silent=True) or {}
    candidate = {
        "full_name": (data.get("full_name") or "").strip() or "Candidate",
        "email": (data.get("email") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "job_role": (data.get("job_role") or "").strip() or "Professional",
        "experience_years": data.get("experience_years") or "",
        "interview_type": (data.get("interview_type") or "general_mixed").lower().strip(),
    }
    sid = secrets.token_hex(16)
    questions = build_questions(candidate["job_role"], candidate["interview_type"])
    sessions[sid] = {
        "candidate": candidate,
        "questions": questions,
        "answers": [],
        "created_at": time.time(),
    }
    return jsonify(
        {
            "session_id": sid,
            "candidate": candidate,
            "questions": questions,
            "total_questions": len(questions),
        }
    )


@app.route("/api/answer", methods=["POST"])
def submit_answer():
    data = request.get_json(force=True, silent=True) or {}
    sid = data.get("session_id")
    if not sid or sid not in sessions:
        return jsonify({"error": "Invalid or expired session."}), 400

    qid = data.get("question_id")
    text = (data.get("answer_text") or "").strip()
    elapsed = float(data.get("elapsed_seconds") or 0)
    face_presence_avg = data.get("face_presence_avg")
    face_samples = data.get("face_samples")

    sess = sessions[sid]
    q = next((x for x in sess["questions"] if x["id"] == qid), None)
    if not q:
        return jsonify({"error": "Unknown question."}), 400

    ev = evaluate_answer(text, sess["candidate"]["job_role"], elapsed, q.get("tag"))
    row = {
        "question_id": qid,
        "question_index": q["index"],
        "answer_text": text,
        "elapsed_seconds": elapsed,
        "face_presence_avg": face_presence_avg,
        "face_samples": face_samples,
        "evaluation": ev,
    }
    sess["answers"].append(row)

    return jsonify({"ok": True, "evaluation": ev})


@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    sid = data.get("session_id")
    if not sid or sid not in sessions:
        return jsonify({"error": "Invalid or expired session."}), 400

    sess = sessions[sid]
    evals = [a["evaluation"] for a in sess["answers"]]
    agg = aggregate_session(evals)

    face_summary = None
    samples = []
    for a in sess["answers"]:
        if a.get("face_presence_avg") is not None:
            samples.append(float(a["face_presence_avg"]))
    if samples:
        face_summary = {
            "avg_face_presence_score": round(sum(samples) / len(samples), 1),
            "readings_count": len(samples),
        }

    return jsonify(
        {
            "session_id": sid,
            "candidate": sess["candidate"],
            "interview_type": sess["candidate"]["interview_type"],
            "job_role": sess["candidate"]["job_role"],
            "questions_answered": len(sess["answers"]),
            "total_questions": len(sess["questions"]),
            "per_answer": sess["answers"],
            "aggregated": agg,
            "face_recognition_summary": face_summary,
        }
    )


if __name__ == "__main__":
    # Accessible on LAN for same-network devices (optional)
    app.run(host="127.0.0.1", port=5000, debug=True)
