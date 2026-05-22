import time
import random
import urllib.parse
from typing import Generator

from playwright.sync_api import Page, sync_playwright, TimeoutError as PwTimeout
from rich.console import Console

console = Console()

LINKEDIN_BASE = "https://www.linkedin.com"

EXPERIENCE_MAP = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid_senior": "4",
    "director": "5",
}

DATE_POSTED_MAP = {
    "day": "r86400",
    "week": "r604800",
    "month": "r2592000",
    "any": "",
}


def _build_search_url(keyword: str, location: str, cfg: dict) -> str:
    params = {
        "keywords": keyword,
        "location": location,
        "f_TPR": DATE_POSTED_MAP.get(cfg.get("date_posted", "week"), "r604800"),
    }
    if cfg.get("easy_apply_only"):
        params["f_LF"] = "f_AL"
    if cfg.get("remote"):
        params["f_WT"] = "2"
    levels = cfg.get("experience_levels", [])
    if levels:
        params["f_E"] = ",".join(EXPERIENCE_MAP[lvl] for lvl in levels if lvl in EXPERIENCE_MAP)
    return f"{LINKEDIN_BASE}/jobs/search/?{urllib.parse.urlencode(params)}"


def _random_delay(min_s=1.5, max_s=4.0):
    time.sleep(random.uniform(min_s, max_s))


def login(page: Page, email: str, password: str):
    page.goto(f"{LINKEDIN_BASE}/login")
    page.fill("#username", email)
    page.fill("#password", password)
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=15000)
    if "checkpoint" in page.url or "login" in page.url:
        console.print("[yellow]LinkedIn demande une vérification manuelle. Connectez-vous dans la fenêtre du navigateur.[/yellow]")
        input("Appuyez sur Entrée une fois connecté…")


def scrape_jobs(page: Page, search_cfg: dict) -> Generator[dict, None, None]:
    keywords = search_cfg.get("keywords", [])
    location = search_cfg.get("location", "France")

    for keyword in keywords:
        url = _build_search_url(keyword, location, search_cfg)
        console.print(f"[cyan]Recherche:[/cyan] {keyword} @ {location}")
        page.goto(url)
        _random_delay()

        # scroll to load all results (LinkedIn lazy-loads)
        for _ in range(5):
            page.keyboard.press("End")
            _random_delay(0.8, 1.5)

        cards = page.query_selector_all(".job-search-card, li.jobs-search-results__list-item")
        console.print(f"  → {len(cards)} offres trouvées")

        for card in cards:
            try:
                job = _parse_card(card)
                if job:
                    yield job
            except Exception as exc:
                console.print(f"  [red]Erreur parsing carte:[/red] {exc}")

        _random_delay(2.0, 5.0)


def _parse_card(card) -> dict | None:
    try:
        link_el = card.query_selector("a.job-search-card__title-link, a.job-card-list__title")
        if not link_el:
            return None
        url = link_el.get_attribute("href") or ""
        # extract numeric job id from URL
        job_id = _extract_job_id(url)
        if not job_id:
            return None

        title = (link_el.inner_text() or "").strip()
        company_el = card.query_selector(".job-search-card__company-name, .job-card-container__company-name")
        company = (company_el.inner_text() if company_el else "").strip()
        location_el = card.query_selector(".job-search-card__location, .job-card-container__metadata-item")
        location = (location_el.inner_text() if location_el else "").strip()
        easy_el = card.query_selector(".job-search-card__easy-apply-label, .job-card-container__apply-method")
        easy_apply = 1 if easy_el else 0

        return {
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "url": url.split("?")[0] if url else "",
            "easy_apply": easy_apply,
            "description": "",
        }
    except Exception:
        return None


def _extract_job_id(url: str) -> str | None:
    # LinkedIn job URLs contain /jobs/view/<id>/ or jobId=<id>
    import re
    m = re.search(r"/jobs/view/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"jobId=(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"-(\d{7,})/?", url)
    if m:
        return m.group(1)
    return None


def fetch_description(page: Page, job_url: str) -> str:
    try:
        page.goto(job_url)
        _random_delay()
        el = page.query_selector(".jobs-description__content, .description__text")
        return (el.inner_text() if el else "").strip()
    except PwTimeout:
        return ""


def apply_easy_apply(page: Page, job: dict) -> bool:
    """
    Attempts LinkedIn Easy Apply. Returns True on success.
    Only works for straightforward one-step Easy Apply flows.
    """
    try:
        page.goto(job["url"])
        _random_delay()

        btn = page.query_selector("button.jobs-apply-button")
        if not btn:
            return False
        btn.click()
        _random_delay()

        # Handle multi-step modal — click Next/Submit until done
        for _ in range(10):
            submit = page.query_selector("button[aria-label='Submit application']")
            if submit:
                submit.click()
                _random_delay()
                return True
            next_btn = page.query_selector("button[aria-label='Continue to next step']")
            if next_btn:
                next_btn.click()
                _random_delay()
            else:
                break
        return False
    except Exception as exc:
        console.print(f"  [red]Easy Apply échoué:[/red] {exc}")
        return False


def create_browser_session(headless: bool = False):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless, args=["--no-sandbox"])
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    return pw, browser, page
