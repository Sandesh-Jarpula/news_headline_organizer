"""Streamlit browser interface for News Headline Organizer."""

import json
import os
import html
import hashlib
import hmac
import re
import secrets
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

from news_headline_organizer import CATEGORIES, SAMPLE_FILE, clean

APP_DIR = Path(__file__).resolve().parent
USERS_FILE = APP_DIR / "users.json"
PASSWORD_ROUNDS = 310_000


def read_users():
    try:
        users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        return users if isinstance(users, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2) + "\n", encoding="utf-8")


def password_digest(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ROUNDS).hex()


def reader_data_file(username):
    folder = APP_DIR / "reader_data" / username
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "headlines.json"


def load_reader_headlines(username):
    path = reader_data_file(username)
    if not path.exists():
        try:
            sample = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
            records = sample if isinstance(sample, list) else []
        except (OSError, json.JSONDecodeError):
            records = []
        save_reader_headlines(username, records)
        return records
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in data if isinstance(item, dict) and item.get("title")] if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_reader_headlines(username, records):
    reader_data_file(username).write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


st.set_page_config(page_title="News Headline Organizer", page_icon="📰", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700;800&display=swap');
:root { --ink:#33201e; --muted:#786c63; --paper:#f7f0e4; --gold:#e6bd68; --line:#e7d9c4; }
.stApp { background:radial-gradient(ellipse at 90% 0%,#f3e4c8 0,transparent 32%),var(--paper); color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stMainBlockContainer"] { padding-top:2.2rem; max-width:1450px; }
html, body, [class*="css"] { font-family:'DM Sans', sans-serif; }
h1,h2,h3 { color:var(--ink); }
.masthead { background:linear-gradient(115deg,#4b2025,#762e36 56%,#9b4b3a); color:#fff8eb; border:1px solid rgba(230,189,104,.45); border-radius:8px; padding:30px 34px 26px; margin-bottom:22px; position:relative; overflow:hidden; box-shadow:0 9px 28px rgba(76,32,37,.12); }
.masthead:after { content:'✦'; position:absolute; right:50px; top:-49px; font:240px 'Playfair Display',serif; color:rgba(230,189,104,.12); }
.mast-kicker { color:var(--gold); font:500 11px 'DM Mono',monospace; letter-spacing:.18em; text-transform:uppercase; }
.mast-title { font:700 clamp(36px,5vw,60px) 'Playfair Display',serif; line-height:1.05; margin:14px 0 10px; color:#fff8eb; }
.mast-sub { font-size:15px; color:#f0ddd1; margin:0; max-width:650px; }
.mast-date { position:absolute; right:35px; bottom:27px; color:#f0ddd1; font:11px 'DM Mono',monospace; letter-spacing:.08em; }
.section-label { color:#748078; font:500 11px 'DM Mono',monospace; letter-spacing:.14em; text-transform:uppercase; margin:12px 0 10px; }
.story-card { background:linear-gradient(145deg,#fffdf8,#fbf4e9); border:1px solid var(--line); border-top:3px solid #a44e42; border-radius:8px; padding:20px 21px 18px; margin:0 0 13px; min-height:180px; box-shadow:0 4px 14px rgba(76,32,37,.045); transition:transform .15s ease, box-shadow .15s ease; }
.story-card:hover { transform:translateY(-2px); box-shadow:0 10px 24px rgba(76,32,37,.12); }
.story-top { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px; }
.tag { display:inline-block; border-radius:3px; padding:5px 10px; background:#efe4ca; color:#735b28; font:500 10px 'DM Mono',monospace; letter-spacing:.06em; text-transform:uppercase; }
.tag.business { background:#efe7c9; color:#716022; } .tag.technology { background:#dce9e8; color:#315d5e; }
.tag.science { background:#e9e0f3; color:#66458a; } .tag.health { background:#f6e2dc; color:#9b4c38; }
.tag.sports { background:#f7ead3; color:#986318; } .tag.entertainment { background:#f2dfe9; color:#8c3f69; }
.story-date { color:#8b968e; font:10px 'DM Mono',monospace; }
.story-title { color:#172821; font:700 22px/1.22 'Playfair Display',serif; margin:0 0 10px; }
.story-desc { color:#69766e; font-size:13px; line-height:1.55; margin:0 0 16px; }
.story-source { color:#45544b; font:500 11px 'DM Mono',monospace; letter-spacing:.04em; }
[data-testid="stMetric"] { background:#fffaf1; border:1px solid var(--line); border-radius:8px; padding:14px 17px; }
[data-testid="stMetricLabel"] { color:#78847c; font:500 10px 'DM Mono',monospace; letter-spacing:.12em; text-transform:uppercase; }
[data-testid="stMetricValue"] { color:#762e36; font:700 29px 'Playfair Display',serif; }
[data-testid="stSidebar"] { background:#efe6d8; border-right:1px solid #e0d1bc; }
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] { background:#762e36; color:#fff8eb; border:0; border-radius:5px; }
div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button[kind="primary"]:hover { background:#542329; color:#fff; border:0; }
.auth-panel { background:linear-gradient(150deg,#fffaf1,#f3e7d5); border:1px solid #ddc9a8; border-radius:9px; padding:30px 32px; box-shadow:0 18px 48px rgba(79,39,40,.12); }
.auth-kicker { color:#956e32; font:500 11px 'DM Mono',monospace; letter-spacing:.15em; text-transform:uppercase; }
.auth-title { color:#51252a; font:700 36px/1.08 'Playfair Display',serif; margin:12px 0; }
.auth-copy { color:#74655a; font-size:14px; line-height:1.6; }
.welcome-note { border-left:3px solid #c29646; background:#f4ead8; color:#634c32; padding:12px 14px; border-radius:0 5px 5px 0; font-size:13px; margin:16px 0; }
div[data-baseweb="tab-list"] { gap:8px; }
button[data-baseweb="tab"] { border-radius:8px 8px 0 0; }
@media(max-width:700px) { .masthead { padding:24px; } .mast-date { position:static; margin-top:18px; } .story-card { min-height:0; } }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<header class="masthead">
  <div class="mast-kicker">The town gazette · established 2026</div>
  <div class="mast-title">The Daily Chronicle</div>
  <p class="mast-sub">A considered reading room for the headlines shaping your day. Gather the stories, follow the topics, keep the record.</p>
  <div class="mast-date">VOL. I &nbsp;·&nbsp; NEWS DESK</div>
</header>
""", unsafe_allow_html=True)

users = read_users()
if "signed_in_user" not in st.session_state:
    st.session_state.signed_in_user = None

if not st.session_state.signed_in_user:
    auth_left, auth_right = st.columns([1.05, 0.95], gap="large")
    with auth_left:
        st.markdown("""
        <section class="auth-panel">
          <div class="auth-kicker">A private reading room</div>
          <div class="auth-title">Your front page<br>starts here.</div>
          <p class="auth-copy">Create a reader account to keep your headlines, notes, and favorite topics together. Your reading list is saved locally on this computer.</p>
          <div class="welcome-note">A new reader? Create your account first. You can sign in here the next time you visit.</div>
        </section>
        """, unsafe_allow_html=True)
    with auth_right:
        if not users:
            st.subheader("Create the first account")
            st.caption("Set up your reader profile to open the newsroom.")
            with st.form("first_registration"):
                new_name = st.text_input("Reader name", placeholder="e.g. alex.reader")
                new_password = st.text_input("Password", type="password", max_chars=128, help="Use at least 8 characters.")
                confirm_password = st.text_input("Confirm password", type="password", max_chars=128)
                register_first = st.form_submit_button("Create reader account", type="primary", use_container_width=True)
            if register_first:
                normalized = new_name.strip().casefold()
                if not re.fullmatch(r"[a-z0-9_.-]{3,24}", normalized):
                    st.error("Choose a reader name with 3–24 letters, numbers, dots, dashes, or underscores.")
                elif len(new_password) < 8:
                    st.error("Choose a password with at least 8 characters.")
                elif new_password != confirm_password:
                    st.error("The passwords do not match.")
                else:
                    salt = secrets.token_bytes(16)
                    users[normalized] = {"salt": salt.hex(), "password_hash": password_digest(new_password, salt)}
                    write_users(users)
                    st.session_state.signed_in_user = normalized
                    st.rerun()
        else:
            sign_in, register = st.tabs(["Sign in", "Create account"])
            with sign_in:
                st.subheader("Welcome back")
                with st.form("login_form"):
                    login_name = st.text_input("Reader name")
                    login_password = st.text_input("Password", type="password", max_chars=128)
                    login_submit = st.form_submit_button("Enter the newsroom", type="primary", use_container_width=True)
                if login_submit:
                    normalized = login_name.strip().casefold()
                    saved = users.get(normalized)
                    if saved:
                        salt = bytes.fromhex(saved.get("salt", ""))
                        supplied = password_digest(login_password, salt)
                        if hmac.compare_digest(supplied, saved.get("password_hash", "")):
                            st.session_state.signed_in_user = normalized
                            st.rerun()
                    st.error("Reader name or password was not recognized.")
            with register:
                st.subheader("Join the newsroom")
                with st.form("registration_form"):
                    new_name = st.text_input("Choose a reader name", placeholder="3–24 characters")
                    new_password = st.text_input("Create a password", type="password", max_chars=128, help="Use at least 8 characters.")
                    confirm_password = st.text_input("Confirm password", type="password", max_chars=128)
                    register_submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
                if register_submit:
                    normalized = new_name.strip().casefold()
                    if not re.fullmatch(r"[a-z0-9_.-]{3,24}", normalized):
                        st.error("Choose a reader name with 3–24 letters, numbers, dots, dashes, or underscores.")
                    elif normalized in users:
                        st.error("That reader name is already registered. Please sign in instead.")
                    elif len(new_password) < 8:
                        st.error("Choose a password with at least 8 characters.")
                    elif new_password != confirm_password:
                        st.error("The passwords do not match.")
                    else:
                        salt = secrets.token_bytes(16)
                        users[normalized] = {"salt": salt.hex(), "password_hash": password_digest(new_password, salt)}
                        write_users(users)
                        st.session_state.signed_in_user = normalized
                        st.rerun()
    st.stop()

reader_col, logout_col = st.columns([6, 1])
reader_col.markdown(f"**Reader:** `{html.escape(st.session_state.signed_in_user)}`")
if logout_col.button("Sign out"):
    st.session_state.signed_in_user = None
    st.rerun()

if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

reader_name = st.session_state.signed_in_user
records = load_reader_headlines(reader_name)

with st.sidebar:
    st.header("Filters")
    selected_categories = st.multiselect("Categories", options=list(CATEGORIES), default=list(CATEGORIES))
    search_term = st.text_input("Search headlines", placeholder="Try: science, city, clean energy")
    st.divider()
    st.caption(f"{len(records)} headline(s) in {reader_name}'s edition")

filtered = [
    item for item in records
    if item.get("category", "general").lower() in selected_categories
    and search_term.casefold() in " ".join(str(v) for v in item.values()).casefold()
]
counts = Counter(item.get("category", "general").title() for item in filtered)
sources = {item.get("source", "") for item in filtered if item.get("source")}

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Headlines", len(filtered))
metric2.metric("Categories", len(counts))
metric3.metric("News sources", len(sources))

left, right = st.columns([1.6, 1])
with left:
    st.markdown('<div class="section-label">Your reading list</div>', unsafe_allow_html=True)
    if filtered:
        for index in range(0, len(filtered), 2):
            card_cols = st.columns(2, gap="medium")
            for card_col, item in zip(card_cols, filtered[index:index + 2]):
                category_name = clean(item.get("category", "general"), 30).lower() or "general"
                category_class = category_name if category_name in CATEGORIES else "general"
                title = html.escape(clean(item.get("title"), 220))
                source = html.escape(clean(item.get("source"), 100) or "Unknown source")
                published = html.escape(clean(item.get("published_at"), 30) or "DATE UNKNOWN")
                description = html.escape(clean(item.get("description"), 260))
                card_col.markdown(f"""
                <article class="story-card">
                  <div class="story-top"><span class="tag {category_class}">{html.escape(category_name)}</span><span class="story-date">{published}</span></div>
                  <h3 class="story-title">{title}</h3>
                  <p class="story-desc">{description or 'A headline saved to your newsroom reading list.'}</p>
                  <div class="story-source">◦ &nbsp;{source}</div>
                </article>
                """, unsafe_allow_html=True)
                if item.get("url", "").startswith(("https://", "http://")):
                    card_col.link_button("Read the story ↗", item["url"], use_container_width=True)
    else:
        st.info("No stories in this edition match those filters. Try another topic or add a headline below.")

with right:
    st.markdown('<div class="section-label">What you are following</div>', unsafe_allow_html=True)
    if counts:
        chart_data = pd.DataFrame(
            [{"Category": category, "Headlines": count} for category, count in sorted(counts.items())]
        ).set_index("Category")
        st.bar_chart(chart_data, color="#2f6f9f")
    else:
        st.info("Category chart appears when there are matching headlines.")

st.divider()
add_tab, fetch_tab, export_tab = st.tabs(["Add a headline", "Fetch live headlines", "Export"])

with add_tab:
    with st.form("add_headline_form", clear_on_submit=True):
        title = st.text_input("Headline title *", max_chars=500)
        category = st.selectbox("Category", options=list(CATEGORIES), index=2)
        source = st.text_input("News source", max_chars=100)
        url = st.text_input("Article URL (optional)", max_chars=1000)
        description = st.text_area("Short description (optional)", max_chars=500)
        submitted = st.form_submit_button("Save headline", type="primary")
    if submitted:
        if not clean(title):
            st.error("Please enter a headline title.")
        else:
            from datetime import datetime, timezone

            records.append({
                "title": clean(title),
                "category": category,
                "source": clean(source, 100) or "Added manually",
                "published_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                "url": clean(url, 1000),
                "description": clean(description, 500),
            })
            save_reader_headlines(reader_name, records)
            st.session_state["notice"] = "Headline saved."
            st.rerun()

with fetch_tab:
    st.write("Fetch up to 20 current headlines with NewsAPI. The API key is read from your `NEWS_API_KEY` environment variable.")
    api_key = os.environ.get("NEWS_API_KEY", "").strip()
    if not api_key:
        st.warning("Set NEWS_API_KEY before starting Streamlit to enable live fetching. The sample data works without it.")
    country, api_category = st.columns(2)
    country_code = country.text_input("Country code", value="us", max_chars=2).strip().lower()
    fetch_category = api_category.selectbox("API category", options=list(CATEGORIES), index=2)
    if st.button("Fetch headlines", disabled=not bool(api_key), type="primary"):
        if len(country_code) != 2 or not country_code.isalpha():
            st.error("Enter a valid two-letter country code, such as us, in, or gb.")
        else:
            params = urlencode({"country": country_code, "category": fetch_category, "pageSize": 20, "apiKey": api_key})
            request = Request(
                f"https://newsapi.org/v2/top-headlines?{params}",
                headers={"User-Agent": "NewsHeadlineOrganizer/1.0"},
            )
            try:
                with urlopen(request, timeout=15) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if payload.get("status") != "ok":
                    st.error(f"NewsAPI error: {clean(payload.get('message'), 200)}")
                else:
                    existing = {item.get("url") for item in records if item.get("url")}
                    added = 0
                    for article in payload.get("articles", []):
                        article_url = clean(article.get("url"), 1000)
                        article_title = clean(article.get("title"))
                        if not article_url or not article_title or article_url in existing:
                            continue
                        records.append({
                            "title": article_title,
                            "category": fetch_category,
                            "source": clean((article.get("source") or {}).get("name"), 100),
                            "published_at": clean(article.get("publishedAt"), 40),
                            "url": article_url,
                            "description": clean(article.get("description"), 500),
                        })
                        existing.add(article_url)
                        added += 1
                    save_reader_headlines(reader_name, records)
                    st.session_state["notice"] = f"Added {added} new headline(s)."
                    st.rerun()
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                st.error(f"Could not fetch headlines: {exc}")

with export_tab:
    csv_data = pd.DataFrame(records, columns=["title", "category", "source", "published_at", "url", "description"]).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download all headlines as CSV",
        data=csv_data,
        file_name="headlines_export.csv",
        mime="text/csv",
        disabled=not bool(records),
    )
    st.caption(f"Your edition is saved locally in `reader_data/{reader_name}/headlines.json`.")
