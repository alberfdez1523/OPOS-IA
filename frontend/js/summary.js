/**
 * MúsicaOpos AI — Summary Page
 * Standalone summary generator with client-side PDF export
 */

const API = '/api';

// ============================================
// State
// ============================================
let summaryText = '';
let summaryPdfName = '';

// ============================================
// DOM References
// ============================================
const summaryConfig = document.getElementById('summary-config');
const summaryLoading = document.getElementById('summary-loading');
const summaryResult = document.getElementById('summary-result');
const summaryPdfSelect = document.getElementById('summary-pdf-select');
const summaryGenerateBtn = document.getElementById('summary-generate-btn');
const summaryContent = document.getElementById('summary-content');
const summaryTitle = document.getElementById('summary-title');
const summaryDownloadBtn = document.getElementById('summary-download-btn');
const summaryNewBtn = document.getElementById('summary-new-btn');

// ============================================
// Auth Guard
// ============================================
(function checkAuth() {
  if (sessionStorage.getItem('musicaopos_auth') !== 'true') {
    window.location.href = 'login.html';
  }
})();

// ============================================
// Init
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  loadPdfList();
  loadSidebarStats();

  summaryGenerateBtn.addEventListener('click', generateSummary);
  summaryDownloadBtn.addEventListener('click', downloadPdf);
  summaryNewBtn.addEventListener('click', resetSummary);
});

// ============================================
// Load PDFs
// ============================================
async function loadPdfList() {
  try {
    const res = await fetch(`${API}/pdfs`);
    const data = await res.json();
    summaryPdfSelect.innerHTML = '';
    if (data.pdfs && data.pdfs.length > 0) {
      data.pdfs.forEach(pdf => {
        const opt = document.createElement('option');
        opt.value = pdf;
        opt.textContent = pdf.replace('.pdf', '');
        summaryPdfSelect.appendChild(opt);
      });
    } else {
      summaryPdfSelect.innerHTML = '<option value="">No hay PDFs disponibles</option>';
    }
  } catch (err) {
    summaryPdfSelect.innerHTML = '<option value="">Error al cargar PDFs</option>';
  }
}

// ============================================
// Sidebar Stats
// ============================================
async function loadSidebarStats() {
  try {
    const res = await fetch(`${API}/stats`);
    const data = await res.json();
    const chunksEl = document.getElementById('sidebar-chunks');
    if (chunksEl) chunksEl.textContent = data.chunks.toLocaleString();
  } catch (e) {
    // ignore
  }
}

// ============================================
// Generate Summary
// ============================================
async function generateSummary() {
  const pdfName = summaryPdfSelect.value;
  if (!pdfName) return;

  summaryPdfName = pdfName;

  // Show loading
  summaryConfig.classList.add('hidden');
  summaryLoading.classList.remove('hidden');
  summaryResult.classList.add('hidden');

  try {
    const res = await fetch(`${API}/generate-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pdf_name: pdfName }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error en el servidor');
    }

    const data = await res.json();
    summaryText = data.summary;

    // Extract topic number from PDF name (e.g. "TEMA 1 .pdf" -> "1")
    const topicMatch = pdfName.match(/(\d+)/);
    const topicNum = topicMatch ? topicMatch[1] : 'X';

    summaryTitle.textContent = `Resumen — ${pdfName.replace('.pdf', '')}`;

    // Render markdown
    if (typeof marked !== 'undefined') {
      summaryContent.innerHTML = marked.parse(summaryText);
    } else {
      summaryContent.innerHTML = `<pre style="white-space: pre-wrap;">${summaryText}</pre>`;
    }

    // Show result
    summaryLoading.classList.add('hidden');
    summaryResult.classList.remove('hidden');

  } catch (err) {
    summaryLoading.classList.add('hidden');
    summaryConfig.classList.remove('hidden');
    alert('Error generando resumen: ' + err.message);
  }
}

// ============================================
// Download PDF (instant — browser print-to-PDF via hidden window)
// ============================================
function downloadPdf() {
  // Extract topic number
  const topicMatch = summaryPdfName.match(/(\d+)/);
  const topicNum = topicMatch ? topicMatch[1] : 'X';
  const fileName = `Resumen_Tema${topicNum}`;

  // Render the summary as a standalone printable HTML
  const renderedHtml = typeof marked !== 'undefined' ? marked.parse(summaryText) : `<pre>${summaryText}</pre>`;

  const printHtml = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>${fileName}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    color: #2d2d3a;
    line-height: 1.7;
    padding: 0;
    background: white;
  }

  .header-bar {
    background: linear-gradient(135deg, #6c5ce7, #a855f7);
    color: white;
    padding: 18px 30px;
    margin-bottom: 8px;
  }
  .header-bar h1 { font-size: 18px; font-weight: 700; }

  .meta {
    font-size: 11px;
    color: #999;
    padding: 4px 30px 12px;
    border-bottom: 2px solid #6c5ce7;
    margin-bottom: 20px;
  }

  .content {
    padding: 0 30px 30px;
  }

  h1 { font-size: 20px; font-weight: 800; color: #6c5ce7; margin: 24px 0 12px; }
  h2 { font-size: 16px; font-weight: 700; color: #3a3a50; margin: 20px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #eee; padding-left: 10px; border-left: 4px solid #6c5ce7; }
  h3 { font-size: 14px; font-weight: 600; color: #4a4a60; margin: 14px 0 6px; }
  p { margin-bottom: 8px; font-size: 13px; }
  ul, ol { margin: 6px 0 12px 24px; font-size: 13px; }
  li { margin-bottom: 4px; }
  strong { color: #4a3ab5; }
  blockquote { border-left: 4px solid #6c5ce7; padding: 8px 16px; margin: 10px 0; background: #f8f7ff; border-radius: 0 6px 6px 0; font-size: 13px; color: #555; }
  code { background: #f0f0f5; padding: 1px 5px; border-radius: 3px; font-size: 12px; }

  @media print {
    body { padding: 0; }
    .header-bar { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    @page { margin: 15mm 10mm; size: A4; }
  }
</style>
</head>
<body>
  <div class="header-bar">
    <h1>Resumen — Tema ${topicNum}</h1>
  </div>
  <div class="meta">Generado por MúsicaOpos AI &nbsp;|&nbsp; ${new Date().toLocaleDateString('es-ES')}</div>
  <div class="content">${renderedHtml}</div>
</body>
</html>`;

  // Open a new window and trigger print (save as PDF)
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('El navegador bloqueó la ventana emergente. Permite las ventanas emergentes e inténtalo de nuevo.');
    return;
  }
  printWindow.document.write(printHtml);
  printWindow.document.close();

  // Wait for fonts to load, then print
  printWindow.onload = () => {
    setTimeout(() => {
      printWindow.print();
    }, 300);
  };
}

// ============================================
// Reset
// ============================================
function resetSummary() {
  summaryText = '';
  summaryPdfName = '';
  summaryContent.innerHTML = '';

  summaryConfig.classList.remove('hidden');
  summaryLoading.classList.add('hidden');
  summaryResult.classList.add('hidden');
}
