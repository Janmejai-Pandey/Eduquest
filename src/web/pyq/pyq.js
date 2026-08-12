/* ════════════════════════════════════════════════════════════
   PYQ ANALYSER — Dynamic year loading with MathJax support
   ════════════════════════════════════════════════════════════ */

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}


function init() {
    console.log('🔥 PYQ Analyser initializing...');

    const $ = (id) => document.getElementById(id);
    const API_URL = 'https://eduquest-3p59.onrender.com';

    // DOM
    const els = {
        semSelect:        $('semSelect'),
        subjectSelect:    $('subjectSelect'),
        examTabs:         document.querySelectorAll('.exam-tab'),
        modeCards:        document.querySelectorAll('.mode-card'),
        modeRadios:       document.querySelectorAll('input[name="mode"]'),
        analyzeBtn:       $('analyzeBtn'),
        paperPreview:     $('paperPreview'),
        paperPreviewList: $('paperPreviewList'),

        setupSection:     $('setupSection'),
        loadingSection:   $('loadingSection'),
        resultsSection:   $('resultsSection'),
        loadingText:      $('loadingText'),

        // Results
        resultTitle:      $('resultTitle'),
        resultSubtitle:   $('resultSubtitle'),
        includedCount:    $('includedCount'),
        rejectedCount:    $('rejectedCount'),
        rejectedContainer: $('rejectedContainer'),
        rejectedBlock:    $('rejectedBlock'),
        includedList:     $('includedList'),
        rejectedList:     $('rejectedList'),
        coverageSummary:  $('coverageSummary'),
        yearsCovered:     $('yearsCovered'),
        difficultyTrend:  $('difficultyTrend'),
        topicList:        $('topicList'),
        qtypeBars:        $('qtypeBars'),
        marksInfo:        $('marksInfo'),
        recurringList:    $('recurringList'),
        mustStudyList:    $('mustStudyList'),
        predictedCard:    $('predictedCard'),
        predictedPaper:   $('predictedPaper'),
        practiceCard:     $('practiceCard'),
        practiceResultsCard: $('practiceResultsCard'),

        // Practice
        practiceTitle:    $('practiceTitle'),
        currentQ:         $('currentQ'),
        totalQ:           $('totalQ'),
        practiceFill:     $('practiceFill'),
        practiceQuestion: $('practiceQuestion'),
        practiceInput:    $('practiceInput'),
        practiceReveal:   $('practiceReveal'),
        revealAnswer:     $('revealAnswer'),
        revealExplanation: $('revealExplanation'),
        prevQBtn:         $('prevQBtn'),
        revealBtn:        $('revealBtn'),
        nextQBtn:         $('nextQBtn'),
        finishPracticeBtn: $('finishPracticeBtn'),

        statAttempted:    $('statAttempted'),
        statTotal:        $('statTotal'),
        statPct:          $('statPct'),

        newAnalysisBtn:   $('newAnalysisBtn'),
        downloadBtn:      $('downloadBtn'),
        printBtn:         $('printBtn'),
    };

    // State
    let selectedExam = null;
    let selectedMode = 'full';
    let lastResult   = null;

    let practiceQuestions = [];
    let practiceIdx       = 0;
    let practiceAnswers   = [];
    let revealed          = [];


    // ════════════════════════════════════════
    // LOAD AVAILABLE YEARS (dynamic)
    // ════════════════════════════════════════
    async function loadAvailableYears() {
        try {
            const res = await fetch(`${API_URL}/pyq/years`);
            const data = await res.json();
            const years = data.years || [];

            els.semSelect.innerHTML = '<option value="">— Select year —</option>';

            if (years.length === 0) {
                els.semSelect.innerHTML = '<option>⚠ No PYQs indexed yet</option>';
                return;
            }

            years.forEach(y => {
                const opt = document.createElement('option');
                opt.value = y;
                opt.textContent = `Year ${y}`;
                els.semSelect.appendChild(opt);
            });

            console.log(`✅ Loaded ${years.length} year(s) with PYQs`);
        } catch (err) {
            console.error('Failed to load years:', err);
            els.semSelect.innerHTML = '<option>⚠ Cannot connect</option>';
        }
    }


    // ════════════════════════════════════════
    // LOAD SUBJECTS on year change
    // ════════════════════════════════════════
    els.semSelect.addEventListener('change', async () => {
        const sem = els.semSelect.value;

        els.subjectSelect.innerHTML = '<option value="">Loading...</option>';
        els.subjectSelect.disabled = true;
        els.paperPreview.style.display = 'none';

        if (!sem) {
            els.subjectSelect.innerHTML = '<option value="">Select year first</option>';
            checkFormValid();
            return;
        }

        try {
            const res = await fetch(`${API_URL}/pyq/subjects/${encodeURIComponent(sem)}`);
            const data = await res.json();

            els.subjectSelect.innerHTML = '<option value="">— Select subject —</option>';

            if (!data.subjects || data.subjects.length === 0) {
                els.subjectSelect.innerHTML = '<option>⚠ No subjects with PYQs for this year</option>';
                return;
            }

            data.subjects.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.name;
                opt.textContent = s.name;
                if (s.aliases && s.aliases.length) {
                    opt.textContent += `  (${s.aliases.slice(0, 3).join(', ')})`;
                }
                els.subjectSelect.appendChild(opt);
            });
            els.subjectSelect.disabled = false;
        } catch (err) {
            els.subjectSelect.innerHTML = '<option>⚠ Cannot load subjects</option>';
        }

        checkFormValid();
    });


    // ════════════════════════════════════════
    // PREVIEW PAPERS
    // ════════════════════════════════════════
    async function previewPapers() {
        const sem = els.semSelect.value;
        const subject = els.subjectSelect.value;
        const exam = selectedExam;

        if (!sem || !subject || !exam) {
            els.paperPreview.style.display = 'none';
            return;
        }

        try {
            const url = `${API_URL}/pyq/papers/${encodeURIComponent(sem)}/${encodeURIComponent(subject)}?exam=${exam}`;
            const res = await fetch(url);
            const data = await res.json();

            if (data.matched > 0) {
                els.paperPreview.style.display = 'block';
                els.paperPreviewList.innerHTML = data.papers.map(p =>
                    p.url
                        ? `<div>📄 <a href="${escapeAttr(p.url)}" target="_blank">${escapeHtml(p.name)}</a></div>`
                        : `<div>📄 ${escapeHtml(p.name)}</div>`
                ).join('');
                els.paperPreview.querySelector('h4').textContent = `📄 ${data.matched} paper(s) will be analyzed`;
            } else {
                els.paperPreview.style.display = 'block';
                els.paperPreviewList.innerHTML = `<div style="color: #dc2626;">⚠️ No ${exam} papers found. Total ${subject} PYQs: ${data.total}</div>`;
            }
        } catch (err) {
            els.paperPreview.style.display = 'none';
        }
    }

    els.subjectSelect.addEventListener('change', () => {
        previewPapers();
        checkFormValid();
    });


    // ════════════════════════════════════════
    // EXAM TABS
    // ════════════════════════════════════════
    els.examTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            els.examTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            selectedExam = tab.dataset.exam;
            previewPapers();
            checkFormValid();
        });
    });


    // ════════════════════════════════════════
    // MODE CARDS
    // ════════════════════════════════════════
    els.modeCards.forEach(card => {
        card.addEventListener('click', () => {
            els.modeCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const radio = card.querySelector('input[type="radio"]');
            radio.checked = true;
            selectedMode = radio.value;
        });
    });


    function checkFormValid() {
        els.analyzeBtn.disabled = !(
            els.semSelect.value &&
            els.subjectSelect.value &&
            selectedExam
        );
    }


    // ════════════════════════════════════════
    // ANALYZE
    // ════════════════════════════════════════
    els.analyzeBtn.addEventListener('click', async () => {
        showLoading();
        animateStages();

        try {
            const res = await fetch(`${API_URL}/pyq/analyze`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    semester: els.semSelect.value,
                    subject:  els.subjectSelect.value,
                    exam:     selectedExam,
                    mode:     selectedMode,
                }),
            });

            const data = await res.json();

            if (!res.ok || !data.success) {
                throw new Error(data.error || `HTTP ${res.status}`);
            }

            lastResult = data;
            showResults(data);

        } catch (err) {
            alert('Error: ' + err.message);
            hideLoading();
        }
    });


    function showLoading() {
        els.setupSection.style.display   = 'none';
        els.loadingSection.style.display = 'block';
        els.resultsSection.style.display = 'none';
    }

    function hideLoading() {
        els.setupSection.style.display   = 'block';
        els.loadingSection.style.display = 'none';
    }

    function animateStages() {
        const stages = ['stage1', 'stage2', 'stage3', 'stage4'];
        const messages = [
            'Loading indexed chunks…',
            'Verifying subject match…',
            'Running AI analysis on patterns…',
            'Building your report…',
        ];
        let i = 0;

        stages.forEach(s => $(s)?.classList.remove('active', 'done'));
        $(stages[0])?.classList.add('active');
        els.loadingText.textContent = messages[0];

        const interval = setInterval(() => {
            if (els.loadingSection.style.display === 'none') {
                clearInterval(interval);
                return;
            }

            $(stages[i])?.classList.remove('active');
            $(stages[i])?.classList.add('done');
            i = (i + 1) % stages.length;
            $(stages[i])?.classList.add('active');
            els.loadingText.textContent = messages[i];
        }, 3000);
    }


    // ════════════════════════════════════════
    // RENDER RESULTS
    // ════════════════════════════════════════
    function showResults(data) {
        els.loadingSection.style.display = 'none';
        els.resultsSection.style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });

        els.resultTitle.textContent = `${data.subject} — ${data.exam} Analysis`;
        els.resultSubtitle.textContent = `Year ${data.semester} · ${data.num_included} paper(s) analyzed`;

        // Papers status
        els.includedCount.textContent = data.num_included;
        els.includedList.innerHTML = data.included_papers
            .map(p => `<li>📄 ${escapeHtml(p)}</li>`).join('');

        if (data.num_rejected > 0) {
            els.rejectedContainer.style.display = 'block';
            els.rejectedBlock.style.display = 'block';
            els.rejectedCount.textContent = data.num_rejected;
            els.rejectedList.innerHTML = data.rejected_papers
                .map(p => `<li>❌ ${escapeHtml(p)}</li>`).join('');
        } else {
            els.rejectedContainer.style.display = 'none';
            els.rejectedBlock.style.display = 'none';
        }

        const a = data.analysis;

        // Coverage
        els.coverageSummary.textContent = a.coverage_summary || 'Analysis of paper trends and topics.';
        els.yearsCovered.textContent    = a.years_covered || '—';
        els.difficultyTrend.textContent = a.difficulty_trend || '—';

        // Topics
        renderTopics(a.topic_frequency || []);

        // Question types
        renderQuestionTypes(a.question_type_distribution || {});

        // Marks
        renderMarks(a.marks_pattern || {});

        // Recurring
        renderRecurring(a.recurring_questions || []);

        // Must-study
        renderMustStudy(a.must_study_topics || []);

        // Mode-specific
        if (selectedMode === 'full' && data.practice_paper) {
            els.predictedCard.style.display = 'block';
            els.predictedPaper.innerHTML = window.marked
                ? marked.parse(data.practice_paper)
                : escapeForMath(data.practice_paper);
        } else {
            els.predictedCard.style.display = 'none';
        }

        if (selectedMode === 'practice' && data.practice_questions) {
            practiceQuestions = data.practice_questions;
            practiceIdx = 0;
            practiceAnswers = new Array(practiceQuestions.length).fill('');
            revealed = new Array(practiceQuestions.length).fill(false);
            els.practiceCard.style.display = 'block';
            els.totalQ.textContent = practiceQuestions.length;
            renderPracticeQuestion();
        } else {
            els.practiceCard.style.display = 'none';
        }

        els.practiceResultsCard.style.display = 'none';

        // Re-render math after everything is in the DOM
        if (window.MathJax && window.MathJax.typesetPromise) {
            MathJax.typesetPromise().catch(err => console.warn(err));
        }
    }


    function renderTopics(topics) {
        if (!topics.length) {
            els.topicList.innerHTML = '<p style="color:#999;">No topics extracted</p>';
            return;
        }

        const maxCount = Math.max(...topics.map(t => t.count || 0), 1);

        els.topicList.innerHTML = topics.map((t, i) => {
            const width = ((t.count || 0) / maxCount) * 100;
            const priority = t.priority || 'LOW';
            return `
                <div class="topic-item">
                    <div class="topic-rank">${i + 1}</div>
                    <div class="topic-name">${escapeHtml(t.topic || 'N/A')}</div>
                    <div class="topic-bar-container">
                        <div class="topic-bar" style="width: ${width}%"></div>
                    </div>
                    <div class="topic-count">${t.count || 0}×</div>
                    <div class="topic-priority priority-${priority}">${priority}</div>
                </div>
            `;
        }).join('');
    }


    function renderQuestionTypes(qtypes) {
        const rows = [
            ['Long Answer',   qtypes.long_answer_percent  || 0],
            ['Short Answer',  qtypes.short_answer_percent || 0],
            ['MCQ',           qtypes.mcq_percent          || 0],
            ['Numerical',     qtypes.numerical_percent    || 0],
        ];

        els.qtypeBars.innerHTML = rows.map(([label, pct]) => `
            <div class="qtype-bar-row">
                <div class="qtype-label">${label}</div>
                <div class="qtype-bar-track">
                    <div class="qtype-bar-fill" style="width: ${pct}%"></div>
                </div>
                <div class="qtype-pct">${pct}%</div>
            </div>
        `).join('');
    }


    function renderMarks(marks) {
        els.marksInfo.innerHTML = `
            <div class="marks-row">
                <span class="marks-row-label">Total marks (typical)</span>
                <span class="marks-row-value">${marks.total_marks_typical || '—'}</span>
            </div>
            <div class="marks-row">
                <span class="marks-row-label">Common Q marks</span>
                <span class="marks-row-value">${marks.most_common_question_marks || '—'}</span>
            </div>
            ${marks.notes ? `<div class="marks-notes">💡 ${escapeHtml(marks.notes)}</div>` : ''}
        `;
    }


    function renderRecurring(recurring) {
        if (!recurring.length) {
            els.recurringList.innerHTML = '<p style="color:#999;">No recurring patterns found</p>';
            return;
        }

        els.recurringList.innerHTML = recurring.slice(0, 10).map(r => `
            <div class="recurring-item">
                <div class="recurring-header">
                    <span class="recurring-freq">${r.frequency || 1}×</span>
                    <span class="recurring-topic">${escapeHtml(r.topic || '')}</span>
                </div>
                <div class="recurring-pattern">${escapeForMath(r.question_pattern || '')}</div>
            </div>
        `).join('');
    }


    function renderMustStudy(topics) {
        if (!topics.length) {
            els.mustStudyList.innerHTML = '<li>No priority topics identified</li>';
            return;
        }

        els.mustStudyList.innerHTML = topics.map(t =>
            `<li>${escapeHtml(t)}</li>`
        ).join('');
    }


    // ════════════════════════════════════════
    // INTERACTIVE PRACTICE
    // ════════════════════════════════════════
    function renderPracticeQuestion() {
        if (!practiceQuestions.length) return;

        const q = practiceQuestions[practiceIdx];
        const total = practiceQuestions.length;

        els.currentQ.textContent = practiceIdx + 1;
        els.practiceFill.style.width = `${((practiceIdx + 1) / total) * 100}%`;
        els.practiceTitle.textContent = q.header || `Question ${practiceIdx + 1}`;

        // ✅ Use innerHTML + escapeForMath so LaTeX renders
        els.practiceQuestion.innerHTML = escapeForMath(q.question_block || '');

        els.practiceInput.value = practiceAnswers[practiceIdx] || '';

        if (revealed[practiceIdx] && q.answer) {
            els.practiceReveal.style.display = 'block';
            els.revealAnswer.innerHTML = escapeForMath(q.answer);
            els.revealExplanation.innerHTML = q.explanation
                ? `💡 ${escapeForMath(q.explanation)}`
                : '';
        } else {
            els.practiceReveal.style.display = 'none';
        }

        els.prevQBtn.disabled = practiceIdx === 0;
        const isLast = practiceIdx === total - 1;
        els.nextQBtn.style.display = isLast ? 'none' : 'inline-block';
        els.finishPracticeBtn.style.display = isLast ? 'inline-block' : 'none';
        els.revealBtn.textContent = revealed[practiceIdx] ? '🙈 Hide Answer' : '👁️ Show Answer';

        // Re-render math in the new question
        if (window.MathJax && window.MathJax.typesetPromise) {
            MathJax.typesetPromise([els.practiceQuestion, els.practiceReveal])
                .catch(err => console.warn(err));
        }
    }

    els.practiceInput.addEventListener('input', e => {
        practiceAnswers[practiceIdx] = e.target.value;
    });

    els.prevQBtn.addEventListener('click', () => {
        if (practiceIdx > 0) {
            practiceIdx--;
            renderPracticeQuestion();
        }
    });

    els.nextQBtn.addEventListener('click', () => {
        if (practiceIdx < practiceQuestions.length - 1) {
            practiceIdx++;
            renderPracticeQuestion();
        }
    });

    els.revealBtn.addEventListener('click', () => {
        revealed[practiceIdx] = !revealed[practiceIdx];
        renderPracticeQuestion();
    });

    els.finishPracticeBtn.addEventListener('click', () => {
        const attempted = practiceAnswers.filter(a => a && a.trim()).length;
        const total = practiceQuestions.length;
        const pct = total > 0 ? Math.round((attempted / total) * 100) : 0;

        els.practiceCard.style.display = 'none';
        els.practiceResultsCard.style.display = 'block';
        els.statAttempted.textContent = attempted;
        els.statTotal.textContent = total;
        els.statPct.textContent = pct + '%';

        window.scrollTo({ top: els.practiceResultsCard.offsetTop - 100, behavior: 'smooth' });
    });


    // ════════════════════════════════════════
    // ACTIONS
    // ════════════════════════════════════════
    els.newAnalysisBtn.addEventListener('click', () => {
        els.setupSection.style.display = 'block';
        els.loadingSection.style.display = 'none';
        els.resultsSection.style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    els.downloadBtn.addEventListener('click', () => {
        if (!lastResult) return;
        const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pyq-${lastResult.subject.replace(/\s+/g, '_')}-${lastResult.exam}.json`;
        a.click();
        URL.revokeObjectURL(url);
    });

    els.printBtn.addEventListener('click', () => window.print());


    // ════════════════════════════════════════
    // HELPERS
    // ════════════════════════════════════════
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }

    function escapeAttr(str) {
        return escapeHtml(str).replace(/"/g, '&quot;');
    }

    /**
     * Escapes HTML but PRESERVES LaTeX math delimiters so MathJax can parse.
     * Also preserves newlines and simple markdown (bold/italic).
     */
    function escapeForMath(str) {
        if (str === null || str === undefined) return '';

        // Escape HTML special chars (but LaTeX \( \) \[ \] survive as-is)
        let s = String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');

        // Preserve newlines
        s = s.replace(/\n/g, '<br>');

        // Simple markdown
        s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        s = s.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

        return s;
    }


    // ════════════════════════════════════════
    // INIT
    // ════════════════════════════════════════
    loadAvailableYears();
    console.log('✅ PYQ Analyser ready');
}