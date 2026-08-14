/* ════════════════════════════════════════════════════════════
   QUIZ PAGE — Strict cascading filters (each requires previous)
   ════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const API_URL = 'https://api.eduquest-jiit.me';

    // DOM
    const branchSelect   = document.getElementById('branchSelect');
    const semSelect      = document.getElementById('semSelect');
    const subjectSelect  = document.getElementById('subjectSelect');
    const categorySelect = document.getElementById('categorySelect');
    const numQuestions   = document.getElementById('numQuestions');
    const numQVal        = document.getElementById('numQVal');
    const saveToDisk     = document.getElementById('saveToDisk');
    const generateBtn    = document.getElementById('generateBtn');

    const fileSelectList = document.getElementById('fileSelectList');
    const fileCountBadge = document.getElementById('fileCountBadge');
    const fileSelectHint = document.getElementById('fileSelectHint');
    const selectAllBtn   = document.getElementById('selectAllFiles');
    const selectNoneBtn  = document.getElementById('selectNoneFiles');

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
    let browseTree     = {};
    let availableFiles = [];
    let selectedFiles  = new Set();
    let currentQuiz    = null;
    let currentIdx     = 0;
    let userAnswers    = [];
    let revealed       = [];
    let difficulty     = 'Medium';


    // ════════════════════════════════════════
    // LOAD BROWSE TREE (only populates branches)
    // ════════════════════════════════════════
    async function loadBrowseTree() {
        try {
            const res  = await fetch(`${API_URL}/quiz/browse`);
            const data = await res.json();
            browseTree = data.tree || {};

            populateBranches();

            // Everything else starts disabled/empty
            disableDropdown(semSelect,      'Select a branch first');
            disableDropdown(subjectSelect,  'Select a semester first');
            disableDropdown(categorySelect, 'Select a subject first');

            resetFileList('👆 Select branch, semester, and subject to see files');
        } catch (err) {
            console.error('Failed to load tree:', err);
            alert('Cannot connect to backend. Is the API running on port 8000?');
        }
    }


    // ════════════════════════════════════════
    // Helpers: enable/disable dropdowns
    // ════════════════════════════════════════
    function disableDropdown(select, placeholder) {
        select.innerHTML = `<option value="">${placeholder}</option>`;
        select.value = '';
        select.disabled = true;
        select.classList.add('disabled-select');
    }

    function enableDropdown(select, placeholder = '— Select —') {
        select.disabled = false;
        select.classList.remove('disabled-select');
        // don't overwrite options here — caller does that
    }


    // ════════════════════════════════════════
    // POPULATE DROPDOWNS (only when parent is selected)
    // ════════════════════════════════════════

    function populateBranches() {
        branchSelect.innerHTML = '<option value="">— Select branch —</option>';
        Object.keys(browseTree).sort().forEach(b => {
            const opt = document.createElement('option');
            opt.value = b;
            opt.textContent = b;
            branchSelect.appendChild(opt);
        });
        branchSelect.disabled = false;
    }


    function populateSemesters() {
        const branch = branchSelect.value;

        if (!branch) {
            disableDropdown(semSelect, 'Select a branch first');
            return;
        }

        enableDropdown(semSelect);
        semSelect.innerHTML = '<option value="">— Select semester —</option>';

        const sems = Object.keys(browseTree[branch] || {}).sort();
        sems.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s;
            opt.textContent = `Semester ${s}`;
            semSelect.appendChild(opt);
        });
    }


    function populateSubjects() {
        const branch = branchSelect.value;
        const sem    = semSelect.value;

        if (!branch || !sem) {
            disableDropdown(subjectSelect, 'Select a semester first');
            return;
        }

        enableDropdown(subjectSelect);
        subjectSelect.innerHTML = '<option value="">— Select subject —</option>';

        const subjects = Object.keys(browseTree[branch]?.[sem] || {}).sort();
        subjects.forEach(s => {
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

        if (!branch || !sem || !subject) {
            disableDropdown(categorySelect, 'Select a subject first');
            return;
        }

        enableDropdown(categorySelect);
        // Category is optional — user may want "All categories"
        categorySelect.innerHTML = '<option value="">— All categories —</option>';

        const cats = browseTree[branch]?.[sem]?.[subject] || [];
        cats.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            categorySelect.appendChild(opt);
        });
    }


    // ════════════════════════════════════════
    // FILE LIST STATE
    // ════════════════════════════════════════
    function resetFileList(message) {
        fileSelectList.innerHTML = `<div class="file-empty">${message}</div>`;
        fileSelectHint.textContent = '💡 Complete the filters above first.';
        fileCountBadge.textContent = '0';
        fileCountBadge.classList.add('zero');
        selectedFiles.clear();
        availableFiles = [];
    }


    // ════════════════════════════════════════
    // CASCADE ON CHANGE
    // ════════════════════════════════════════
    branchSelect.addEventListener('change', () => {
        // Reset everything downstream
        populateSemesters();
        disableDropdown(subjectSelect,  'Select a semester first');
        disableDropdown(categorySelect, 'Select a subject first');
        resetFileList('👆 Now select a semester');
    });

    semSelect.addEventListener('change', () => {
        populateSubjects();
        disableDropdown(categorySelect, 'Select a subject first');
        resetFileList('👆 Now select a subject');
    });

    subjectSelect.addEventListener('change', () => {
        populateCategories();
        // Now we CAN load files (category is optional)
        if (subjectSelect.value) {
            loadFiles();
        } else {
            resetFileList('👆 Select a subject to see files');
        }
    });

    categorySelect.addEventListener('change', () => {
        // Category is optional — reload files with/without it
        if (subjectSelect.value) {
            loadFiles();
        }
    });


    // ════════════════════════════════════════
    // LOAD FILES matching filters
    // ════════════════════════════════════════
    async function loadFiles() {
        // Must have at least subject selected
        if (!branchSelect.value || !semSelect.value || !subjectSelect.value) {
            resetFileList('👆 Fill in branch, semester, and subject first');
            return;
        }

        const params = new URLSearchParams();
        params.append('branch',  branchSelect.value);
        params.append('sem',     semSelect.value);
        params.append('subject', subjectSelect.value);
        if (categorySelect.value) params.append('category', categorySelect.value);

        fileSelectList.innerHTML = '<div class="file-empty">⏳ Loading files...</div>';
        fileSelectHint.textContent = '⏳ Loading files matching filters...';

        try {
            const res  = await fetch(`${API_URL}/quiz/files?${params}`);
            const data = await res.json();
            availableFiles = data.files || [];

            // Reset selections when filters change
            selectedFiles.clear();

            renderFileList();
            updateSelectionCount();

            if (availableFiles.length === 0) {
                fileSelectHint.textContent = '⚠️ No files match these filters.';
            } else {
                const scope = [
                    branchSelect.value,
                    `Sem ${semSelect.value}`,
                    subjectSelect.value,
                ];
                if (categorySelect.value) scope.push(categorySelect.value);

                fileSelectHint.textContent =
                    `💡 ${availableFiles.length} file(s) in ${scope.join(' / ')}. ` +
                    `Check specific ones, OR leave all unchecked to use everything.`;
            }
        } catch (err) {
            console.error(err);
            fileSelectList.innerHTML = '<div class="file-empty">⚠️ Failed to load files</div>';
            fileSelectHint.textContent = '⚠️ Error loading files';
        }
    }


    // Build a unique key for a file
    function fileKey(f) {
        return `${f.branch}|${f.semester}|${f.subject}|${f.name}`;
    }

    // Natural sort comparator
    // Smart lecture sort — handles L1, L-1, Lec 1, Lecture 1, Chapter 1, etc.
    function naturalCompare(a, b) {
        const keyA = getLectureSortKey(a);
        const keyB = getLectureSortKey(b);

        // Compare tuple: [hasNumber, number, remaining]
        if (keyA[0] !== keyB[0]) return keyA[0] - keyB[0];
        if (keyA[1] !== keyB[1]) return keyA[1] - keyB[1];
        return keyA[2].localeCompare(keyB[2]);
    }

    function getLectureSortKey(text) {
        const s = String(text).toLowerCase().trim();

        // Try patterns in order
        const patterns = [
            // "lecture 15", "lecture-15", "lec 8", "lec-11", "chapter 3"
            /^(?:lecture|lec|chapter|ch|lesson)[\s\-_]*(\d+)/,
            // "l 9", "l-10", "l11", "l_2"
            /^l[\s\-_]*(\d+)/,
            // Fallback: leading number
            /^(\d+)/,
        ];

        for (const pattern of patterns) {
            const m = s.match(pattern);
            if (m) {
                const num = parseInt(m[1], 10);
                const remaining = s.substring(m[0].length).trim();
                return [0, num, remaining];   // 0 = has number, sorts first
            }
        }

        // No number found — sort alphabetically at the end
        return [1, 0, s];   // 1 = no number, sorts last
    }

    function renderFileList() {
        if (availableFiles.length === 0) {
            fileSelectList.innerHTML = '<div class="file-empty">No files match the current filters</div>';
            return;
        }

        availableFiles.sort((a, b) => naturalCompare(a.name, b.name));  

        fileSelectList.innerHTML = availableFiles.map((f) => {
            const key = fileKey(f);
            const isSelected = selectedFiles.has(key);
            const metaParts = [];
            if (f.category)    metaParts.push(`📁 ${escapeHtml(f.category)}`);
            if (f.chunk_count) metaParts.push(`${f.chunk_count} chunks`);

            const linkBtn = f.url
                ? `<a href="${escapeAttr(f.url)}" target="_blank" rel="noopener" class="file-item-link" title="Open original file">🔗</a>`
                : '';

            return `
                <label class="file-item ${isSelected ? 'selected' : ''}" data-key="${escapeAttr(key)}">
                    <input type="checkbox" data-key="${escapeAttr(key)}" ${isSelected ? 'checked' : ''}>
                    <div class="file-item-info">
                        <div class="file-item-name">📄 ${escapeHtml(f.name)}</div>
                        ${metaParts.length ? `<div class="file-item-meta">${metaParts.map(m => `<span>${m}</span>`).join('')}</div>` : ''}
                    </div>
                    ${linkBtn}
                </label>
            `;
        }).join('');

        // Checkbox listeners
        fileSelectList.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const key = e.target.dataset.key;
                const item = e.target.closest('.file-item');
                if (e.target.checked) {
                    selectedFiles.add(key);
                    item.classList.add('selected');
                } else {
                    selectedFiles.delete(key);
                    item.classList.remove('selected');
                }
                updateSelectionCount();
            });
        });

        // Prevent link click from toggling checkbox
        fileSelectList.querySelectorAll('.file-item-link').forEach(link => {
            link.addEventListener('click', (e) => e.stopPropagation());
        });
    }


    function updateSelectionCount() {
        fileCountBadge.textContent = selectedFiles.size;
        fileCountBadge.classList.toggle('zero', selectedFiles.size === 0);
    }


    selectAllBtn.addEventListener('click', () => {
        if (availableFiles.length === 0) return;
        availableFiles.forEach(f => selectedFiles.add(fileKey(f)));
        renderFileList();
        updateSelectionCount();
    });

    selectNoneBtn.addEventListener('click', () => {
        selectedFiles.clear();
        renderFileList();
        updateSelectionCount();
    });


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
    // GENERATE (requires at least subject)
    // ════════════════════════════════════════
    generateBtn.addEventListener('click', async () => {
        // Validation
        if (!branchSelect.value || !semSelect.value || !subjectSelect.value) {
            alert('Please select at least branch, semester, and subject.');
            return;
        }

        const types = [...document.querySelectorAll('.type-chip input:checked')]
                        .map(cb => cb.value);
        if (types.length === 0) {
            alert('Pick at least one question type');
            return;
        }

        const numQ = parseInt(numQuestions.value, 10);
        showSection('loading');

        // Send selected files if any
        let fileList = null;
        if (selectedFiles.size > 0) {
            fileList = availableFiles
                .filter(f => selectedFiles.has(fileKey(f)))
                .map(f => f.name);
        }

        try {
            const res = await fetch(`${API_URL}/quiz/generate`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    branch:         branchSelect.value,
                    sem:            semSelect.value,
                    subject:        subjectSelect.value,
                    category:       categorySelect.value || null,
                    file_names:     fileList,
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
        else if (q.type === 'True/False') {
            html += '<div class="tf-options">';
            ['True', 'False'].forEach(v => {
                const selected = userAnswers[currentIdx] === v ? 'selected' : '';
                html += `<button class="tf-btn ${selected}" data-val="${v}">${v}</button>`;
            });
            html += '</div>';
        }
        else {
            const value  = userAnswers[currentIdx] || '';
            const isLong = q.type === 'Long Answer';
            const rows   = isLong ? 8 : (q.type === 'Short Answer' ? 3 : 2);
            const placeholder = getPlaceholder(q.type);

            html += `
                <div class="answer-input-wrapper">
                    <label class="answer-input-label">✏️ Your Answer:</label>
                    <textarea class="answer-input" id="answerInput" rows="${rows}"
                        placeholder="${placeholder}">${escapeHtml(value)}</textarea>
                    <div class="answer-input-hint">
                        ${q.type === 'Numerical' ? '💡 Include units in your answer' : '💡 Type your answer above'}
                    </div>
                </div>
            `;
        }

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

        if (window.MathJax && window.MathJax.typesetPromise) {
            MathJax.typesetPromise([questionContainer]).catch(err => {
                console.warn('MathJax render error:', err);
            });
        }

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


    // NAVIGATION
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


    // FINISH → SCORE
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


    // RESULTS
    function showResults(score) {
        showSection('results');

        document.getElementById('resultMeta').textContent =
            `${currentQuiz.label} · ${currentQuiz.num_questions} questions · ${currentQuiz.difficulty}`;

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

        const reviewList = document.getElementById('reviewList');
        reviewList.innerHTML = score.results.map((r) => {
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

        if (window.MathJax && window.MathJax.typesetPromise) {
            MathJax.typesetPromise([reviewList]).catch(err => {
                console.warn('MathJax render error:', err);
            });
        }
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


    // HELPERS
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