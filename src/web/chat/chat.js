(function () {
  "use strict";

  // ── Config ──────────────────────────────
  const API_URL = "http://localhost:8000";
  const SESSION_ID = "web_" + Date.now();

  // ── DOM ─────────────────────────────────
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const submitBtn = document.getElementById("submitBtn");
  const messagesBox = document.getElementById("chatMessages");
  const statusPill = document.getElementById("statusPill");
  const statFiles = document.getElementById("statFiles");
  const statChunks = document.getElementById("statChunks");
  const fileList = document.getElementById("fileList");
  const clearBtn = document.getElementById("clearChatBtn");

  // ════════════════════════════════════════
  // 1. API CALLS
  // ════════════════════════════════════════
  async function apiChat(message) {
    const res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: SESSION_ID }),
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
      method: "POST",
    });
    return res.json();
  }

  // ════════════════════════════════════════
  // 2. STATUS
  // ════════════════════════════════════════
  function setStatus(online) {
    if (online) {
      statusPill.classList.remove("offline");
      statusPill.innerHTML = '<span class="status-dot"></span> Connected';
    } else {
      statusPill.classList.add("offline");
      statusPill.innerHTML = '<span class="status-dot"></span> Offline';
    }
  }

  // ════════════════════════════════════════
  // 3. LOAD STATS & FILES (with tree)
  // ════════════════════════════════════════
  let fullTree = {}; // store globally for search/filter

  async function loadStats() {
    try {
      const data = await apiStats();
      statFiles.textContent = data.total_files;
      statChunks.textContent = data.total_chunks;

      fullTree = data.tree || {};
      renderTree(fullTree);

      setStatus(true);
    } catch (err) {
      console.error("Stats error:", err);
      statFiles.textContent = "!";
      statChunks.textContent = "!";
      fileList.innerHTML =
        '<div class="tree-empty">Cannot connect to backend</div>';
      setStatus(false);
    }
  }

  // ════════════════════════════════════════
  // 3b. RENDER FILE TREE
  // ════════════════════════════════════════
  function renderTree(tree) {
    if (!tree || Object.keys(tree).length === 0) {
      fileList.innerHTML = '<div class="tree-empty">No files indexed yet</div>';
      return;
    }

    let html = "";

    // Sort branches
    const branches = Object.keys(tree).sort();
    branches.forEach((branch) => {
      const sems = tree[branch];
      const branchCount = countFilesIn(sems);

      html += `
            <div class="tree-node tree-branch">
                <button class="tree-toggle" onclick="this.parentElement.classList.toggle('open')">
                    <span class="tree-arrow">▶</span>
                    🎓 ${escapeHtml(branch)}
                    <span class="tree-count">${branchCount}</span>
                </button>
                <div class="tree-children">
        `;

      // Sort semesters numerically if possible
      const sems_keys = Object.keys(sems).sort((a, b) => {
        const na = parseInt(a),
          nb = parseInt(b);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        return a.localeCompare(b);
      });

      sems_keys.forEach((sem) => {
        const subjects = sems[sem];
        const semCount = countFilesIn(subjects);

        html += `
                <div class="tree-node tree-sem">
                    <button class="tree-toggle" onclick="this.parentElement.classList.toggle('open')">
                        <span class="tree-arrow">▶</span>
                        📅 Semester ${escapeHtml(sem)}
                        <span class="tree-count">${semCount}</span>
                    </button>
                    <div class="tree-children">
            `;

        // Sort subjects alphabetically
        const subjects_keys = Object.keys(subjects).sort();
        subjects_keys.forEach((subject) => {
          const categories = subjects[subject];
          const subjectCount = countFilesIn(categories);

          html += `
                    <div class="tree-node tree-subject">
                        <button class="tree-toggle" onclick="this.parentElement.classList.toggle('open')">
                            <span class="tree-arrow">▶</span>
                            📚 ${escapeHtml(subject)}
                            <span class="tree-count">${subjectCount}</span>
                        </button>
                        <div class="tree-children">
                `;

          // Sort categories with preferred order
          const categoryOrder = [
            "Syllabus",
            "Lectures",
            "Notes",
            "Tutorials",
            "Assignments",
            "Lab",
            "PYQs",
            "Solutions",
            "Books",
            "Other",
          ];
          const cat_keys = Object.keys(categories).sort((a, b) => {
            const ia = categoryOrder.indexOf(a);
            const ib = categoryOrder.indexOf(b);
            if (ia === -1 && ib === -1) return a.localeCompare(b);
            if (ia === -1) return 1;
            if (ib === -1) return -1;
            return ia - ib;
          });

          cat_keys.forEach((category) => {
            const files = categories[category];
            const catIcon = getCategoryIcon(category);

            html += `
                        <div class="tree-node tree-category">
                            <button class="tree-toggle" onclick="this.parentElement.classList.toggle('open')">
                                <span class="tree-arrow">▶</span>
                                ${catIcon} ${escapeHtml(category)}
                                <span class="tree-count">${files.length}</span>
                            </button>
                            <div class="tree-children">
                    `;

            // Sort files alphabetically
            files.sort((a, b) => a.name.localeCompare(b.name));
            files.forEach((file) => {
              const fileIcon = getFileIcon(file.name);
              if (file.url) {
                html += `
                                <a href="${escapeAttr(file.url)}"
                                   target="_blank"
                                   class="tree-file with-link"
                                   title="${escapeAttr(file.name)} — opens in new tab">
                                    <span class="file-emoji">${fileIcon}</span>
                                    <span>${escapeHtml(file.name)}</span>
                                    <span class="file-link-icon">🔗</span>
                                </a>
                            `;
              } else {
                html += `
                                <div class="tree-file" title="${escapeAttr(file.name)}">
                                    <span class="file-emoji">${fileIcon}</span>
                                    <span>${escapeHtml(file.name)}</span>
                                </div>
                            `;
              }
            });

            html += `</div></div>`; // close category
          });

          html += `</div></div>`; // close subject
        });

        html += `</div></div>`; // close sem
      });

      html += `</div></div>`; // close branch
    });

    fileList.innerHTML = html;
  }

  // ════════════════════════════════════════
  // 3c. HELPERS
  // ════════════════════════════════════════
  function countFilesIn(obj) {
    if (Array.isArray(obj)) return obj.length;
    if (typeof obj !== "object" || obj === null) return 0;
    return Object.values(obj).reduce((sum, v) => sum + countFilesIn(v), 0);
  }

  function getCategoryIcon(cat) {
    const icons = {
      Lectures: "🎥",
      Tutorials: "✏️",
      PYQs: "📝",
      Assignments: "📋",
      Lab: "🧪",
      Books: "📖",
      Syllabus: "📜",
      Solutions: "💡",
      Notes: "📒",
      Other: "📄",
    };
    return icons[cat] || "📄";
  }

  function getFileIcon(filename) {
    const ext = filename.split(".").pop().toLowerCase();
    if (ext === "pdf") return "📕";
    if (["pptx", "ppt"].includes(ext)) return "📊";
    if (["docx", "doc"].includes(ext)) return "📘";
    if (["xlsx", "xls"].includes(ext)) return "📗";
    if (["mp4", "avi", "mov"].includes(ext)) return "🎬";
    return "📄";
  }

  function escapeAttr(str) {
    return escapeHtml(str).replace(/"/g, "&quot;");
  }

  // ════════════════════════════════════════
  // 3d. TREE CONTROLS (expand/collapse/search)
  // ════════════════════════════════════════
  document.addEventListener("DOMContentLoaded", () => {
    const expandBtn = document.getElementById("expandAllBtn");
    const collapseBtn = document.getElementById("collapseAllBtn");
    const searchInput = document.getElementById("fileSearch");

    if (expandBtn) {
      expandBtn.addEventListener("click", () => {
        document
          .querySelectorAll("#fileList .tree-node")
          .forEach((n) => n.classList.add("open"));
      });
    }

    if (collapseBtn) {
      collapseBtn.addEventListener("click", () => {
        document
          .querySelectorAll("#fileList .tree-node")
          .forEach((n) => n.classList.remove("open"));
      });
    }

    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();

        if (!query) {
          renderTree(fullTree);
          return;
        }

        const filtered = filterTree(fullTree, query);
        renderTree(filtered);

        // Auto-expand all nodes when searching
        setTimeout(() => {
          document
            .querySelectorAll("#fileList .tree-node")
            .forEach((n) => n.classList.add("open"));
        }, 50);
      });
    }
  });

  function filterTree(tree, query) {
    const result = {};
    for (const [branch, sems] of Object.entries(tree)) {
      const newSems = {};
      for (const [sem, subjects] of Object.entries(sems)) {
        const newSubjects = {};
        for (const [subject, categories] of Object.entries(subjects)) {
          const newCategories = {};
          for (const [category, files] of Object.entries(categories)) {
            const matches = files.filter(
              (f) =>
                f.name.toLowerCase().includes(query) ||
                subject.toLowerCase().includes(query) ||
                category.toLowerCase().includes(query) ||
                branch.toLowerCase().includes(query),
            );
            if (matches.length > 0) {
              newCategories[category] = matches;
            }
          }
          if (Object.keys(newCategories).length > 0) {
            newSubjects[subject] = newCategories;
          }
        }
        if (Object.keys(newSubjects).length > 0) {
          newSems[sem] = newSubjects;
        }
      }
      if (Object.keys(newSems).length > 0) {
        result[branch] = newSems;
      }
    }
    return result;
  }

  // ════════════════════════════════════════
  // 4. MESSAGE RENDERING
  // ════════════════════════════════════════
  function clearWelcome() {
    const welcome = messagesBox.querySelector(".welcome-screen");
    if (welcome) welcome.remove();
  }

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatAnswer(text) {
    return escapeHtml(text).replace(/\n/g, "<br>");
  }

  function scrollToBottom() {
    messagesBox.scrollTop = messagesBox.scrollHeight;
  }

  function addUserMessage(text) {
    clearWelcome();
    const el = document.createElement("div");
    el.className = "message user";
    el.innerHTML = `
            <div class="message-avatar">🧑</div>
            <div class="message-content">${escapeHtml(text)}</div>
        `;
    messagesBox.appendChild(el);
    scrollToBottom();
  }

  function addTypingIndicator() {
    const el = document.createElement("div");
    el.className = "message bot";
    el.id = "typingIndicator";
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
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  function renderSource(s, i) {
    const fname = escapeHtml(s.source_file);
    const loc   = escapeHtml(s.location);
    const text  = escapeHtml((s.text || '').substring(0, 200));
    const url   = s.url || '';
    const isWeb = s.is_web === true;

    const fileLabel = url
        ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">${fname} 🔗</a>`
        : fname;

    const metaParts = [];
    if (s.branch)   metaParts.push(`🎓 ${escapeHtml(s.branch)}`);
    if (s.semester) metaParts.push(`📅 Sem ${escapeHtml(s.semester)}`);
    if (s.subject)  metaParts.push(`📚 ${escapeHtml(s.subject)}`);
    const meta = metaParts.length
        ? `<div class="source-item-meta">${metaParts.join(' · ')}</div>`
        : '';

    return `
        <div class="source-item ${isWeb ? 'web-source' : ''}">
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
    const el = document.createElement("div");
    el.className = "message bot";

    // Sources HTML
    let sourcesHtml = "";
    if (sources && sources.length > 0) {
      const items = sources.map(renderSource).join("");
      sourcesHtml = `
            <div class="sources">
                <div class="sources-header" onclick="this.parentElement.classList.toggle('open')">
                    📚 View ${sources.length} sources
                </div>
                <div class="sources-content">${items}</div>
            </div>
        `;
    }

    // ✅ RENDER MARKDOWN with marked.js
    const renderedAnswer =
      typeof marked !== "undefined" && marked.parse
        ? marked.parse(answer)
        : answer.replace(/</g, "&lt;").replace(/\n/g, "<br>");

    el.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content markdown-body">
            ${renderedAnswer}
            ${sourcesHtml}
        </div>
    `;
    messagesBox.appendChild(el);
    scrollToBottom();
  }

  function addErrorMessage(error) {
    const el = document.createElement("div");
    el.className = "message bot";
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
    chatInput.value = "";
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
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + "px";
  }

  chatInput.addEventListener("input", autoResize);

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(chatInput.value);
  });

  // ════════════════════════════════════════
  // 7. SUGGESTION CHIPS
  // ════════════════════════════════════════
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("suggestion-chip")) {
      sendMessage(e.target.textContent);
    }
  });

  // ════════════════════════════════════════
  // 8. CLEAR CHAT
  // ════════════════════════════════════════
  clearBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    if (!confirm("Clear all messages?")) return;

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
  console.log("💬 Chat ready. Session:", SESSION_ID);
})();
