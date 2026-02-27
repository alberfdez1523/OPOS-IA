/**
 * MúsicaOpos AI — Test Page
 * Standalone test generator page
 */

const TEST_API = 'http://localhost:8000/api';

// ============================================
// State
// ============================================
let testData = null;
let currentQuestion = 0;
let userAnswers = {};
let testScore = 0;
let testAnswered = 0;
let selectedDifficulty = 'medio';
let isReviewMode = false;

// ============================================
// DOM References
// ============================================
const testConfig = document.getElementById('test-config');
const testLoading = document.getElementById('test-loading');
const testQuestions = document.getElementById('test-questions');
const testResults = document.getElementById('test-results');
const testPdfSelect = document.getElementById('test-pdf-select');
const testGenerateBtn = document.getElementById('test-generate-btn');
const testQuestionContainer = document.getElementById('test-question-container');
const testProgressFill = document.getElementById('test-progress-fill');
const testQuestionCounter = document.getElementById('test-question-counter');
const testScoreEl = document.getElementById('test-score');
const testPrevBtn = document.getElementById('test-prev-btn');
const testNextBtn = document.getElementById('test-next-btn');

// ============================================
// Auth Guard
// ============================================
(function checkAuth() {
  if (sessionStorage.getItem('musicaopos_auth') !== 'true') {
    window.location.href = 'login.html';
  }
})();

// ============================================
// Reset
// ============================================
function resetTest() {
  testData = null;
  currentQuestion = 0;
  userAnswers = {};
  testScore = 0;
  testAnswered = 0;
  isReviewMode = false;

  testConfig.classList.remove('hidden');
  testLoading.classList.add('hidden');
  testQuestions.classList.add('hidden');
  testResults.classList.add('hidden');
}

// ============================================
// Load PDF List
// ============================================
async function loadPdfList() {
  try {
    const res = await fetch(`${TEST_API}/pdfs`);
    if (res.ok) {
      const data = await res.json();
      testPdfSelect.innerHTML = '';
      if (data.pdfs.length === 0) {
        testPdfSelect.innerHTML = '<option value="">No hay PDFs disponibles</option>';
        return;
      }
      data.pdfs.forEach(pdf => {
        const opt = document.createElement('option');
        opt.value = pdf;
        opt.textContent = pdf.replace('.pdf', '');
        testPdfSelect.appendChild(opt);
      });
    }
  } catch (e) {
    testPdfSelect.innerHTML = '<option value="">Error al cargar PDFs</option>';
  }
}

// ============================================
// Load sidebar stats
// ============================================
async function loadSidebarStats() {
  try {
    const res = await fetch(`${TEST_API}/stats`);
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
// Generate Test
// ============================================
async function generateTest() {
  const pdfName = testPdfSelect.value;
  if (!pdfName) {
    alert('Selecciona un PDF primero');
    return;
  }

  testConfig.classList.add('hidden');
  testLoading.classList.remove('hidden');

  try {
    const res = await fetch(`${TEST_API}/generate-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pdf_name: pdfName,
        difficulty: selectedDifficulty,
        num_questions: 10,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error generando test');
    }

    const data = await res.json();
    testData = data.test;
    currentQuestion = 0;
    userAnswers = {};
    testScore = 0;
    testAnswered = 0;
    isReviewMode = false;

    testLoading.classList.add('hidden');
    testQuestions.classList.remove('hidden');
    renderQuestion();
  } catch (e) {
    testLoading.classList.add('hidden');
    testConfig.classList.remove('hidden');
    alert(`Error: ${e.message}`);
  }
}

// ============================================
// Render Question
// ============================================
function renderQuestion() {
  if (!testData || !testData.questions) return;

  const q = testData.questions[currentQuestion];
  const total = testData.questions.length;
  const answered = userAnswers[currentQuestion] !== undefined;

  // Update progress
  testProgressFill.style.width = `${((currentQuestion + 1) / total) * 100}%`;
  testQuestionCounter.textContent = `Pregunta ${currentQuestion + 1} de ${total}`;
  testScoreEl.textContent = `Aciertos: ${testScore}/${testAnswered}`;

  // Build question HTML
  let optionsHtml = '';
  const letters = ['A', 'B', 'C', 'D'];

  letters.forEach(letter => {
    const optText = q.options[letter];
    if (!optText) return;

    let stateClass = '';
    let indicator = '';

    if (answered || isReviewMode) {
      const userPick = userAnswers[currentQuestion];
      if (letter === q.correct) {
        stateClass = 'correct';
        indicator = '<span class="option-indicator">✓</span>';
      } else if (letter === userPick && userPick !== q.correct) {
        stateClass = 'incorrect';
        indicator = '<span class="option-indicator">✗</span>';
      } else {
        stateClass = 'disabled';
      }
    }

    optionsHtml += `
      <button class="test-option ${stateClass}" data-letter="${letter}" ${answered ? 'disabled' : ''}>
        <span class="option-letter">${letter}</span>
        <span class="option-text">${optText}</span>
        ${indicator}
      </button>
    `;
  });

  // Explanation (only after answering)
  let explanationHtml = '';
  if (answered || isReviewMode) {
    const isCorrect = userAnswers[currentQuestion] === q.correct;
    explanationHtml = `
      <div class="test-explanation ${isCorrect ? 'correct' : 'incorrect'}">
        <div class="explanation-header">
          ${isCorrect ? '✅ ¡Correcto!' : '❌ Incorrecto — La respuesta correcta es ' + q.correct}
        </div>
        <div class="explanation-text">${q.explanation}</div>
      </div>
    `;
  }

  testQuestionContainer.innerHTML = `
    <div class="test-question-card">
      <div class="test-question-number">Pregunta ${currentQuestion + 1}</div>
      <div class="test-question-text">${q.question}</div>
      <div class="test-options">
        ${optionsHtml}
      </div>
      ${explanationHtml}
    </div>
  `;

  // Navigation
  testPrevBtn.disabled = currentQuestion === 0;
  if (currentQuestion === total - 1 && testAnswered === total) {
    testNextBtn.textContent = '📊 Ver resultados';
    testNextBtn.disabled = false;
  } else if (currentQuestion < total - 1) {
    testNextBtn.textContent = 'Siguiente →';
    testNextBtn.disabled = !answered;
  } else {
    testNextBtn.textContent = 'Siguiente →';
    testNextBtn.disabled = true;
  }

  // Bind option click handlers
  if (!answered && !isReviewMode) {
    document.querySelectorAll('.test-option').forEach(btn => {
      btn.addEventListener('click', () => selectAnswer(btn.dataset.letter));
    });
  }
}

// ============================================
// Select Answer
// ============================================
function selectAnswer(letter) {
  if (userAnswers[currentQuestion] !== undefined) return;

  const q = testData.questions[currentQuestion];
  userAnswers[currentQuestion] = letter;
  testAnswered++;

  if (letter === q.correct) {
    testScore++;
  }

  renderQuestion();
}

// ============================================
// Navigation
// ============================================
function goNextQuestion() {
  if (!testData) return;
  const total = testData.questions.length;
  if (currentQuestion === total - 1 && testAnswered === total) {
    showResults();
    return;
  }
  if (currentQuestion < total - 1) {
    currentQuestion++;
    renderQuestion();
  }
}

function goPrevQuestion() {
  if (currentQuestion > 0) {
    currentQuestion--;
    renderQuestion();
  }
}

// ============================================
// Results
// ============================================
function showResults() {
  testQuestions.classList.add('hidden');
  testResults.classList.remove('hidden');

  const total = testData.questions.length;
  const pct = Math.round((testScore / total) * 100);

  document.getElementById('test-results-number').textContent = `${testScore}/${total}`;

  let icon, title, msg;
  if (pct >= 80) {
    icon = '🏆'; title = '¡Excelente!'; msg = 'Dominas este tema. ¡Sigue así!';
  } else if (pct >= 60) {
    icon = '👍'; title = '¡Bien hecho!'; msg = 'Buen nivel, repasa los fallos para mejorar.';
  } else if (pct >= 40) {
    icon = '📚'; title = 'Necesitas repasar'; msg = 'Revisa el temario y vuelve a intentarlo.';
  } else {
    icon = '💪'; title = 'No te rindas'; msg = 'Estudia el tema con más profundidad y vuelve a intentarlo.';
  }

  document.getElementById('test-results-icon').textContent = icon;
  document.getElementById('test-results-title').textContent = title;
  document.getElementById('test-results-msg').textContent = msg;
}

function reviewAnswers() {
  testResults.classList.add('hidden');
  testQuestions.classList.remove('hidden');
  isReviewMode = true;
  currentQuestion = 0;
  renderQuestion();
}

// ============================================
// Event Listeners
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  loadPdfList();
  loadSidebarStats();

  // Difficulty selector
  document.getElementById('diff-medio').addEventListener('click', () => {
    selectedDifficulty = 'medio';
    document.getElementById('diff-medio').classList.add('active');
    document.getElementById('diff-dificil').classList.remove('active');
  });

  document.getElementById('diff-dificil').addEventListener('click', () => {
    selectedDifficulty = 'dificil';
    document.getElementById('diff-dificil').classList.add('active');
    document.getElementById('diff-medio').classList.remove('active');
  });

  // Generate
  testGenerateBtn.addEventListener('click', generateTest);

  // Navigation
  testNextBtn.addEventListener('click', goNextQuestion);
  testPrevBtn.addEventListener('click', goPrevQuestion);

  // Results actions
  document.getElementById('test-review-btn').addEventListener('click', reviewAnswers);
  document.getElementById('test-retry-btn').addEventListener('click', () => {
    resetTest();
    loadPdfList();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (!testData || testQuestions.classList.contains('hidden')) return;
    if (e.key === 'ArrowRight') goNextQuestion();
    if (e.key === 'ArrowLeft') goPrevQuestion();
    if (['a','b','c','d'].includes(e.key.toLowerCase()) && userAnswers[currentQuestion] === undefined && !isReviewMode) {
      selectAnswer(e.key.toUpperCase());
    }
  });
});
