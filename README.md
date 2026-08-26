# 📚 EduQuest: AI-Powered Academic Companion Platform

> **Study Smarter, Not Harder.**  
> EduQuest transforms static academic materials (PDFs, PPTXs, DOCXs, and scanned notes) into a unified, interactive knowledge engine powered by Hybrid RAG (BM25 + FAISS + BGE-M3 + Cross-Encoder Reranker) and Large Language Models.

---

## 🔗 Live Links

* **Frontend Web Application:** [https://eduquest-jiit.vercel.app](https://eduquest-jiit.vercel.app) *(or [https://eduquest-jiit.me](https://eduquest-jiit.me))*
* **API Server:** `https://api.eduquest-jiit.me`
* **Interactive API Documentation:** [https://api.eduquest-jiit.me/docs](https://api.eduquest-jiit.me/docs)

---

## 🌟 Key Features

EduQuest offers five core modules designed specifically for engineering undergraduates:

### 1. 💬 Document Chat (Context-Aware RAG)
* **Hybrid Search:** Combines Okapi BM25 keyword search and dense vector embeddings via **BAAI/bge-m3** (1024 dimensions).
* **Two-Stage Retrieval:** Candidates retrieved via hybrid search are re-ranked using **`bge-reranker-v2-m3`** cross-encoder for high-precision context retrieval.
* **Inline Source Citations:** Every response includes clickable source references with exact locations (e.g., page/slide numbers) and Google Drive links.
* **Fallback Mechanisms:** Automatically falls back to Google Search grounding / general LLM knowledge when local documents lack coverage.
* **Multi-Turn Memory:** Sliding-window context memory retains history for multi-step follow-ups.

### 2. 📝 Lecture Summarizer
* **Single & Series Summaries:** Summarize individual lecture files or entire course series.
* **Hierarchical Chunk Merging:** Large content is batched and merged in passes to bypass LLM token limits (prevents HTTP 413 errors).
* **Progressive Dialog:** Remembers partial queries (e.g., *"summarize DBMS"* → *"sem 3"* → *"lec 2"*).
* **Interactive Follow-ups:** Easily reformat outputs on demand (*"give in brief"*, *"bullet points only"*, *"explain simpler"*).

### 3. 🎯 Quiz Generator
* **6 Question Formats:** Multiple Choice (MCQ), True/False, Fill in the Blanks, Short Answer, Long Answer, and Numerical Problems.
* **Smart Answer Evaluation:** Handles math equivalencies (e.g., $8/15 \approx 0.533$) using relative (1%) and absolute (0.01) tolerance matching.
* **Interactive Interface:** Single-question navigation, instant answer reveal, explanation cards, and automatic grade scorecards.
* **Exportable Reports:** Download quizzes as Markdown (`.md`) or JSON files.

### 4. 🔥 Previous Year Question (PYQ) Analyser
* **Automatic Exam Type Detection:** Identifies T1 (Test 1), T2 (Test 2), and T3 (End-Sem) papers using regex pattern matching.
* **Subject Verification:** Verifies paper text against subject keywords to prevent cross-contamination.
* **Exam Insights:** Generates topic frequency charts with priority badges (HIGH/MEDIUM/LOW), marks distribution, and recurring question patterns.
* **Predicted Papers:** Generates AI-predicted practice test papers based on historical exam patterns.

### 5. 📄 Resume Ranker
* **Cohort-Based Ranking:** Ranks student resumes against peers in the same year and target job role.
* **Scoring Mechanics:** 70% direct skill pattern matching + 30% TF-IDF cosine similarity using `scikit-learn`.
* **Enrollment Tracking:** Persistent CSV storage tracks student resubmissions, displaying Before vs. After score deltas.
* **Targeted Recommendations:** Identifies missing skills and prioritizes them based on placement urgency.

---

## 🏗️ System Architecture

```
                               ┌─────────────────────────┐
                               │   Web Browser (Client)  │
                               │  HTML5 / CSS3 / JS      │
                               │  MathJax v3 · Marked.js │
                               └────────────┬────────────┘
                                            │ HTTPS
                               ┌────────────▼────────────┐
                               │    Vercel Global CDN    │
                               │  (eduquest-jiit.me)     │
                               └────────────┬────────────┘
                                            │ HTTPS API Calls
                               ┌────────────▼────────────┐
                               │   Nginx Reverse Proxy   │
                               │  (api.eduquest-jiit.me) │
                               └────────────┬────────────┘
                                            │ Localhost :8000
                               ┌────────────▼────────────┐
                               │   FastAPI Backend Server│
                               │   (Azure B2s Ubuntu VM) │
                               └────────────┬────────────┘
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         │                                  │                                  │
┌────────▼────────┐                ┌────────▼────────┐                ┌────────▼────────┐
│  RAG Chatbot    │                │  Quiz Generator │                │ PYQ Analyser    │
│  & Summarizer   │                │  & Resume Rank  │                │ & Predictor     │
└────────┬────────┘                └────────┬────────┘                └────────┬────────┘
         │                                  │                                  │
         └──────────────────────────────────┼──────────────────────────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │  Two-Stage Search Engine│
                               │  1. BM25 + FAISS        │
                               │  2. BGE-Reranker-v2-M3  │
                               └────────────┬────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
        ┌───────────▼───────────┐                       ┌───────────▼───────────┐
        │  Local Index Store    │                       │  LLM Inference Engine │
        │  • chunks.json        │                       │  Primary: Groq        │
        │  • faiss.index        │                       │    (Qwen3-32B)        │
        │  • bm25.pkl           │                       │  Fallback: OpenRouter │
        └───────────────────────┘                       │    (Qwen3-14B:free)   │
                                                        └───────────────────────┘
```

---

## 🛠️ Tech Stack

* **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, Pydantic
* **LLM Engine:** [Groq LPU](https://groq.com/) (Primary: `gpt-oss-120b`) with [OpenRouter](https://openrouter.ai/) (Fallback: `openrouter:free`)
* **Embeddings & Vector Search:** [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) via `sentence-transformers`, [FAISS](https://github.com/facebookresearch/faiss) (`IndexFlatIP`)
* **Keyword Search:** [rank_bm25](https://pypi.org/project/rank-bm25/) (Okapi BM25)
* **Reranker:** [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) via `sentence-transformers` CrossEncoder
* **Document Extraction:** `pdfplumber`, `python-pptx`, `python-docx`
* **OCR System:** Tesseract OCR + `pdf2image` (Poppler backend) + `Pillow`
* **Machine Learning & NLP:** `scikit-learn` (TF-IDF, Cosine Similarity), `numpy`, `nltk`
* **Frontend:** Vanilla HTML5, CSS3 (relative units `rem`, fluid typography `clamp()`), JavaScript
* **Client-Side Rendering:** [MathJax v3](https://www.mathjax.org/) (LaTeX math), [Marked.js](https://marked.js.org/) (Markdown)
* **Cloud Infrastructure:** Microsoft Azure VM (Ubuntu 24.04 LTS), Vercel, Nginx, Let's Encrypt (Certbot)

---

## 📁 Repository Structure

```
EduQuest/
├── .env.example                            # Configuration template
├── .gitignore
├── requirements.txt                        # Python dependencies
├── README.md                               # Project documentation
│
├── dataset/                                # Raw course materials
│   └── study_material/
│       ├── CSE/
│       │   ├── 3/                          # Semester/Year
│       │   │   ├── Data Structures/
│       │   │   │   ├── Lectures/
│       │   │   │   ├── Tutorials/
│       │   │   │   ├── PYQs/
│       │   │   │   └── gdrive_links.json   # Drive links mapping
│       │   │   └── Database Management Systems/
│       │   └── 4/
│       └── M&C/
│
├── index_store/                            # Built indexes (auto-generated)
│   ├── chunks.json                         # Chunk text + metadata
│   ├── faiss.index                         # BGE-M3 vector embeddings
│   ├── bm25.pkl                            # BM25 sparse index
│   └── config.json                         # Index build settings
│
├── resume_index_store/                     # Resume ranking CSV database
│   ├── 3/                                  # Year 3 rankings
│   │   └── rankings_Software_Developer.csv
│   └── 4/
│
├── src/
│   ├── IR/                                 # Search & AI Backend
│   │   ├── api.py                          # FastAPI endpoints
│   │   ├── config.py                       # Configuration loader
│   │   ├── llm.py                          # Resilient Groq + OpenRouter client
│   │   ├── extract.py                      # Multi-format document extractor
│   │   ├── ocr.py                          # Tesseract OCR wrapper
│   │   ├── build_index.py                  # FAISS & BM25 index builder
│   │   ├── search.py                       # Two-stage hybrid searcher
│   │   ├── chatbot.py                      # Conversational RAG controller
│   │   ├── quiz_indexed.py                 # Quiz generator & scoring
│   │   ├── pyq_analyser_indexed.py         # PYQ analytics & predicted papers
│   │   ├── summariser_indexed.py           # Multi-lecture summarizer
│   │   └── resume_api.py                   # Resume ranking API wrapper
│   │
│   ├── resume_project/                     # Resume ML Engine
│   │   ├── ranking.py                      # TF-IDF & Skill Matcher
│   │   ├── user_ranking.py                 # Cohort & CSV Manager
│   │   └── job_desc/                       # Skill profile definitions
│   │
│   └── web/                                # Frontend Application
│       ├── index.html                      # Landing page
│       ├── chat.html / chat.js / chat.css  # Document Chat UI
│       ├── quiz.html / quiz.js / quiz.css  # Quiz UI
│       ├── pyq.html / pyq.js / pyq.css     # PYQ Analyser UI
│       ├── resume.html / resume.js / css   # Resume Ranker UI
│       ├── config.js                       # API URL selector
│       ├── style.css                       # Global styles
│       └── utils.css                       # Responsive CSS variables
```

---

## ⚡ Local Setup & Development

### Prerequisites
* **Python:** 3.10+
* **System Binaries (for OCR on scanned PDFs):**
  * **Tesseract OCR:** [Download Windows Installer](https://github.com/UB-Mannheim/tesseract/wiki) (Install to default path `C:\Program Files\Tesseract-OCR\`)
  * **Poppler for Windows:** [Download Release](https://github.com/oschwartz10612/poppler-windows/releases) (Extract to `C:\poppler\` and add `C:\poppler\Library\bin` to PATH)

---

### Step 1: Clone Repository & Setup Virtual Environment

```powershell
# Clone the repository
git clone https://github.com/Janmejai-Pandey/EduQuest.git
cd EduQuest

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
```

---

### Step 2: Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```env
# ═══════════════════════════════════════════════════════
# LLM PROVIDERS
# ═══════════════════════════════════════════════════════
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=gpt-oss-120b
GROQ_TEMPERATURE=0.3
GROQ_MAX_TOKENS=2048

OPENROUTER_API_KEY=sk-or-v1-your_openrouter_api_key_here
OPENROUTER_MODEL=openrouter:free
OPENROUTER_TEMPERATURE=0.3
OPENROUTER_MAX_TOKENS=2048
OPENROUTER_APP_URL=http://localhost:8000
OPENROUTER_APP_NAME=EduQuest

LLM_MAX_RETRIES=2
LLM_RETRY_DELAY=2

# ═══════════════════════════════════════════════════════
# EMBEDDINGS & RERANKER
# ═══════════════════════════════════════════════════════
EMBED_MODEL=BAAI/bge-m3
EMBED_BATCH_SIZE=32
EMBED_NORMALIZE=true

RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANKER_USE_FP16=false
USE_RERANKER=true

# ═══════════════════════════════════════════════════════
# SEARCH & CHATBOT THRESHOLDS
# ═══════════════════════════════════════════════════════
SEARCH_TOP_K=5
SEARCH_RERANK_POOL=20
SEARCH_ALPHA=0.5
SEARCH_MIN_SCORE=0.3

MAX_HISTORY_TURNS=6
WEB_FALLBACK_SCORE=0.4
ENABLE_WEB_FALLBACK=false
```

> **Note:** Get free API keys at [Groq Console](https://console.groq.com/keys) and [OpenRouter](https://openrouter.ai/keys).

---

### Step 4: Build Search Indexes

Index your course materials placed in `dataset/study_material/`:

```powershell
python src/IR/extract.py
```

---

### Step 5: Run Locally

#### Terminal 1 — FastAPI Backend:
```powershell
uvicorn src.api:app --reload --port 8000
```
> API runs at `http://localhost:8000` | Swagger UI at `http://localhost:8000/docs`

#### Terminal 2 — Frontend:
```powershell
cd src/web
python -m http.server 5500 # or just start Live Server on VS Code
```
> Open browser at `http://localhost:5500`

---

## 🚀 Deployment Architecture & Production Setup

EduQuest is deployed using a decoupled, high-availability production setup:

* **Frontend:** Hosted on **Vercel** connected directly to the GitHub repository for automatic CD/CI deployments.
* **Backend API:** Hosted on a **Microsoft Azure B2s Virtual Machine** (Ubuntu 24.04 LTS, 4 GB RAM, 2 vCPUs) located in Central India.
* **Domain & Security:** Custom `.me` domain (`eduquest-jiit.me`) with a dedicated `api` subdomain routed through **Nginx** reverse proxy and secured with **Let's Encrypt SSL (Certbot)**.

```
+-----------------------------------------------------------------------------------+
|                                  PRODUCTION SETUP                                 |
+-----------------------------------------------------------------------------------+
|  Custom Domain (Namecheap):     eduquest-jiit.me                                  |
|  Frontend CDN (Vercel):         https://eduquest-jiit.vercel.app                  |
|  Backend Host (Azure VM):       Ubuntu Server 24.04 LTS                           |
|  Backend API Subdomain:         https://api.eduquest-jiit.me                      |
|  Reverse Proxy & SSL:           Nginx 1.24 + Let's Encrypt Certbot                |
|  Process Manager:               systemd (eduquest.service)                        |
+-----------------------------------------------------------------------------------+
```

### DNS Configuration (Namecheap)

| Type | Host | Value | Purpose |
|---|---|---|---|
| **A** | `@` | `76.76.21.21` | Apex domain points to Vercel |
| **CNAME** | `www` | `cname.vercel-dns.com` | WWW subdomain routes to Vercel |
| **A** | `api` | `4.187.149.198` | API subdomain points to Azure VM IP |

---

### Server Configuration (Azure Ubuntu VM)

#### 1. Systemd Service (`/etc/systemd/system/eduquest.service`)

Manages the FastAPI Uvicorn process automatically with background restart policies:

```ini
[Unit]
Description=EduQuest FastAPI Backend Service
After=network.target

[Service]
User=janmejai
Group=janmejai
WorkingDirectory=/home/janmejai/Eduquest/src/IR
Environment="PATH=/home/janmejai/Eduquest/.venv/bin:/usr/bin"
EnvironmentFile=/home/janmejai/Eduquest/.env
ExecStart=/home/janmejai/Eduquest/.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000 --workers 1 --timeout-keep-alive 120
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 2. Nginx Reverse Proxy with SSL (`/etc/nginx/sites-available/eduquest`)

Routes external HTTPS traffic from `api.eduquest-jiit.me` to local Uvicorn process on port 8000 while managing SSL certificates:

```nginx
server {
    server_name api.eduquest-jiit.me;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        client_max_body_size 10M;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/api.eduquest-jiit.me/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.eduquest-jiit.me/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = api.eduquest-jiit.me) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name api.eduquest-jiit.me;
    return 404;
}
```

---

## 📖 Usage Guide

### 1. Document Chat (`/chat.html`)
* Browse files on the left sidebar tree (Branch → Year → Subject → Category).
* Ask questions in natural language (e.g., *"What is the auxiliary equation for a Cauchy-Euler differential equation?"*).
* View answers formatted in Markdown with MathJax rendered LaTeX equations.
* Click **"View Sources"** to inspect relevant document excerpts and jump to the original file on Google Drive.

### 2. Quiz Generator (`/quiz.html`)
* Select Branch, Year, Subject, or specific files.
* Select question formats (MCQs, True/False, Fill in Blanks, Short/Long Answer, Numerical).
* Choose difficulty (Easy, Medium, Hard) and question count.
* Attempt the generated quiz interactively, reveal correct answers with detailed explanations, and review your final grade scorecard.

### 3. PYQ Analyser (`/pyq.html`)
* Select a year, subject, and exam type (T1, T2, T3).
* View topic frequency bar charts, question type breakdowns, and marks patterns.
* Inspect recurring question trends and top must-study topics.
* Switch to **"Practice Paper"** mode to take an AI-predicted exam paper based on past paper patterns.

### 4. Resume Ranker (`/resume.html`)
* Fill in your name, enrollment number, year, branch, and target job role.
* Upload your resume (`.pdf` or `.pptx`).
* Get an instant ATS-style score, cohort rank, percentile standing, and an actionable list of missing technical skills.
* Re-upload an updated resume with the same enrollment number to see your **Before vs. After** score progress.

---

## ⚙️ Configuration Reference (`.env`)

| Variable | Default Value | Description |
|---|---|---|
| `GROQ_API_KEY` | `""` | Primary LLM provider key |
| `GROQ_MODEL` | `gpt-oss-120b` | Primary Groq model ID |
| `OPENROUTER_API_KEY` | `""` | Fallback LLM provider key |
| `OPENROUTER_MODEL` | `openrouter:free` | Fallback model on OpenRouter |
| `EMBED_MODEL` | `BAAI/bge-m3` | Vector embedding model (1024 dim) |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | Cross-encoder reranking model |
| `USE_RERANKER` | `true` | Toggle cross-encoder reranking stage |
| `SEARCH_TOP_K` | `5` | Final context chunks sent to LLM |
| `SEARCH_RERANK_POOL` | `20` | Candidate chunks passed to reranker |
| `SEARCH_ALPHA` | `0.5` | Hybrid weight (0.0 = BM25, 1.0 = Vector) |
| `SEARCH_MIN_SCORE` | `0.3` | Minimum score threshold for context |

---

## 👥 Contributors

EduQuest was built and is maintained by:

* **Janmejai Pandey** — [@Janmejai-Pandey](https://github.com/Janmejai-Pandey)
* **Pari Mittal** — [@parim2250](https://github.com/parim2250)

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/NewFeature`)
3. Commit your changes (`git commit -m 'Add NewFeature'`)
4. Push to the branch (`git push origin feature/NewFeature`)
5. Open a Pull Request