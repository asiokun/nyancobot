#!/usr/bin/env python3
"""cw_job_hunter.py - CrowdWorks job hunter for nyancobot.

Searches CrowdWorks for AI/automation-related jobs matching our skills,
scores them, and sends notifications to Slack.

Skills to match:
  - AI自動化, LLM, ChatGPT, Claude
  - n8n, ワークフロー自動化
  - 書籍編集, ライティング
  - Web開発, スクレイピング
  - データ分析, マーケティング

Usage:
  python3 cw_job_hunter.py [--notify] [--dry-run]
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SKILLS = [
    {"keywords": ["AI", "人工知能", "ChatGPT", "Claude", "LLM", "生成AI"],
     "weight": 3.0, "label": "AI/LLM"},
    {"keywords": ["自動化", "n8n", "ワークフロー", "RPA", "効率化"],
     "weight": 2.5, "label": "自動化"},
    {"keywords": ["書籍", "出版", "編集", "ライティング", "原稿", "執筆"],
     "weight": 2.0, "label": "ライティング"},
    {"keywords": ["スクレイピング", "クローラー", "データ収集"],
     "weight": 2.0, "label": "スクレイピング"},
    {"keywords": ["Python", "TypeScript", "Node.js", "React"],
     "weight": 1.5, "label": "開発"},
    {"keywords": ["マーケティング", "SEO", "広告", "LP"],
     "weight": 1.0, "label": "マーケティング"},
]

CW_SEARCH_URLS = [
    "https://crowdworks.jp/public/jobs/search?category_id=249&order=new",  # AI/機械学習
    "https://crowdworks.jp/public/jobs/search?keyword=AI+%E8%87%AA%E5%8B%95%E5%8C%96&order=new",
    "https://crowdworks.jp/public/jobs/search?keyword=ChatGPT&order=new",
    "https://crowdworks.jp/public/jobs/search?keyword=n8n&order=new",
]

SEEN_JOBS_FILE = Path.home() / ".nyancobot" / "data" / "seen_jobs.json"
SLACK_CHANNEL = "C0AJ1T31JBA"  # shogun2-cmd


# ---------------------------------------------------------------------------
# Playwright-based scraper
# ---------------------------------------------------------------------------
def scrape_cw_jobs(url: str, max_jobs: int = 20) -> list[dict]:
    """Scrape CrowdWorks job listings using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[cw_job_hunter] playwright not installed. pip install playwright", file=sys.stderr)
        return []

    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)  # Wait for Vue.js render

            # Extract job cards
            job_elements = page.query_selector_all('[data-testid="job-card"], .job_listing, .job-card, article.job')

            if not job_elements:
                # Fallback: try broader selectors
                job_elements = page.query_selector_all('a[href*="/public/jobs/"]')

            for elem in job_elements[:max_jobs]:
                try:
                    # Try to extract structured data
                    title_el = elem.query_selector('h3, .job-title, [class*="title"]')
                    price_el = elem.query_selector('[class*="price"], [class*="budget"], [class*="reward"]')
                    link_el = elem if elem.tag_name == 'a' else elem.query_selector('a[href*="/public/jobs/"]')

                    title = title_el.text_content().strip() if title_el else elem.text_content().strip()[:100]
                    price = price_el.text_content().strip() if price_el else ""
                    href = link_el.get_attribute("href") if link_el else ""

                    if href and not href.startswith("http"):
                        href = f"https://crowdworks.jp{href}"

                    if title and len(title) > 5:
                        jobs.append({
                            "title": title,
                            "price": price,
                            "url": href,
                            "source": "crowdworks",
                        })
                except Exception:
                    continue

            # If selectors didn't work, try page content extraction
            if not jobs:
                content = page.content()
                # Extract from rendered HTML
                links = page.query_selector_all('a')
                for link in links:
                    href = link.get_attribute("href") or ""
                    text = link.text_content().strip()
                    if "/public/jobs/" in href and len(text) > 10 and "検索" not in text:
                        if not href.startswith("http"):
                            href = f"https://crowdworks.jp{href}"
                        jobs.append({
                            "title": text[:200],
                            "price": "",
                            "url": href,
                            "source": "crowdworks",
                        })

        except Exception as e:
            print(f"[cw_job_hunter] Scrape error: {e}", file=sys.stderr)
        finally:
            browser.close()

    # Deduplicate by URL
    seen_urls = set()
    unique_jobs = []
    for j in jobs:
        if j["url"] not in seen_urls:
            seen_urls.add(j["url"])
            unique_jobs.append(j)

    return unique_jobs


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_job(job: dict) -> float:
    """Score a job based on skill match."""
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    score = 0.0
    matched_skills = []

    for skill in SKILLS:
        for kw in skill["keywords"]:
            if kw.lower() in text:
                score += skill["weight"]
                matched_skills.append(skill["label"])
                break  # One match per skill group

    job["match_score"] = round(score, 1)
    job["matched_skills"] = list(set(matched_skills))
    return score


# ---------------------------------------------------------------------------
# Seen jobs tracking
# ---------------------------------------------------------------------------
def load_seen_jobs() -> set:
    if SEEN_JOBS_FILE.exists():
        try:
            data = json.loads(SEEN_JOBS_FILE.read_text(encoding="utf-8"))
            return set(data.get("urls", []))
        except (json.JSONDecodeError, KeyError):
            pass
    return set()


def save_seen_jobs(seen: set):
    SEEN_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Keep only last 1000
    urls = list(seen)[-1000:]
    SEEN_JOBS_FILE.write_text(
        json.dumps({"urls": urls, "updated": datetime.now().isoformat()},
                    ensure_ascii=False),
        encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------
def send_slack(message: str):
    """Send via gunrei2 bot."""
    try:
        token = subprocess.run(
            ["security", "find-generic-password", "-s", "gunrei2-bot-token", "-a", "shogun", "-w"],
            capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        print("[cw_job_hunter] Failed to get Slack token", file=sys.stderr)
        return

    import urllib.request
    import urllib.error

    data = json.dumps({"channel": SLACK_CHANNEL, "text": message}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[cw_job_hunter] Slack send error: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    notify = "--notify" in sys.argv
    dry_run = "--dry-run" in sys.argv

    print(f"[cw_job_hunter] Start: {datetime.now().isoformat()}")
    print(f"[cw_job_hunter] Notify: {notify}, Dry-run: {dry_run}")

    seen = load_seen_jobs()
    all_jobs = []

    for url in CW_SEARCH_URLS:
        print(f"[cw_job_hunter] Scraping: {url[:80]}...")
        jobs = scrape_cw_jobs(url)
        print(f"[cw_job_hunter]   Found: {len(jobs)} jobs")
        all_jobs.extend(jobs)
        time.sleep(2)  # Polite delay

    # Deduplicate
    seen_urls = set()
    unique_jobs = []
    for j in all_jobs:
        if j["url"] not in seen_urls:
            seen_urls.add(j["url"])
            unique_jobs.append(j)

    # Score and filter
    for job in unique_jobs:
        score_job(job)

    # Filter: score > 0 and not seen before
    new_jobs = [j for j in unique_jobs if j["match_score"] > 0 and j["url"] not in seen]
    new_jobs.sort(key=lambda x: x["match_score"], reverse=True)

    print(f"\n[cw_job_hunter] Total unique: {len(unique_jobs)}")
    print(f"[cw_job_hunter] Matching (score>0): {sum(1 for j in unique_jobs if j['match_score'] > 0)}")
    print(f"[cw_job_hunter] New (unseen): {len(new_jobs)}")

    if new_jobs:
        # Show top results
        for j in new_jobs[:10]:
            print(f"  [{j['match_score']}] {j['matched_skills']} {j['title'][:60]}")
            if j["url"]:
                print(f"       {j['url']}")

        # Slack notification
        if notify and not dry_run:
            msg_lines = [f"🔍 *CW新着案件* ({len(new_jobs)}件マッチ)\n"]
            for j in new_jobs[:5]:
                skills = ", ".join(j["matched_skills"])
                msg_lines.append(f"*[{j['match_score']}点]* {j['title'][:80]}")
                msg_lines.append(f"  スキル: {skills}")
                if j["price"]:
                    msg_lines.append(f"  報酬: {j['price']}")
                if j["url"]:
                    msg_lines.append(f"  {j['url']}")
                msg_lines.append("")

            if len(new_jobs) > 5:
                msg_lines.append(f"他{len(new_jobs) - 5}件あり")

            send_slack("\n".join(msg_lines))

        # Update seen
        if not dry_run:
            for j in new_jobs:
                seen.add(j["url"])
            save_seen_jobs(seen)

        # Store in memory
        if not dry_run:
            sys.path.insert(0, str(Path(__file__).parent))
            from memory_search_server import execute_memory_store
            for j in new_jobs[:10]:
                execute_memory_store(
                    text=f"CW案件: {j['title']} | スコア:{j['match_score']} | {j['url']}",
                    category="knowledge",
                    metadata={"source": "crowdworks", "score": str(j["match_score"])},
                )
    else:
        print("[cw_job_hunter] No new matching jobs found.")

    print(f"\n[cw_job_hunter] Done: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
