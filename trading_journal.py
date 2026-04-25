"""
MNQ TRADING JOURNAL — PROFESSIONAL EDITION
Run: streamlit run trading_journal.py
Requires: streamlit pandas plotly pillow
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import sqlite3
from datetime import datetime, date, timedelta
import random
import base64
import calendar as cal_module
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
DB_FILE       = "trading_journal.db"
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

EXPENSE_CATEGORIES = [
    "Platform/Software", "Data Feed", "Education/Course", "Books",
    "Hardware", "Internet", "Prop Firm Fee", "Tax", "Other"
]

INCOME_CATEGORIES = [
    "Trading Profit", "Prop Firm Payout", "Funded Account", "Refund", "Other"
]

COLORS = {
    "bg_dark":  "#0a0e1a",
    "bg_card":  "#0f1629",
    "bg_side":  "#080c18",
    "accent":   "#00d4ff",
    "accent2":  "#7c3aed",
    "green":    "#00e676",
    "red":      "#ff1744",
    "yellow":   "#ffd600",
    "text":     "#e2e8f0",
    "dim":      "#64748b",
    "border":   "#1e2a45",
}

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL, symbol TEXT DEFAULT 'MNQ',
        direction TEXT, entry_price REAL, exit_price REAL,
        contracts INTEGER DEFAULT 1, pnl REAL,
        timeframe TEXT, setup_type TEXT, notes TEXT, screenshot TEXT,
        liquidity_hunt INTEGER DEFAULT 0, engulf_confirm INTEGER DEFAULT 0,
        killzone INTEGER DEFAULT 0, trend_align INTEGER DEFAULT 0,
        risk_defined INTEGER DEFAULT 0, no_revenge INTEGER DEFAULT 0,
        followed_sl INTEGER DEFAULT 0, followed_plan INTEGER DEFAULT 0,
        no_emotion INTEGER DEFAULT 0, rule_score REAL DEFAULT 0,
        passed INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS daily_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_date TEXT UNIQUE NOT NULL,
        followed_rules INTEGER DEFAULT 0, no_revenge INTEGER DEFAULT 0,
        risk_respected INTEGER DEFAULT 0, no_overtrade INTEGER DEFAULT 0,
        notes TEXT, discipline_score REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS account (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TEXT NOT NULL, event_type TEXT,
        amount REAL, notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL, entry_type TEXT NOT NULL,
        category TEXT, amount REAL, description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# DATA ACCESS
# ─────────────────────────────────────────────
def load_trades():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM trades ORDER BY trade_date DESC, created_at DESC", conn)
    conn.close()
    if not df.empty:
        df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df

def save_trade(data):
    conn = get_db()
    conn.execute("""INSERT INTO trades (
        trade_date,symbol,direction,entry_price,exit_price,contracts,pnl,
        timeframe,setup_type,notes,screenshot,
        liquidity_hunt,engulf_confirm,killzone,trend_align,risk_defined,
        no_revenge,followed_sl,followed_plan,no_emotion,rule_score,passed
    ) VALUES (
        :trade_date,:symbol,:direction,:entry_price,:exit_price,:contracts,:pnl,
        :timeframe,:setup_type,:notes,:screenshot,
        :liquidity_hunt,:engulf_confirm,:killzone,:trend_align,:risk_defined,
        :no_revenge,:followed_sl,:followed_plan,:no_emotion,:rule_score,:passed
    )""", data)
    conn.commit()
    conn.close()

def delete_trade(tid):
    conn = get_db()
    conn.execute("DELETE FROM trades WHERE id=?", (tid,))
    conn.commit()
    conn.close()

def load_daily_checklist():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM daily_checklist ORDER BY check_date DESC", conn)
    conn.close()
    if not df.empty:
        df["check_date"] = pd.to_datetime(df["check_date"])
    return df

def save_daily_checklist(data):
    conn = get_db()
    conn.execute("""INSERT OR REPLACE INTO daily_checklist
        (check_date,followed_rules,no_revenge,risk_respected,no_overtrade,notes,discipline_score)
        VALUES (:check_date,:followed_rules,:no_revenge,:risk_respected,:no_overtrade,:notes,:discipline_score)
    """, data)
    conn.commit()
    conn.close()

def load_account():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM account ORDER BY event_date ASC", conn)
    conn.close()
    return df

def save_account_event(data):
    conn = get_db()
    conn.execute("INSERT INTO account (event_date,event_type,amount,notes) VALUES (:event_date,:event_type,:amount,:notes)", data)
    conn.commit()
    conn.close()

def load_expenses():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM expenses ORDER BY entry_date DESC", conn)
    conn.close()
    if not df.empty:
        df["entry_date"] = pd.to_datetime(df["entry_date"])
    return df

def save_expense(data):
    conn = get_db()
    conn.execute("INSERT INTO expenses (entry_date,entry_type,category,amount,description) VALUES (:entry_date,:entry_type,:category,:amount,:description)", data)
    conn.commit()
    conn.close()

def delete_expense(eid):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=?", (eid,))
    conn.commit()
    conn.close()

def load_settings():
    defaults = {"account_name": "MNQ Prop Account", "target_daily_pnl": 500.0, "max_daily_loss": -200.0}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
        defaults.update(s)
    return defaults

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def calc_rule_score(d):
    keys = ["liquidity_hunt","engulf_confirm","killzone","trend_align","risk_defined",
            "no_revenge","followed_sl","followed_plan","no_emotion"]
    score = sum(d.get(k, 0) for k in keys)
    pct   = round((score / len(keys)) * 100, 1)
    return pct, pct >= 70.0

def calc_discipline_score(d):
    keys = ["followed_rules","no_revenge","risk_respected","no_overtrade"]
    return round((sum(d.get(k, 0) for k in keys) / len(keys)) * 100, 1)

def calc_pnl(direction, entry, exit_p, contracts=1):
    ticks = (exit_p - entry) / 0.25 if direction == "Buy" else (entry - exit_p) / 0.25
    return round(ticks * 0.50 * contracts, 2)

def pnl_color(v):
    if v > 0: return COLORS["green"]
    if v < 0: return COLORS["red"]
    return COLORS["yellow"]

def get_equity_curve(trades_df, account_df):
    events = []
    if not trades_df.empty:
        for _, r in trades_df.iterrows():
            events.append({"date": r["trade_date"], "amount": r["pnl"]})
    if not account_df.empty:
        for _, r in account_df.iterrows():
            events.append({"date": pd.to_datetime(r["event_date"]), "amount": r["amount"]})
    if not events:
        return pd.DataFrame(columns=["date","equity"])
    eq = pd.DataFrame(events).sort_values("date")
    eq["equity"] = eq["amount"].cumsum()
    return eq[["date","equity"]]

def get_streak(cl_df):
    if cl_df.empty:
        return 0, 0
    df = cl_df.sort_values("check_date", ascending=False).reset_index(drop=True)
    current = 0
    for _, row in df.iterrows():
        if row["discipline_score"] >= 75:
            current += 1
        else:
            break
    best, run = 0, 0
    for _, row in df.sort_values("check_date").iterrows():
        if row["discipline_score"] >= 75:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return current, best

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&family=Bebas+Neue&display=swap');
    html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{{background:{COLORS['bg_dark']}!important;color:{COLORS['text']}!important;font-family:'DM Sans',sans-serif;}}
    [data-testid="stSidebar"]{{background:{COLORS['bg_side']}!important;border-right:1px solid {COLORS['border']};}}
    [data-testid="stSidebar"] *{{color:{COLORS['text']}!important;}}
    .main .block-container{{padding:1.5rem 2rem 3rem 2rem;max-width:1400px;}}
    .metric-card{{background:{COLORS['bg_card']};border:1px solid {COLORS['border']};border-radius:12px;padding:1.2rem 1.4rem;position:relative;overflow:hidden;margin-bottom:4px;}}
    .metric-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,{COLORS['accent']},{COLORS['accent2']});}}
    .metric-card .label{{font-size:0.72rem;text-transform:uppercase;letter-spacing:0.12em;color:{COLORS['dim']};font-weight:600;margin-bottom:0.4rem;}}
    .metric-card .value{{font-family:'Space Mono',monospace;font-size:1.6rem;font-weight:700;color:{COLORS['text']};line-height:1;}}
    .metric-card .delta{{font-size:0.78rem;margin-top:0.3rem;color:{COLORS['dim']};}}
    .section-title{{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:0.06em;color:{COLORS['accent']};margin-bottom:0.1rem;}}
    .section-sub{{font-size:0.82rem;color:{COLORS['dim']};margin-bottom:1.2rem;}}
    .quote-card{{background:linear-gradient(135deg,#0d1528,#111827);border:1px solid #1a2740;border-left:3px solid {COLORS['accent']};border-radius:10px;padding:1rem 1.4rem;margin-bottom:1.2rem;}}
    .quote-text{{font-size:1.05rem;font-style:italic;color:{COLORS['text']};line-height:1.6;}}
    .quote-author{{font-size:0.78rem;color:{COLORS['accent']};margin-top:0.4rem;font-family:'Space Mono',monospace;}}
    .badge-pass{{display:inline-block;background:rgba(0,230,118,0.15);color:{COLORS['green']};border:1px solid rgba(0,230,118,0.3);border-radius:20px;padding:2px 12px;font-size:0.75rem;font-weight:700;}}
    .badge-fail{{display:inline-block;background:rgba(255,23,68,0.15);color:{COLORS['red']};border:1px solid rgba(255,23,68,0.3);border-radius:20px;padding:2px 12px;font-size:0.75rem;font-weight:700;}}
    .streak-box{{background:linear-gradient(135deg,rgba(124,58,237,0.2),rgba(0,212,255,0.1));border:1px solid rgba(124,58,237,0.4);border-radius:12px;padding:1.2rem;text-align:center;margin-bottom:0.8rem;}}
    .streak-num{{font-family:'Bebas Neue',sans-serif;font-size:3.5rem;color:{COLORS['accent']};line-height:1;}}
    .streak-label{{font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;color:{COLORS['dim']};}}
    .trade-row{{background:{COLORS['bg_card']};border:1px solid {COLORS['border']};border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;}}
    .stTextInput input,.stNumberInput input,.stSelectbox select,.stDateInput input,.stTextArea textarea{{background:#0d1627!important;border:1px solid {COLORS['border']}!important;color:{COLORS['text']}!important;border-radius:8px!important;}}
    .stCheckbox label{{color:{COLORS['text']}!important;}}
    .stButton>button{{background:linear-gradient(135deg,{COLORS['accent2']},#5b21b6)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;}}
    .alert-green{{background:rgba(0,230,118,0.08);border:1px solid rgba(0,230,118,0.25);border-radius:8px;padding:0.8rem 1rem;color:{COLORS['green']};margin-bottom:0.5rem;}}
    .alert-red{{background:rgba(255,23,68,0.08);border:1px solid rgba(255,23,68,0.25);border-radius:8px;padding:0.8rem 1rem;color:{COLORS['red']};margin-bottom:0.5rem;}}
    .alert-blue{{background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);border-radius:8px;padding:0.8rem 1rem;color:{COLORS['accent']};margin-bottom:0.5rem;}}
    hr{{border-color:{COLORS['border']}!important;}}
    ::-webkit-scrollbar{{width:5px;height:5px;}}
    ::-webkit-scrollbar-track{{background:{COLORS['bg_dark']};}}
    ::-webkit-scrollbar-thumb{{background:{COLORS['border']};border-radius:3px;}}
    #MainMenu,footer,[data-testid="stDecoration"]{{visibility:hidden;}}
    [data-testid="stHeader"]{{background:transparent;}}
    </style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────
def metric_card(label, value, delta="", color=""):
    cs = f"color:{color};" if color else ""
    st.markdown(f"""<div class="metric-card">
        <div class="label">{label}</div>
        <div class="value" style="{cs}">{value}</div>
        {"<div class='delta'>"+delta+"</div>" if delta else ""}
    </div>""", unsafe_allow_html=True)

def section_header(title, sub=""):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="section-sub">{sub}</div>', unsafe_allow_html=True)

def quote_card():
    q, a = random.choice(DISCIPLINE_QUOTES)
    st.markdown(f"""<div class="quote-card">
        <div class="quote-text">"{q}"</div>
        <div class="quote-author">{a}</div>
    </div>""", unsafe_allow_html=True)

def dark_layout(fig, title="", height=320):
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

    quote_card()
    section_header("PERFORMANCE OVERVIEW", "Real-time trading metrics")

    net_pnl  = trades["pnl"].sum() if not trades.empty else 0
    wins     = int((trades["pnl"] > 0).sum()) if not trades.empty else 0
    total_tr = len(trades)
    win_rate = round(wins / total_tr * 100, 1) if total_tr else 0
    comp     = round(trades["rule_score"].mean(), 1) if not trades.empty else 0
    ext_flow = acct_df["amount"].sum() if not acct_df.empty else 0
    equity   = net_pnl + ext_flow

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: metric_card("NET PnL",      f"${net_pnl:+,.2f}", "",                  pnl_color(net_pnl))
    with c2: metric_card("WIN RATE",     f"{win_rate}%",       f"{wins}W / {total_tr-wins}L")
    with c3: metric_card("TOTAL TRADES", str(total_tr),         "all time")
    with c4: metric_card("RULE SCORE",   f"{comp}%",            "avg compliance")
    with c5: metric_card("ACCOUNT P&L",  f"${equity:+,.2f}",   "trading + flows",   pnl_color(equity))

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        st.markdown(f"""<div class="streak-box">
            <div class="streak-label">FIRE Current Streak</div>
            <div class="streak-num">{streak}</div>
            <div class="streak-label">disciplined days</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="streak-box" style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(15,22,41,0.9))">
            <div class="streak-label">TROPHY Best Streak</div>
            <div class="streak-num" style="color:{COLORS['yellow']}">{best_streak}</div>
            <div class="streak-label">days ever</div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        if streak == 0:
            st.markdown('<div class="alert-red">⚠️ <b>Discipline streak broken.</b> Reset your mindset and start fresh today.</div>', unsafe_allow_html=True)
        elif streak >= 5:
            st.markdown(f'<div class="alert-green">🔥 <b>Excellent!</b> {streak}-day streak. You are building consistency.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-blue">✅ <b>Keep going!</b> {streak}-day streak. Aim for 5+ consecutive sessions.</div>', unsafe_allow_html=True)

        today     = date.today().isoformat()
        today_df  = trades[trades["trade_date"].dt.date.astype(str) == today] if not trades.empty else pd.DataFrame()
        today_pnl = today_df["pnl"].sum() if not today_df.empty else 0
        max_loss  = settings.get("max_daily_loss", -200)
        tgt       = settings.get("target_daily_pnl", 500)
        if today_pnl <= max_loss:
            st.markdown('<div class="alert-red">STOP Daily loss limit hit! STOP TRADING.</div>', unsafe_allow_html=True)
        elif today_pnl >= tgt:
            st.markdown(f'<div class="alert-green">TARGET Daily target ${tgt:,.0f} reached! Consider stopping.</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c_left, c_right = st.columns([2, 1])
    with c_left:
        section_header("EQUITY CURVE")
        eq = get_equity_curve(trades, acct_df)
        if not eq.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=eq["date"], y=eq["equity"], mode="lines", name="Equity",
                line=dict(color=COLORS["accent"], width=2.5),
                fill="tozeroy", fillcolor="rgba(0,212,255,0.06)"
            ))
            fig.add_hline(y=0, line_dash="dot", line_color=COLORS["dim"], annotation_text="Breakeven")
            dark_layout(fig, height=300)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<div class="alert-blue">No trade data yet. Log your first trade!</div>', unsafe_allow_html=True)

    with c_right:
        section_header("TODAY")
        metric_card("TODAY PnL",    f"${today_pnl:+,.2f}", "", pnl_color(today_pnl))
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        metric_card("TODAY TRADES", str(len(today_df)) if not today_df.empty else "0")

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("RECENT TRADES")
    if not trades.empty:
        disp = trades.head(10)[["trade_date","symbol","direction","entry_price","exit_price","contracts","pnl","setup_type","rule_score","passed"]].copy()
        disp["trade_date"] = disp["trade_date"].dt.strftime("%Y-%m-%d")
        disp["pnl"]        = disp["pnl"].apply(lambda x: f"${x:+,.2f}")
        disp["rule_score"] = disp["rule_score"].apply(lambda x: f"{x:.0f}%")
        disp["passed"]     = disp["passed"].apply(lambda x: "PASS" if x else "FAIL")
        st.dataframe(disp.rename(columns={
            "trade_date":"Date","symbol":"Sym","direction":"Dir",
            "entry_price":"Entry","exit_price":"Exit","contracts":"Qty",
            "pnl":"PnL","setup_type":"Setup","rule_score":"Score","passed":"Status"
        }), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="alert-blue">No trades yet. Use Add Trade to get started.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: ADD TRADE
# ─────────────────────────────────────────────
def page_add_trade():
    section_header("LOG NEW TRADE", "Document every entry — discipline starts here")

    with st.form("trade_form", clear_on_submit=True):
        st.markdown("#### Trade Details")
        c1, c2, c3, c4 = st.columns(4)
        with c1: trade_date  = st.date_input("Date", value=date.today())
        with c2: symbol      = st.text_input("Symbol", value="MNQ")
        with c3: direction   = st.selectbox("Direction", ["Buy", "Sell"])
        with c4: contracts   = st.number_input("Contracts", min_value=1, max_value=100, value=1)

        c5, c6, c7, c8 = st.columns(4)
        with c5: entry_price = st.number_input("Entry Price", min_value=0.0, value=18000.0, step=0.25, format="%.2f")
        with c6: exit_price  = st.number_input("Exit Price",  min_value=0.0, value=18010.0, step=0.25, format="%.2f")
        with c7: timeframe   = st.selectbox("Timeframe", TIMEFRAMES, index=2)
        with c8: setup_type  = st.selectbox("Setup Type", SETUP_TYPES)

        auto_pnl = calc_pnl(direction, entry_price, exit_price, contracts)
        pc = pnl_color(auto_pnl)
        st.markdown(f"""<div class="metric-card" style="margin:0.5rem 0">
            <span class="label">AUTO-CALCULATED PnL</span>
            <span class="value" style="color:{pc};margin-left:1rem">${auto_pnl:+,.2f}</span>
            <span class="delta" style="margin-left:0.5rem">({contracts} contract{'s' if contracts > 1 else ''} · MNQ $0.50/tick)</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### ICT Rule Checklist")
        ci1, ci2, ci3, ci4, ci5 = st.columns(5)
        with ci1: liq   = st.checkbox("15m Liquidity Hunt")
        with ci2: eng   = st.checkbox("1m Engulfing")
        with ci3: kz    = st.checkbox("Killzone OK")
        with ci4: trend = st.checkbox("Trend Aligned")
        with ci5: rdef  = st.checkbox("Risk Defined")

        st.markdown("#### Discipline Checklist")
        cd1, cd2, cd3, cd4 = st.columns(4)
        with cd1: no_rev = st.checkbox("No Revenge Trade")
        with cd2: fol_sl = st.checkbox("Followed SL")
        with cd3: fol_pl = st.checkbox("Followed Plan")
        with cd4: no_emo = st.checkbox("No Emotional Entry")

        raw = {
            "liquidity_hunt": liq, "engulf_confirm": eng, "killzone": kz,
            "trend_align": trend, "risk_defined": rdef, "no_revenge": no_rev,
            "followed_sl": fol_sl, "followed_plan": fol_pl, "no_emotion": no_emo
        }
        ls, lp = calc_rule_score(raw)
        sc = COLORS["green"] if lp else COLORS["red"]
        badge_cls = "pass" if lp else "fail"
        badge_txt = "PASS" if lp else "FAIL"
        st.markdown(f"""<div style="display:flex;align-items:center;gap:1rem;margin:0.5rem 0 1rem 0">
            <span style="font-size:0.85rem;color:{COLORS['dim']}">RULE COMPLIANCE</span>
            <span style="font-family:'Space Mono',monospace;font-size:1.4rem;font-weight:700;color:{sc}">{ls}%</span>
            <span class="badge-{badge_cls}">{badge_txt}</span>
        </div>""", unsafe_allow_html=True)

        notes  = st.text_area("Notes / Lessons", height=90)
        ss     = st.file_uploader("Screenshot (optional)", type=["png","jpg","jpeg","webp"])
        submit = st.form_submit_button("SAVE TRADE", use_container_width=True)

    if submit:
        ss_b64 = base64.b64encode(ss.read()).decode() if ss else None
        save_trade({
            "trade_date": trade_date.isoformat(), "symbol": symbol.upper(), "direction": direction,
            "entry_price": entry_price, "exit_price": exit_price, "contracts": contracts, "pnl": auto_pnl,
            "timeframe": timeframe, "setup_type": setup_type, "notes": notes, "screenshot": ss_b64,
            "liquidity_hunt": int(liq), "engulf_confirm": int(eng), "killzone": int(kz),
            "trend_align": int(trend), "risk_defined": int(rdef), "no_revenge": int(no_rev),
            "followed_sl": int(fol_sl), "followed_plan": int(fol_pl), "no_emotion": int(no_emo),
            "rule_score": ls, "passed": int(lp),
        })
        if lp:
            st.success(f"Trade logged! Score: {ls}% — PASS")
        else:
            st.warning(f"Trade logged. Score: {ls}% — FAIL. Review your rules.")

    st.markdown("---")
    section_header("TRADE LOG")
    trades = load_trades()
    if not trades.empty:
        for _, row in trades.head(20).iterrows():
            pc = pnl_color(row["pnl"])
            dir_color = COLORS["green"] if row["direction"] == "Buy" else COLORS["red"]
            badge_cls = "pass" if row["passed"] else "fail"
            badge_txt = "PASS" if row["passed"] else "FAIL"
            st.markdown(f"""<div class="trade-row">
                <span style="color:{COLORS['dim']};font-size:0.8rem;min-width:90px">{row['trade_date'].strftime('%Y-%m-%d')}</span>
                <span style="font-weight:600;min-width:50px">{row['symbol']}</span>
                <span style="color:{dir_color};min-width:40px">{row['direction']}</span>
                <span style="color:{COLORS['dim']};font-size:0.85rem;min-width:160px">{row['setup_type']}</span>
                <span style="font-family:'Space Mono',monospace;color:{pc};font-weight:700">${row['pnl']:+,.2f}</span>
                <span style="font-size:0.8rem;color:{COLORS['dim']}">{row['rule_score']:.0f}%</span>
                <span class="badge-{badge_cls}" style="margin-left:auto">{badge_txt}</span>
            </div>""", unsafe_allow_html=True)

        with st.expander("Delete a Trade"):
            del_id = st.number_input("Trade ID", min_value=1, step=1, key="del_trade")
            if st.button("Delete", key="del_trade_btn"):
                delete_trade(int(del_id))
                st.success(f"Trade #{del_id} deleted.")
                st.rerun()

# ─────────────────────────────────────────────
# PAGE: CALENDAR
# ─────────────────────────────────────────────
def page_calendar():
    section_header("PnL CALENDAR", "Heatmap of daily performance")
    trades = load_trades()
    cl_df  = load_daily_checklist()

    if trades.empty:
        st.markdown('<div class="alert-blue">No trade data yet.</div>', unsafe_allow_html=True)
        return

    trades["date_str"] = trades["trade_date"].dt.date
    daily = trades.groupby("date_str").agg(
        total_pnl=("pnl", "sum"), trade_count=("id", "count"), avg_score=("rule_score", "mean")
    ).reset_index()
    daily_dict = {str(r["date_str"]): r for _, r in daily.iterrows()}

    all_periods   = sorted(trades["trade_date"].dt.to_period("M").unique())
    month_options = [str(p) for p in all_periods]
    sel           = st.selectbox("Month", month_options[::-1])
    year, month   = int(sel.split("-")[0]), int(sel.split("-")[1])
    st.markdown(f"### {cal_module.month_name[month]} {year}")

    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    hcols = st.columns(7)
    for i, d in enumerate(day_names):
        hcols[i].markdown(
            f"<div style='text-align:center;color:{COLORS['dim']};font-size:0.8rem;font-weight:600;padding-bottom:4px'>{d}</div>",
            unsafe_allow_html=True
        )

    for week in cal_module.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='height:70px'></div>", unsafe_allow_html=True)
                    continue
                d_str = f"{year}-{month:02d}-{day:02d}"
                if d_str in daily_dict:
                    row   = daily_dict[d_str]
                    pnl   = row["total_pnl"]
                    color = COLORS["green"] if pnl >= 0 else COLORS["red"]
                    bg    = "rgba(0,230,118,0.2)" if pnl > 0 else ("rgba(255,23,68,0.2)" if pnl < 0 else "rgba(255,214,0,0.15)")
                    bdr   = "rgba(0,230,118,0.35)" if pnl > 0 else ("rgba(255,23,68,0.35)" if pnl < 0 else "rgba(255,214,0,0.3)")
                    st.markdown(f"""<div style="background:{bg};border:1px solid {bdr};border-radius:6px;padding:6px;text-align:center;">
                        <div style="font-weight:700">{day}</div>
                        <div style="font-size:0.65rem;font-weight:700;color:{color}">${pnl:+,.0f}</div>
                        <div style="font-size:0.6rem;color:{COLORS['dim']}">{row['trade_count']}T</div>
                    </div>""", unsafe_allow_html=True)
                    if st.button("View", key=f"c_{d_str}", use_container_width=True):
                        st.session_state["cal_sel"] = d_str
                else:
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid {COLORS['border']};border-radius:6px;padding:6px;text-align:center;color:{COLORS['dim']};">
                        <div style="font-weight:600">{day}</div>
                        <div style="font-size:0.6rem">—</div>
                    </div>""", unsafe_allow_html=True)

    if "cal_sel" in st.session_state:
        d_str = st.session_state["cal_sel"]
        st.markdown("---")
        section_header(f"TRADES — {d_str}")
        day_t = trades[trades["date_str"].astype(str) == d_str]
        if not day_t.empty:
            c1, c2, c3 = st.columns(3)
            dp = day_t["pnl"].sum()
            with c1: metric_card("Day PnL",   f"${dp:+,.2f}", "", pnl_color(dp))
            with c2: metric_card("Trades",    str(len(day_t)))
            with c3: metric_card("Avg Score", f"{day_t['rule_score'].mean():.1f}%")
            st.markdown("<br>", unsafe_allow_html=True)
            for _, r in day_t.iterrows():
                pc  = pnl_color(r["pnl"])
                dc  = COLORS["green"] if r["direction"] == "Buy" else COLORS["red"]
                bcl = "pass" if r["passed"] else "fail"
                btx = "PASS" if r["passed"] else "FAIL"
                st.markdown(f"""<div class="trade-row">
                    <b>{r['symbol']}</b>
                    <span style="color:{dc}">{r['direction']}</span>
                    <span>Entry: <b>{r['entry_price']}</b></span>
                    <span>Exit: <b>{r['exit_price']}</b></span>
                    <span style="font-family:'Space Mono',monospace;color:{pc};font-weight:700">${r['pnl']:+,.2f}</span>
                    <span class="badge-{bcl}" style="margin-left:auto">{btx}</span>
                </div>""", unsafe_allow_html=True)
                if r["notes"]:
                    st.markdown(f"<div style='color:{COLORS['dim']};font-size:0.82rem;padding:0.2rem 1rem 0.6rem'>Notes: {r['notes']}</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: DISCIPLINE
# ─────────────────────────────────────────────
def page_discipline():
    section_header("DAILY DISCIPLINE CHECK", "Complete every session")
    cl_df  = load_daily_checklist()
    today  = date.today().isoformat()
    streak, best_streak = get_streak(cl_df)
    already = not cl_df.empty and (cl_df["check_date"].dt.strftime("%Y-%m-%d") == today).any()

    if already:
        today_row = cl_df[cl_df["check_date"].dt.strftime("%Y-%m-%d") == today].iloc[0]
        ds = today_row["discipline_score"]
        cls = "green" if ds >= 75 else "red"
        st.markdown(f'<div class="alert-{cls}">Today\'s checklist done! Discipline Score: {ds:.0f}%</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.form("daily_check", clear_on_submit=False):
            st.markdown(f"#### {today}")
            fr    = st.checkbox("I followed my trading rules today")
            nr    = st.checkbox("I did NOT take revenge trades")
            rr    = st.checkbox("I respected risk management")
            no_ot = st.checkbox("I did NOT overtrade")
            live_ds = calc_discipline_score({"followed_rules": fr, "no_revenge": nr, "risk_respected": rr, "no_overtrade": no_ot})
            dsc = COLORS["green"] if live_ds >= 75 else COLORS["red"]
            st.markdown(f"""<div style="margin:1rem 0;padding:0.8rem;background:{COLORS['bg_card']};border-radius:8px;border:1px solid {COLORS['border']}">
                <span style="color:{COLORS['dim']};font-size:0.85rem">SCORE PREVIEW: </span>
                <span style="font-family:'Space Mono',monospace;font-size:1.3rem;font-weight:700;color:{dsc}">{live_ds:.0f}%</span>
            </div>""", unsafe_allow_html=True)
            notes  = st.text_area("Reflection...", height=90)
            submit = st.form_submit_button("SAVE CHECK", use_container_width=True)

        if submit:
            fs = calc_discipline_score({"followed_rules": fr, "no_revenge": nr, "risk_respected": rr, "no_overtrade": no_ot})
            save_daily_checklist({
                "check_date": today, "followed_rules": int(fr), "no_revenge": int(nr),
                "risk_respected": int(rr), "no_overtrade": int(no_ot), "notes": notes, "discipline_score": fs
            })
            if fs >= 75:
                st.success(f"{fs:.0f}% — Streak continues!")
            else:
                st.warning(f"{fs:.0f}% — Streak reset. Review your habits.")
            st.rerun()

    with c2:
        st.markdown(f"""<div class="streak-box">
            <div class="streak-label">Current Streak</div>
            <div class="streak-num">{streak}</div>
            <div class="streak-label">days</div>
        </div>
        <div class="streak-box">
            <div class="streak-label">Best Ever</div>
            <div class="streak-num" style="color:{COLORS['yellow']}">{best_streak}</div>
            <div class="streak-label">days</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    section_header("DISCIPLINE HISTORY")
    if not cl_df.empty:
        recent = cl_df.head(14).copy()
        dates  = recent["check_date"].dt.strftime("%m/%d").tolist()[::-1]
        scores = recent["discipline_score"].tolist()[::-1]
        colors = [COLORS["green"] if s >= 75 else COLORS["red"] for s in scores]
        fig = go.Figure(go.Bar(x=dates, y=scores, marker_color=colors, marker_line_width=0))
        fig.add_hline(y=75, line_dash="dot", line_color=COLORS["yellow"], annotation_text="Pass (75%)")
        dark_layout(fig, "14-Day Discipline", 260)
        fig.update_layout(yaxis=dict(range=[0, 105]))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────
# PAGE: ACCOUNT
# ─────────────────────────────────────────────
def page_account():
    section_header("ACCOUNT MANAGEMENT", "Capital flows and equity tracking")
    settings = load_settings()
    trades   = load_trades()
    acct_df  = load_account()

    net_trade_pnl = trades["pnl"].sum() if not trades.empty else 0
    ext_flow      = acct_df["amount"].sum() if not acct_df.empty else 0
    equity        = net_trade_pnl + ext_flow

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("TRADING PnL",    f"${net_trade_pnl:+,.2f}", "", pnl_color(net_trade_pnl))
    with c2: metric_card("EXTERNAL FLOWS", f"${ext_flow:+,.2f}",      "deposits/payouts")
    with c3: metric_card("NET EQUITY",     f"${equity:+,.2f}",         "", pnl_color(equity))
    with c4: metric_card("TOTAL TRADES",   str(len(trades)))

    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1, 2])
    with c_left:
        st.markdown("#### Settings")
        acc_name = st.text_input("Account Name", value=settings.get("account_name", ""))
        tgt_pnl  = st.number_input("Daily Target ($)", value=float(settings.get("target_daily_pnl", 500)), step=50.0)
        max_loss = st.number_input("Max Daily Loss ($)", value=float(settings.get("max_daily_loss", -200)), step=50.0)
        if st.button("Save Settings"):
            settings.update({"account_name": acc_name, "target_daily_pnl": tgt_pnl, "max_daily_loss": max_loss})
            save_settings(settings)
            st.success("Saved!")
        st.markdown("---")
        st.markdown("#### Log Transaction")
        ev_date   = st.date_input("Date", value=date.today(), key="acct_d")
        ev_type   = st.selectbox("Type", ["Deposit","Withdrawal","Payout","Funded Account"])
        ev_amount = st.number_input("Amount ($)", value=0.0, step=100.0)
        ev_notes  = st.text_input("Notes", key="acct_n")
        if st.button("Add Transaction"):
            sign = 1 if ev_type in ["Deposit","Funded Account"] else -1
            save_account_event({"event_date": ev_date.isoformat(), "event_type": ev_type, "amount": sign * abs(ev_amount), "notes": ev_notes})
            st.success("Transaction saved!")
            st.rerun()

    with c_right:
        eq = get_equity_curve(trades, acct_df)
        if not eq.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=eq["date"], y=eq["equity"], mode="lines+markers", name="Equity",
                line=dict(color=COLORS["accent"], width=2.5),
                fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
                marker=dict(size=5, color=COLORS["accent"])
            ))
            fig.add_hline(y=0, line_dash="dot", line_color=COLORS["dim"], annotation_text="Zero")
            dark_layout(fig, "Account Equity Curve", 320)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        if not acct_df.empty:
            st.markdown("##### Transaction History")
            st.dataframe(
                acct_df[["event_date","event_type","amount","notes"]].rename(
                    columns={"event_date":"Date","event_type":"Type","amount":"Amount","notes":"Notes"}
                ), use_container_width=True, hide_index=True
            )

# ─────────────────────────────────────────────
# PAGE: EXPENSES & INCOME
# ─────────────────────────────────────────────
def page_expenses():
    section_header("EXPENSES & INCOME", "Track all trading-related costs and non-trade income")
    exp_df = load_expenses()

    total_income  = exp_df[exp_df["entry_type"] == "Income"]["amount"].sum()  if not exp_df.empty else 0
    total_expense = exp_df[exp_df["entry_type"] == "Expense"]["amount"].sum() if not exp_df.empty else 0
    net           = total_income - total_expense

    c1, c2, c3 = st.columns(3)
    with c1: metric_card("TOTAL INCOME",   f"${total_income:,.2f}",  "", COLORS["green"])
    with c2: metric_card("TOTAL EXPENSES", f"${total_expense:,.2f}", "", COLORS["red"])
    with c3: metric_card("NET",            f"${net:+,.2f}",           "", pnl_color(net))

    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1, 2])

    with c_left:
        st.markdown("#### Add Entry")
        with st.form("exp_form", clear_on_submit=True):
            entry_date  = st.date_input("Date", value=date.today())
            entry_type  = st.selectbox("Type", ["Expense", "Income"])
            cat_options = EXPENSE_CATEGORIES if entry_type == "Expense" else INCOME_CATEGORIES
            category    = st.selectbox("Category", cat_options)
            amount      = st.number_input("Amount ($)", min_value=0.01, value=10.0, step=1.0, format="%.2f")
            description = st.text_input("Description")
            submitted   = st.form_submit_button("SAVE ENTRY", use_container_width=True)

        if submitted:
            save_expense({
                "entry_date":  entry_date.isoformat(),
                "entry_type":  entry_type,
                "category":    category,
                "amount":      amount,
                "description": description,
            })
            st.success(f"{entry_type} of ${amount:.2f} saved!")
            st.rerun()

        if not exp_df.empty:
            st.markdown("---")
            with st.expander("Delete Entry"):
                del_id = st.number_input("Entry ID", min_value=1, step=1, key="del_exp")
                if st.button("Delete", key="del_exp_btn"):
                    delete_expense(int(del_id))
                    st.success("Deleted.")
                    st.rerun()

    with c_right:
        if not exp_df.empty:
            inc_df = exp_df[exp_df["entry_type"] == "Income"]
            exd_df = exp_df[exp_df["entry_type"] == "Expense"]

            r1c1, r1c2 = st.columns(2)
            with r1c1:
                if not exd_df.empty:
                    cat_exp = exd_df.groupby("category")["amount"].sum().reset_index()
                    fig = go.Figure(go.Pie(
                        labels=cat_exp["category"], values=cat_exp["amount"],
                        hole=0.55,
                        marker_colors=["#ff1744","#ff4569","#ff616f","#ff8a80","#ffcdd2","#b71c1c","#d32f2f"][:len(cat_exp)],
                        textinfo="label+percent"
                    ))
                    dark_layout(fig, "Expenses by Category", 260)
                    fig.update_traces(textfont_color=COLORS["text"])
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with r1c2:
                if not inc_df.empty:
                    cat_inc = inc_df.groupby("category")["amount"].sum().reset_index()
                    fig = go.Figure(go.Pie(
                        labels=cat_inc["category"], values=cat_inc["amount"],
                        hole=0.55,
                        marker_colors=["#00e676","#69f0ae","#b9f6ca","#00c853","#1b5e20","#2e7d32","#388e3c"][:len(cat_inc)],
                        textinfo="label+percent"
                    ))
                    dark_layout(fig, "Income by Category", 260)
                    fig.update_traces(textfont_color=COLORS["text"])
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            exp_df["month"] = exp_df["entry_date"].dt.to_period("M").astype(str)
            monthly_inc = exp_df[exp_df["entry_type"] == "Income"].groupby("month")["amount"].sum()
            monthly_exp = exp_df[exp_df["entry_type"] == "Expense"].groupby("month")["amount"].sum()
            all_months  = sorted(set(monthly_inc.index.tolist() + monthly_exp.index.tolist()))
            fig = go.Figure()
            fig.add_trace(go.Bar(x=all_months, y=[monthly_inc.get(m, 0) for m in all_months],  name="Income",  marker_color=COLORS["green"], marker_line_width=0))
            fig.add_trace(go.Bar(x=all_months, y=[-monthly_exp.get(m, 0) for m in all_months], name="Expense", marker_color=COLORS["red"],   marker_line_width=0))
            dark_layout(fig, "Monthly Income vs Expenses", 260)
            fig.update_layout(barmode="relative")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            st.markdown("##### All Entries")
            disp = exp_df[["id","entry_date","entry_type","category","amount","description"]].copy()
            disp["entry_date"] = disp["entry_date"].dt.strftime("%Y-%m-%d")
            disp["amount"]     = disp["amount"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(disp.rename(columns={
                "id":"ID","entry_date":"Date","entry_type":"Type",
                "category":"Category","amount":"Amount","description":"Description"
            }), use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="alert-blue">No entries yet. Add your first expense or income above.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: ANALYTICS
# ─────────────────────────────────────────────
def page_analytics():
    section_header("ANALYTICS DASHBOARD", "Deep performance insights")
    trades = load_trades()

    if trades.empty:
        st.markdown('<div class="alert-blue">No trade data yet.</div>', unsafe_allow_html=True)
        return

    total  = len(trades)
    wins   = int((trades["pnl"] > 0).sum())
    losses = int((trades["pnl"] < 0).sum())
    wr     = round(wins / total * 100, 1)
    net    = trades["pnl"].sum()
    avg_w  = trades[trades["pnl"] > 0]["pnl"].mean() if wins   else 0
    avg_l  = abs(trades[trades["pnl"] < 0]["pnl"].mean()) if losses else 0
    rr     = round(avg_w / avg_l, 2) if avg_l else 0
    comp   = round(trades["rule_score"].mean(), 1)
    pass_r = round(trades["passed"].mean() * 100, 1)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: metric_card("TOTAL TRADES", str(total))
    with c2: metric_card("WIN RATE",     f"{wr}%",          f"{wins}W/{losses}L")
    with c3: metric_card("NET PnL",      f"${net:+,.2f}",   "", pnl_color(net))
    with c4: metric_card("AVG R:R",      f"{rr:.2f}",       f"W:{avg_w:.0f}/L:{avg_l:.0f}")
    with c5: metric_card("RULE SCORE",   f"{comp:.1f}%")
    with c6: metric_card("PASS RATE",    f"{pass_r}%")

    st.markdown("<br>", unsafe_allow_html=True)

    r1c1, r1c2 = st.columns(2)
    with r1c1:
        trades["month"] = trades["trade_date"].dt.to_period("M").astype(str)
        monthly = trades.groupby("month")["pnl"].sum().reset_index()
        colors  = [COLORS["green"] if v >= 0 else COLORS["red"] for v in monthly["pnl"]]
        fig = go.Figure(go.Bar(x=monthly["month"], y=monthly["pnl"], marker_color=colors, marker_line_width=0))
        dark_layout(fig, "Monthly PnL", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with r1c2:
        sp = trades.groupby("setup_type").agg(
            total_pnl=("pnl", "sum"),
            count=("id", "count"),
            win_rate=("pnl", lambda x: (x > 0).mean() * 100)
        ).reset_index().sort_values("total_pnl", ascending=True)
        colors_s = [COLORS["green"] if v >= 0 else COLORS["red"] for v in sp["total_pnl"]]
        fig = go.Figure(go.Bar(
            x=sp["total_pnl"], y=sp["setup_type"], orientation="h",
            marker_color=colors_s, marker_line_width=0,
            text=sp["count"].apply(lambda x: f"{x}T"), textposition="outside"
        ))
        dark_layout(fig, "PnL by Setup", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        fig = go.Figure(go.Histogram(
            x=trades["pnl"], nbinsx=30,
            marker_color=COLORS["accent2"],
            marker_line_color=COLORS["bg_dark"], marker_line_width=0.5
        ))
        fig.add_vline(x=0, line_color=COLORS["yellow"], line_dash="dot")
        dark_layout(fig, "PnL Distribution", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with r2c2:
        ts = trades.sort_values("trade_date")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts["trade_date"], y=ts["rule_score"].rolling(5, min_periods=1).mean(),
            mode="lines", name="5-Trade MA", line=dict(color=COLORS["accent"], width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=ts["trade_date"], y=ts["rule_score"], mode="markers", name="Per Trade",
            marker=dict(color=[COLORS["green"] if p else COLORS["red"] for p in ts["passed"]], size=6)
        ))
        fig.add_hline(y=70, line_dash="dot", line_color=COLORS["yellow"], annotation_text="Pass (70%)")
        dark_layout(fig, "Rule Compliance Trend", 280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    r3c1, r3c2 = st.columns(2)
    with r3c1:
        be  = total - wins - losses
        fig = go.Figure(go.Pie(
            labels=["Wins","Losses","Breakeven"],
            values=[wins, losses, be],
            marker_colors=[COLORS["green"], COLORS["red"], COLORS["yellow"]],
            hole=0.6, textinfo="label+percent"
        ))
        dark_layout(fig, "Win / Loss / BE", 280)
        fig.update_traces(textfont_color=COLORS["text"])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with r3c2:
        setup_wr = trades.groupby("setup_type").agg(
            wr=("pnl", lambda x: round((x > 0).mean() * 100, 1)),
            count=("id", "count")
        ).reset_index().sort_values("wr", ascending=False)

        bar_colors = [COLORS["green"] if v >= 50 else COLORS["red"] for v in setup_wr["wr"]]
        fig = go.Figure(go.Bar(
            x=setup_wr["setup_type"], y=setup_wr["wr"],
            marker_color=bar_colors, marker_line_width=0,
            text=setup_wr["wr"].apply(lambda x: f"{x:.0f}%"),
            textposition="outside"
        ))
        fig.add_hline(y=50, line_dash="dot", line_color=COLORS["yellow"])
        dark_layout(fig, "Win Rate by Setup", 280)
        # FIXED: use update_layout instead of update_yaxis
        fig.update_layout(yaxis=dict(range=[0, 110]))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("---")
    ca, cb = st.columns(2)
    with ca:
        section_header("BEST PATTERNS")
        best = sp.sort_values("total_pnl", ascending=False).head(3)
        for _, row in best.iterrows():
            st.markdown(f"""<div class="trade-row">
                <span style="font-weight:600">{row['setup_type']}</span>
                <span style="font-family:'Space Mono',monospace;color:{pnl_color(row['total_pnl'])}">${row['total_pnl']:+,.0f}</span>
                <span style="color:{COLORS['dim']}">{row['count']} trades · {row['win_rate']:.0f}% WR</span>
            </div>""", unsafe_allow_html=True)
    with cb:
        section_header("MISTAKE PATTERNS")
        worst = sp.sort_values("total_pnl").head(3)
        for _, row in worst.iterrows():
            st.markdown(f"""<div class="trade-row">
                <span style="font-weight:600">{row['setup_type']}</span>
                <span style="font-family:'Space Mono',monospace;color:{pnl_color(row['total_pnl'])}">${row['total_pnl']:+,.0f}</span>
                <span style="color:{COLORS['dim']}">{row['count']} trades · {row['win_rate']:.0f}% WR</span>
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""<div style="padding:1.2rem 0 0.5rem 0;text-align:center">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:{COLORS['accent']};letter-spacing:0.12em">MNQ JOURNAL</div>
            <div style="font-size:0.72rem;color:{COLORS['dim']};letter-spacing:0.15em;margin-top:-2px">PROP TRADER · DISCIPLINE SYSTEM</div>
        </div>
        <hr style="border-color:{COLORS['border']};margin:0.5rem 0 1rem 0">""", unsafe_allow_html=True)

        pages = {
            "Dashboard":         "dashboard",
            "Add Trade":         "add_trade",
            "Calendar":          "calendar",
            "Discipline Check":  "discipline",
            "Account":           "account",
            "Expenses & Income": "expenses",
            "Analytics":         "analytics",
        }

        if "page" not in st.session_state:
            st.session_state["page"] = "dashboard"

        for label, key in pages.items():
            is_active = st.session_state["page"] == key
            if st.button(label, key=f"nav_{key}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state["page"] = key
                st.rerun()

        st.markdown(f"<hr style='border-color:{COLORS['border']};margin:1rem 0'>", unsafe_allow_html=True)

        trades = load_trades()
        if not trades.empty:
            today_str = date.today().isoformat()
            today_t   = trades[trades["trade_date"].dt.date.astype(str) == today_str]
            today_pnl = today_t["pnl"].sum()
            pc = COLORS["green"] if today_pnl >= 0 else COLORS["red"]
            st.markdown(f"""<div style="padding:0 0.5rem">
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:{COLORS['dim']};margin-bottom:6px">TODAY</div>
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="color:{COLORS['dim']};font-size:0.82rem">PnL</span>
                    <span style="font-family:'Space Mono',monospace;font-size:0.82rem;color:{pc};font-weight:700">${today_pnl:+,.2f}</span>
                </div>
                <div style="display:flex;justify-content:space-between">
                    <span style="color:{COLORS['dim']};font-size:0.82rem">Trades</span>
                    <span style="font-size:0.82rem;color:{COLORS['text']}">{len(today_t)}</span>
                </div>
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="MNQ Trading Journal",
        page_icon="chart_with_upwards_trend",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_css()
    init_db()
    render_sidebar()

    page = st.session_state.get("page", "dashboard")
    if   page == "dashboard":  page_dashboard()
    elif page == "add_trade":  page_add_trade()
    elif page == "calendar":   page_calendar()
    elif page == "discipline": page_discipline()
    elif page == "account":    page_account()
    elif page == "expenses":   page_expenses()
    elif page == "analytics":  page_analytics()

if __name__ == "__main__":
    main()

