#!/usr/bin/env python3
"""
jiit_shelf_scraper.py
Complete scraper for JIIT Shelf — auto-selects Branch & Semester,
visits every subject, expands every accordion section, and downloads
ALL GDrive files sorted strictly into:
   <subject>/<category>/<file>
where category = Lectures | Tutorials | PYQs | YouTube Resources |
                Books | Course Description

Run: python jiit_shelf_scraper.py
"""

import os
import re
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Set, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs

import requests
import gdown
from bs4 import BeautifulSoup
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager

# ═══════════════════════════════════════════════════════════════════════════════
#                              CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG = {
    "BASE_URL"      : "https://jiitshelf.vercel.app",
    "BRANCH"        : "CSE",
    "SEMESTER"      : "3",
    "HEADLESS"      : False,
    "OUTPUT_DIR"    : "jiit_downloads",
    "MAX_WORKERS"   : 4,
    "SKIP_EXISTING" : True,
    "PAGE_TIMEOUT"  : 20,
    "CHUNK_SIZE"    : 8192,
    "SCROLL_PAUSE"  : 0.8,
}

# Exact accordion sections shown on subject pages
CATEGORIES = [
    "Lectures",
    "Tutorials",
    "PYQs",
    "Course Description",
]

# Patterns
GDRIVE_PATTERNS = [
    r"https?://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
    r"https?://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
    r"https?://drive\.google\.com/uc\?(?:[^&]+&)*id=([a-zA-Z0-9_-]+)",
    r"https?://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
    r"https?://drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)",
    r"https?://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)",
    r"https?://docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)",
]
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in GDRIVE_PATTERNS]

RESOURCE_TYPES = {
    "folder"       : re.compile(r"drive\.google\.com/drive/folders/", re.I),
    "document"     : re.compile(r"docs\.google\.com/document/",       re.I),
    "presentation" : re.compile(r"docs\.google\.com/presentation/",   re.I),
}

# YouTube patterns (we won't download but we'll log them under YouTube Resources)
YOUTUBE_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+", re.I
)

# ═══════════════════════════════════════════════════════════════════════════════
#                              LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler("jiit_scraper.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("JIITShelf")

# ═══════════════════════════════════════════════════════════════════════════════
#                              DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GDriveLink:
    file_id       : str
    original_url  : str
    resource_type : str  = "file"
    source_page   : str  = ""
    subject       : str  = ""
    category      : str  = "General"   # always set to one of CATEGORIES
    item_name     : str  = ""
    is_folder     : bool = False
    found_at      : str  = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return asdict(self)


@dataclass
class DownloadResult:
    file_id      : str
    filename     : str  = ""
    filepath     : str  = ""
    size_bytes   : int  = 0
    success      : bool = False
    skipped      : bool = False
    error        : str  = ""
    subject      : str  = ""
    category     : str  = ""

    def to_dict(self):
        d = asdict(self)
        d["size_mb"] = round(self.size_bytes / 1024 / 1024, 2)
        return d

# ═══════════════════════════════════════════════════════════════════════════════
#                       JIIT SHELF BROWSER AUTOMATION
# ═══════════════════════════════════════════════════════════════════════════════

class JIITShelfBot:
    """Full automation of the JIIT Shelf SPA with proper category tracking."""

    def __init__(self):
        self.driver = self._init_driver()
        self.wait   = WebDriverWait(self.driver, CONFIG["PAGE_TIMEOUT"])
        self.gdrive_links : List[GDriveLink] = []
        # Track (file_id, category) so the same file can be added if it
        # appears in multiple categories (rare but possible)
        self.seen_pairs   : Set[tuple]       = set()

    # ── Driver setup ──────────────────────────────────────────────────────────

    def _init_driver(self):
        opts = Options()
        if CONFIG["HEADLESS"]:
            opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=opts)
        driver.execute_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        return driver

    # ── Generic helpers ───────────────────────────────────────────────────────

    def _safe_click(self, element):
        try:
            element.click()
        except (ElementClickInterceptedException, Exception):
            self.driver.execute_script("arguments[0].click();", element)

    def _scroll_into_view(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", element
        )
        time.sleep(0.2)

    def _scroll_to_bottom(self, max_scrolls: int = 6):
        last_h = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(max_scrolls):
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(CONFIG["SCROLL_PAUSE"])
            new_h = self.driver.execute_script("return document.body.scrollHeight")
            if new_h == last_h:
                break
            last_h = new_h

    # ── Open homepage ─────────────────────────────────────────────────────────

    def open_homepage(self):
        log.info(f"Opening {CONFIG['BASE_URL']}")
        self.driver.get(CONFIG["BASE_URL"])
        time.sleep(2)

    # ── Dropdown selection ────────────────────────────────────────────────────

    def _select_dropdown(self, label_text: str, option_text: str) -> bool:
        log.info(f"  Selecting '{option_text}' in '{label_text}' dropdown")
        # Native <select>
        try:
            sel_el = self.driver.find_element(
                By.XPATH,
                f"//label[normalize-space()='{label_text}']"
                f"/following::select[1]"
            )
            Select(sel_el).select_by_visible_text(option_text)
            log.info(f"    ✓ Native <select>")
            return True
        except Exception:
            pass
        # Custom React dropdown
        try:
            trigger = self.driver.find_element(
                By.XPATH,
                f"//label[normalize-space()='{label_text}']"
                f"/following::*[self::button or @role='combobox' "
                f"or contains(@class,'select') or contains(@class,'dropdown')][1]"
            )
            self._scroll_into_view(trigger)
            self._safe_click(trigger)
            time.sleep(0.6)
            option = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f"//*[normalize-space()='{option_text}' "
                    f"and (self::li or self::div or self::option "
                    f"or self::span or self::button)]"
                ))
            )
            self._safe_click(option)
            log.info(f"    ✓ Custom dropdown")
            time.sleep(0.5)
            return True
        except Exception as e:
            log.error(f"    ✗ Failed: {e}")
            return False

    def select_branch_and_semester(self, branch: str, semester: str):
        log.info("Selecting Branch and Semester ...")
        self._select_dropdown("Branch", branch)
        time.sleep(1.2)
        self._select_dropdown("Semester", semester)
        time.sleep(0.8)

    # ── View Subjects ─────────────────────────────────────────────────────────

    def click_view_subjects(self):
        log.info("Clicking 'View Subjects'")
        btn = self.wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz'), 'view subjects')]"
            ))
        )
        self._safe_click(btn)
        time.sleep(3)
        log.info(f"  ✓ At: {self.driver.current_url}")

    # ── Get subjects ──────────────────────────────────────────────────────────

    def get_subjects(self) -> List[dict]:
        log.info("Collecting subjects ...")
        time.sleep(2)
        try:
            self.wait.until(
                EC.presence_of_all_elements_located((
                    By.XPATH, "//button[contains(., 'View Material')]"
                ))
            )
        except TimeoutException:
            log.error("  ✗ No 'View Material' buttons found")
            return []

        buttons = self.driver.find_elements(
            By.XPATH, "//button[contains(., 'View Material')]"
        )
        log.info(f"  Found {len(buttons)} 'View Material' buttons")

        subjects = []
        for idx in range(len(buttons)):
            try:
                btns = self.driver.find_elements(
                    By.XPATH, "//button[contains(., 'View Material')]"
                )
                btn = btns[idx]
            except IndexError:
                break

            try:
                card = btn.find_element(By.XPATH, "./ancestor::*[self::div][1]")
                lines = [l.strip() for l in card.text.strip().split("\n")
                         if l.strip() and "View Material" not in l]
                name = lines[0] if len(lines) >= 1 else f"Subject_{idx+1}"
                code = lines[1] if len(lines) >= 2 else ""
            except Exception:
                name, code = f"Subject_{idx+1}", ""

            try:
                self._scroll_into_view(btn)
                self._safe_click(btn)
                time.sleep(2.5)
                url = self.driver.current_url
                subjects.append({"name": name, "code": code, "url": url})
                log.info(f"    [{idx+1}] {name} ({code})")
                self.driver.back()
                time.sleep(2)
            except Exception as e:
                log.error(f"    ✗ Failed on subject {idx+1}: {e}")
                continue

        log.info(f"  ✓ {len(subjects)} subjects collected")
        return subjects

    # ── Scrape subject — STRICT per-category collection ──────────────────────

    def scrape_subject(self, subject: dict):
        url  = subject["url"]
        name = subject["name"]
        log.info(f"\n▶ Subject: {name}")
        log.info(f"  URL: {url}")

        try:
            self.driver.get(url)
            time.sleep(2.5)
            self._scroll_to_bottom(max_scrolls=3)
        except Exception as e:
            log.error(f"  ✗ Load failed: {e}")
            return

        # ── 1. Course Description (it's a standalone button at the top) ──
        self._scrape_course_description(name, url)

        # ── 2. For each accordion: expand, scope the content, extract ──
        for cat in CATEGORIES:
            if cat == "Course Description":
                continue   # handled separately
            self._scrape_category(cat, name, url)

    def _scrape_course_description(self, subject: str, source_url: str):
        """The 'Course Description' button has a Drive href."""
        try:
            btn = self.driver.find_element(
                By.XPATH,
                "//*[normalize-space()='Course Description']"
                "/ancestor-or-self::*[self::a or self::button][1]"
            )
            href = btn.get_attribute("href") or ""
            # Check data-* attributes too
            for attr in ["href", "data-href", "data-url", "data-link"]:
                v = btn.get_attribute(attr) or ""
                if self._is_gdrive(v):
                    self._add_link(
                        v, source_url, subject,
                        category="Course Description",
                        item_name="Course Description",
                    )
                    return
            # If no direct link, try clicking & capturing
            if href:
                if self._is_gdrive(href):
                    self._add_link(
                        href, source_url, subject,
                        category="Course Description",
                        item_name="Course Description",
                    )
                    return
            # Last resort: click and capture new tab
            self._try_click_capture(
                btn, "Course Description", subject,
                "Course Description", source_url
            )
        except NoSuchElementException:
            log.debug(f"  [skip] No 'Course Description' on {subject}")

    def _scrape_category(self, category: str, subject: str, source_url: str):
        """
        Expand the accordion for `category`, then collect ONLY the links
        that appear inside that accordion's panel.
        """
        log.info(f"  ▶ Category: {category}")

        # 1. Find the accordion header
        header = self._find_accordion_header(category)
        if header is None:
            log.debug(f"    [skip] '{category}' not present")
            return

        # 2. Expand it (click)
        try:
            self._scroll_into_view(header)
            self._safe_click(header)
            time.sleep(0.9)
        except Exception as e:
            log.warning(f"    [warn] Could not click '{category}': {e}")

        # 3. Locate the panel that belongs to THIS header
        panel = self._find_panel_for_header(header, category)
        if panel is None:
            log.warning(f"    [warn] No panel found for '{category}'")
            return

        # 4. Collect every item inside that panel
        self._extract_links_from_panel(panel, subject, category, source_url)

        # 5. (optional) Collapse it back to keep DOM clean
        try:
            self._safe_click(header)
            time.sleep(0.3)
        except Exception:
            pass

    # ── Find the accordion header element ─────────────────────────────────────

    def _find_accordion_header(self, category: str):
        """
        Returns the clickable header element of the accordion for `category`,
        or None if not present.
        """
        xpaths = [
            # Standard: header text inside button
            f"//button[normalize-space()='{category}']",
            # Text inside any clickable wrapper
            f"//*[normalize-space()='{category}']"
            f"/ancestor::*[self::button or @role='button'][1]",
            # Aria-controls / accordion wrappers
            f"//*[normalize-space()='{category}']"
            f"/ancestor::*[contains(@class,'accordion') "
            f"or contains(@class,'collaps')][1]",
        ]
        for xp in xpaths:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                if el:
                    return el
            except NoSuchElementException:
                continue
        return None

    # ── Find the content panel belonging to a header ─────────────────────────

    def _find_panel_for_header(self, header, category: str):
        """
        Locate the expanded content panel beside / after the header element.
        We try multiple strategies because DOM may differ per implementation.
        """
        # Strategy A: aria-controls attribute points to panel id
        try:
            panel_id = header.get_attribute("aria-controls")
            if panel_id:
                el = self.driver.find_element(By.ID, panel_id)
                if el:
                    return el
        except Exception:
            pass

        # Strategy B: header has data-state="open" → next sibling is the panel
        for xp in [
            "./following-sibling::*[1]",
            "./parent::*/following-sibling::*[1]",
            "./ancestor::*[1]/following-sibling::*[1]",
            "./ancestor::*[2]/following-sibling::*[1]",
        ]:
            try:
                el = header.find_element(By.XPATH, xp)
                if el and el.is_displayed() and el.text.strip():
                    return el
            except Exception:
                continue

        # Strategy C: parent accordion container — look for content inside it
        try:
            container = header.find_element(
                By.XPATH,
                "./ancestor::*[contains(@class,'accordion') "
                "or contains(@class,'collaps') or contains(@class,'group')][1]"
            )
            # Inside container, find the panel that isn't the header
            panels = container.find_elements(
                By.XPATH,
                ".//*[contains(@class,'content') or contains(@class,'panel') "
                "or contains(@class,'body') or @role='region']"
            )
            for p in panels:
                if p.is_displayed() and p.text.strip():
                    return p
        except Exception:
            pass

        # Strategy D: text-based — anything between this header and the next
        try:
            next_header_xp = " or ".join([
                f"normalize-space()='{c}'" for c in CATEGORIES if c != category
            ])
            # Take the parent and grab elements until next header
            parent = header.find_element(By.XPATH, "./..")
            return parent
        except Exception:
            return None

    # ── Extract every GDrive link inside one panel ────────────────────────────

    def _extract_links_from_panel(
        self, panel, subject: str, category: str, source_url: str
    ):
        """Inside a panel, find <a>, data-*, and clickable items."""
        added_before = len(self.gdrive_links)

        # 1. <a href> tags
        try:
            anchors = panel.find_elements(By.CSS_SELECTOR, "a[href]")
            for a in anchors:
                href = a.get_attribute("href") or ""
                text = (a.text or "").strip()
                if self._is_gdrive(href):
                    self._add_link(href, source_url, subject, category, text)
        except Exception:
            pass

        # 2. Look for data-* attributes
        try:
            elems = panel.find_elements(By.XPATH, ".//*[@data-href or @data-url "
                                                  "or @data-link or @data-file]")
            for el in elems:
                text = (el.text or "").strip()
                for attr in ["data-href", "data-url", "data-link", "data-file"]:
                    val = el.get_attribute(attr) or ""
                    if self._is_gdrive(val):
                        self._add_link(val, source_url, subject, category, text)
                        break
        except Exception:
            pass

        # 3. <iframe src>
        try:
            iframes = panel.find_elements(By.CSS_SELECTOR, "iframe[src]")
            for ifr in iframes:
                src = ifr.get_attribute("src") or ""
                if self._is_gdrive(src):
                    self._add_link(src, source_url, subject, category, "[iframe]")
        except Exception:
            pass

        # 4. Clickable items without hrefs (capture by clicking)
        try:
            items = panel.find_elements(
                By.XPATH,
                ".//*[self::button or self::div[@role='button'] "
                "or contains(@class,'item') or contains(@class,'card') "
                "or contains(@class,'row')]"
            )
            for item in items:
                text = (item.text or "").strip()
                if not text:
                    continue
                # Skip if it already has child anchor we processed
                if item.find_elements(By.CSS_SELECTOR, "a[href]"):
                    continue
                self._try_click_capture(
                    item, text, subject, category, source_url
                )
        except Exception:
            pass

        # 5. Regex-scan the panel's innerHTML (catches inline-script links)
        try:
            inner_html = panel.get_attribute("innerHTML") or ""
            soup = BeautifulSoup(inner_html, "lxml")
            # YouTube links → record under YouTube Resources only
            if category == "YouTube Resources":
                for yt in YOUTUBE_PATTERN.findall(inner_html):
                    log.info(f"      ☆ YouTube: {yt[:60]}")
            for raw in re.findall(
                r"https?://(?:drive|docs)\.google\.com/[^\s\"'<>)]+",
                inner_html, re.I,
            ):
                clean = raw.rstrip("\"',;)>\\ \t\n")
                if self._is_gdrive(clean):
                    self._add_link(clean, source_url, subject, category, "")
        except Exception:
            pass

        added = len(self.gdrive_links) - added_before
        log.info(f"    ✓ {added} link(s) added under '{category}'")

    # ── Click + capture (for items without hrefs) ────────────────────────────

    def _try_click_capture(
        self, element, item_name: str, subject: str,
        category: str, source_url: str
    ):
        before_handles = self.driver.window_handles[:]
        before_url     = self.driver.current_url

        try:
            self._scroll_into_view(element)
            self._safe_click(element)
            time.sleep(1.5)

            # New tab opened
            new_handles = [h for h in self.driver.window_handles
                           if h not in before_handles]
            if new_handles:
                self.driver.switch_to.window(new_handles[0])
                time.sleep(1)
                new_url = self.driver.current_url
                if self._is_gdrive(new_url):
                    self._add_link(
                        new_url, source_url, subject, category, item_name
                    )
                self.driver.close()
                self.driver.switch_to.window(before_handles[0])
                return

            # Same-tab navigation
            current = self.driver.current_url
            if current != before_url and self._is_gdrive(current):
                self._add_link(
                    current, source_url, subject, category, item_name
                )
                self.driver.back()
                time.sleep(2)
                # Re-expand the category we just left
                hdr = self._find_accordion_header(category)
                if hdr:
                    self._safe_click(hdr)
                    time.sleep(0.5)
        except Exception:
            pass

    # ── GDrive helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _is_gdrive(url: str) -> bool:
        if not url:
            return False
        return bool(re.search(
            r"(?:drive|docs)\.google\.com|lh\d+\.googleusercontent\.com/d/",
            url, re.I
        ))

    @staticmethod
    def _extract_id(url: str) -> Optional[str]:
        params = parse_qs(urlparse(url).query)
        if "id" in params:
            return params["id"][0]
        for pat in COMPILED_PATTERNS:
            m = pat.search(url)
            if m and m.lastindex:
                return m.group(1)
        return None

    @staticmethod
    def _resource_type(url: str) -> str:
        for rtype, pat in RESOURCE_TYPES.items():
            if pat.search(url):
                return rtype
        return "file"

    def _add_link(self, url: str, source_url: str, subject: str,
                  category: str, item_name: str):
        file_id = self._extract_id(url)
        if not file_id:
            return
        # Allow the same file in different categories
        pair = (file_id, category)
        if pair in self.seen_pairs:
            return
        self.seen_pairs.add(pair)

        rtype = self._resource_type(url)
        link = GDriveLink(
            file_id       = file_id,
            original_url  = url,
            resource_type = rtype,
            source_page   = source_url,
            subject       = subject,
            category      = category,
            item_name     = item_name,
            is_folder     = (rtype == "folder"),
        )
        self.gdrive_links.append(link)
        log.info(f"      ★ [{category}] {file_id} | {item_name[:50]}")

    def close(self):
        if self.driver:
            self.driver.quit()
            log.info("Browser closed")

    def __enter__(self): return self
    def __exit__(self, *a): self.close()

# ═══════════════════════════════════════════════════════════════════════════════
#                          GOOGLE DRIVE DOWNLOADER
# ═══════════════════════════════════════════════════════════════════════════════

class GDriveDownloader:
    def __init__(self):
        self.out_dir = Path(CONFIG["OUTPUT_DIR"])
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.results : List[DownloadResult] = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
        })

    # ── Folder = subject/category (strict) ────────────────────────────────────

    def _dest_dir(self, subject: str, category: str) -> Path:
        clean_sub = re.sub(r'[<>:"/\\|?*]', "_", subject or "Uncategorized").strip()
        clean_cat = re.sub(r'[<>:"/\\|?*]', "_", category or "General").strip()
        d = self.out_dir / clean_sub / clean_cat
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _confirm_token(r: requests.Response) -> Optional[str]:
        for k, v in r.cookies.items():
            if k.startswith("download_warning"):
                return v
        for pat in [r'confirm=([0-9A-Za-z_\-]+)', r'"confirm"\s*:\s*"([^"]+)"']:
            m = re.search(pat, r.text)
            if m:
                return m.group(1)
        return None

    def _stream(self, r, path: Path, label: str) -> int:
        total = int(r.headers.get("Content-Length", 0))
        written = 0
        with open(path, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True,
            unit_divisor=1024, desc=f"↓ {label[:40]}", leave=False,
        ) as bar:
            for chunk in r.iter_content(CONFIG["CHUNK_SIZE"]):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
                    written += len(chunk)
        return written

    # ── gdown ────────────────────────────────────────────────────────────────

    def _gdown_file(self, link: GDriveLink) -> DownloadResult:
        result = DownloadResult(
            file_id=link.file_id, subject=link.subject, category=link.category
        )
        dest_dir = self._dest_dir(link.subject, link.category)
        try:
            path = gdown.download(
                f"https://drive.google.com/uc?id={link.file_id}",
                output=str(dest_dir) + "/",
                quiet=True, fuzzy=True, resume=True,
            )
            if path and os.path.exists(path):
                result.success    = True
                result.filepath   = path
                result.filename   = os.path.basename(path)
                result.size_bytes = os.path.getsize(path)
            else:
                result.error = "gdown returned no file"
        except Exception as e:
            result.error = str(e)
        return result

    # ── HTTP fallback ─────────────────────────────────────────────────────────

    def _http_file(self, link: GDriveLink) -> DownloadResult:
        result = DownloadResult(
            file_id=link.file_id, subject=link.subject, category=link.category
        )
        dest_dir = self._dest_dir(link.subject, link.category)
        url = f"https://drive.google.com/uc?export=download&id={link.file_id}"
        try:
            r = self.session.get(url, stream=True, timeout=30)
            token = self._confirm_token(r)
            if token:
                r = self.session.get(f"{url}&confirm={token}",
                                     stream=True, timeout=30)
            cd = r.headers.get("Content-Disposition", "")
            m  = re.findall(r'filename[^;=\n]*=(["\']?)([^\n"\']+)\1', cd)
            filename = m[0][1].strip() if m else f"{link.file_id}.bin"
            filepath = dest_dir / filename

            if CONFIG["SKIP_EXISTING"] and filepath.exists():
                result.skipped  = True
                result.filename = filename
                result.filepath = str(filepath)
                return result

            written = self._stream(r, filepath, filename)
            result.success    = True
            result.filename   = filename
            result.filepath   = str(filepath)
            result.size_bytes = written
        except Exception as e:
            result.error = str(e)
        return result

    # ── Folder download ───────────────────────────────────────────────────────

    def _gdown_folder(self, link: GDriveLink) -> List[DownloadResult]:
        results = []
        dest = self._dest_dir(link.subject, link.category) / link.file_id
        dest.mkdir(parents=True, exist_ok=True)
        try:
            gdown.download_folder(
                f"https://drive.google.com/drive/folders/{link.file_id}",
                output=str(dest), quiet=True, resume=True, remaining_ok=True,
            )
            for f in dest.rglob("*"):
                if f.is_file():
                    r = DownloadResult(
                        file_id=link.file_id, filename=f.name,
                        filepath=str(f), size_bytes=f.stat().st_size,
                        success=True, subject=link.subject,
                        category=link.category,
                    )
                    results.append(r)
        except Exception as e:
            results.append(DownloadResult(
                file_id=link.file_id, subject=link.subject,
                category=link.category, error=str(e)
            ))
        return results

    # ── Dispatcher ────────────────────────────────────────────────────────────

    def download_one(self, link: GDriveLink) -> List[DownloadResult]:
        if link.is_folder:
            return self._gdown_folder(link)

        dest_dir = self._dest_dir(link.subject, link.category)
        existing = list(dest_dir.glob(f"*{link.file_id}*"))
        if CONFIG["SKIP_EXISTING"] and existing:
            return [DownloadResult(
                file_id  = link.file_id,
                filename = existing[0].name,
                filepath = str(existing[0]),
                skipped  = True,
                subject  = link.subject,
                category = link.category,
            )]

        r = self._gdown_file(link)
        if not r.success and not r.skipped:
            r = self._http_file(link)
        return [r]

    def download_all(self, links: List[GDriveLink]) -> List[DownloadResult]:
        if not links:
            return []
        log.info(f"\nDownloading {len(links)} file(s) | workers={CONFIG['MAX_WORKERS']}")
        all_results = []
        with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as pool:
            futures = {pool.submit(self.download_one, l): l for l in links}
            with tqdm(total=len(links), desc="Overall", unit="file") as bar:
                for fut in as_completed(futures):
                    try:
                        all_results.extend(fut.result())
                    except Exception as e:
                        l = futures[fut]
                        all_results.append(DownloadResult(
                            file_id=l.file_id, subject=l.subject,
                            category=l.category, error=str(e)
                        ))
                    finally:
                        bar.update(1)
        self.results = all_results
        return all_results

    # ── Summary by subject+category ───────────────────────────────────────────

    def print_summary(self):
        ok   = [r for r in self.results if r.success]
        skip = [r for r in self.results if r.skipped]
        fail = [r for r in self.results if not r.success and not r.skipped]
        size_mb = sum(r.size_bytes for r in ok) / 1024 / 1024

        # Group: subject → category → count
        breakdown: Dict[str, Dict[str, int]] = {}
        for r in ok + skip:
            breakdown.setdefault(r.subject, {})
            breakdown[r.subject][r.category] = \
                breakdown[r.subject].get(r.category, 0) + 1

        print("\n" + "═" * 70)
        print("  JIIT SHELF — DOWNLOAD SUMMARY")
        print("═" * 70)
        print(f"  Total       : {len(self.results)}")
        print(f"  ✓ Done      : {len(ok)}")
        print(f"  ⊘ Skipped   : {len(skip)}")
        print(f"  ✗ Failed    : {len(fail)}")
        print(f"  Total size  : {size_mb:.2f} MB")
        print(f"  Saved to    : {self.out_dir.resolve()}")

        if breakdown:
            print("\n  Files by subject/category:")
            for subj in sorted(breakdown.keys()):
                print(f"\n    📁 {subj}")
                for cat in sorted(breakdown[subj].keys()):
                    print(f"        └── {cat:<25} {breakdown[subj][cat]}")

        if fail:
            print("\n  Failed:")
            for r in fail[:15]:
                print(f"    ✗ [{r.subject}/{r.category}] {r.file_id} — {r.error[:50]}")
        print("═" * 70 + "\n")

# ═══════════════════════════════════════════════════════════════════════════════
#                                MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def save_json(data: list, name: str):
    p = Path(CONFIG["OUTPUT_DIR"]) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"Saved → {p}")


def run():
    print("═" * 70)
    print("  JIIT SHELF — AUTO SCRAPER & DOWNLOADER")
    print("  (Files sorted by Subject → Category)")
    print("═" * 70)
    print(f"  URL      : {CONFIG['BASE_URL']}")
    print(f"  Branch   : {CONFIG['BRANCH']}")
    print(f"  Semester : {CONFIG['SEMESTER']}")
    print(f"  Output   : {CONFIG['OUTPUT_DIR']}/")
    print("═" * 70 + "\n")

    print("[1/3] Opening site & selecting Branch/Semester ...")
    with JIITShelfBot() as bot:
        bot.open_homepage()
        bot.select_branch_and_semester(CONFIG["BRANCH"], CONFIG["SEMESTER"])
        bot.click_view_subjects()

        subjects = bot.get_subjects()
        save_json(subjects, "subjects.json")
        print(f"      ✓ Found {len(subjects)} subjects\n")

        print("[2/3] Scraping each subject's categories ...")
        for i, subj in enumerate(subjects, 1):
            print(f"\n      [{i}/{len(subjects)}] {subj['name']}")
            bot.scrape_subject(subj)

        gdrive_links = bot.gdrive_links

    print(f"\n      ✓ Found {len(gdrive_links)} GDrive links\n")
    if not gdrive_links:
        print("  Nothing to download.")
        return

    save_json([l.to_dict() for l in gdrive_links], "gdrive_links.json")

    print("[3/3] Downloading & sorting into category folders ...")
    downloader = GDriveDownloader()
    results = downloader.download_all(gdrive_links)
    save_json([r.to_dict() for r in results], "download_results.json")
    downloader.print_summary()


if __name__ == "__main__":
    run()