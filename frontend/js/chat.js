/**
 * MúsicaOpos AI — Chat Page JavaScript
 * Handles messaging, streaming, file upload, markdown rendering
 */

const API_BASE = '/api';
const API_BASE_URL = "https://opos-ia-backend.onrender.com";

// ============================================
// Auth Guard
// ============================================
(function checkAuth() {
  if (sessionStorage.getItem('musicaopos_auth') !== 'true') {
    window.location.href = 'login.html';
  }
})();

function getUserName() {
  return sessionStorage.getItem('musicaopos_user') || 'Usuario';
}

// ============================================
// State
// ============================================
let isGenerating = false;

// ============================================
// DOM Elements
// ============================================
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const uploadBtn = document.getElementById('upload-btn');
const fileInput = document.getElementById('file-input');
const ingestBtn = document.getElementById('ingest-btn');

// ============================================
// Markdown & Math Rendering
// ============================================
function buildSourcesHtml(sources) {
  const cards = sources.map((s, i) => {
    const filename = (s.source || 'desconocido').replace(/^.*[\\\/]/, '');
    const page = s.page || '?';
    const score = s.score ? (s.score * 100).toFixed(0) : '—';
    const preview = s.preview || '';
    const relevanceClass = s.score <= 1.0 ? 'high' : s.score <= 1.5 ? 'medium' : 'low';
    return `
      <div class="source-card" onclick="this.classList.toggle('expanded')">
        <div class="source-card-header">
          <div class="source-card-icon">📄</div>
          <div class="source-card-info">
            <span class="source-card-name" title="${s.source || ''}">${filename}</span>
            <span class="source-card-meta">Página ${page}</span>
          </div>
          <div class="source-card-badge ${relevanceClass}">${relevanceClass === 'high' ? 'Alta' : relevanceClass === 'medium' ? 'Media' : 'Baja'} relevancia</div>
          <div class="source-card-chevron">▾</div>
        </div>
        <div class="source-card-preview">
          <div class="source-card-preview-text">${preview}</div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="sources-panel">
      <div class="sources-panel-header">
        <span class="sources-panel-icon">📚</span>
        <span class="sources-panel-title">Fuentes consultadas</span>
        <span class="sources-panel-count">${sources.length} fuente${sources.length > 1 ? 's' : ''}</span>
      </div>
      <div class="sources-panel-cards">
        ${cards}
      </div>
    </div>
  `;
}

function renderMarkdown(text) {
  // Replace LaTeX math delimiters for rendering
  let rendered = text;

  // Block math: $$...$$
  rendered = rendered.replace(/\$\$([\s\S]*?)\$\$/g, (match, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
    } catch (e) {
      return match;
    }
  });

  // Inline math: $...$
  rendered = rendered.replace(/\$([^\$\n]+?)\$/g, (match, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
    } catch (e) {
      return match;
    }
  });

  // Parse markdown
  if (typeof marked !== 'undefined') {
    marked.setOptions({
      breaks: true,
      gfm: true,
    });
    rendered = marked.parse(rendered);
  }

  return rendered;
}

// ============================================
// Message Creation
// ============================================
function addMessage(role, content, sources = null) {
  // Remove welcome message if present
  const welcome = chatMessages.querySelector('.welcome-message');
  if (welcome) welcome.remove();

  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;

  const avatarEmoji = role === 'assistant' ? '🎵' : '👤';

  let sourcesHtml = '';
  if (sources && sources.length > 0) {
    sourcesHtml = buildSourcesHtml(sources);
  }

  messageDiv.innerHTML = `
    <div class="message-avatar">${avatarEmoji}</div>
    <div class="message-body">
      <div class="message-content">${renderMarkdown(content)}</div>
      ${sourcesHtml}
    </div>
  `;

  chatMessages.appendChild(messageDiv);
  scrollToBottom();
  return messageDiv;
}

function addTypingIndicator() {
  const welcome = chatMessages.querySelector('.welcome-message');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = 'message assistant';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="message-avatar">🎵</div>
    <div class="message-body">
      <div class="message-content">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  `;
  chatMessages.appendChild(div);
  scrollToBottom();
  return div;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============================================
// Streaming Response
// ============================================
async function sendMessage(question) {
  if (!question.trim() || isGenerating) return;

  isGenerating = true;
  sendBtn.disabled = true;
  chatInput.value = '';
  autoResizeInput();

  // Add user message
  addMessage('user', question);

  // Add typing indicator
  addTypingIndicator();

  try {
    const response = await fetch(`${API_BASE_URL}/api/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, k: 5 }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    removeTypingIndicator();

    // Create assistant message container
    const messageDiv = addMessage('assistant', '');
    const contentEl = messageDiv.querySelector('.message-content');

    let fullText = '';
    let sources = [];

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            break;
          }

          if (data.startsWith('[SOURCES]')) {
            try {
              sources = JSON.parse(data.slice(9));
            } catch (e) {
              console.error('Error parsing sources:', e);
            }
            continue;
          }

          if (data.startsWith('[ERROR]')) {
            fullText += `\n\n⚠️ Error: ${data.slice(7)}`;
            continue;
          }

          fullText += data;
          contentEl.innerHTML = renderMarkdown(fullText);
          scrollToBottom();
        }
      }
    }

    // Add sources if available
    if (sources.length > 0) {
      const bodyEl = messageDiv.querySelector('.message-body');
      bodyEl.insertAdjacentHTML('beforeend', buildSourcesHtml(sources));
    }

  } catch (error) {
    removeTypingIndicator();
    console.error('Error:', error);

    // Fallback: try non-streaming endpoint
    try {
      const fallbackRes = await fetch(`${API_BASE_URL}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, k: 5 }),
      });

      if (fallbackRes.ok) {
        const data = await fallbackRes.json();
        addMessage('assistant', data.answer, data.sources);
      } else {
        addMessage('assistant', `⚠️ Error al conectar con el servidor. Asegúrate de que:\n\n1. El backend está ejecutándose (\`uvicorn app.main:app\`)\n2. Ollama está activo con Llama 3.1 (\`ollama run llama3.1\`)\n3. Los PDFs han sido indexados (\`/api/ingest\`)`);
      }
    } catch (e) {
      addMessage('assistant', `⚠️ No se puede conectar con el servidor.\n\nAsegúrate de que el backend está ejecutándose en el puerto 8000.`);
    }
  } finally {
    isGenerating = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// ============================================
// Auto-resize textarea
// ============================================
function autoResizeInput() {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
}

// ============================================
// File Upload
// ============================================
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    addMessage('assistant', `📤 Subiendo **${file.name}**...`);

    const res = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      addMessage('assistant', `✅ **${data.filename}** subido correctamente.\n\nAhora pulsa "🔄 Indexar documentos" para procesar el PDF.`);
    } else {
      const err = await res.json();
      addMessage('assistant', `❌ Error al subir: ${err.detail || 'Unknown error'}`);
    }
  } catch (e) {
    addMessage('assistant', `❌ Error de conexión al subir el archivo.`);
  }
}

async function ingestDocuments() {
  try {
    addMessage('assistant', '🔄 Indexando documentos... Esto puede tardar unos minutos.');

    const res = await fetch(`${API_BASE_URL}/api/ingest`, { method: 'POST' });

    if (res.ok) {
      const data = await res.json();
      addMessage('assistant', `✅ **Indexación completada**\n\n${data.message}\n\nTotal chunks: **${data.chunks}**`);
      loadSidebarStats();
    } else {
      const err = await res.json();
      addMessage('assistant', `❌ Error al indexar: ${err.detail || 'Unknown error'}`);
    }
  } catch (e) {
    addMessage('assistant', `❌ Error de conexión al indexar documentos.`);
  }
}

// ============================================
// Load sidebar stats
// ============================================
async function loadSidebarStats() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/stats`);
    if (res.ok) {
      const data = await res.json();
      const chunksEl = document.getElementById('sidebar-chunks');
      if (chunksEl) chunksEl.textContent = data.chunks || '0';

      const statusEl = document.getElementById('sidebar-status');
      if (statusEl) {
        statusEl.textContent = data.status === 'active' ? '● Activo' : '○ Sin datos';
        statusEl.style.color = data.status === 'active' ? 'var(--green)' : 'var(--yellow)';
      }
    }
  } catch (e) {
    console.log('API not available');
  }
}

// ============================================
// Event Listeners
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  // Send message
  sendBtn.addEventListener('click', () => {
    sendMessage(chatInput.value);
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(chatInput.value);
    }
  });

  chatInput.addEventListener('input', autoResizeInput);

  // Suggested questions
  document.querySelectorAll('.suggested-q').forEach(el => {
    el.addEventListener('click', () => {
      sendMessage(el.dataset.q);
    });
  });

  // Topic list clicks
  document.querySelectorAll('.topic-list li').forEach(el => {
    el.addEventListener('click', () => {
      sendMessage(el.dataset.q);
    });
  });

  // File upload
  uploadBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
      e.target.value = '';
    }
  });

  // Ingest
  ingestBtn.addEventListener('click', ingestDocuments);

  // Load stats
  loadSidebarStats();

  // Set user name in topbar
  const userNameEl = document.getElementById('user-name');
  if (userNameEl) userNameEl.textContent = getUserName();

  // Logout
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      sessionStorage.removeItem('musicaopos_auth');
      sessionStorage.removeItem('musicaopos_user');
      window.location.href = 'login.html';
    });
  }

  // Focus input
  chatInput.focus();
});
