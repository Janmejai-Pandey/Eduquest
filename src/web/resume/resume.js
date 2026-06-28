(function () {
    'use strict';

    const API_URL = 'http://localhost:8000';

    // ── DOM ──
    const userName        = document.getElementById('userName');
    const branchSelect    = document.getElementById('branchSelect');
    const yearSelect      = document.getElementById('yearSelect');
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
    const uploadCard      = document.getElementById('uploadCard');
    const loadingSection  = document.getElementById('loadingSection');
    const resultsSection  = document.getElementById('resultsSection');
    const loadingText     = document.getElementById('loadingText');

    let selectedFile = null;
    let lastResult   = null;
    let rolesData    = [];


    // ════════════════════════════════════════
    // 1. LOAD ROLES
    // ════════════════════════════════════════
    async function loadRoles() {
        try {
            const res  = await fetch(`${API_URL}/resume/roles`);
            const data = await res.json();
            rolesData  = data.roles;

            roleSelect.innerHTML = '<option value="">— Select target role —</option>';
            rolesData.forEach(role => {
                const opt = document.createElement('option');
                opt.value = role.name;
                opt.textContent = `${role.name} (${role.skills_count} skills)`;
                roleSelect.appendChild(opt);
            });
        } catch (err) {
            console.error('Cannot load roles:', err);
            roleSelect.innerHTML = '<option value="">⚠ Cannot connect to backend</option>';
        }
    }

    roleSelect.addEventListener('change', () => {
        const role = rolesData.find(r => r.name === roleSelect.value);
        if (role && role.skills.length > 0) {
            const preview = role.skills.slice(0, 6).join(', ');
            const extra   = role.skills.length > 6 ? ` and ${role.skills.length - 6} more…` : '';
            roleSkillsHint.textContent = `💡 Skills required: ${preview}${extra}`;
        } else {
            roleSkillsHint.textContent = '';
        }
        checkFormValid();
    });


    // ════════════════════════════════════════
    // 2. DROPZONE & FILE HANDLING
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
    [userName, roleSelect].forEach(el => {
        el.addEventListener('input',  checkFormValid);
        el.addEventListener('change', checkFormValid);
    });

    function checkFormValid() {
        analyzeBtn.disabled = !(
            userName.value.trim() &&
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
            formData.append('file',     selectedFile);
            formData.append('name',     userName.value.trim());
            formData.append('job_role', roleSelect.value);
            formData.append('branch',   branchSelect.value);
            formData.append('year',     yearSelect.value);

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
        uploadCard.style.display     = 'none';
        loadingSection.style.display = 'block';
        resultsSection.style.display = 'none';

        const stages = [
            'Extracting text from resume…',
            'Analyzing skills…',
            'Computing TF-IDF similarity…',
            'Calculating your rank…',
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
        uploadCard.style.display     = 'block';
        loadingSection.style.display = 'none';
        resultsSection.style.display = 'none';
    }


    // ════════════════════════════════════════
    // 5. RENDER RESULTS
    // ════════════════════════════════════════
    function showResults(data) {
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

        // Animate number
        animateNumber('scoreNumber', 0, Math.round(score), 1500);

        // Tag + title from your tier
        const tagInfo = getTagFromTier(data.ranking_tier);
        const tagEl = document.getElementById('resultTag');
        tagEl.textContent           = tagInfo.label;
        tagEl.style.background      = tagInfo.bg;
        tagEl.style.color           = tagInfo.color;

        document.getElementById('resultTitle').textContent    = data.ranking_tier;
        document.getElementById('resultSubtitle').textContent =
            `${data.candidate_name} · ${data.job_role}` +
            (data.branch ? ` · ${data.branch}` : '') +
            (data.year   ? ` · Year ${data.year}` : '');

        // Rank stats
        document.getElementById('rankValue').textContent       = `#${data.rank}`;
        document.getElementById('percentileValue').textContent = `Top ${data.percentile}%`;
        document.getElementById('cohortValue').textContent     = data.total_candidates;

        // Standing message
        document.getElementById('standingMessage').textContent =
            getStandingMessage(data.rank, data.percentile, data.total_candidates);

        // Breakdown
        renderBreakdown(data);

        // Found skills
        renderFoundSkills(data);

        // Recommendations
        renderRecommendations(data.recommendations);

        // Missing skills (all)
        renderMissingSkills(data.missing_skills);
    }

    function getTagFromTier(tier) {
        if (tier.includes('Excellent')) return { label: 'Excellent',     bg: '#dcfce7', color: '#15803d' };
        if (tier.includes('Strong'))    return { label: 'Strong',        bg: '#dbeafe', color: '#1d4ed8' };
        if (tier.includes('Moderate'))  return { label: 'Moderate',      bg: '#fef3c7', color: '#a16207' };
        if (tier.includes('Below'))     return { label: 'Below Average', bg: '#fde4cf', color: '#c2410c' };
        return                                  { label: 'Needs Work',   bg: '#fee2e2', color: '#dc2626' };
    }

    function getStandingMessage(rank, percentile, total) {
        if (total === 1)        return '🎯 You\'re the first candidate in the system. Upload more to see your rank!';
        if (rank === 1)         return '🥇 Congratulations! You are the TOP candidate among all applicants!';
        if (percentile >= 90)   return `🌟 Outstanding! You're in the top 10% of ${total} candidates.`;
        if (percentile >= 75)   return `🎉 Great work! You're in the top 25% of all candidates.`;
        if (percentile >= 50)   return `👍 You're in the top half. Focus on the missing skills to climb higher.`;
        if (percentile >= 25)   return `📌 You're in the bottom half. Work on the priority skills listed below.`;
        return                         `⚠️ You're in the bottom 25%. Focus on the high-priority skills to improve.`;
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

        // Your ranking.py uses: 70% skill match + 30% TF-IDF = final score
        const items = [
            {
                label:      'Final Score',
                value:      data.final_score,
                max:        100,
                weight:     '100% (overall)',
                pct:        data.final_score,
            },
            {
                label:      'Skill Match',
                value:      data.skill_match_percentage,
                max:        100,
                weight:     '70% weight',
                pct:        data.skill_match_percentage,
            },
            {
                label:      'TF-IDF Similarity',
                value:      data.tfidf_similarity,
                max:        100,
                weight:     '30% weight',
                pct:        data.tfidf_similarity,
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
        const found     = data.found_skills || [];
        const required  = data.required_skills || [];
        const top2      = data.top2_found_skills || [];

        subtitle.textContent = `${found.length} of ${required.length} required skills matched`;

        if (found.length === 0) {
            container.innerHTML = '<p style="color:#8a8a9a;">No required skills detected. Try adding skill keywords like Python, SQL, etc.</p>';
            return;
        }

        container.innerHTML = found.map(skill => {
            const isPriority = top2.includes(skill);
            const cls = isPriority ? 'skill-chip priority' : 'skill-chip';
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
        userName.value     = '';
        roleSelect.value   = '';
        branchSelect.value = '';
        yearSelect.value   = '0';
        roleSkillsHint.textContent = '';
        checkFormValid();
        uploadCard.style.display     = 'block';
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
        a.download = `resume-analysis-${lastResult.candidate_name.replace(/\s/g, '_')}.json`;
        a.click();
        URL.revokeObjectURL(url);
    });


    // ════════════════════════════════════════
    // 7. INIT
    // ════════════════════════════════════════
    loadRoles();
    console.log('📄 Resume page ready');

})();