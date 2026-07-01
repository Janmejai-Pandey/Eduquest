/* ════════════════════════════════════════════════════════════
   QUIZ PAGE — Full version with cascading dropdowns + scoring
   ════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const API_URL = 'http://localhost:8000';

    // DOM
    const branchSelect   = document.getElementById('branchSelect');
    const semSelect      = document.getElementById('semSelect');
    const subjectSelect  = document.getElementById('subjectSelect');
    const categorySelect = document.getElementById('categorySelect');
    const numQuestions   = document.getElementById('numQuestions');
    const numQVal        = document.getElementById('numQVal');
    const saveToDisk     = document.getElementById('saveToDisk');
    const generateBtn    = document.getElementById('generateBtn');

    const setupSection   = document.getElementById('setupSection');
    const loadingSection = document.getElementById('loadingSection');
    const quizSection    = document.getElementById('quizSection');
    const resultsSection = document.getElementById('resultsSection');

    const questionContainer = document.getElementById('questionContainer');
    const prevBtn    = document.getElementById('prevBtn');
    const nextBtn    = document.getElementById('nextBtn');
    const finishBtn  = document.getElementById('finishBtn');
    const revealBtn  = document.getElementById('revealBtn');

    // State
    let browseTree   = {};
    let currentQuiz  = null;
    let currentIdx   = 0;
    let userAnswers  = [];
    let revealed     = [];
    let difficulty   = 'Medium';


    // ════════════════════════════════════════
    // LOAD BROWSE TREE
    // ════════════════════════════════════════
    async function loadBrowseTree() {
        try {
            const res  = await fetch(`${API_URL}/quiz/browse`);
            const data = await res.json();
            browseTree = data.tree || {};

            console.log('📚 Browse tree:', browseTree);

            // Populate branch dropdown
            branchSelect.innerHTML = '<option value="">— All branches —</option>';
            Object.keys(browseTree).sort().forEach(b => {
                const opt = document.createElement('option');
                opt.value = b;
                opt.textContent = b;
                branchSelect.appendChild(opt);
            });

            populateSemesters();
            populateSubjects();
            populateCategories();
        } catch (err) {
            console.error('Failed to load tree:', err);
            alert('Cannot connect to backend. Is the API running on port 8000?');
        }
    }

    function populateSemesters() {
        const branch = branchSelect.value;
        semSelect.innerHTML = '<option value="">— All semesters —</option>';

        const sems = new Set();
        if (branch) {
            Object.keys(browseTree[branch] || {}).forEach(s => sems.add(s));
        } else {
            Object.values(browseTree).forEach(bSems => {
                Object.keys(bSems).forEach(s => sems.add(s));
            });
        }

        [...sems].sort().forEach(s => {
            const opt = document.createElement('option');
            opt.value = s;
            opt.textContent = `Semester ${s}`;
            semSelect.appendChild(opt);
        });
    }

    function populateSubjects() {
        const branch = branchSelect.value;
        const sem    = semSelect.value;
        subjectSelect.innerHTML = '<option value="">— All subjects —</option>';

        const subjects = new Set();

        if (branch && sem) {
            Object.keys(browseTree[branch]?.[sem] || {}).forEach(s => subjects.add(s));
        } else if (branch) {
            Object.values(browseTree[branch] || {}).forEach(subs => {
                Object.keys(subs).forEach(s => subjects.add(s));
            });
        } else if (sem) {
            Object.values(browseTree).forEach(bSems => {
                if (bSems[sem]) {
                    Object.keys(bSems[sem]).forEach(s => subjects.add(s));
                }
            });
        } else {
            Object.values(browseTree).forEach(bSems => {
                Object.values(bSems).forEach(subs => {
                    Object.keys(subs).forEach(s => subjects.add(s));
                });
            });
        }

        [...subjects].sort().forEach(s => {
            const opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            subjectSelect.appendChild(opt);
        });
    }

    function populateCategories() {
        const branch  = branchSelect.value;
        const sem     = semSelect.value;
        const subject = subjectSelect.value;

        categorySelect.innerHTML = '<option value="">— All categories —</option>';

        const cats = new Set();

        function collectCatsFromSubjects(subs) {
            Object.entries(subs).forEach(([subjName, catList]) => {
                if (!subject || subject === subjName) {
                    catList.forEach(c => cats.add(c));
                }
            });
        }

        if (branch && sem) {
            collectCatsFromSubjects(browseTree[branch]?.[sem] || {});
        } else if (branch) {
            Object.values(browseTree[branch] || {}).forEach(subs => {
                collectCatsFromSubjects(subs);
            });
        } else if (sem) {
            Object.values(browseTree).forEach(bSems => {
                if (bSems[sem]) collectCatsFromSubjects(bSems[sem]);
            });
        } else {
            Object.values(browseTree).forEach(bSems => {
                Object.values(bSems).forEach(subs => collectCatsFromSubjects(subs));
            });
        }

        [...cats].sort().forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            categorySelect.appendChild(opt);
        });
    }

    // Cascade updates
    branchSelect.addEventListener('change', () => {
        populateSemesters();
        populateSubjects();
        populateCategories();
    });

    semSelect.addEventListener('change', () => {
        populateSubjects();
        populateCategories();
    });

    subjectSelect.addEventListener('change', populateCategories);


    // ════════════════════════════════════════
    // UI CONTROLS
    // ════════════════════════════════════════
    numQuestions.addEventListener('input', e => {
        const v = parseInt(e.target.value, 10);
        numQVal.textContent = v === 0 ? 'Auto' : v;
    });

    document.querySelectorAll('.type-chip').forEach(chip => {
        const cb = chip.querySelector('input');
        cb.addEventListener('change', () => {
            chip.classList.toggle('selected', cb.checked);
        });
    });

    document.querySelectorAll('.diff-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            difficulty = btn.dataset.diff;
        });
    });


    // ════════════════════════════════════════
    // GENERATE
    // ════════════════════════════════════════
    generateBtn.addEventListener('click', async () => {
        const types = [...document.querySelectorAll('.type-chip input:checked')]
                        .map(cb => cb.value);
        if (types.length === 0) {
            alert('Pick at least one question type');
            return;
        }

        const numQ = parseInt(numQuestions.value, 10);
        showSection('loading');

        try {
            const res = await fetch(`${API_URL}/quiz/generate`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    branch:         branchSelect.value   || null,
                    sem:            semSelect.value      || null,
                    subject:        subjectSelect.value  || null,
                    category:       categorySelect.value || null,
                    question_types: types,
                    difficulty:     difficulty,
                    num_questions:  numQ === 0 ? null : numQ,
                    save_to_disk:   saveToDisk.checked,
                }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `HTTP ${res.status}`);
            }

            currentQuiz = await res.json();
            currentIdx  = 0;
            userAnswers = new Array(currentQuiz.questions.length).fill(null);
            revealed    = new Array(currentQuiz.questions.length).fill(false);

            startQuiz();

        } catch (err) {
            alert('Error: ' + err.message);
            showSection('setup');
        }
    });


    // ════════════════════════════════════════
    // RENDER QUIZ
    // ════════════════════════════════════════
    function startQuiz() {
        showSection('quiz');
        document.getElementById('quizTitle').textContent = currentQuiz.label || 'Quiz';
        document.getElementById('quizMeta').textContent =
            `${currentQuiz.num_questions} questions · ${currentQuiz.difficulty} · ${currentQuiz.question_types.join(', ')}`;
        document.getElementById('totalQ').textContent = currentQuiz.num_questions;
        renderQuestion();
    }

    function renderQuestion() {
        const q = currentQuiz.questions[currentIdx];
        const total = currentQuiz.questions.length;

        document.getElementById('currentQ').textContent = currentIdx + 1;
        document.getElementById('progressFill').style.width = `${((currentIdx + 1) / total) * 100}%`;

        let html = '';
        html += `<div class="question-type">${escapeHtml(q.type || 'Question')}</div>`;
        html += `<div class="question-text">${escapeHtml(q.question_text)}</div>`;

        // ── MCQ ──
        if (q.type === 'MCQ' && q.options && q.options.length) {
            html += '<div class="options-list">';
            q.options.forEach(opt => {
                const selected = userAnswers[currentIdx] === opt.letter ? 'selected' : '';
                let extra = '';
                if (revealed[currentIdx]) {
                    const correctLetter = extractCorrectLetter(q.answer);
                    if (opt.letter === correctLetter)                extra = 'correct';
                    else if (opt.letter === userAnswers[currentIdx]) extra = 'wrong';
                }
                html += `
                    <div class="option-item ${selected} ${extra}" data-letter="${opt.letter}">
                        <div class="option-letter">${opt.letter}</div>
                        <div>${escapeHtml(opt.text)}</div>
                    </div>
                `;
            });
            html += '</div>';
        }
        // ── True/False ──
        else if (q.type === 'True/False') {
            html += '<div class="tf-options">';
            ['True', 'False'].forEach(v => {
                const selected = userAnswers[currentIdx] === v ? 'selected' : '';
                html += `<button class="tf-btn ${selected}" data-val="${v}">${v}</button>`;
            });
            html += '</div>';
        }
        // ── Text input (Fill/Short/Long/Numerical) ──
        else {
            const value  = userAnswers[currentIdx] || '';
            const isLong = q.type === 'Long Answer';
            const rows   = isLong ? 8 : (q.type === 'Short Answer' ? 3 : 2);
            const placeholder = getPlaceholder(q.type);

            html += `
                <div class="answer-input-wrapper">
                    <label class="answer-input-label">✏️ Your Answer:</label>
                    <textarea
                        class="answer-input"
                        id="answerInput"
                        rows="${rows}"
                        placeholder="${placeholder}">${escapeHtml(value)}</textarea>
                    <div class="answer-input-hint">
                        ${q.type === 'Numerical' ? '💡 Include units in your answer' : '💡 Type your answer above'}
                    </div>
                </div>
            `;
        }

        // Show answer if revealed
        if (revealed[currentIdx] && q.answer) {
            html += `
                <div class="answer-reveal">
                    <h4>✅ Correct Answer</h4>
                    <div class="answer-text">${escapeHtml(q.answer)}</div>
                    ${q.explanation ? `<div class="explanation-text">💡 <strong>Explanation:</strong> ${escapeHtml(q.explanation)}</div>` : ''}
                </div>
            `;
        }

        questionContainer.innerHTML = html;

        // Attach handlers
        questionContainer.querySelectorAll('.option-item[data-letter]').forEach(el => {
            el.addEventListener('click', () => {
                if (revealed[currentIdx]) return;
                questionContainer.querySelectorAll('.option-item').forEach(x => x.classList.remove('selected'));
                el.classList.add('selected');
                userAnswers[currentIdx] = el.dataset.letter;
            });
        });

        questionContainer.querySelectorAll('.tf-btn').forEach(el => {
            el.addEventListener('click', () => {
                questionContainer.querySelectorAll('.tf-btn').forEach(x => x.classList.remove('selected'));
                el.classList.add('selected');
                userAnswers[currentIdx] = el.dataset.val;
            });
        });

        const inputEl = document.getElementById('answerInput');
        if (inputEl) {
            inputEl.addEventListener('input', e => {
                userAnswers[currentIdx] = e.target.value;
            });
        }

        // Buttons
        prevBtn.disabled = currentIdx === 0;
        const isLast = currentIdx === total - 1;
        nextBtn.style.display   = isLast ? 'none' : 'inline-block';
        finishBtn.style.display = isLast ? 'inline-block' : 'none';
        revealBtn.textContent = revealed[currentIdx] ? '🙈 Hide Answer' : '👁️ Show Answer';
    }

    function getPlaceholder(type) {
        const map = {
            'Fill in the Blanks': 'Type the word(s) to fill the blank...',
            'Numerical':          'Enter your numerical answer with units (e.g., 42 m/s)',
            'Short Answer':       'Write a concise 1-2 line answer...',
            'Long Answer':        'Write a detailed answer with structured points...',
        };
        return map[type] || 'Type your answer here...';
    }

    function extractCorrectLetter(answerText) {
        const m = String(answerText).match(/\b([A-D])\b/);
        return m ? m[1] : null;
    }


    // ════════════════════════════════════════
    // NAVIGATION
    // ════════════════════════════════════════
    prevBtn.addEventListener('click', () => {
        if (currentIdx > 0) { currentIdx--; renderQuestion(); }
    });

    nextBtn.addEventListener('click', () => {
        if (currentIdx < currentQuiz.questions.length - 1) {
            currentIdx++;
            renderQuestion();
        }
    });

    revealBtn.addEventListener('click', () => {
        revealed[currentIdx] = !revealed[currentIdx];
        renderQuestion();
    });


    // ════════════════════════════════════════
    // FINISH → SCORE
    // ════════════════════════════════════════
    finishBtn.addEventListener('click', async () => {
        const unanswered = userAnswers.filter(a => !a || a === '').length;
        if (unanswered > 0) {
            if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
        }

        showSection('loading');

        try {
            const res = await fetch(`${API_URL}/quiz/score`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    questions:    currentQuiz.questions,
                    user_answers: userAnswers,
                }),
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const score = await res.json();
            showResults(score);

        } catch (err) {
            alert('Error scoring: ' + err.message);
            showSection('quiz');
        }
    });


    // ════════════════════════════════════════
    // RESULTS
    // ════════════════════════════════════════
    function showResults(score) {
        showSection('results');

        document.getElementById('resultMeta').textContent =
            `${currentQuiz.label} · ${currentQuiz.num_questions} questions · ${currentQuiz.difficulty}`;

        // Score card
        const scoreCard = document.getElementById('scoreCard');
        scoreCard.innerHTML = `
            <div class="score-grade">${score.grade}</div>
            <div class="score-tier">${escapeHtml(score.tier)}</div>
            <div class="score-numbers">
                <div class="score-num-item">
                    <div class="score-num-val">${score.auto_correct}/${score.auto_total}</div>
                    <div class="score-num-label">Auto-graded</div>
                </div>
                <div class="score-num-item">
                    <div class="score-num-val">${score.percentage}%</div>
                    <div class="score-num-label">Accuracy</div>
                </div>
                ${score.manual_review > 0 ? `
                <div class="score-num-item">
                    <div class="score-num-val">${score.manual_review}</div>
                    <div class="score-num-label">Manual Review</div>
                </div>` : ''}
            </div>
        `;

        // Sources
        const sourcesBlock = document.getElementById('sourcesBlock');
        if (currentQuiz.sources && currentQuiz.sources.length) {
            sourcesBlock.innerHTML = `
                <h4>📚 Source Files Used</h4>
                <ul>
                    ${currentQuiz.sources.map(s => s.url
                        ? `<li><a href="${escapeAttr(s.url)}" target="_blank">📄 ${escapeHtml(s.name)}</a></li>`
                        : `<li>📄 ${escapeHtml(s.name)}</li>`
                    ).join('')}
                </ul>
            `;
        } else {
            sourcesBlock.innerHTML = '';
        }

        // Review
        const reviewList = document.getElementById('reviewList');
        reviewList.innerHTML = score.results.map((r, i) => {
            let cls = '';
            let statusIcon = '';
            if (r.needs_review) {
                cls = 'needs-review';
                statusIcon = '📝';
            } else if (r.is_correct) {
                cls = 'correct';
                statusIcon = '✅';
            } else {
                cls = 'wrong';
                statusIcon = '❌';
            }

            let optionsHtml = '';
            if (r.type === 'MCQ' && r.options && r.options.length) {
                optionsHtml = '<div class="review-options">';
                r.options.forEach(opt => {
                    let optCls = '';
                    if (opt.letter === r.correct_letter) optCls = 'correct-option';
                    if (opt.letter === r.user_answer && opt.letter !== r.correct_letter) optCls = 'wrong-option';
                    optionsHtml += `<div class="${optCls}">(${opt.letter}) ${escapeHtml(opt.text)}</div>`;
                });
                optionsHtml += '</div>';
            }

            return `
                <div class="review-item ${cls}">
                    <div class="review-header">
                        <span class="review-q-num">${statusIcon} ${escapeHtml(r.number)}</span>
                        <span class="review-q-type">${escapeHtml(r.type)}</span>
                    </div>
                    <div class="review-q">${escapeHtml(r.question)}</div>
                    ${optionsHtml}
                    <div class="review-user">
                        <strong>Your answer:</strong> ${escapeHtml(String(r.user_answer || '(not answered)'))}
                    </div>
                    ${r.correct_answer ? `<div class="review-ans"><strong>✓ Correct:</strong> ${escapeHtml(r.correct_answer)}</div>` : ''}
                    ${r.explanation ? `<div class="review-exp">💡 ${escapeHtml(r.explanation)}</div>` : ''}
                </div>
            `;
        }).join('');
    }

    document.getElementById('retryBtn').addEventListener('click', () => {
        showSection('setup');
    });

    document.getElementById('downloadBtn').addEventListener('click', () => {
        if (!currentQuiz?.quiz_text) return;

        let content = `# Quiz: ${currentQuiz.label}\n\n`;
        content += `**Difficulty:** ${currentQuiz.difficulty}\n`;
        content += `**Questions:** ${currentQuiz.num_questions}\n\n`;

        if (currentQuiz.sources?.length) {
            content += `## Source Files\n\n`;
            currentQuiz.sources.forEach(s => {
                content += s.url ? `- [${s.name}](${s.url})\n` : `- ${s.name}\n`;
            });
            content += `\n---\n\n`;
        }

        content += currentQuiz.quiz_text;

        const blob = new Blob([content], { type: 'text/markdown' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = `quiz_${Date.now()}.md`;
        a.click();
        URL.revokeObjectURL(url);
    });

    document.getElementById('printBtn').addEventListener('click', () => window.print());


    // ════════════════════════════════════════
    // HELPERS
    // ════════════════════════════════════════
    function showSection(name) {
        setupSection.style.display   = name === 'setup'   ? 'block' : 'none';
        loadingSection.style.display = name === 'loading' ? 'block' : 'none';
        quizSection.style.display    = name === 'quiz'    ? 'block' : 'none';
        resultsSection.style.display = name === 'results' ? 'block' : 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }

    function escapeAttr(str) {
        return escapeHtml(str).replace(/"/g, '&quot;');
    }

    // INIT
    loadBrowseTree();
    console.log('🎯 Quiz page ready');

})();