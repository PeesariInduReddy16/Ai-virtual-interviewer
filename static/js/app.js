(function () {
  const API = "";
  let sessionId = null;
  let questions = [];
  let currentIndex = 0;
  let questionStartAt = 0;
  let videoStream = null;

  const el = (id) => document.getElementById(id);

  function setStatus(msg, type) {
    const bar = el("statusBar");
    bar.textContent = msg;
    bar.className = "status-bar " + (type === "ok" ? "ok" : type === "err" ? "err" : "");
  }

  async function initTypes() {
    try {
      const r = await fetch(API + "/api/types");
      const j = await r.json();
      const sel = el("interviewType");
      sel.innerHTML = "";
      const labels = {
        technical: "Technical",
        behavioral: "Behavioral (STAR)",
        hr: "HR & Culture",
        leadership: "Leadership & Management",
        sales_client: "Sales & Client-facing",
        case_problem_solving: "Case & Problem-solving",
        operations: "Operations & Execution",
        product_ux: "Product & UX",
        finance_legal: "Finance & Legal / Compliance",
        general_mixed: "General / Mixed",
      };
      j.interview_types.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = labels[t] || t;
        sel.appendChild(opt);
      });
    } catch (e) {
      setStatus("Could not load interview types. Is the Python server running?", "err");
    }
  }

  async function startSession() {
    const payload = {
      full_name: el("fullName").value.trim(),
      email: el("email").value.trim(),
      phone: el("phone").value.trim(),
      job_role: el("jobRole").value.trim(),
      experience_years: el("expYears").value.trim(),
      interview_type: el("interviewType").value,
    };
    if (!payload.job_role) {
      setStatus("Please enter a job role (any title — e.g. Data Analyst, Nurse, Mechanic).", "err");
      return;
    }
    setStatus("Starting session…", "");
    const r = await fetch(API + "/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      setStatus("Failed to start session.", "err");
      return;
    }
    const data = await r.json();
    sessionId = data.session_id;
    questions = data.questions;
    currentIndex = 0;
    el("setupPanel").classList.add("hidden");
    el("interviewPanel").classList.remove("hidden");
    el("reportPanel").classList.add("hidden");
    await startCamera();
    showQuestion();
    setStatus("Session active. Answer each question — 10 total.", "ok");
  }

  async function startCamera() {
    const video = el("videoCam");
    try {
      videoStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      video.srcObject = videoStream;
      await video.play();
      if (window.FaceSession) {
        await FaceSession.start(video, el("faceCanvas"));
      }
    } catch (e) {
      setStatus("Camera unavailable — you can still continue with text/voice only.", "err");
    }
  }

  function stopCamera() {
    if (window.FaceSession) FaceSession.stop();
    if (videoStream) {
      videoStream.getTracks().forEach((t) => t.stop());
      videoStream = null;
    }
  }

  function showQuestion() {
    if (currentIndex >= questions.length) {
      finishInterview();
      return;
    }
    const q = questions[currentIndex];
    el("qIndex").textContent = String(q.index);
    el("qTotal").textContent = String(questions.length);
    el("qText").textContent = q.text;
    el("answerText").value = "";
    questionStartAt = Date.now();
    if (window.FaceSession) {
      FaceSession.clearSamples();
    }
    tickTimer();
  }

  let timerId = null;
  function tickTimer() {
    if (timerId) clearInterval(timerId);
    timerId = setInterval(() => {
      const sec = Math.floor((Date.now() - questionStartAt) / 1000);
      el("timerEl").textContent = sec + "s";
    }, 500);
  }

  function getSpeechRecognition() {
    return window.SpeechRecognition || window.webkitSpeechRecognition;
  }

  el("btnVoice").addEventListener("click", () => {
    const SR = getSpeechRecognition();
    if (!SR) {
      setStatus("Speech recognition not supported in this browser.", "err");
      return;
    }
    const rec = new SR();
    rec.lang = document.documentElement.lang || "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (ev) => {
      const text = ev.results[0][0].transcript;
      const ta = el("answerText");
      ta.value = (ta.value ? ta.value + " " : "") + text;
    };
    rec.onerror = () => setStatus("Voice capture error.", "err");
    rec.start();
    setStatus("Listening… speak your answer.", "ok");
  });

  el("btnSubmitAnswer").addEventListener("click", submitCurrentAnswer);

  async function submitCurrentAnswer() {
    const text = el("answerText").value.trim();
    if (text.length < 8) {
      setStatus("Please enter a more complete answer (at least a few words).", "err");
      return;
    }
    const elapsed = (Date.now() - questionStartAt) / 1000;
    const q = questions[currentIndex];
    let faceAvg = null;
    let faceSamples = 0;
    if (window.FaceSession) {
      faceAvg = FaceSession.getAveragePresence();
      faceSamples = FaceSession.getSampleCount();
    }
    setStatus("Evaluating answer…", "");
    const r = await fetch(API + "/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        question_id: q.id,
        answer_text: text,
        elapsed_seconds: elapsed,
        face_presence_avg: faceAvg,
        face_samples: faceSamples,
      }),
    });
    if (!r.ok) {
      setStatus("Failed to submit answer.", "err");
      return;
    }
    const data = await r.json();
    const ev = data.evaluation;
    el("lastFeedback").innerHTML =
      "<strong>Instant feedback</strong> — Overall: " +
      ev.overall_answer_score +
      "/100 · Content " +
      ev.content_quality +
      " · Grammar " +
      ev.grammar +
      " · Comm " +
      ev.communication +
      " · Confidence " +
      ev.confidence_level +
      " · Pace " +
      ev.response_time_score;
    setStatus("Answer recorded.", "ok");
    currentIndex += 1;
    showQuestion();
  }

  async function finishInterview() {
    if (timerId) clearInterval(timerId);
    stopCamera();
    const r = await fetch(API + "/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!r.ok) {
      setStatus("Could not build report.", "err");
      return;
    }
    const rep = await r.json();
    renderReport(rep);
    el("interviewPanel").classList.add("hidden");
    el("reportPanel").classList.remove("hidden");
    setStatus("Interview complete.", "ok");
  }

  function renderReport(rep) {
    const c = rep.candidate;
    const agg = rep.aggregated;
    const face = rep.face_recognition_summary;

    let perQuestionSection = null;
    if (rep.per_answer && rep.per_answer.length) {
      const rows = rep.per_answer
        .map(
          (a) =>
            "<div style='margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid rgba(255,255,255,0.08)'>" +
            "<strong>Q" +
            a.question_index +
            "</strong> (score " +
            a.evaluation.overall_answer_score +
            "/100)<br/><span style='color:#9aa4bd;font-size:0.9rem'>" +
            escapeHtml((a.answer_text || "").slice(0, 220)) +
            (a.answer_text && a.answer_text.length > 220 ? "…" : "") +
            "</span></div>"
        )
        .join("");
      perQuestionSection = { title: "Per-question answers & scores", html: rows };
    }

    const sections = [
      { title: "Full name", html: escapeHtml(c.full_name) },
      { title: "Email", html: escapeHtml(c.email || "—") },
      { title: "Phone", html: escapeHtml(c.phone || "—") },
      { title: "Job role applied for", html: escapeHtml(c.job_role) },
      { title: "Interview type", html: escapeHtml(rep.interview_type) },
      { title: "Experience (years)", html: escapeHtml(String(c.experience_years || "—")) },
      {
        title: "Session details",
        html:
          `<div>Questions answered: <strong>${rep.questions_answered}</strong> / ${rep.total_questions}</div>` +
          (face
            ? `<div>Face presence (avg): <strong>${face.avg_face_presence_score}%</strong> (${face.readings_count} face detections sampled)</div>`
            : "<div>Face camera not used or no samples.</div>"),
      },
      {
        title: "Interview performance score",
        html:
          '<div class="big-score">' +
          agg.interview_performance_score +
          '</div><div class="meter"><span style="width:' +
          agg.interview_performance_score +
          '%"></span></div>',
      },
      ...(perQuestionSection ? [perQuestionSection] : []),
      {
        title: "Dimension averages (NLP)",
        html:
          "<ul class='clean-list'>" +
          Object.entries(agg.averages)
            .map(([k, v]) => "<li>" + escapeHtml(k.replace(/_/g, " ")) + ": <strong>" + v + "</strong></li>")
            .join("") +
          "</ul>",
      },
      {
        title: "Strengths",
        html: "<ul class='clean-list'>" + agg.strengths.map((s) => "<li>" + escapeHtml(s) + "</li>").join("") + "</ul>",
      },
      {
        title: "Weaknesses",
        html:
          "<ul class='clean-list'>" + agg.weaknesses.map((s) => "<li>" + escapeHtml(s) + "</li>").join("") + "</ul>",
      },
      {
        title: "Confidence level analysis",
        html: "<p class='value'>" + escapeHtml(agg.confidence_analysis) + "</p>",
      },
    ];

    const root = el("reportVertical");
    root.innerHTML = sections
      .map(
        (s) =>
          '<div class="report-section"><h3>' +
          escapeHtml(s.title) +
          "</h3><div class='value'>" +
          s.html +
          "</div></div>"
      )
      .join("");
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  el("btnStart").addEventListener("click", startSession);
  el("btnRestart").addEventListener("click", () => {
    el("reportPanel").classList.add("hidden");
    el("setupPanel").classList.remove("hidden");
    sessionId = null;
    questions = [];
    currentIndex = 0;
    el("lastFeedback").textContent = "";
  });

  initTypes();
})();
