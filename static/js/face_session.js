/**
 * Face presence for interview sessions — BlazeFace (TensorFlow.js).
 * Provides average detection probability while answering (not identity).
 */
(function () {
  const state = {
    model: null,
    rafId: null,
    video: null,
    canvas: null,
    ctx: null,
    samples: [],
    running: false,
  };

  async function loadScripts() {
    if (window.blazeface) return;
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.10.0/dist/tf.min.js";
      s.onload = resolve;
      s.onerror = () => reject(new Error("tfjs load failed"));
      document.head.appendChild(s);
    });
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface@1.0.2";
      s.onload = resolve;
      s.onerror = () => reject(new Error("blazeface load failed"));
      document.head.appendChild(s);
    });
  }

  async function initModel() {
    if (state.model) return state.model;
    await loadScripts();
    state.model = await blazeface.load();
    return state.model;
  }

  function drawBox(prediction, video) {
    if (!state.ctx || !prediction || !video.videoWidth) return;
    const tl = prediction.topLeft;
    const br = prediction.bottomRight;
    const sx = state.canvas.width / video.videoWidth;
    const sy = state.canvas.height / video.videoHeight;
    const x = tl[0] * sx;
    const y = tl[1] * sy;
    const bw = (br[0] - tl[0]) * sx;
    const bh = (br[1] - tl[1]) * sy;
    state.ctx.strokeStyle = "rgba(61, 214, 199, 0.95)";
    state.ctx.lineWidth = 2;
    state.ctx.strokeRect(x, y, bw, bh);
  }

  let lastDetect = 0;
  async function loop(ts) {
    if (!state.running || !state.video || !state.model) return;
    const video = state.video;
    if (video.readyState >= 2 && ts - lastDetect > 200) {
      lastDetect = ts;
      try {
        const preds = await state.model.estimateFaces(video, false);
        state.ctx.clearRect(0, 0, state.canvas.width, state.canvas.height);
        if (preds && preds.length) {
          const p = preds[0];
          let prob = 0.88;
          if (p.probability != null) {
            prob = Array.isArray(p.probability) ? p.probability[0] : p.probability;
          }
          state.samples.push(Math.min(1, Math.max(0, prob)));
          drawBox(p, video);
        } else {
          state.samples.push(0);
        }
      } catch (e) {
        /* ignore frame errors */
      }
    }
    state.rafId = requestAnimationFrame(loop);
  }

  window.FaceSession = {
    async start(videoEl, canvasEl) {
      state.video = videoEl;
      state.canvas = canvasEl;
      state.ctx = canvasEl.getContext("2d");
      await initModel();
      const resize = () => {
        if (!videoEl.videoWidth) return;
        canvasEl.width = videoEl.clientWidth;
        canvasEl.height = videoEl.clientHeight;
      };
      videoEl.addEventListener("loadeddata", resize);
      resize();
      state.samples = [];
      state.running = true;
      if (state.rafId) cancelAnimationFrame(state.rafId);
      loop();
    },

    stop() {
      state.running = false;
      if (state.rafId) {
        cancelAnimationFrame(state.rafId);
        state.rafId = null;
      }
    },

    clearSamples() {
      state.samples = [];
    },

    getAveragePresence() {
      if (!state.samples.length) return null;
      const sum = state.samples.reduce((a, b) => a + b, 0);
      return Math.round((sum / state.samples.length) * 100);
    },

    getSampleCount() {
      return state.samples.length;
    },
  };
})();
