// Maps backend mood labels to the CSS accent themes in style.css.
const MOOD_THEME = {
  "Happy 😄": "happy",
  "Sad 😢": "sad",
  "Angry 😠": "angry",
  "Surprised 😲": "surprised",
  "Fearful 😨": "fearful",
  "Neutral 😐": "neutral",
};

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
  const saveBtn = document.getElementById("saveBtn");
  const shuffleBtn = document.getElementById("shuffleBtn");
  const savedLink = document.getElementById("savedLink");
  const statusEl = document.getElementById("status");

  let mediaStream = null;
  let currentMood = null;
  let currentTracks = [];

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
      showStatus(cameraErrorMessage(err), "error");
    }
  });

  // Turn getUserMedia failures into an actionable message.
  function cameraErrorMessage(err) {
    if (!navigator.mediaDevices) {
      return "Camera API unavailable: open the app at http://127.0.0.1:5000 in a regular browser (not a LAN IP or editor preview).";
    }
    const reasons = {
      NotAllowedError: "Camera permission was denied. Click the camera icon in the address bar, allow it, and reload.",
      NotReadableError: "The camera is in use by another app or tab (e.g. a VS Code preview, Teams, Zoom). Close it and try again.",
      NotFoundError: "No camera was found. Check that it is connected and enabled.",
      OverconstrainedError: "The camera does not support the requested settings.",
    };
    return `${reasons[err.name] || "Could not access camera."} (${err.name}) You can also pick a mood manually.`;
  }

  // 2. Capture Frame (after a short countdown) and Send to Flask API
  captureBtn.addEventListener("click", async () => {
    if (!mediaStream) return;
    captureBtn.disabled = true;
    await runCountdown(3);

    // Draw current video frame to hidden canvas
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to Data URL (Base64 JPEG)
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

    // Display snapshot preview, hide live video
    snapshot.src = dataUrl;
    snapshot.hidden = false;
    video.hidden = true;
    captureBtn.hidden = true;
    retakeBtn.hidden = false;

    processMoodImage(dataUrl);
  });

  // 3. Retake Button Handler
  retakeBtn.addEventListener("click", () => {
    snapshot.hidden = true;
    video.hidden = false;
    retakeBtn.hidden = true;
    captureBtn.hidden = false;
    captureBtn.disabled = !mediaStream;
    resetResults();
  });

  // 4. Manual Chip Selection Handlers
  document.querySelectorAll(".chip").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedMood = button.dataset.mood;
      renderMood({ detected: selectedMood });
      fetchRecommendations(selectedMood);
    });
  });

  // 5. Playlist actions
  shuffleBtn.addEventListener("click", () => {
    if (currentMood) fetchRecommendations(currentMood);
  });
  saveBtn.addEventListener("click", savePlaylist);

  // API Call 1: Detect Emotion from Image
  async function processMoodImage(dataUrl) {
    showStatus("Analyzing your facial expression with AI...");
    try {
      const data = await postJSON("/api/detect-emotion", { image: dataUrl }, "Failed to analyze emotion");
      renderMood(data);
      fetchRecommendations(data.detected);
    } catch (err) {
      console.error(err);
      showStatus(err.message, "error");
    }
  }

  // API Call 2: Fetch Spotify Recommendations (no playlist is created yet)
  async function fetchRecommendations(mood) {
    showStatus(`Finding tracks for "${mood}"...`);
    shuffleBtn.disabled = true;
    try {
      const data = await postJSON("/api/recommend", { mood }, "Failed to fetch recommendations");
      renderPlaylist(data.tracks);
      showStatus("");
    } catch (err) {
      console.error(err);
      showStatus(err.message, "error");
    } finally {
      shuffleBtn.disabled = false;
    }
  }

  // API Call 3: Save current tracks as a playlist on the user's Spotify account
  async function savePlaylist() {
    if (!currentMood || currentTracks.length === 0) return;
    saveBtn.disabled = true;
    showStatus("Saving playlist to your Spotify account...");
    try {
      const data = await postJSON(
        "/api/save-playlist",
        { mood: currentMood, uris: currentTracks.map((t) => t.uri) },
        "Failed to save playlist",
      );
      savedLink.href = data.playlist.url;
      savedLink.hidden = false;
      saveBtn.textContent = "Saved ✓";
      showStatus("Playlist saved to your Spotify account! 🎧", "success");
    } catch (err) {
      console.error(err);
      saveBtn.disabled = false;
      showStatus(err.message, "error");
    }
  }

  // POST JSON and return the parsed body; throws with the server's error message.
  async function postJSON(url, body, fallbackError) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let data = null;
    try {
      data = await response.json();
    } catch {
      // Non-JSON body (e.g. an HTML error page); fall through to the status check.
    }
    if (!response.ok || data === null) {
      throw new Error((data && data.error) || `${fallbackError} (HTTP ${response.status})`);
    }
    return data;
  }

  // UI Render Helpers
  function renderMood(data) {
    currentMood = data.detected;
    moodEmpty.hidden = true;
    moodResult.hidden = false;
    document.body.dataset.mood = MOOD_THEME[data.detected] || "";

    // "Happy 🎉" -> name "Happy", emoji "🎉"
    const splitAt = data.detected.lastIndexOf(" ");
    moodName.textContent = data.detected.slice(0, splitAt);
    moodEmoji.textContent = data.detected.slice(splitAt + 1);

    if (data.confidence == null) {
      moodConfidence.textContent = "Selected manually";
    } else {
      const faceNote = data.face_detected ? "" : " · no face found, used full frame";
      moodConfidence.textContent = `${data.raw_label} · ${Math.round(data.confidence * 100)}% confidence${faceNote}`;
    }

    // Score breakdown bars (top 3 raw model labels)
    scoreBars.innerHTML = "";
    (data.raw_predictions || []).forEach((pred, i) => {
      const li = document.createElement("li");
      if (i === 0) li.className = "top";
      const pct = Math.round(pred.score * 100);

      const label = document.createElement("span");
      label.className = "label";
      label.textContent = pred.label;
      const track = document.createElement("div");
      track.className = "track";
      const fill = document.createElement("div");
      fill.className = "fill";
      fill.style.width = "0";
      track.appendChild(fill);
      const pctEl = document.createElement("span");
      pctEl.className = "pct";
      pctEl.textContent = `${pct}%`;

      li.append(label, track, pctEl);
      scoreBars.appendChild(li);
      requestAnimationFrame(() => (fill.style.width = `${pct}%`));
    });
  }

  function renderPlaylist(tracks) {
    currentTracks = tracks;
    playlistEmpty.hidden = tracks.length > 0;
    playlistEmpty.textContent = tracks.length ? "" : "No tracks found for this mood. Try shuffling.";
    playlist.hidden = tracks.length === 0;
    playlist.innerHTML = "";

    tracks.forEach((track, i) => {
      const li = document.createElement("li");
      li.style.animationDelay = `${i * 60}ms`;

      const art = track.album_art ? document.createElement("img") : document.createElement("div");
      art.className = "art";
      if (track.album_art) {
        art.src = track.album_art;
        art.alt = "";
      } else {
        art.textContent = "♪";
      }

      const meta = document.createElement("div");
      meta.className = "meta";
      const title = document.createElement("div");
      title.className = "title";
      title.textContent = track.name;
      const artist = document.createElement("div");
      artist.className = "artist";
      artist.textContent = track.artist;
      meta.append(title, artist);

      const link = document.createElement("a");
      link.className = "icon-btn";
      link.href = track.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.title = "Open in Spotify";
      link.textContent = "↗";

      li.append(art, meta, link);
      playlist.appendChild(li);
    });

    // New track list: allow saving again
    saveBtn.hidden = tracks.length === 0;
    saveBtn.disabled = false;
    saveBtn.textContent = "Save to Spotify";
    savedLink.hidden = true;
    shuffleBtn.hidden = false;
  }

  function resetResults() {
    currentMood = null;
    currentTracks = [];
    moodEmpty.hidden = false;
    moodResult.hidden = true;
    playlistEmpty.hidden = false;
    playlistEmpty.textContent = "5 tracks matched to your mood.";
    playlist.hidden = true;
    saveBtn.hidden = true;
    shuffleBtn.hidden = true;
    savedLink.hidden = true;
    document.body.dataset.mood = "";
    showStatus("");
  }

  async function runCountdown(seconds) {
    countdownEl.hidden = false;
    for (let i = seconds; i > 0; i--) {
      countdownEl.textContent = i;
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
    countdownEl.hidden = true;
  }

  function showStatus(message, type = "info") {
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
  }
});
