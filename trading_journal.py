"""
╔══════════════════════════════════════════════════════════╗
║        MNQ TRADING JOURNAL — PROFESSIONAL EDITION       ║
║   Discipline · Analytics · Psychology · Consistency     ║
╚══════════════════════════════════════════════════════════╝
Run: streamlit run trading_journal.py
Requires: streamlit pandas plotly pillow
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
import sqlite3
from datetime import datetime, date, timedelta
import random
import base64
from io import BytesIO
import calendar as cal_module
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURATION & CONSTANTS
# ─────────────────────────────────────────────
DB_FILE = "trading_journal.db"
SETTINGS_FILE = "journal_settings.json"

DISCIPLINE_QUOTES = [
    ("Discipline is the edge that no one can copy.", "— Anonymous Trader"),
    ("Consistency beats intensity. Every. Single. Time.", "— Mark Douglas"),
    ("Protect capital first. Profits will follow.", "— Paul Tudor Jones"),
    ("The goal is not to be right. The goal is to make money.", "— Marty Schwartz"),
    ("Trade what you see, not what you think.", "— Anonymous"),
    ("Every loss is tuition. Pay attention in class.", "— Anonymous Trader"),
    ("The market rewards patience and punishes urgency.", "— Steve Burns"),
    ("Your job is not to predict. Your job is to react.", "— Linda Raschke"),
    ("A disciplined trader is an unstoppable trader.", "— Anonymous"),
    ("One good trade. Then another. That's consistency.", "— Anonymous"),
    ("Risk management is the only edge you truly own.", "— Anonymous"),
    ("Amateurs want to be right. Professionals want to make money.", "— Anonymous"),
    ("The best trade you'll ever make is passing on a bad setup.", "— Anonymous"),
    ("Emotional trading is just gambling with extra steps.", "— Anonymous"),
    ("Your mindset IS your trading system.", "— Mark Douglas"),
]

SETUP_TYPES = [
    "ICT MMXM", "ICT OTE", "ICT Liquidity Sweep", "ICT Order Block",
    "ICT FVG Fill", "ICT Breaker Block", "SMC BOS", "SMC CHOCH",
    "Supply/Demand", "VWAP Bounce", "Opening Range", "Other"
]

TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h"]

COLORS = {
    "bg_dark":    "#0a0e1a",
    "bg_card":    "#0f1629",
    "bg_sidebar": "#080c18",
    "accent":     "#00d4ff",
    "accent2":    "#7c3aed",
    "green":      "#00e676",
    "red":        "#ff1744",
    "yellow":     "#ffd600",
    "text":       "#e2e8f0",
    "text_dim":   "#64748b",
    "border":     "#1e2a45",
}

# ─────────────────────────────────────────────
# DATABASE LAYER
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            symbol TEXT DEFAULT 'MNQ',
            direction TEXT,
            entry_price REAL,
            exit_price  REAL,
            contracts   INTEGER DEFAULT 1,
            pnl         REAL,
            timeframe   TEXT,
            setup_type  TEXT,
            notes       TEXT,
            screenshot  TEXT,
            -- ICT Rules
            liquidity_hunt   INTEGER DEFAULT 0,
            engulf_confirm   INTEGER DEFAULT 0,
            killzone         INTEGER DEFAULT 0,
            trend_align      INTEGER DEFAULT 0,
            risk_defined     INTEGER DEFAULT 0,
            -- Discipline Rules
            no_revenge       INTEGER DEFAULT 0,
            followed_sl      INTEGER DEFAULT 0,
            followed_plan    INTEGER DEFAULT 0,
            no_emotion       INTEGER DEFAULT 0,
            -- Computed
            rule_score       REAL DEFAULT 0,
            passed           INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_date   TEXT UNIQUE NOT NULL,
            followed_rules  INTEGER DEFAULT 0,
            no_revenge      INTEGER DEFAULT 0,
            risk_respected  INTEGER DEFAULT 0,
            no_overtrade    INTEGER DEFAULT 0,
            notes           TEXT,
            discipline_score REAL DEFAULT 0,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date  TEXT NOT NULL,
            event_type  TEXT,
            amount      REAL,
            notes       TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# DATA ACCESS FUNCTIONS
# ─────────────────────────────────────────────
def load_trades() -> pd.DataFrame:
    conn = get_db()
    df = pd.read_sql("SELECT * FROM trades ORDER BY trade_date DESC, created_at DESC", conn)
    conn.close()
    if df.empty:
        return df
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df

def save_trade(data: dict) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO trades (
            trade_date, symbol, direction, entry_price, exit_price,
            contracts, pnl, timeframe, setup_type, notes, screenshot,
            liquidity_hunt, engulf_confirm, killzone, trend_align, risk_defined,
            no_revenge, followed_sl, followed_plan, no_emotion,
            rule_score, passed
        ) VALUES (
            :trade_date,:symbol,:direction,:entry_price,:exit_price,
            :contracts,:pnl,:timeframe,:setup_type,:notes,:screenshot,
            :liquidity_hunt,:engulf_confirm,:killzone,:trend_align,:risk_defined,
            :no_revenge,:followed_sl,:followed_plan,:no_emotion,
            :rule_score,:passed
        )
    """, data)
    conn.commit()
    lid = c.lastrowid
    conn.close()
    return lid

def delete_trade(trade_id: int):
    conn = get_db()
    conn.execute("DELETE FROM trades WHERE id=?", (trade_id,))
    conn.commit()
    conn.close()

def load_daily_checklist() -> pd.DataFrame:
    conn = get_db()
    df = pd.read_sql("SELECT * FROM daily_checklist ORDER BY check_date DESC", conn)
    conn.close()
    if not df.empty:
        df["check_date"] = pd.to_datetime(df["check_date"])
    return df

def save_daily_checklist(data: dict):
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO daily_checklist
        (check_date, followed_rules, no_revenge, risk_respected, no_overtrade, notes, discipline_score)
        VALUES (:check_date,:followed_rules,:no_revenge,:risk_respected,:no_overtrade,:notes,:discipline_score)
    """, data)
    conn.commit()
    conn.close()

def load_account() -> pd.DataFrame:
    conn = get_db()
    df = pd.read_sql("SELECT * FROM account ORDER BY event_date ASC", conn)
    conn.close()
    return df

def save_account_event(data: dict):
    conn = get_db()
    conn.execute("""
        INSERT INTO account (event_date, event_type, amount, notes)
        VALUES (:event_date,:event_type,:amount,:notes)
    """, data)
    conn.commit()
    conn.close()

def load_settings() -> dict:
    defaults = {"starting_capital": 50000.0, "account_name": "MNQ Prop Account", "target_daily_pnl": 500.0, "max_daily_loss": -200.0, "theme": "dark"}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
        defaults.update(s)
    return defaults

def save_settings(s: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)

# ─────────────────────────────────────────────
# COMPUTATION HELPERS
# ─────────────────────────────────────────────
def calc_rule_score(d: dict) -> tuple[float, bool]:
    ict_keys  = ["liquidity_hunt","engulf_confirm","killzone","trend_align","risk_defined"]
    disc_keys = ["no_revenge","followed_sl","followed_plan","no_emotion"]
    total = len(ict_keys) + len(disc_keys)
    score_raw = sum(d.get(k, 0) for k in ict_keys + disc_keys)
    pct = round((score_raw / total) * 100, 1)
    passed = pct >= 70.0
    return pct, passed

def calc_discipline_score(d: dict) -> float:
    keys = ["followed_rules","no_revenge","risk_respected","no_overtrade"]
    total = len(keys)
    score = sum(d.get(k, 0) for k in keys)
    return round((score / total) * 100, 1)

def calc_pnl(direction, entry, exit_p, contracts=1):
    tick_size   = 0.25
    tick_value  = 0.50
    if direction == "Buy":
        ticks = (exit_p - entry) / tick_size
    else:
        ticks = (entry - exit_p) / tick_size
    return round(ticks * tick_value * contracts, 2)

def get_equity_curve(trades_df: pd.DataFrame, starting_capital: float, account_df: pd.DataFrame) -> pd.DataFrame:
    events = []
    if not account_df.empty:
        for _, row in account_df.iterrows():
            events.append({"date": pd.to_datetime(row["event_date"]), "amount": row["amount"]})
    if not trades_df.empty:
        for _, row in trades_df.iterrows():
            events.append({"date": row["trade_date"], "amount": row["pnl"]})
    if not events:
        return pd.DataFrame(columns=["date","equity"])
    eq = pd.DataFrame(events).sort_values("date")
    eq["equity"] = starting_capital + eq["amount"].cumsum()
    return eq[["date","equity"]]

def get_streak(checklist_df: pd.DataFrame) -> tuple[int, int]:
    if checklist_df.empty:
        return 0, 0
    df = checklist_df.sort_values("check_date", ascending=False).reset_index(drop=True)
    current = 0
    for _, row in df.iterrows():
        if row["discipline_score"] >= 75:
            current += 1
        else:
            break
    best = 0
    run  = 0
    for _, row in df.sort_values("check_date").iterrows():
        if row["discipline_score"] >= 75:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return current, best

# ─────────────────────────────────────────────
# STYLE INJECTION
# ─────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&family=Bebas+Neue&display=swap');

    :root {{
        --bg:      {COLORS['bg_dark']};
        --card:    {COLORS['bg_card']};
        --accent:  {COLORS['accent']};
        --accent2: {COLORS['accent2']};
        --green:   {COLORS['green']};
        --red:     {COLORS['red']};
        --yellow:  {COLORS['yellow']};
        --text:    {COLORS['text']};
        --dim:     {COLORS['text_dim']};
        --border:  {COLORS['border']};
    }}

    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif;
    }}

    [data-testid="stSidebar"] {{
        background: {COLORS['bg_sidebar']} !important;
        border-right: 1px solid var(--border);
    }}

    [data-testid="stSidebar"] * {{ color: var(--text) !important; }}

    .main .block-container {{
        padding: 1.5rem 2rem 3rem 2rem;
        max-width: 1400px;
    }}

    /* Cards */
    .metric-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        position: relative;
        overflow: hidden;
    }}
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
    }}
    .metric-card .label {{
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--dim);
        font-weight: 600;
        margin-bottom: 0.4rem;
    }}
    .metric-card .value {{
        font-family: 'Space Mono', monospace;
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text);
        line-height: 1;
    }}
    .metric-card .delta {{
        font-size: 0.78rem;
        margin-top: 0.3rem;
        color: var(--dim);
    }}

    /* Section headers */
    .section-title {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.8rem;
        letter-spacing: 0.06em;
        color: var(--accent);
        margin-bottom: 0.1rem;
    }}
    .section-sub {{
        font-size: 0.82rem;
        color: var(--dim);
        margin-bottom: 1.2rem;
    }}

    /* Quote card */
    .quote-card {{
        background: linear-gradient(135deg, #0d1528 0%, #111827 100%);
        border: 1px solid #1a2740;
        border-left: 3px solid var(--accent);
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.2rem;
    }}
    .quote-text {{
        font-size: 1.05rem;
        font-style: italic;
        color: var(--text);
        line-height: 1.6;
    }}
    .quote-author {{
        font-size: 0.78rem;
        color: var(--accent);
        margin-top: 0.4rem;
        font-family: 'Space Mono', monospace;
    }}

    /* Badges */
    .badge-pass {{
        display: inline-block;
        background: rgba(0,230,118,0.15);
        color: var(--green);
        border: 1px solid rgba(0,230,118,0.3);
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
    }}
    .badge-fail {{
        display: inline-block;
        background: rgba(255,23,68,0.15);
        color: var(--red);
        border: 1px solid rgba(255,23,68,0.3);
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
    }}
    .badge-warn {{
        display: inline-block;
        background: rgba(255,214,0,0.15);
        color: var(--yellow);
        border: 1px solid rgba(255,214,0,0.3);
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.75rem;
        font-weight: 700;
    }}

    /* Streak */
    .streak-box {{
        background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(0,212,255,0.1));
        border: 1px solid rgba(124,58,237,0.4);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }}
    .streak-num {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 3.5rem;
        color: var(--accent);
        line-height: 1;
    }}
    .streak-label {{
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--dim);
    }}

    /* Trade rows */
    .trade-row {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }}

    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox select,
    .stDateInput input, .stTextArea textarea {{
        background: #0d1627 !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
    }}

    .stCheckbox label {{ color: var(--text) !important; }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, var(--accent2), #5b21b6) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        letter-spacing: 0.03em;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(124,58,237,0.4) !important;
    }}

    /* Nav pills in sidebar */
    .nav-item {{
        padding: 0.6rem 1rem;
        border-radius: 8px;
        cursor: pointer;
        font-size: 0.9rem;
        color: var(--dim);
        transition: all 0.15s;
    }}
    .nav-item:hover {{ background: var(--border); color: var(--text); }}
    .nav-item.active {{ background: rgba(0,212,255,0.12); color: var(--accent); font-weight: 600; }}

    /* Divider */
    hr {{ border-color: var(--border) !important; }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

    /* Calendar cells */
    .cal-cell {{
        border-radius: 6px;
        padding: 6px;
        text-align: center;
        font-size: 0.75rem;
        cursor: pointer;
        transition: transform 0.15s;
    }}
    .cal-cell:hover {{ transform: scale(1.05); }}
    .cal-win  {{ background: rgba(0,230,118,0.2); border: 1px solid rgba(0,230,118,0.35); }}
    .cal-loss {{ background: rgba(255,23,68,0.2);  border: 1px solid rgba(255,23,68,0.35); }}
    .cal-even {{ background: rgba(255,214,0,0.15); border: 1px solid rgba(255,214,0,0.3); }}
    .cal-none {{ background: rgba(255,255,255,0.03); border: 1px solid var(--border); color: var(--dim); }}

    /* Alert boxes */
    .alert-green {{ background: rgba(0,230,118,0.08); border: 1px solid rgba(0,230,118,0.25); border-radius: 8px; padding: 0.8rem 1rem; color: var(--green); }}
    .alert-red   {{ background: rgba(255,23,68,0.08);  border: 1px solid rgba(255,23,68,0.25);  border-radius: 8px; padding: 0.8rem 1rem; color: var(--red);   }}
    .alert-blue  {{ background: rgba(0,212,255,0.08);  border: 1px solid rgba(0,212,255,0.2);   border-radius: 8px; padding: 0.8rem 1rem; color: var(--accent); }}

    /* Hide Streamlit branding */
    #MainMenu, footer, [data-testid="stDecoration"] {{ visibility: hidden; }}
    [data-testid="stHeader"] {{ background: transparent; }}
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# REUSABLE UI COMPONENTS
# ─────────────────────────────────────────────
def metric_card(label: str, value: str, delta: str = "", color: str = ""):
    color_style = f"color:{color};" if color else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value" style="{color_style}">{value}</div>
        {"<div class='delta'>" + delta + "</div>" if delta else ""}
    </div>""", unsafe_allow_html=True)

def section_header(title: str, sub: str = ""):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="section-sub">{sub}</div>', unsafe_allow_html=True)

def quote_card():
    q, a = random.choice(DISCIPLINE_QUOTES)
    st.markdown(f"""
    <div class="quote-card">
        <div class="quote-text">"{q}"</div>
        <div class="quote-author">{a}</div>
    </div>""", unsafe_allow_html=True)

def pnl_color(v: float) -> str:
    if v > 0: return COLORS["green"]
    if v < 0: return COLORS["red"]
    return COLORS["yellow"]

def badge(text: str, kind: str = "pass"):
    st.markdown(f'<span class="badge-{kind}">{text}</span>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────
def dark_layout(fig, title="", height=360):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,22,41,0.6)",
        font=dict(family="DM Sans", color=COLORS["text"], size=12),
        title=dict(text=title, font=dict(size=14, color=COLORS["accent"])),
        margin=dict(l=40, r=20, t=40 if title else 20, b=40),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"]),
        xaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"]),
        yaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"]),
    )
    return fig

# ─────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────
def page_dashboard():
    settings = load_settings()
    trades   = load_trades()
    cl_df    = load_daily_checklist()
    acct_df  = load_account()
    streak, best_streak = get_streak(cl_df)

    # Daily quote
    quote_card()

    section_header("PERFORMANCE OVERVIEW", "Real-time trading metrics")

    # ── Top KPIs ──
    c1,c2,c3,c4,c5 = st.columns(5)
    net_pnl   = trades["pnl"].sum() if not trades.empty else 0
    wins      = (trades["pnl"] > 0).sum() if not trades.empty else 0
    total_tr  = len(trades)
    win_rate  = round(wins/total_tr*100,1) if total_tr else 0
    comp_rate = round(trades["rule_score"].mean(),1) if not trades.empty else 0
    equity    = settings["starting_capital"] + net_pnl + (acct_df["amount"].sum() if not acct_df.empty else 0)
    growth    = round((equity / settings["starting_capital"] - 1)*100, 2)

    with c1: metric_card("NET PnL", f"${net_pnl:+,.2f}", "", pnl_color(net_pnl))
    with c2: metric_card("WIN RATE", f"{win_rate}%", f"{wins}W / {total_tr-wins}L")
    with c3: metric_card("TOTAL TRADES", str(total_tr), "all time")
    with c4: metric_card("RULE COMPLIANCE", f"{comp_rate}%", "avg per trade")
    with c5: metric_card("ACCOUNT EQUITY", f"${equity:,.0f}", f"{growth:+.2f}% growth", pnl_color(equity - settings["starting_capital"]))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Streak + Discipline ──
    col_a, col_b, col_c = st.columns([1,1,2])
    with col_a:
        st.markdown(f"""
        <div class="streak-box">
            <div class="streak-label">🔥 Current Streak</div>
            <div class="streak-num">{streak}</div>
            <div class="streak-label">disciplined days</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="streak-box" style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(15,22,41,0.9))">
            <div class="streak-label">🏆 Best Streak</div>
            <div class="streak-num" style="color:var(--yellow)">{best_streak}</div>
            <div class="streak-label">days ever</div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        if streak == 0:
            st.markdown('<div class="alert-red">⚠️ <b>Discipline streak broken.</b> Reset your mindset and start fresh today.</div>', unsafe_allow_html=True)
        elif streak >= 5:
            st.markdown(f'<div class="alert-green">🔥 <b>Excellent!</b> {streak}-day discipline streak. You\'re building consistency.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-blue">✅ <b>Keep going!</b> {streak}-day streak. Aim for 5+ consecutive disciplined sessions.</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Equity Curve + Recent Trades ──
    c_left, c_right = st.columns([2, 1])

    with c_left:
        section_header("EQUITY CURVE")
        eq = get_equity_curve(trades, settings["starting_capital"], acct_df)
        if not eq.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=eq["date"], y=eq["equity"],
                mode="lines", name="Equity",
                line=dict(color=COLORS["accent"], width=2.5),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,0.06)"
            ))
            fig.add_hline(y=settings["starting_capital"], line_dash="dot",
                          line_color=COLORS["text_dim"], annotation_text="Starting Capital")
            dark_layout(fig, height=300)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        else:
            st.markdown('<div class="alert-blue">No trade data yet. Log your first trade!</div>', unsafe_allow_html=True)

    with c_right:
        section_header("TODAY'S STATS")
        today = date.today().isoformat()
        today_trades = trades[trades["trade_date"].dt.date.astype(str) == today] if not trades.empty else pd.DataFrame()
        today_pnl  = today_trades["pnl"].sum() if not today_trades.empty else 0
        today_wins = (today_trades["pnl"]>0).sum() if not today_trades.empty else 0
        metric_card("TODAY'S PnL",    f"${today_pnl:+,.2f}", "", pnl_color(today_pnl))
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        metric_card("TODAY'S TRADES", str(len(today_trades)), f"{today_wins} winners")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        # Max loss warning
        max_loss = settings.get("max_daily_loss", -200)
        if today_pnl <= max_loss:
            st.markdown(f'<div class="alert-red">🛑 Daily loss limit hit! STOP TRADING.</div>', unsafe_allow_html=True)
        elif today_pnl >= settings.get("target_daily_pnl", 500):
            st.markdown(f'<div class="alert-green">🎯 Daily target reached! Consider stopping.</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recent trades table ──
    section_header("RECENT TRADES")
    if not trades.empty:
        display_df = trades.head(10)[["trade_date","symbol","direction","entry_price","exit_price","contracts","pnl","setup_type","rule_score","passed"]].copy()
        display_df["trade_date"] = display_df["trade_date"].dt.strftime("%Y-%m-%d")
        display_df["pnl"] = display_df["pnl"].apply(lambda x: f"${x:+,.2f}")
        display_df["rule_score"] = display_df["rule_score"].apply(lambda x: f"{x:.0f}%")
        display_df["passed"] = display_df["passed"].apply(lambda x: "✅ PASS" if x else "❌ FAIL")
        st.dataframe(
            display_df.rename(columns={
                "trade_date":"Date","symbol":"Symbol","direction":"Dir",
                "entry_price":"Entry","exit_price":"Exit","contracts":"Qty",
                "pnl":"PnL","setup_type":"Setup","rule_score":"Score","passed":"Status"
            }),
            use_container_width=True, hide_index=True,
        )
    else:
        st.markdown('<div class="alert-blue">No trades logged yet. Use "Add Trade" to get started.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: ADD TRADE
# ─────────────────────────────────────────────
def page_add_trade():
    section_header("LOG NEW TRADE", "Document every entry — discipline starts here")

    with st.form("trade_form", clear_on_submit=True):
        st.markdown("#### 📋 Trade Details")
        c1,c2,c3,c4 = st.columns(4)
        with c1: trade_date  = st.date_input("Date", value=date.today())
        with c2: symbol      = st.text_input("Symbol", value="MNQ")
        with c3: direction   = st.selectbox("Direction", ["Buy","Sell"])
        with c4: contracts   = st.number_input("Contracts", min_value=1, max_value=100, value=1)

        c5,c6,c7,c8 = st.columns(4)
        with c5: entry_price = st.number_input("Entry Price", min_value=0.0, value=18000.0, step=0.25, format="%.2f")
        with c6: exit_price  = st.number_input("Exit Price",  min_value=0.0, value=18010.0, step=0.25, format="%.2f")
        with c7: timeframe   = st.selectbox("Timeframe", TIMEFRAMES, index=2)
        with c8: setup_type  = st.selectbox("Setup Type", SETUP_TYPES)

        # Auto-calc PnL preview
        auto_pnl = calc_pnl(direction, entry_price, exit_price, contracts)
        pnl_color_hex = pnl_color(auto_pnl)
        st.markdown(f"""
        <div class="metric-card" style="margin:0.5rem 0">
            <span class="label">AUTO-CALCULATED PnL</span>
            <span class="value" style="color:{pnl_color_hex}; margin-left:1rem;">${auto_pnl:+,.2f}</span>
            <span class="delta" style="margin-left:0.5rem">({contracts} contract{'s' if contracts>1 else ''} · MNQ tick = $0.50)</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### ⚙️ ICT Rule Checklist")
        ci1,ci2,ci3,ci4,ci5 = st.columns(5)
        with ci1: liq_hunt  = st.checkbox("15m Liquidity Hunt confirmed")
        with ci2: engulf    = st.checkbox("1m Engulfing entry")
        with ci3: killzone  = st.checkbox("Killzone respected")
        with ci4: trend     = st.checkbox("Trend aligned")
        with ci5: risk_def  = st.checkbox("Risk defined pre-entry")

        st.markdown("#### 🧠 Discipline Checklist")
        cd1,cd2,cd3,cd4 = st.columns(4)
        with cd1: no_revenge   = st.checkbox("No revenge trade")
        with cd2: followed_sl  = st.checkbox("Followed stop loss")
        with cd3: followed_plan= st.checkbox("Followed plan exactly")
        with cd4: no_emotion   = st.checkbox("No emotional entry")

        # Live score preview
        raw = {"liquidity_hunt":liq_hunt,"engulf_confirm":engulf,"killzone":killzone,
               "trend_align":trend,"risk_defined":risk_def,"no_revenge":no_revenge,
               "followed_sl":followed_sl,"followed_plan":followed_plan,"no_emotion":no_emotion}
        live_score, live_pass = calc_rule_score(raw)
        score_color = COLORS["green"] if live_pass else COLORS["red"]
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;margin:0.5rem 0 1rem 0">
            <span style="font-size:0.85rem;color:var(--dim)">RULE COMPLIANCE SCORE</span>
            <span style="font-family:'Space Mono',monospace;font-size:1.4rem;font-weight:700;color:{score_color}">{live_score}%</span>
            <span class="badge-{'pass' if live_pass else 'fail'}">{'✅ PASS' if live_pass else '❌ FAIL'}</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### 📝 Notes")
        notes      = st.text_area("Trade notes, mistakes, lessons learned...", height=100)
        screenshot = st.file_uploader("Screenshot (optional)", type=["png","jpg","jpeg","webp"])

        submitted = st.form_submit_button("💾 LOG TRADE", use_container_width=True)

    if submitted:
        screenshot_b64 = None
        if screenshot:
            screenshot_b64 = base64.b64encode(screenshot.read()).decode()

        data = {
            "trade_date":    trade_date.isoformat(),
            "symbol":        symbol.upper(),
            "direction":     direction,
            "entry_price":   entry_price,
            "exit_price":    exit_price,
            "contracts":     contracts,
            "pnl":           auto_pnl,
            "timeframe":     timeframe,
            "setup_type":    setup_type,
            "notes":         notes,
            "screenshot":    screenshot_b64,
            "liquidity_hunt":int(liq_hunt),
            "engulf_confirm":int(engulf),
            "killzone":      int(killzone),
            "trend_align":   int(trend),
            "risk_defined":  int(risk_def),
            "no_revenge":    int(no_revenge),
            "followed_sl":   int(followed_sl),
            "followed_plan": int(followed_plan),
            "no_emotion":    int(no_emotion),
            "rule_score":    live_score,
            "passed":        int(live_pass),
        }
        save_trade(data)
        if live_pass:
            st.success(f"✅ Trade logged! Rule score: {live_score}% — PASS")
        else:
            st.warning(f"⚠️ Trade logged with score {live_score}% — FAIL. Review your rules.")

    st.markdown("---")
    section_header("TRADE LOG", "All logged trades")
    trades = load_trades()
    if not trades.empty:
        for _, row in trades.head(20).iterrows():
            pnl_c = pnl_color(row["pnl"])
            st.markdown(f"""
            <div class="trade-row">
                <span style="color:var(--dim);font-size:0.8rem;min-width:90px">{row['trade_date'].strftime('%Y-%m-%d')}</span>
                <span style="font-weight:600;min-width:50px">{row['symbol']}</span>
                <span style="color:{'var(--green)' if row['direction']=='Buy' else 'var(--red)'};min-width:40px">{row['direction']}</span>
                <span style="color:var(--dim);font-size:0.85rem;min-width:180px">{row['setup_type']}</span>
                <span style="font-family:'Space Mono',monospace;color:{pnl_c};font-weight:700;min-width:100px">${row['pnl']:+,.2f}</span>
                <span style="font-size:0.8rem;color:var(--dim)">{row['rule_score']:.0f}% compliance</span>
                <span class="badge-{'pass' if row['passed'] else 'fail'}" style="margin-left:auto">{'PASS' if row['passed'] else 'FAIL'}</span>
            </div>""", unsafe_allow_html=True)

        # Delete trade option
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🗑️ Delete a Trade"):
            del_id = st.number_input("Trade ID to delete", min_value=1, step=1)
            if st.button("Delete Trade", type="secondary"):
                delete_trade(del_id)
                st.success(f"Trade #{del_id} deleted.")
                st.rerun()

# ─────────────────────────────────────────────
# PAGE: CALENDAR
# ─────────────────────────────────────────────
def page_calendar():
    section_header("PnL CALENDAR", "Heatmap of your trading performance")
    trades  = load_trades()
    cl_df   = load_daily_checklist()

    if trades.empty:
        st.markdown('<div class="alert-blue">No trade data yet. Log trades to see the calendar.</div>', unsafe_allow_html=True)
        return

    # Build daily summary
    trades["date_str"] = trades["trade_date"].dt.date
    daily = trades.groupby("date_str").agg(
        total_pnl=("pnl","sum"),
        trade_count=("id","count"),
        avg_score=("rule_score","mean")
    ).reset_index()
    daily_dict = {str(r["date_str"]): r for _, r in daily.iterrows()}

    # Pick month
    all_dates = sorted(trades["trade_date"].dt.to_period("M").unique())
    month_options = [str(p) for p in all_dates]
    if not month_options:
        return
    sel_month = st.selectbox("Select Month", month_options[::-1])
    year, month = int(sel_month.split("-")[0]), int(sel_month.split("-")[1])

    st.markdown(f"### {cal_module.month_name[month]} {year}")

    # Calendar grid
    cal = cal_module.monthcalendar(year, month)
    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    cols = st.columns(7)
    for i, d in enumerate(day_names):
        cols[i].markdown(f"<div style='text-align:center;color:var(--dim);font-size:0.8rem;font-weight:600;padding-bottom:4px'>{d}</div>", unsafe_allow_html=True)

    selected_date = st.session_state.get("cal_selected_date", None)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='height:70px'></div>", unsafe_allow_html=True)
                    continue
                d_str = f"{year}-{month:02d}-{day:02d}"
                if d_str in daily_dict:
                    row = daily_dict[d_str]
                    pnl = row["total_pnl"]
                    n   = row["trade_count"]
                    sc  = row["avg_score"]
                    cls = "cal-win" if pnl > 0 else ("cal-loss" if pnl < 0 else "cal-even")
                    pnl_str = f"${pnl:+,.0f}"
                    cell_html = f"""
                    <div class="cal-cell {cls}">
                        <div style="font-weight:700;font-size:0.9rem">{day}</div>
                        <div style="font-size:0.65rem;font-weight:700;color:{'#00e676' if pnl>=0 else '#ff1744'}">{pnl_str}</div>
                        <div style="font-size:0.6rem;color:var(--dim)">{n}T · {sc:.0f}%</div>
                    </div>"""
                    st.markdown(cell_html, unsafe_allow_html=True)
                    if st.button(f"View", key=f"cal_{d_str}", use_container_width=True):
                        st.session_state["cal_selected_date"] = d_str
                else:
                    st.markdown(f"""
                    <div class="cal-cell cal-none">
                        <div style="font-weight:600">{day}</div>
                        <div style="font-size:0.6rem">—</div>
                    </div>""", unsafe_allow_html=True)

    # ── Day detail ──
    if "cal_selected_date" in st.session_state and st.session_state["cal_selected_date"]:
        d_str = st.session_state["cal_selected_date"]
        st.markdown("---")
        section_header(f"TRADES ON {d_str}")
        day_trades = trades[trades["date_str"].astype(str) == d_str]
        if not day_trades.empty:
            c1,c2,c3 = st.columns(3)
            dpnl = day_trades["pnl"].sum()
            with c1: metric_card("Day PnL", f"${dpnl:+,.2f}", "", pnl_color(dpnl))
            with c2: metric_card("Trades",  str(len(day_trades)))
            with c3: metric_card("Avg Score", f"{day_trades['rule_score'].mean():.1f}%")
            st.markdown("<br>", unsafe_allow_html=True)
            for _, row in day_trades.iterrows():
                pnl_c = pnl_color(row["pnl"])
                st.markdown(f"""
                <div class="trade-row">
                    <b>{row['symbol']}</b>
                    <span style="color:{'var(--green)' if row['direction']=='Buy' else 'var(--red)'}">{row['direction']}</span>
                    <span>Entry: <b>{row['entry_price']}</b></span>
                    <span>Exit: <b>{row['exit_price']}</b></span>
                    <span style="font-family:'Space Mono',monospace;color:{pnl_c};font-weight:700">${row['pnl']:+,.2f}</span>
                    <span style="font-size:0.8rem;color:var(--dim)">{row['setup_type']}</span>
                    <span class="badge-{'pass' if row['passed'] else 'fail'}" style="margin-left:auto">{'PASS' if row['passed'] else 'FAIL'}</span>
                </div>""", unsafe_allow_html=True)
                if row["notes"]:
                    st.markdown(f"<div style='color:var(--dim);font-size:0.82rem;padding:0.3rem 0.5rem 0.8rem 1rem'>📝 {row['notes']}</div>", unsafe_allow_html=True)
                if row["screenshot"]:
                    try:
                        img_data = base64.b64decode(row["screenshot"])
                        st.image(img_data, caption="Trade Screenshot", width=400)
                    except:
                        pass

        # Discipline for this day
        if not cl_df.empty:
            day_cl = cl_df[cl_df["check_date"].dt.strftime("%Y-%m-%d") == d_str]
            if not day_cl.empty:
                st.markdown(f"**Discipline Score:** {day_cl.iloc[0]['discipline_score']:.0f}%")
                if day_cl.iloc[0]["notes"]:
                    st.markdown(f"📝 *{day_cl.iloc[0]['notes']}*")

# ─────────────────────────────────────────────
# PAGE: DISCIPLINE CHECK
# ─────────────────────────────────────────────
def page_discipline():
    section_header("DAILY DISCIPLINE CHECK", "Complete this every trading session")

    cl_df = load_daily_checklist()
    today = date.today().isoformat()
    streak, best_streak = get_streak(cl_df)

    # Check if already completed today
    already_done = not cl_df.empty and (cl_df["check_date"].dt.strftime("%Y-%m-%d") == today).any()

    if already_done:
        today_row = cl_df[cl_df["check_date"].dt.strftime("%Y-%m-%d") == today].iloc[0]
        ds = today_row["discipline_score"]
        sc = pnl_color(ds - 50)
        st.markdown(f"""
        <div class="alert-{'green' if ds>=75 else 'red'}">
            ✅ <b>Today's checklist completed!</b> Discipline Score: {ds:.0f}%
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns([2,1])
    with c1:
        with st.form("daily_check_form", clear_on_submit=not already_done):
            st.markdown("#### 📋 Today's Checklist")
            st.markdown(f"**Date:** {today}")

            fr = st.checkbox("✅ I followed my trading rules today")
            nr = st.checkbox("✅ I did NOT take any revenge trades")
            rr = st.checkbox("✅ I respected my risk management")
            no_ot = st.checkbox("✅ I did NOT overtrade")

            # Live preview
            live_d = {"followed_rules":fr,"no_revenge":nr,"risk_respected":rr,"no_overtrade":no_ot}
            live_ds = calc_discipline_score(live_d)
            ds_color = COLORS["green"] if live_ds >= 75 else COLORS["red"]
            st.markdown(f"""
            <div style="margin:1rem 0;padding:0.8rem;background:var(--card);border-radius:8px;border:1px solid var(--border)">
                <span style="color:var(--dim);font-size:0.85rem">DISCIPLINE SCORE PREVIEW: </span>
                <span style="font-family:'Space Mono',monospace;font-size:1.3rem;font-weight:700;color:{ds_color}">{live_ds:.0f}%</span>
            </div>""", unsafe_allow_html=True)

            notes = st.text_area("Reflection & notes for today...", height=100)
            submitted = st.form_submit_button("💾 SAVE DAILY CHECK", use_container_width=True)

        if submitted:
            final_score = calc_discipline_score({"followed_rules":fr,"no_revenge":nr,"risk_respected":rr,"no_overtrade":no_ot})
            save_daily_checklist({
                "check_date":     today,
                "followed_rules": int(fr),
                "no_revenge":     int(nr),
                "risk_respected": int(rr),
                "no_overtrade":   int(no_ot),
                "notes":          notes,
                "discipline_score": final_score
            })
            if final_score >= 75:
                st.success(f"🔥 Excellent! {final_score:.0f}% discipline score. Streak continues!")
            else:
                st.warning(f"⚠️ {final_score:.0f}% discipline score. Streak reset. Review your habits.")
            st.rerun()

    with c2:
        st.markdown(f"""
        <div class="streak-box" style="margin-bottom:1rem">
            <div class="streak-label">🔥 Current Streak</div>
            <div class="streak-num">{streak}</div>
            <div class="streak-label">days</div>
        </div>
        <div class="streak-box">
            <div class="streak-label">🏆 Best Ever</div>
            <div class="streak-num" style="color:var(--yellow)">{best_streak}</div>
            <div class="streak-label">days</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    section_header("DISCIPLINE HISTORY")

    if not cl_df.empty:
        recent = cl_df.head(14)
        dates  = recent["check_date"].dt.strftime("%m/%d").tolist()[::-1]
        scores = recent["discipline_score"].tolist()[::-1]
        colors = [COLORS["green"] if s >= 75 else COLORS["red"] for s in scores]

        fig = go.Figure(go.Bar(
            x=dates, y=scores,
            marker_color=colors,
            marker_line_width=0,
            name="Discipline Score"
        ))
        fig.add_hline(y=75, line_dash="dot", line_color=COLORS["yellow"], annotation_text="Pass threshold (75%)")
        dark_layout(fig, "14-Day Discipline History", height=280)
        fig.update_yaxis(range=[0,105])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # Table
        disp = cl_df.head(20)[["check_date","followed_rules","no_revenge","risk_respected","no_overtrade","discipline_score","notes"]].copy()
        disp["check_date"] = disp["check_date"].dt.strftime("%Y-%m-%d")
        disp["discipline_score"] = disp["discipline_score"].apply(lambda x: f"{x:.0f}%")
        disp.columns = ["Date","Rules ✓","No Revenge ✓","Risk Mgmt ✓","No OT ✓","Score","Notes"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# PAGE: ACCOUNT MANAGEMENT
# ─────────────────────────────────────────────
def page_account():
    section_header("ACCOUNT MANAGEMENT", "Track capital, deposits, withdrawals & growth")
    settings  = load_settings()
    trades    = load_trades()
    acct_df   = load_account()

    net_trade_pnl = trades["pnl"].sum() if not trades.empty else 0
    external_flow = acct_df["amount"].sum() if not acct_df.empty else 0
    equity = settings["starting_capital"] + net_trade_pnl + external_flow
    growth = (equity / settings["starting_capital"] - 1) * 100

    c1,c2,c3,c4 = st.columns(4)
    with c1: metric_card("Starting Capital", f"${settings['starting_capital']:,.0f}")
    with c2: metric_card("Trading PnL",      f"${net_trade_pnl:+,.2f}", "", pnl_color(net_trade_pnl))
    with c3: metric_card("Current Equity",   f"${equity:,.2f}", f"{growth:+.2f}% growth", pnl_color(equity - settings["starting_capital"]))
    with c4: metric_card("External Flows",   f"${external_flow:+,.2f}", "deposits/payouts")

    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1, 2])

    with c_left:
        st.markdown("#### ⚙️ Account Settings")
        new_capital = st.number_input("Starting Capital", value=float(settings["starting_capital"]), step=1000.0)
        acc_name    = st.text_input("Account Name", value=settings.get("account_name",""))
        tgt_pnl     = st.number_input("Daily Target PnL ($)", value=float(settings.get("target_daily_pnl",500)), step=50.0)
        max_loss    = st.number_input("Max Daily Loss ($)", value=float(settings.get("max_daily_loss",-200)), step=50.0)
        if st.button("Save Settings"):
            settings.update({"starting_capital":new_capital,"account_name":acc_name,"target_daily_pnl":tgt_pnl,"max_daily_loss":max_loss})
            save_settings(settings)
            st.success("Settings saved!")

        st.markdown("---")
        st.markdown("#### ➕ Log Transaction")
        ev_date   = st.date_input("Date", value=date.today(), key="acct_date")
        ev_type   = st.selectbox("Type", ["Deposit","Withdrawal","Payout","Funded Account"])
        ev_amount = st.number_input("Amount ($)", value=0.0, step=100.0)
        ev_notes  = st.text_input("Notes")
        if st.button("Add Transaction"):
            sign = 1 if ev_type in ["Deposit","Funded Account"] else -1
            save_account_event({"event_date":ev_date.isoformat(),"event_type":ev_type,"amount":sign*abs(ev_amount),"notes":ev_notes})
            st.success(f"{ev_type} logged!")
            st.rerun()

    with c_right:
        eq_curve = get_equity_curve(trades, settings["starting_capital"], acct_df)
        if not eq_curve.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=eq_curve["date"], y=eq_curve["equity"],
                mode="lines+markers", name="Equity",
                line=dict(color=COLORS["accent"], width=2.5),
                fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
                marker=dict(size=5, color=COLORS["accent"])
            ))
            fig.add_hline(y=settings["starting_capital"], line_dash="dot",
                          line_color=COLORS["text_dim"], annotation_text="Start")
            dark_layout(fig, "Account Equity Curve", height=320)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        if not acct_df.empty:
            st.markdown("##### Transaction History")
            st.dataframe(acct_df[["event_date","event_type","amount","notes"]].rename(
                columns={"event_date":"Date","event_type":"Type","amount":"Amount","notes":"Notes"}
            ), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# PAGE: ANALYTICS
# ─────────────────────────────────────────────
def page_analytics():
    section_header("ANALYTICS DASHBOARD", "Deep performance insights")
    trades = load_trades()

    if trades.empty:
        st.markdown('<div class="alert-blue">No trade data yet. Log trades to see analytics.</div>', unsafe_allow_html=True)
        return

    # ── KPI Row ──
    total  = len(trades)
    wins   = (trades["pnl"] > 0).sum()
    losses = (trades["pnl"] < 0).sum()
    wr     = round(wins/total*100,1)
    net    = trades["pnl"].sum()
    avg_w  = trades[trades["pnl"]>0]["pnl"].mean() if wins else 0
    avg_l  = abs(trades[trades["pnl"]<0]["pnl"].mean()) if losses else 0
    rr     = round(avg_w/avg_l,2) if avg_l else 0
    comp   = round(trades["rule_score"].mean(),1)
    pass_r = round(trades["passed"].mean()*100,1)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: metric_card("TOTAL TRADES", str(total))
    with c2: metric_card("WIN RATE", f"{wr}%", f"{wins}W/{losses}L")
    with c3: metric_card("NET PnL", f"${net:+,.2f}", "", pnl_color(net))
    with c4: metric_card("AVG R:R", f"{rr:.2f}", f"W:{avg_w:.0f} / L:{avg_l:.0f}")
    with c5: metric_card("RULE SCORE", f"{comp:.1f}%", "avg compliance")
    with c6: metric_card("PASS RATE", f"{pass_r}%", "% trades that passed")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Monthly PnL + Setup Performance ──
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        trades["month"] = trades["trade_date"].dt.to_period("M").astype(str)
        monthly = trades.groupby("month")["pnl"].sum().reset_index()
        colors  = [COLORS["green"] if v >= 0 else COLORS["red"] for v in monthly["pnl"]]
        fig = go.Figure(go.Bar(x=monthly["month"], y=monthly["pnl"], marker_color=colors, marker_line_width=0))
        dark_layout(fig, "Monthly PnL", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with r1c2:
        setup_perf = trades.groupby("setup_type").agg(
            total_pnl=("pnl","sum"), count=("id","count"), win_rate=("pnl",lambda x:(x>0).mean()*100)
        ).reset_index().sort_values("total_pnl", ascending=True)
        colors_s = [COLORS["green"] if v>=0 else COLORS["red"] for v in setup_perf["total_pnl"]]
        fig = go.Figure(go.Bar(
            x=setup_perf["total_pnl"], y=setup_perf["setup_type"],
            orientation="h", marker_color=colors_s, marker_line_width=0,
            text=setup_perf["count"].apply(lambda x: f"{x}T"),
            textposition="outside"
        ))
        dark_layout(fig, "PnL by Setup Type", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # ── Row 2: Daily PnL distribution + Rule compliance trend ──
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        fig = go.Figure(go.Histogram(
            x=trades["pnl"], nbinsx=30,
            marker_color=COLORS["accent2"],
            marker_line_color=COLORS["bg_dark"],
            marker_line_width=0.5
        ))
        fig.add_vline(x=0, line_color=COLORS["yellow"], line_dash="dot")
        dark_layout(fig, "Trade PnL Distribution", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with r2c2:
        trades_sorted = trades.sort_values("trade_date")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trades_sorted["trade_date"], y=trades_sorted["rule_score"].rolling(5, min_periods=1).mean(),
            mode="lines", name="5-Trade MA",
            line=dict(color=COLORS["accent"], width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=trades_sorted["trade_date"], y=trades_sorted["rule_score"],
            mode="markers", name="Per Trade",
            marker=dict(color=[COLORS["green"] if p else COLORS["red"] for p in trades_sorted["passed"]], size=6)
        ))
        fig.add_hline(y=70, line_dash="dot", line_color=COLORS["yellow"], annotation_text="Pass (70%)")
        dark_layout(fig, "Rule Compliance Trend", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # ── Row 3: Win/Loss pie + Hour analysis ──
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        fig = go.Figure(go.Pie(
            labels=["Wins","Losses","Breakeven"],
            values=[wins, losses, total-wins-losses],
            marker_colors=[COLORS["green"], COLORS["red"], COLORS["yellow"]],
            hole=0.6,
            textinfo="label+percent"
        ))
        dark_layout(fig, "Win / Loss Breakdown", 280)
        fig.update_traces(textfont_color=COLORS["text"])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with r3c2:
        setup_wr = trades.groupby("setup_type").agg(
            wr=("pnl", lambda x: round((x>0).mean()*100,1)),
            count=("id","count")
        ).reset_index().sort_values("wr", ascending=False)
        fig = go.Figure(go.Bar(
            x=setup_wr["setup_type"], y=setup_wr["wr"],
            marker_color=COLORS["accent2"], marker_line_width=0,
            text=setup_wr["wr"].apply(lambda x: f"{x:.0f}%"),
            textposition="outside"
        ))
        fig.add_hline(y=50, line_dash="dot", line_color=COLORS["yellow"])
        dark_layout(fig, "Win Rate by Setup", 280)
        fig.update_yaxis(range=[0, 110])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # ── Best/Worst patterns ──
    st.markdown("---")
    ca, cb = st.columns(2)
    with ca:
        section_header("🏆 BEST PATTERNS")
        best = setup_perf.sort_values("total_pnl", ascending=False).head(3)
        for _, row in best.iterrows():
            st.markdown(f"""
            <div class="trade-row">
                <span style="font-weight:600">{row['setup_type']}</span>
                <span style="font-family:'Space Mono',monospace;color:{pnl_color(row['total_pnl'])};">${row['total_pnl']:+,.0f}</span>
                <span style="color:var(--dim)">{row['count']} trades · {row['win_rate']:.0f}% WR</span>
            </div>""", unsafe_allow_html=True)
    with cb:
        section_header("⚠️ MISTAKE PATTERNS")
        worst = setup_perf.sort_values("total_pnl").head(3)
        for _, row in worst.iterrows():
            st.markdown(f"""
            <div class="trade-row">
                <span style="font-weight:600">{row['setup_type']}</span>
                <span style="font-family:'Space Mono',monospace;color:{pnl_color(row['total_pnl'])};">${row['total_pnl']:+,.0f}</span>
                <span style="color:var(--dim)">{row['count']} trades · {row['win_rate']:.0f}% WR</span>
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:1.2rem 0 0.5rem 0;text-align:center">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:#00d4ff;letter-spacing:0.12em">MNQ JOURNAL</div>
            <div style="font-size:0.72rem;color:#64748b;letter-spacing:0.15em;margin-top:-2px">PROP TRADER · DISCIPLINE SYSTEM</div>
        </div>
        <hr style="border-color:#1e2a45;margin:0.5rem 0 1rem 0">
        """, unsafe_allow_html=True)

        pages = {
            "📊 Dashboard":        "dashboard",
            "📝 Add Trade":        "add_trade",
            "📅 Calendar":         "calendar",
            "🧠 Discipline Check": "discipline",
            "💰 Account":          "account",
            "📈 Analytics":        "analytics",
        }

        if "page" not in st.session_state:
            st.session_state["page"] = "dashboard"

        for label, key in pages.items():
            is_active = st.session_state["page"] == key
            if st.button(label, key=f"nav_{key}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["page"] = key
                st.rerun()

        st.markdown("<hr style='border-color:#1e2a45;margin:1rem 0'>", unsafe_allow_html=True)

        # Quick stats
        trades = load_trades()
        if not trades.empty:
            today_str = date.today().isoformat()
            today_t   = trades[trades["trade_date"].dt.date.astype(str) == today_str]
            today_pnl = today_t["pnl"].sum()
            st.markdown(f"""
            <div style="padding:0 0.5rem">
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:#64748b;margin-bottom:6px">TODAY</div>
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="color:#94a3b8;font-size:0.82rem">PnL</span>
                    <span style="font-family:'Space Mono',monospace;font-size:0.82rem;color:{'#00e676' if today_pnl>=0 else '#ff1744'};font-weight:700">${today_pnl:+,.2f}</span>
                </div>
                <div style="display:flex;justify-content:space-between">
                    <span style="color:#94a3b8;font-size:0.82rem">Trades</span>
                    <span style="font-size:0.82rem;color:#e2e8f0">{len(today_t)}</span>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="position:absolute;bottom:1rem;left:0;right:0;text-align:center">
            <div style="font-size:0.65rem;color:#334155;letter-spacing:0.08em">BUILT FOR DISCIPLINE</div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="MNQ Trading Journal",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_css()
    init_db()
    render_sidebar()

    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":    page_dashboard()
    elif page == "add_trade":  page_add_trade()
    elif page == "calendar":   page_calendar()
    elif page == "discipline": page_discipline()
    elif page == "account":    page_account()
    elif page == "analytics":  page_analytics()

if __name__ == "__main__":
    main()
