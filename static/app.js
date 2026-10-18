document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("video");
  const snapshot = document.getElementById("snapshot");
  const canvas = document.getElementById("canvas");
  const startBtn = document.getElementById("startBtn");
  const captureBtn = document.getElementById("captureBtn");
  const retakeBtn = document.getElementById("retakeBtn");
  const cameraOff = document.getElementById("cameraOff");
  const countdownEl = document.getElementById("countdown");

  const moodEmpty = document.getElementById("moodEmpty");
  const moodResult = document.getElementById("moodResult");
  const moodEmoji = document.getElementById("moodEmoji");
  const moodName = document.getElementById("moodName");
  const moodConfidence = document.getElementById("moodConfidence");
  const scoreBars = document.getElementById("scoreBars");

  const playlistEmpty = document.getElementById("playlistEmpty");
  const playlist = document.getElementById("playlist");
  const shuffleBtn = document.getElementById("shuffleBtn");
  const statusEl = document.getElementById("status");

  let mediaStream = null;

  // 1. Enable Webcam Stream
  startBtn.addEventListener("click", async () => {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });
      video.srcObject = mediaStream;
      cameraOff.hidden = true;
      captureBtn.disabled = false;
      showStatus("Camera active. Ready to capture your vibe!");
    } catch (err) {
      console.error("Webcam access error:", err);
      showStatus(
        "Could not access camera. Please check permissions or use manual selection.",
        "error",
      );
    }
  });

  // 2. Capture Frame and Send to Flask API
  captureBtn.addEventListener("click", () => {
    if (!mediaStream) return;

    // Draw current video frame to hidden canvas
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to Data URL (Base64 JPEG)
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

    // Display snapshot preview, hide live video
    snapshot.src = dataUrl;
    snapshot.hidden = false;
    video.hidden = true;
    captureBtn.hidden = true;
    retakeBtn.hidden = false;

    // Process Emotion & Recommendations
    processMoodImage(dataUrl);
  });

  // 3. Retake Button Handler
  retakeBtn.addEventListener("click", () => {
    snapshot.hidden = true;
    video.hidden = false;
    retakeBtn.hidden = true;
    captureBtn.hidden = false;
    resetResults();
  });

  // 4. Manual Chip Selection Handlers
  document.querySelectorAll(".chip").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedMood = button.dataset.mood;
      fetchRecommendations(selectedMood);
    });
  });

  // API Call 1: Detect Emotion from Image
  async function processMoodImage(dataUrl) {
    showStatus("Analyzing your facial expression with AI...");
    try {
      const response = await fetch("/api/detect-emotion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: dataUrl }),
      });

      const data = await response.json();
      if (!response.ok)
        throw new Error(data.error || "Failed to analyze emotion");

      renderMood(data);
      fetchRecommendations(data.detected);
    } catch (err) {
      console.error(err);
      showStatus(err.message, "error");
    }
  }

  // API Call 2: Fetch Spotify Recommendations
  async function fetchRecommendations(mood) {
    showStatus(`Generating your custom Spotify playlist for "${mood}"...`);
    try {
      const response = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mood: mood }),
      });

      const data = await response.json();
      if (!response.ok)
        throw new Error(data.error || "Failed to generate playlist");

      renderPlaylist(data.tracks);
      showStatus(
        "Playlist successfully generated and saved to your Spotify account! 🎧",
        "success",
      );
    } catch (err) {
      console.error(err);
      showStatus(err.message, "error");
    }
  }

  // UI Render Helpers
  function renderMood(data) {
    moodEmpty.hidden = true;
    moodResult.hidden = false;

    document.body.dataset.mood = data.detected;
    moodName.textContent = data.detected;
    moodConfidence.textContent = `Confidence: ${Math.round(data.confidence * 100)}%`;

    // Render score breakdown bars if available
    scoreBars.innerHTML = "";
    if (data.raw_predictions) {
      data.raw_predictions.forEach((pred) => {
        const li = document.createElement("li");
        const pct = Math.round(pred.score * 100);
        li.innerHTML = `<span>${pred.label}</span><div class="bar-track"><div class="bar-fill" style="width: ${pct}%"></div></div><span>${pct}%</span>`;
        scoreBars.appendChild(li);
      });
    }
  }

  function renderPlaylist(tracks) {
    playlistEmpty.hidden = true;
    playlist.hidden = false;
    playlist.innerHTML = "";

    tracks.forEach((track) => {
      const li = document.createElement("li");
      li.innerHTML = `<a href="${track.url}" target="_blank"><strong>${track.name}</strong></a><span class="artist">${track.artist}</span>`;
      playlist.appendChild(li);
    });
    shuffleBtn.hidden = false;
  }

  function resetResults() {
    moodEmpty.hidden = false;
    moodResult.hidden = true;
    playlistEmpty.hidden = false;
    playlist.hidden = true;
    shuffleBtn.hidden = true;
    document.body.dataset.mood = "";
    showStatus("");
  }

  function showStatus(message, type = "info") {
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
  }
});
