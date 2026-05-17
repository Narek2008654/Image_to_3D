"use strict";

// Minimal client for the Image-to-3D API: upload an image, poll the job,
// show the rotatable result and download links.

const el = (id) => document.getElementById(id);
const dropzone = el("dropzone");
const fileInput = el("file-input");
const preview = el("preview");
const generateBtn = el("generate");
const statusBox = el("status");
const statusText = el("status-text");
const errorBox = el("error");
const resultBox = el("result");
const viewer = el("viewer");
const meta = el("meta");
const downloads = el("downloads");

let selectedFile = null;
const POLL_MS = 2000;

function show(node, visible) {
  node.hidden = !visible;
}

function reset() {
  show(errorBox, false);
  show(resultBox, false);
}

function fail(message) {
  show(statusBox, false);
  errorBox.textContent = message;
  show(errorBox, true);
  generateBtn.disabled = !selectedFile;
}

function selectFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    fail("Please choose an image file.");
    return;
  }
  selectedFile = file;
  preview.src = URL.createObjectURL(file);
  show(preview, true);
  generateBtn.disabled = false;
  reset();
}

el("browse").addEventListener("click", () => fileInput.click());
dropzone.addEventListener("click", (e) => {
  if (e.target.id !== "browse") fileInput.click();
});
fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) =>
  selectFile(e.dataTransfer.files[0])
);

generateBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  reset();
  generateBtn.disabled = true;
  statusText.textContent = "Uploading…";
  show(statusBox, true);

  const form = new FormData();
  form.append("image", selectedFile);
  form.append("mc_resolution", el("resolution").value);

  try {
    const res = await fetch("/api/reconstruct", { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Upload failed (${res.status}).`);
    }
    const { job_id } = await res.json();
    pollJob(job_id);
  } catch (err) {
    fail(err.message);
  }
});

function pollJob(jobId) {
  statusText.textContent =
    "Generating 3D model… this can take 30s–2min on CPU.";
  const timer = setInterval(async () => {
    let job;
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      job = await res.json();
    } catch {
      return; // transient; keep polling
    }
    if (job.state === "done") {
      clearInterval(timer);
      renderResult(job);
    } else if (job.state === "error") {
      clearInterval(timer);
      fail(job.error || "Reconstruction failed.");
    }
  }, POLL_MS);
}

function renderResult(job) {
  show(statusBox, false);
  viewer.src = job.downloads.glb;
  meta.textContent =
    `${job.vertex_count.toLocaleString()} vertices · ` +
    `${job.face_count.toLocaleString()} faces · ` +
    `${job.elapsed_seconds}s`;
  downloads.innerHTML = "";
  for (const [fmt, url] of Object.entries(job.downloads)) {
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    a.textContent = `Download .${fmt}`;
    downloads.appendChild(a);
  }
  show(resultBox, true);
  generateBtn.disabled = false;
}
