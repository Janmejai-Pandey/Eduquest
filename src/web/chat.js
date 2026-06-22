/* ════════════════════════════════════════════════════════════
   CHAT PAGE LOGIC — Connects to FastAPI backend
   ════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── Config ──────────────────────────────
    const API_URL    = 'http://localhost:8000';
    const SESSION_ID = 'web_' + Date.now();

    // ── DOM ─────────────────────────────────
    const chatForm    = document.getElementById('chatForm');
    const chatInput   = document.getElementById('chatInput');
    const submitBtn   = document.getElementById('submitBtn');
    const messagesBox = document.getElementById('chatMessages');
    const statusPill  = document.getElementById('statusPill');
    const statFiles   = document.getElementById('statFiles');
    const statChunks  = document.getElementById('statChunks');
    const fileList    = document.getElementById('fileList');
    const clearBtn    = document.getElementById('clearChatBtn');


    // ════════════════════════════════════════
    // 1. API CALLS
    // ════════════════════════════════════════
    async function apiChat(message) {
        const res = await fetch(`${API_URL}/chat`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ message, session_id: SESSION_ID }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    async function apiStats() {
        const res = await fetch(`${API_URL}/stats`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    async function apiReset() {
        const res = await fetch(`${API_URL}/reset?session_id=${SESSION_ID}`, {
            method: 'POST',
        });
        return res.json();
    }


    // ════════════════════════════════════════
    // 2. STATUS
    // ════════════════════════════════════════
    function setStatus(online) {
        if (online) {
            statusPill.classList.remove('offline');
            statusPill.innerHTML = '<span class="status-dot"></span> Connected';
        } else {
            statusPill.classList.add('offline');
            statusPill.innerHTML = '<span class="status-dot"></span> Offline';
        }
    }


    // ════════════════════════════════════════
    // 3. LOAD STATS & FILES
    // ════════════════════════════════════════
    async function loadStats() {
        try {
            const data = await apiStats();
            statFiles.textContent  = data.total_files;
            statChunks.textContent = data.total_chunks;

            fileList.innerHTML = '';
            data.files.forEach(file => {
                const fname = typeof file === 'string' ? file : file.name;
                const url   = typeof file === 'string' ? '' : file.url;

                let el;
                if (url) {
                    el = document.createElement('a');
                    el.href = url;
                    el.target = '_blank';
                    el.className = 'file-item with-link';
                } else {
                    el = document.createElement('div');
                    el.className = 'file-item';
                }
                el.textContent = `📄 ${fname}`;
                el.title = fname;
                fileList.appendChild(el);
            });

            setStatus(true);
        } catch (err) {
            console.error('Stats error:', err);
            statFiles.textContent  = '!';
            statChunks.textContent = '!';
            fileList.innerHTML = '<div class="loading">Cannot connect to backend</div>';
            setStatus(false);
        }
    }


    // ════════════════════════════════════════
    // 4. MESSAGE RENDERING
    // ════════════════════════════════════════
    function clearWelcome() {
        const welcome = messagesBox.querySelector('.welcome-screen');
        if (welcome) welcome.remove();
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatAnswer(text) {
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    function scrollToBottom() {
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    function addUserMessage(text) {
        clearWelcome();
        const el = document.createElement('div');
        el.className = 'message user';
        el.innerHTML = `
            <div class="message-avatar">🧑</div>
            <div class="message-content">${escapeHtml(text)}</div>
        `;
        messagesBox.appendChild(el);
        scrollToBottom();
    }

    function addTypingIndicator() {
        const el = document.createElement('div');
        el.className = 'message bot';
        el.id = 'typingIndicator';
        el.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="typing"><span></span><span></span><span></span></div>
            </div>
        `;
        messagesBox.appendChild(el);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    function renderSource(s, i) {
        const fname = escapeHtml(s.source_file);
        const loc   = escapeHtml(s.location);
        const text  = escapeHtml((s.text || '').substring(0, 200));
        const url   = s.url || '';

        const fileLabel = url
            ? `<a href="${url}" target="_blank">📄 ${fname} 🔗</a>`
            : `📄 ${fname}`;

        const metaParts = [];
        if (s.branch)   metaParts.push(`🎓 ${escapeHtml(s.branch)}`);
        if (s.semester) metaParts.push(`📅 Sem ${escapeHtml(s.semester)}`);
        if (s.subject)  metaParts.push(`📚 ${escapeHtml(s.subject)}`);
        const meta = metaParts.length
            ? `<div class="source-item-meta">${metaParts.join(' · ')}</div>`
            : '';

        return `
            <div class="source-item">
                <div class="source-item-header">
                    <span>${i + 1}. ${fileLabel} · ${loc}</span>
                    <span class="source-item-score">Score: ${s.score.toFixed(2)}</span>
                </div>
                ${meta}
                <div class="source-item-text">"${text}…"</div>
            </div>
        `;
    }

    function addBotMessage(answer, sources = []) {
        const el = document.createElement('div');
        el.className = 'message bot';

        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            const items = sources.map(renderSource).join('');
            sourcesHtml = `
                <div class="sources">
                    <div class="sources-header" onclick="this.parentElement.classList.toggle('open')">
                        📚 View ${sources.length} sources
                    </div>
                    <div class="sources-content">${items}</div>
                </div>
            `;
        }

        el.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                ${formatAnswer(answer)}
                ${sourcesHtml}
            </div>
        `;
        messagesBox.appendChild(el);
        scrollToBottom();
    }

    function addErrorMessage(error) {
        const el = document.createElement('div');
        el.className = 'message bot';
        el.innerHTML = `
            <div class="message-avatar">⚠️</div>
            <div class="message-content">
                <div class="error-banner">
                    <strong>Error:</strong> ${escapeHtml(error)}
                </div>
                Make sure the backend is running at <code>${API_URL}</code>
            </div>
        `;
        messagesBox.appendChild(el);
        scrollToBottom();
    }


    // ════════════════════════════════════════
    // 5. SEND MESSAGE
    // ════════════════════════════════════════
    async function sendMessage(message) {
        message = message.trim();
        if (!message) return;

        addUserMessage(message);
        chatInput.value = '';
        autoResize();
        submitBtn.disabled = true;
        addTypingIndicator();

        try {
            const data = await apiChat(message);
            removeTypingIndicator();
            addBotMessage(data.answer, data.sources);
        } catch (err) {
            removeTypingIndicator();
            addErrorMessage(err.message);
            setStatus(false);
        } finally {
            submitBtn.disabled = false;
            chatInput.focus();
        }
    }


    // ════════════════════════════════════════
    // 6. INPUT HANDLING
    // ════════════════════════════════════════
    function autoResize() {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
    }

    chatInput.addEventListener('input', autoResize);

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage(chatInput.value);
    });


    // ════════════════════════════════════════
    // 7. SUGGESTION CHIPS
    // ════════════════════════════════════════
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('suggestion-chip')) {
            sendMessage(e.target.textContent);
        }
    });


    // ════════════════════════════════════════
    // 8. CLEAR CHAT
    // ════════════════════════════════════════
    clearBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        if (!confirm('Clear all messages?')) return;

        await apiReset();

        messagesBox.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-icon">✨</div>
                <h2>Chat cleared</h2>
                <p>Start a new conversation below.</p>
            </div>
        `;
    });


    // ════════════════════════════════════════
    // 9. INIT
    // ════════════════════════════════════════
    loadStats();
    chatInput.focus();
    console.log('💬 Chat ready. Session:', SESSION_ID);

})();