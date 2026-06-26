from flask import Flask, request, send_file, render_template_string
from PyPDF2 import PdfReader, PdfWriter
import os, io, json

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PDF Merger</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 40px 20px; }
  h1 { font-size: 2rem; font-weight: 700; margin-bottom: 6px; background: linear-gradient(135deg, #a78bfa, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .subtitle { color: #64748b; font-size: 0.9rem; margin-bottom: 32px; }
  .container { width: 100%; max-width: 720px; }
  #dropzone { border: 2px dashed #334155; border-radius: 16px; padding: 48px 20px; text-align: center; cursor: pointer; transition: all 0.2s; background: #1e2433; margin-bottom: 24px; }
  #dropzone.drag-over { border-color: #a78bfa; background: #1e1a2e; }
  #dropzone .icon { font-size: 2.5rem; margin-bottom: 12px; }
  #dropzone p { color: #94a3b8; font-size: 0.95rem; }
  #dropzone span { color: #a78bfa; font-weight: 600; cursor: pointer; }
  #fileInput { display: none; }
  #fileList { list-style: none; display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
  #fileList li { background: #1e2433; border: 1px solid #2d3748; border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; gap: 12px; cursor: grab; transition: background 0.15s; user-select: none; }
  #fileList li.dragging { opacity: 0.4; border-color: #a78bfa; }
  #fileList li.drag-target { border-color: #60a5fa; background: #1a2540; }
  .file-name { flex: 1; font-size: 0.9rem; color: #cbd5e1; word-break: break-all; }
  .file-size { font-size: 0.75rem; color: #475569; flex-shrink: 0; }
  .btn-remove { background: none; border: none; color: #475569; cursor: pointer; font-size: 1rem; padding: 2px 6px; border-radius: 4px; }
  .btn-remove:hover { color: #f87171; background: #2d1f1f; }
  .drag-handle { color: #334155; font-size: 1rem; flex-shrink: 0; }
  .toolbar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
  .btn { padding: 10px 20px; border-radius: 8px; border: none; font-size: 0.88rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }
  .btn:hover { opacity: 0.85; }
  .btn-primary { background: linear-gradient(135deg, #7c3aed, #2563eb); color: white; flex: 1; }
  .btn-secondary { background: #1e2433; color: #94a3b8; border: 1px solid #2d3748; }
  .btn-danger { background: #2d1f1f; color: #f87171; border: 1px solid #3d2020; }
  #status { text-align: center; font-size: 0.88rem; color: #64748b; min-height: 24px; margin-top: 8px; }
  #status.success { color: #4ade80; }
  #status.error { color: #f87171; }
  #countBadge { font-size: 0.8rem; background: #2d1a4a; color: #a78bfa; border-radius: 20px; padding: 2px 10px; margin-left: 10px; font-weight: 600; }
  .section-label { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #475569; margin-bottom: 10px; display: flex; align-items: center; }
</style>
</head>
<body>
<div class="container">
  <h1>PDF Merger</h1>
  <p class="subtitle">Drag, reorder, and merge up to 50+ PDF files instantly</p>
  <div id="dropzone">
    <div class="icon">📄</div>
    <p>Drag & drop your PDF files here</p>
    <p style="margin-top:8px">or <span onclick="document.getElementById('fileInput').click()">browse files</span></p>
    <input type="file" id="fileInput" accept=".pdf" multiple>
  </div>
  <div class="section-label">Files to merge <span id="countBadge">0 files</span></div>
  <ul id="fileList"></ul>
  <div class="toolbar">
    <button class="btn btn-secondary" onclick="sortAlpha()">⬆ Sort A–Z</button>
    <button class="btn btn-danger" onclick="clearAll()">✕ Clear All</button>
    <button class="btn btn-primary" onclick="mergePDFs()">⬇ Merge & Download</button>
  </div>
  <div id="status"></div>
</div>
<script>
  let files = [];
  let dragSrcIdx = null;
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const fileList = document.getElementById('fileList');
  const status = document.getElementById('status');
  const badge = document.getElementById('countBadge');
  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', e => { e.preventDefault(); dropzone.classList.remove('drag-over'); addFiles([...e.dataTransfer.files]); });
  fileInput.addEventListener('change', () => addFiles([...fileInput.files]));
  function addFiles(newFiles) {
    const pdfs = newFiles.filter(f => f.type === 'application/pdf' || f.name.endsWith('.pdf'));
    if (pdfs.length < newFiles.length) setStatus((newFiles.length - pdfs.length) + ' non-PDF file(s) skipped.', 'error');
    files = files.concat(pdfs);
    renderList();
    fileInput.value = '';
  }
  function renderList() {
    fileList.innerHTML = '';
    badge.textContent = files.length + ' file' + (files.length !== 1 ? 's' : '');
    files.forEach((f, i) => {
      const li = document.createElement('li');
      li.draggable = true;
      li.dataset.idx = i;
      li.innerHTML = '<span class="drag-handle">⠿</span><span>📄</span><span class="file-name">' + f.name + '</span><span class="file-size">' + (f.size/1024).toFixed(1) + ' KB</span><button class="btn-remove" onclick="removeFile(' + i + ')">✕</button>';
      li.addEventListener('dragstart', () => { dragSrcIdx = i; setTimeout(() => li.classList.add('dragging'), 0); });
      li.addEventListener('dragend', () => li.classList.remove('dragging'));
      li.addEventListener('dragover', e => { e.preventDefault(); li.classList.add('drag-target'); });
      li.addEventListener('dragleave', () => li.classList.remove('drag-target'));
      li.addEventListener('drop', e => { e.preventDefault(); li.classList.remove('drag-target'); if (dragSrcIdx !== null && dragSrcIdx !== i) { const moved = files.splice(dragSrcIdx, 1)[0]; files.splice(i, 0, moved); renderList(); } });
      fileList.appendChild(li);
    });
  }
  function removeFile(i) { files.splice(i, 1); renderList(); }
  function clearAll() { files = []; renderList(); setStatus(''); }
  function sortAlpha() { files.sort((a,b) => a.name.localeCompare(b.name)); renderList(); }
  async function mergePDFs() {
    if (files.length < 2) { setStatus('Add at least 2 PDF files.', 'error'); return; }
    setStatus('Merging ' + files.length + ' files...');
    const formData = new FormData();
    files.forEach(f => formData.append('pdfs', f, f.name));
    formData.append('order', JSON.stringify(files.map(f => f.name)));
    try {
      const res = await fetch('/merge', { method: 'POST', body: formData });
      if (!res.ok) { const t = await res.text(); setStatus('Error: ' + t, 'error'); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'merged.pdf'; a.click();
      URL.revokeObjectURL(url);
      setStatus('✓ Merged successfully! Download started.', 'success');
    } catch(err) { setStatus('Network error: ' + err.message, 'error'); }
  }
  function setStatus(msg, type='') { status.textContent = msg; status.className = type; }
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/merge", methods=["POST"])
def merge():
    uploaded = request.files.getlist("pdfs")
    order_json = request.form.get("order", "[]")
    try:
        order = json.loads(order_json)
    except Exception:
        order = [f.filename for f in uploaded]
    file_map = {f.filename: f for f in uploaded}
    writer = PdfWriter()
    errors = []
    for name in order:
        if name not in file_map:
            continue
        try:
            data = file_map[name].read()
            reader = PdfReader(io.BytesIO(data))
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            errors.append(f"{name}: {e}")
    if errors:
        return "\n".join(errors), 400
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name="merged.pdf")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
