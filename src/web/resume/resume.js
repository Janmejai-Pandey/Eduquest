/* ════════════════════════════════════════════════════════════
   RESUME RANKING — With Year + enrollment + branch tracking
   ════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const API_URL = 'http://localhost:8000';

    // DOM
    const userName        = document.getElementById('userName');
    const enrollmentInput = document.getElementById('enrollment');
    const yearSelect       = document.getElementById('yearSelect');
    const branchSelect    = document.getElementById('branchSelect');
    const roleSelect      = document.getElementById('roleSelect');
    const roleSkillsHint  = document.getElementById('roleSkillsHint');
    const dropzone        = document.getElementById('dropzone');
    const fileInput       = document.getElementById('resumeFile');
    const dropzoneContent = dropzone.querySelector('.dropzone-content');
    const dropzoneFile    = document.getElementById('dropzoneFile');
    const fileName        = document.getElementById('fileName');
    const fileSize        = document.getElementById('fileSize');
    const fileRemove      = document.getElementById('fileRemove');
    const form            = document.getElementById('resumeForm');
    const analyzeBtn      = document.getElementById('analyzeBtn');
    const uploadSection   = document.querySelector('.upload-section');
    const loadingSection  = document.getElementById('loadingSection');
    const resultsSection  = document.getElementById('resultsSection');
    const loadingText     = document.getElementById('loadingText');
    const resumeHero      = document.querySelector('.resume-hero');

    // State
    let selectedFile = null;
    let lastResult   = null;
    let branchTree   = {};   // {branch: [roles]}
    let roleSkillsMap = {};  // {role: [skills]} — cached


    // ════════════════════════════════════════
    // 1. LOAD BRANCHES & ROLES
    // ════════════════════════════════════════
    async function loadBranches() {
        try {
            const res  = await fetch(`${API_URL}/resume/branches`);
            const data = await res.json();
            branchTree = data.tree || {};

            branchSelect.innerHTML = '<option value="">— Select branch —</option>';
            Object.keys(branchTree).sort().forEach(b => {
                const opt = document.createElement('option');
                opt.value = b;
                opt.textContent = b;
                branchSelect.appendChild(opt);
            });
        } catch (err) {
            console.error('Failed to load branches:', err);
            branchSelect.innerHTML = '<option>⚠ Cannot connect</option>';
        }
    }

    // Populate role dropdown when branch changes
    branchSelect.addEventListener('change', () => {
        const branch = branchSelect.value;

        if (!branch) {
            roleSelect.innerHTML = '<option value="">Select branch first</option>';
            roleSelect.disabled = true;
            roleSkillsHint.textContent = '';
            checkFormValid();
            return;
        }

        const roles = branchTree[branch] || [];

        roleSelect.innerHTML = '<option value="">— Select target role —</option>';
        roles.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r;
            opt.textContent = r;
            roleSelect.appendChild(opt);
        });

        roleSelect.disabled = false;
        roleSelect.value = '';
        roleSkillsHint.textContent = '';
        checkFormValid();
    });

    // Fetch skills when role changes
    roleSelect.addEventListener('change', async () => {
        const role = roleSelect.value;
        if (!role) {
            roleSkillsHint.textContent = '';
            checkFormValid();
            return;
        }

        // Check cache
        if (roleSkillsMap[role]) {
            displayRoleSkills(role, roleSkillsMap[role]);
        } else {
            try {
                const res = await fetch(`${API_URL}/resume/skills/${encodeURIComponent(role)}`);
                const data = await res.json();
                roleSkillsMap[role] = data.skills || [];
                displayRoleSkills(role, data.skills);
            } catch (err) {
                roleSkillsHint.textContent = '⚠ Could not load skills';
            }
        }
        checkFormValid();
    });

    function displayRoleSkills(role, skills) {
        if (!skills || skills.length === 0) {
            roleSkillsHint.textContent = '';
            return;
        }
        const preview = skills.slice(0, 8).join(', ');
        const extra   = skills.length > 8 ? ` and ${skills.length - 8} more…` : '';
        roleSkillsHint.textContent = `💡 Top skills for ${role}: ${preview}${extra}`;
    }


    // ════════════════════════════════════════
    // 2. DROPZONE
    // ════════════════════════════════════════
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFile(file);
    });

    fileRemove.addEventListener('click', (e) => {
        e.stopPropagation();
        resetFile();
    });

    function handleFile(file) {
        const valid = ['.pdf', '.pptx'].some(ext => file.name.toLowerCase().endsWith(ext));
        if (!valid) {
            alert('Please upload a PDF or PPTX file.');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert('File too large. Maximum size is 10MB.');
            return;
        }

        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        dropzoneContent.style.display = 'none';
        dropzoneFile.style.display    = 'flex';
        checkFormValid();
    }

    function resetFile() {
        selectedFile = null;
        fileInput.value = '';
        dropzoneContent.style.display = 'block';
        dropzoneFile.style.display    = 'none';
        checkFormValid();
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }


    // ════════════════════════════════════════
    // 3. FORM VALIDATION
    // ════════════════════════════════════════
    [userName, enrollmentInput, yearSelect, branchSelect, roleSelect].forEach(el => {
        el.addEventListener('input',  checkFormValid);
        el.addEventListener('change', checkFormValid);
    });

    function checkFormValid() {
        analyzeBtn.disabled = !(
            userName.value.trim() &&
            enrollmentInput.value.trim().length >= 4 &&
            yearSelect.value &&
            branchSelect.value &&
            roleSelect.value &&
            selectedFile
        );
    }


    // ════════════════════════════════════════
    // 4. SUBMIT
    // ════════════════════════════════════════
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        showLoading();

        try {
            const formData = new FormData();
            formData.append('file',       selectedFile);
            formData.append('name',       userName.value.trim());
            formData.append('enrollment', enrollmentInput.value.trim().toUpperCase());
            formData.append('year',   yearSelect.value);
            formData.append('branch',     branchSelect.value);
            formData.append('job_role',   roleSelect.value);

            const res = await fetch(`${API_URL}/resume/analyze`, {
                method: 'POST',
                body:   formData,
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `HTTP ${res.status}`);
            }

            const data = await res.json();
            lastResult = data;
            showResults(data);

        } catch (err) {
            console.error(err);
            alert('Error: ' + err.message);
            hideLoading();
        }
    });

    function showLoading() {
        uploadSection.style.display     = 'none';
        loadingSection.style.display = 'block';
        resultsSection.style.display = 'none';

        const stages = [
            'Extracting text from resume…',
            'Analyzing skills…',
            'Computing TF-IDF similarity…',
            'Calculating your rank in your cohort…',
            'Building recommendations…',
        ];
        let i = 0;
        const interval = setInterval(() => {
            if (loadingSection.style.display === 'none') {
                clearInterval(interval);
                return;
            }
            loadingText.textContent = stages[i % stages.length];
            i++;
        }, 1500);
    }

    function hideLoading() {
        uploadSection.style.display     = 'block';
        loadingSection.style.display = 'none';
        resultsSection.style.display = 'none';
    }


    // ════════════════════════════════════════
    // 5. RENDER RESULTS
    // ════════════════════════════════════════
    function showResults(data) {

        resumeHero.style.display = 'none';
        loadingSection.style.display = 'none';
        resultsSection.style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });

        const score = data.final_score;

        // Animate circle
        const circumference = 2 * Math.PI * 90;
        const offset = circumference - (score / 100) * circumference;
        setTimeout(() => {
            document.getElementById('scoreCircle').style.strokeDashoffset = offset;
        }, 100);

        animateNumber('scoreNumber', 0, Math.round(score), 1500);

        // Status banner (first-time or update)
        renderStatusBanner(data);

        // Tag + title
        const tagInfo = getTagFromTier(data.ranking_tier);
        const tagEl = document.getElementById('resultTag');
        tagEl.textContent = tagInfo.label;
        tagEl.style.background = tagInfo.bg;
        tagEl.style.color = tagInfo.color;

        document.getElementById('resultTitle').textContent = data.ranking_tier;
        document.getElementById('resultSubtitle').textContent =
            `${data.candidate_name} (${data.enrollment}) · ${data.branch} · Year ${data.year} · ${data.job_role}`;

        // Rank stats
        document.getElementById('rankValue').textContent       = `#${data.current_rank}`;
        document.getElementById('percentileValue').textContent = `Top ${data.percentile}%`;
        document.getElementById('cohortValue').textContent     = data.total;

        // Standing message
        document.getElementById('standingMessage').textContent =
            getStandingMessage(data);

        // Score change (only for updates)
        renderScoreChange(data);

        // Breakdown
        renderBreakdown(data);

        // Found skills
        renderFoundSkills(data);

        // Recommendations
        renderRecommendations(data.recommendations);

        // Missing skills
        renderMissingSkills(data.missing_skills);
    }


    function renderStatusBanner(data) {
        const banner = document.getElementById('statusBanner');

        if (data.is_first) {
            banner.className = 'first-time';
            banner.style.display = 'flex';
            banner.innerHTML = `
                <div class="banner-icon">🎉</div>
                <div class="banner-content">
                    <strong>Congratulations! You're the FIRST!</strong>
                    You're the first candidate to submit a resume for
                    <strong>${escapeHtml(data.job_role)}</strong> in
                    <strong>year ${data.year}</strong>.
                    Check back later to see how you rank when peers submit.
                </div>
            `;
        } else if (data.was_update) {
            banner.className = 'update';
            banner.style.display = 'flex';
            banner.innerHTML = `
                <div class="banner-icon">🔄</div>
                <div class="banner-content">
                    <strong>Resume Updated!</strong>
                    We've replaced your previous submission for
                    <strong>${escapeHtml(data.job_role)}</strong>.
                    See how you changed below.
                </div>
            `;
        } else {
            banner.style.display = 'none';
        }
    }


    function renderScoreChange(data) {
        const card = document.getElementById('scoreChangeCard');

        if (!data.was_update) {
            card.style.display = 'none';
            return;
        }

        const prevScore = data.previous_score;
        const currScore = data.final_score;
        const scoreDelta = currScore - prevScore;

        const prevRank = data.previous_rank;
        const currRank = data.current_rank;
        const rankDelta = prevRank - currRank;  // positive = improved

        card.style.display = 'block';
        card.innerHTML = `
            <h3>📊 Your Progress</h3>
            <div class="score-change-grid">
                <div class="change-item">
                    <div class="change-item-label">Score</div>
                    <div class="change-values">
                        <span class="change-before">${prevScore.toFixed(1)}%</span>
                        <span class="change-arrow">→</span>
                        <span class="change-after">${currScore.toFixed(1)}%</span>
                    </div>
                    <div class="change-delta ${scoreDelta > 0 ? 'positive' : (scoreDelta < 0 ? 'negative' : 'neutral')}">
                        ${scoreDelta > 0 ? '⬆ +' : (scoreDelta < 0 ? '⬇ ' : '')}${scoreDelta.toFixed(1)}%
                        ${scoreDelta === 0 ? '(no change)' : ''}
                    </div>
                </div>

                <div class="change-item">
                    <div class="change-item-label">Rank</div>
                    <div class="change-values">
                        <span class="change-before">#${prevRank}</span>
                        <span class="change-arrow">→</span>
                        <span class="change-after">#${currRank}</span>
                    </div>
                    <div class="change-delta ${rankDelta > 0 ? 'positive' : (rankDelta < 0 ? 'negative' : 'neutral')}">
                        ${rankDelta > 0 ? `⬆ Up ${rankDelta} place${rankDelta > 1 ? 's' : ''}` : ''}
                        ${rankDelta < 0 ? `⬇ Down ${Math.abs(rankDelta)} place${Math.abs(rankDelta) > 1 ? 's' : ''}` : ''}
                        ${rankDelta === 0 ? '(same rank)' : ''}
                    </div>
                </div>
            </div>
        `;
    }


    function getTagFromTier(tier) {
        if (tier.includes('Excellent')) return { label: 'Excellent',     bg: '#dcfce7', color: '#15803d' };
        if (tier.includes('Strong'))    return { label: 'Strong',        bg: '#dbeafe', color: '#1d4ed8' };
        if (tier.includes('Moderate'))  return { label: 'Moderate',      bg: '#fef3c7', color: '#a16207' };
        if (tier.includes('Below'))     return { label: 'Below Average', bg: '#fde4cf', color: '#c2410c' };
        return                                  { label: 'Needs Work',   bg: '#fee2e2', color: '#dc2626' };
    }


    function getStandingMessage(data) {
        const { current_rank: rank, total, percentile, is_first } = data;

        if (is_first)         return '🎯 You\'re the first! Percentile will be meaningful once more candidates submit.';
        if (total === 1)      return '🎯 You\'re the only candidate in this cohort so far.';
        if (rank === 1)       return '🥇 Congratulations! You are the TOP candidate in your year!';
        if (percentile >= 90) return `🌟 Outstanding! You're in the top 10% of ${total} candidates in your cohort.`;
        if (percentile >= 75) return `🎉 Great work! You're in the top 25% of your cohort.`;
        if (percentile >= 50) return `👍 You're in the top half of your cohort. Focus on missing skills to climb higher.`;
        if (percentile >= 25) return `📌 You're in the bottom half. Work on the priority skills below.`;
        return                       `⚠️ You're in the bottom 25% of your cohort. Focus on the high-priority skills to improve.`;
    }


    function animateNumber(elId, start, end, duration) {
        const el = document.getElementById(elId);
        const startTime = performance.now();
        function update(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(start + (end - start) * progress);
            el.textContent = current;
            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    }


    function renderBreakdown(data) {
        const grid = document.getElementById('breakdownGrid');

        const items = [
            {
                label:  'Final Score',
                value:  data.final_score,
                weight: '100% (overall)',
                pct:    data.final_score,
            },
            {
                label:  'Skill Match',
                value:  data.skill_match_percentage,
                weight: '70% weight',
                pct:    data.skill_match_percentage,
            },
            {
                label:  'TF-IDF Similarity',
                value:  data.tfidf_similarity,
                weight: '30% weight',
                pct:    data.tfidf_similarity,
            },
        ];

        grid.innerHTML = items.map(it => `
            <div class="breakdown-item">
                <div class="breakdown-label">${it.label}</div>
                <div class="breakdown-value">${it.value.toFixed(1)}<small>%</small></div>
                <div class="breakdown-bar"><div class="breakdown-bar-fill" style="width:${it.pct}%;"></div></div>
                <div class="breakdown-weight">${it.weight}</div>
            </div>
        `).join('');
    }


    function renderFoundSkills(data) {
        const container = document.getElementById('foundSkillsContainer');
        const subtitle  = document.getElementById('foundSkillsSubtitle');
        const found     = data.found_skills    || [];
        const required  = data.required_skills || [];
        const top2      = data.top2_found_skills || [];

        subtitle.textContent = `${found.length} of ${required.length} required skills matched`;

        if (found.length === 0) {
            container.innerHTML = '<p style="color:#8a8a9a;">No required skills detected. Try adding relevant skill keywords to your resume.</p>';
            return;
        }

        container.innerHTML = found.map(skill => {
            const isPriority = top2.includes(skill);
            const cls  = isPriority ? 'skill-chip priority' : 'skill-chip';
            const star = isPriority ? '⭐ ' : '';
            return `<span class="${cls}">${star}${escapeHtml(skill)}</span>`;
        }).join('');
    }


    function renderRecommendations(recs) {
        const container = document.getElementById('recommendationsContainer');
        if (!recs || recs.length === 0) {
            container.innerHTML = '<p style="color:#15803d;">🎉 You\'ve covered all the major skills for this role!</p>';
            return;
        }
        container.innerHTML = recs.map(r => `
            <div class="rec-item ${r.priority}">
                <div class="rec-header">
                    <span class="rec-skill">${escapeHtml(r.skill)}</span>
                    <span class="rec-priority ${r.priority}">${r.priority}</span>
                </div>
                <div class="rec-reason">${escapeHtml(r.reason)}</div>
            </div>
        `).join('');
    }


    function renderMissingSkills(missing) {
        const container = document.getElementById('missingSkillsContainer');
        if (!missing || missing.length === 0) {
            container.innerHTML = '<p style="color:#15803d;">🎉 No skill gaps! All required skills are present in your resume.</p>';
            return;
        }
        container.innerHTML = `
            <div class="skill-category">
                <div class="skill-category-name">${missing.length} skill${missing.length === 1 ? '' : 's'} to learn (sorted by priority)</div>
                <div class="skills-container">
                    ${missing.map(s => `<span class="skill-chip missing">${escapeHtml(s)}</span>`).join('')}
                </div>
            </div>
        `;
    }


    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }


    // ════════════════════════════════════════
    // 6. ACTIONS
    // ════════════════════════════════════════
    document.getElementById('newScanBtn').addEventListener('click', () => {
        resetFile();
        userName.value       = '';
        enrollmentInput.value = '';
        yearSelect.value      = '';
        branchSelect.value   = '';
        roleSelect.innerHTML = '<option value="">Select branch first</option>';
        roleSelect.disabled  = true;
        roleSkillsHint.textContent = '';
        checkFormValid();
        resumeHero.style.display = 'block';
        uploadSection.style.display     = 'block';
        loadingSection.style.display = 'none';
        resultsSection.style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    document.getElementById('downloadBtn').addEventListener('click', () => {
        if (!lastResult) return;
        const data = JSON.stringify(lastResult, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = `resume-analysis-${lastResult.enrollment}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    });


    // ════════════════════════════════════════
    // 7. INIT
    // ════════════════════════════════════════
    loadBranches();
    console.log('📄 Resume page ready');

})();