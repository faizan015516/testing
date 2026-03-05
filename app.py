import logging
import sys
import uuid
import os
from flask import Flask, request, jsonify, render_template_string

from config import Config
from storage import ensure_container_exists, upload_file_to_blob, delete_blob
from database import init_db, insert_file_record, get_all_files, delete_file_record

# ── Logging to stdout (Azure Monitor picks this up) ──────────────────────────
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "txt", "csv", "xlsx", "docx", "zip"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ── HTML template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Azure File Vault</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #111118;
    --border: #1e1e2e;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --text: #e2e8f0;
    --muted: #64748b;
    --danger: #ef4444;
    --success: #22c55e;
    --mono: 'DM Mono', monospace;
    --sans: 'Syne', sans-serif;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--mono);
    min-height: 100vh;
    padding: 2rem;
    background-image:
      radial-gradient(ellipse 80% 60% at 50% -10%, rgba(0,212,255,0.07) 0%, transparent 60%),
      radial-gradient(ellipse 50% 40% at 90% 80%, rgba(124,58,237,0.06) 0%, transparent 60%);
  }
  header {
    max-width: 860px; margin: 0 auto 3rem;
    display: flex; align-items: baseline; gap: 1rem;
    border-bottom: 1px solid var(--border); padding-bottom: 1.5rem;
  }
  header h1 {
    font-family: var(--sans); font-size: 1.8rem; font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  header span { font-size: 0.75rem; color: var(--muted); }
  main { max-width: 860px; margin: 0 auto; }

  /* Upload card */
  .upload-card {
    border: 1px solid var(--border); border-radius: 12px;
    padding: 2rem; margin-bottom: 2.5rem;
    background: var(--surface);
    position: relative; overflow: hidden;
  }
  .upload-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
  }
  .upload-card h2 {
    font-family: var(--sans); font-size: 1rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--muted); margin-bottom: 1.5rem;
  }
  #drop-zone {
    border: 2px dashed var(--border); border-radius: 8px;
    padding: 3rem 2rem; text-align: center; cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    margin-bottom: 1.25rem;
  }
  #drop-zone.drag-over {
    border-color: var(--accent);
    background: rgba(0,212,255,0.04);
  }
  #drop-zone p { font-size: 0.85rem; color: var(--muted); line-height: 1.8; }
  #drop-zone strong { color: var(--accent); }
  #file-input { display: none; }

  #selected-file {
    font-size: 0.8rem; color: var(--accent);
    min-height: 1.2rem; margin-bottom: 1rem;
  }
  #upload-btn {
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #fff; border: none; border-radius: 6px;
    padding: 0.65rem 1.5rem; font-family: var(--mono); font-size: 0.85rem;
    font-weight: 500; cursor: pointer; transition: opacity 0.2s;
    display: flex; align-items: center; gap: 0.5rem;
  }
  #upload-btn:hover { opacity: 0.85; }
  #upload-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  #status-msg {
    margin-top: 1rem; font-size: 0.8rem; min-height: 1.2rem;
    padding: 0.5rem 0.75rem; border-radius: 4px;
  }
  #status-msg.success { background: rgba(34,197,94,0.1); color: var(--success); }
  #status-msg.error   { background: rgba(239,68,68,0.1);  color: var(--danger); }

  /* File table */
  .files-card { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: var(--surface); }
  .files-card-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
  }
  .files-card-header h2 {
    font-family: var(--sans); font-size: 1rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted);
  }
  #file-count { font-size: 0.75rem; color: var(--muted); }

  table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
  th {
    text-align: left; padding: 0.75rem 1.5rem;
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--muted); border-bottom: 1px solid var(--border);
    font-weight: 500;
  }
  td { padding: 0.9rem 1.5rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,0.015); }

  .file-name { color: var(--text); font-weight: 500; }
  .file-name a { color: var(--accent); text-decoration: none; }
  .file-name a:hover { text-decoration: underline; }
  .badge {
    display: inline-block; padding: 0.2rem 0.5rem;
    border-radius: 4px; font-size: 0.7rem;
    background: rgba(0,212,255,0.08); color: var(--accent);
    border: 1px solid rgba(0,212,255,0.15);
  }
  .del-btn {
    background: none; border: 1px solid var(--border); border-radius: 4px;
    color: var(--muted); cursor: pointer; font-family: var(--mono);
    font-size: 0.7rem; padding: 0.25rem 0.6rem;
    transition: border-color 0.15s, color 0.15s;
  }
  .del-btn:hover { border-color: var(--danger); color: var(--danger); }

  .empty-state { text-align: center; padding: 3rem; color: var(--muted); font-size: 0.8rem; }

  /* Progress bar */
  #progress-wrap { display: none; margin-top: 0.75rem; }
  #progress-bar-bg {
    height: 4px; background: var(--border); border-radius: 2px; overflow: hidden;
  }
  #progress-bar {
    height: 100%; width: 0%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    transition: width 0.15s;
  }
  #progress-pct { font-size: 0.7rem; color: var(--muted); margin-top: 0.35rem; }
</style>
</head>
<body>
<header>
  <h1>Azure File Vault</h1>
  <span>Flask · Blob Storage · SQL</span>
</header>
<main>
  <!-- Upload card -->
  <div class="upload-card">
    <h2>Upload File</h2>
    <div id="drop-zone">
      <p>Drag &amp; drop a file here<br>or <strong>click to browse</strong></p>
      <input type="file" id="file-input">
    </div>
    <div id="selected-file"></div>
    <button id="upload-btn" disabled>↑ Upload to Azure</button>
    <div id="progress-wrap">
      <div id="progress-bar-bg"><div id="progress-bar"></div></div>
      <div id="progress-pct">0%</div>
    </div>
    <div id="status-msg"></div>
  </div>

  <!-- Files list -->
  <div class="files-card">
    <div class="files-card-header">
      <h2>Uploaded Files</h2>
      <span id="file-count"></span>
    </div>
    <div id="files-container">
      <div class="empty-state">Loading…</div>
    </div>
  </div>
</main>

<script>
const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('file-input');
const selectedEl = document.getElementById('selected-file');
const uploadBtn  = document.getElementById('upload-btn');
const statusMsg  = document.getElementById('status-msg');
const progressWrap = document.getElementById('progress-wrap');
const progressBar  = document.getElementById('progress-bar');
const progressPct  = document.getElementById('progress-pct');

let selectedFile = null;

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) selectFile(f);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) selectFile(fileInput.files[0]); });

function selectFile(f) {
  selectedFile = f;
  selectedEl.textContent = `${f.name}  (${formatBytes(f.size)})`;
  uploadBtn.disabled = false;
  statusMsg.textContent = ''; statusMsg.className = '';
}

uploadBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  uploadBtn.disabled = true;
  progressWrap.style.display = 'block';
  statusMsg.textContent = ''; statusMsg.className = '';

  const fd = new FormData();
  fd.append('file', selectedFile);

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/upload');
  xhr.upload.addEventListener('progress', e => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      progressBar.style.width = pct + '%';
      progressPct.textContent = pct + '%';
    }
  });
  xhr.addEventListener('load', () => {
    progressWrap.style.display = 'none';
    progressBar.style.width = '0%';
    try {
      const res = JSON.parse(xhr.responseText);
      if (xhr.status === 201) {
        statusMsg.textContent = `✓ Uploaded: ${res.filename}`;
        statusMsg.className = 'success';
        selectedFile = null; selectedEl.textContent = '';
        fileInput.value = '';
        loadFiles();
      } else {
        statusMsg.textContent = `✗ ${res.error || 'Upload failed'}`;
        statusMsg.className = 'error';
        uploadBtn.disabled = false;
      }
    } catch { statusMsg.textContent = '✗ Unexpected error'; statusMsg.className = 'error'; uploadBtn.disabled = false; }
  });
  xhr.addEventListener('error', () => {
    statusMsg.textContent = '✗ Network error'; statusMsg.className = 'error';
    uploadBtn.disabled = false; progressWrap.style.display = 'none';
  });
  xhr.send(fd);
});

async function loadFiles() {
  try {
    const res = await fetch('/api/files');
    const data = await res.json();
    const files = data.files || [];
    document.getElementById('file-count').textContent = `${files.length} file${files.length !== 1 ? 's' : ''}`;
    const container = document.getElementById('files-container');
    if (!files.length) {
      container.innerHTML = '<div class="empty-state">No files uploaded yet.</div>'; return;
    }
    container.innerHTML = `<table>
      <thead><tr>
        <th>Filename</th><th>Type</th><th>Size</th><th>Uploaded</th><th></th>
      </tr></thead>
      <tbody>${files.map(f => `
        <tr>
          <td class="file-name"><a href="${f.blob_url}" target="_blank">${esc(f.filename)}</a></td>
          <td><span class="badge">${esc(f.content_type || '—')}</span></td>
          <td>${formatBytes(f.size_bytes)}</td>
          <td>${new Date(f.uploaded_at).toLocaleString()}</td>
          <td><button class="del-btn" onclick="deleteFile(${f.id}, '${esc(f.filename)}')">delete</button></td>
        </tr>`).join('')}
      </tbody></table>`;
  } catch { document.getElementById('files-container').innerHTML = '<div class="empty-state">Failed to load files.</div>'; }
}

async function deleteFile(id, name) {
  if (!confirm(`Delete "${name}"?`)) return;
  const res = await fetch(`/api/files/${id}`, { method: 'DELETE' });
  if (res.ok) loadFiles();
}

function formatBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
  return (b / (1024 * 1024)).toFixed(2) + ' MB';
}
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

loadFiles();
</script>
</body>
</html>
"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    # Make filename unique to avoid collisions
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"

    file_bytes = file.read()
    size_bytes = len(file_bytes)

    import io
    blob_url = upload_file_to_blob(io.BytesIO(file_bytes), unique_filename, content_type)
    record_id = insert_file_record(unique_filename, blob_url, size_bytes, content_type)

    logger.info(f"File upload complete: id={record_id} name={unique_filename} size={size_bytes}")
    return jsonify({
        "id": record_id,
        "filename": unique_filename,
        "blob_url": blob_url,
        "size_bytes": size_bytes,
        "content_type": content_type,
    }), 201


@app.route("/api/files", methods=["GET"])
def list_files():
    files = get_all_files()
    return jsonify({"files": files}), 200


@app.route("/api/files/<int:file_id>", methods=["DELETE"])
def delete_file(file_id):
    files = get_all_files()
    record = next((f for f in files if f["id"] == file_id), None)
    if not record:
        return jsonify({"error": "File not found"}), 404

    delete_blob(record["filename"])
    delete_file_record(file_id)
    return jsonify({"deleted": True}), 200


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Config.validate()
    ensure_container_exists()
    init_db()
    logger.info("Starting Azure File Vault on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
