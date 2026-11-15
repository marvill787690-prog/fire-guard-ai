from __future__ import annotations

import copy
import hashlib
import html
import inspect
import json
import math
import time
from datetime import date

import pandas as pd
import streamlit as st

# ============================================================
# 머니체크 v7 | 누구나 쉽게 쓰는 가계 재무진단
# - 재무 계산은 규칙 기반(직접 계산), 설명은 선택적으로 Gemini AI 코치가 도와줘요.
# - 모든 금액 단위: 만원
# ============================================================

st.set_page_config(
    page_title="머니체크 | 내 돈을 쉽게 이해하기",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit 버전별 width 옵션 호환 (use_container_width → width="stretch")
def _full(fn) -> dict:
    try:
        return {"width": "stretch"} if "width" in inspect.signature(fn).parameters else {"use_container_width": True}
    except Exception:  # noqa: BLE001
        return {"use_container_width": True}


FULL = _full(st.button)
FULL_DL = _full(st.download_button)
FULL_DF = _full(st.dataframe)
FULL_ALT = _full(st.altair_chart)


# ============================================================
# 1. 디자인 (읽기 쉽고 단순하게)
# ============================================================
st.markdown(
    """
    <style>
      @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
      :root{ --ink:#14213d; --sub:#475467; --mute:#667085; --line:#e4e7ec; --brand:#0f766e; --navy:#17324d; }
      html{ font-size:17px; }
      .stApp{ font-family:'Pretendard',-apple-system,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif; }
      .block-container{ max-width:1020px; padding-top:1.2rem; padding-bottom:4rem; }
      h1,h2,h3,h4{ letter-spacing:-.025em; color:var(--ink); }
      [data-testid="stWidgetLabel"] p{ font-size:1rem; font-weight:600; color:var(--ink); }
      [data-testid="stSidebar"]{ background:#f6f8fb; border-right:1px solid var(--line); }
      [data-testid="stSidebar"] [role="radiogroup"] label{ padding:10px 12px; border-radius:11px; margin-bottom:3px; width:100%; }
      [data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:#e8f1f0; }
      .brand{ font-size:1.3rem; font-weight:800; color:var(--navy); }
      .brand-sub{ color:var(--mute); font-size:.82rem; margin:-2px 0 12px 0; }

      .hero{ background:linear-gradient(120deg,#17324d 0%,#0f766e 100%); color:#fff; border-radius:18px; padding:24px 28px; margin:0 0 18px 0; }
      .hero h1{ color:#fff; font-size:1.7rem; line-height:1.35; margin:0 0 6px 0; }
      .hero p{ color:#eaf7f5; margin:0; font-size:1rem; line-height:1.65; }

      .kpi{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px 16px; height:100%; }
      .kpi-l{ color:var(--mute); font-size:.85rem; font-weight:600; margin-bottom:4px; }
      .kpi-v{ color:var(--ink); font-size:1.45rem; font-weight:800; letter-spacing:-.03em; line-height:1.25; }
      .kpi-s{ color:var(--mute); font-size:.8rem; margin-top:4px; line-height:1.45; }

      .card{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:18px 20px; height:100%; }
      .card h4{ margin:0 0 6px 0; font-size:1.05rem; }
      .card p{ margin:0; color:var(--sub); font-size:.95rem; line-height:1.65; }
      .card .step{ color:var(--brand); font-weight:800; font-size:.76rem; letter-spacing:.06em; margin-bottom:4px; }
      .callout{ border-radius:14px; padding:14px 16px; line-height:1.7; font-size:.97rem; margin:8px 0; }
      .callout b.t{ display:block; margin-bottom:2px; }
      .tiny{ color:var(--mute); font-size:.82rem; line-height:1.55; }

      /* 예시 카드: 세 장이 항상 같은 높이로 정렬되도록 칸 높이를 고정 */
      .demo-tag{ color:var(--brand); font-size:.76rem; font-weight:800; letter-spacing:.04em; }
      .demo-t{ font-size:1.12rem; font-weight:800; color:var(--ink); margin:2px 0 6px 0; white-space:nowrap; }
      .demo-d{ color:var(--sub); font-size:.92rem; line-height:1.6; min-height:6.6em; }

      /* 신호등 카드 */
      .check{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:15px 18px; margin:10px 0; }
      .check-t{ color:var(--mute); font-size:.85rem; font-weight:700; }
      .check-h{ color:var(--ink); font-size:1.2rem; font-weight:800; margin:2px 0 6px 0; line-height:1.4; }
      .check-m{ color:var(--sub); font-size:.95rem; line-height:1.65; }
      .check-a{ margin-top:8px; padding:9px 12px; background:#f8fafc; border-radius:10px; color:var(--ink); font-size:.93rem; line-height:1.6; }
      .check details{ margin-top:8px; color:var(--mute); font-size:.82rem; line-height:1.55; }
      .check summary{ cursor:pointer; font-weight:600; }

      .overall{ border-radius:16px; padding:18px 22px; margin:0 0 14px 0; }
      .overall .o-row{ display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; }
      .overall .o-t{ font-size:1.25rem; font-weight:800; margin-bottom:4px; }
      .overall .o-s{ font-size:.95rem; line-height:1.7; color:#1d2939; }
      .overall .o-score{ text-align:center; min-width:90px; }
      .overall .o-score b{ display:block; font-size:2.3rem; font-weight:800; line-height:1.1; letter-spacing:-.03em; }
      .overall .o-score span{ color:var(--mute); font-size:.75rem; }

      div[data-testid="stExpander"]{ border:1px solid var(--line); border-radius:13px; background:#fff; }
      div.stButton > button, div[data-testid="stDownloadButton"] button{ border-radius:11px; min-height:2.8rem; font-weight:650; }
      button[data-baseweb="tab"]{ font-weight:650; font-size:.98rem; }
      /* 자동 계산 칸(잠금)은 회색으로 */
      input:disabled{ background:#f2f4f7 !important; color:#14213d !important; -webkit-text-fill-color:#14213d !important; font-weight:700; }
      @media (max-width:720px){ .hero{padding:18px;} .hero h1{font-size:1.4rem;} .demo-d{min-height:0;} }
    </style>
    """,
    unsafe_allow_html=True,
)

# 신호등은 오직 빨강(bad)·노랑(warn)·초록(ok) 세 가지. info/neutral은 신호등이 아닌 일반 안내용(청록·회색).
TONES = {  # (글자색, 배경색, 테두리색)
    "ok": ("#166534", "#f0fdf4", "#86efac"),
    "warn": ("#854d0e", "#fefce8", "#fde047"),
    "bad": ("#b91c1c", "#fef2f2", "#fca5a5"),
    "info": ("#0f766e", "#f0faf8", "#99d5cf"),
    "neutral": ("#344054", "#f2f4f7", "#d0d5dd"),
}
BAR = {"ok": "#16a34a", "warn": "#eab308", "bad": "#dc2626", "info": "#0f766e", "neutral": "#98a2b3"}
TONE_EMOJI = {"ok": "🟢", "warn": "🟡", "bad": "🔴", "info": "💡", "neutral": "⚪"}
TONE_ORDER = {"bad": 0, "warn": 1, "info": 2, "ok": 3, "neutral": 4}
TONE_SCORE = {"ok": 100, "warn": 55, "bad": 15}
NAVY = "#17324d"


def esc(x) -> str:
    return html.escape(str(x))


def kpi(label, value, sub="", tone="neutral") -> str:
    return (f'<div class="kpi" style="border-top:4px solid {BAR[tone]}"><div class="kpi-l">{esc(label)}</div>'
            f'<div class="kpi-v">{esc(value)}</div><div class="kpi-s">{esc(sub)}</div></div>')


def kpi_row(items):
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        col.markdown(kpi(*it), unsafe_allow_html=True)


def callout(body_html: str, tone="info", title: str | None = None):
    fg, bg, bd = TONES[tone]
    head = f'<b class="t" style="color:{fg}">{esc(title)}</b>' if title else ""
    st.markdown(f'<div class="callout" style="background:{bg};border:1px solid {bd};color:#1d2939">{head}{body_html}</div>',
                unsafe_allow_html=True)


def hero(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)


def section(title, subtitle=None):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def note(text):
    st.markdown(f'<div class="tiny">※ {esc(text)}</div>', unsafe_allow_html=True)


def show_df(df: pd.DataFrame):
    try:
        st.dataframe(df, hide_index=True, **FULL_DF)
    except TypeError:
        st.dataframe(df, hide_index=True)


# ============================================================
# 2. 숫자 표기
# ============================================================
def won(v) -> str:
    """만원 단위 값을 '1억 2,000만 원'처럼 읽기 쉽게."""
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "계산할 수 없음"
    v = float(v)
    sign = "−" if v < 0 else ""
    a = abs(v)
    if a >= 10000:
        n = int(round(a))
        eok, rest = divmod(n, 10000)
        return f"{sign}{eok:,}억 원" if rest == 0 else f"{sign}{eok:,}억 {rest:,}만 원"
    if abs(a - round(a)) >= 0.05:
        return f"{sign}{a:,.1f}만 원"
    return f"{sign}{int(round(a)):,}만 원"


def signed(v) -> str:
    """증감 표기: +2억 6,000만 원 / −1,000만 원"""
    if v is None or not math.isfinite(v) or abs(v) < 0.05:
        return "변화 없음"
    return ("+" if v > 0 else "") + won(v)


def pct(v, d=0) -> str:
    return "해당 없음" if v is None or not math.isfinite(v) else f"{v:.{d}f}%"


def ratio(n, d):
    return None if d is None or d <= 0 else n / d * 100


def fmt_months(v) -> str:
    if v is None:
        return "지출 입력 필요"
    return "계산할 수 없음" if not math.isfinite(v) else f"{v:.1f}개월"


def fmt_runway(liquid, runway) -> str:
    """현금·예금이 마이너스(부족)면 개월 수 대신 부족 금액을 보여줘요."""
    if liquid is not None and liquid < 0:
        return f"현금 {won(-liquid)} 부족"
    return fmt_months(runway)


# ============================================================
# 3. 상태 관리
# ============================================================
GOALS = ["전반적인 재무 점검", "비상자금 마련", "빚 갚기", "결혼 자금", "내 집 마련", "자녀 교육비", "은퇴 준비", "자산 불리기"]
GOAL_EMERGENCY = "비상자금 마련"
KNOW = ["있어요", "없어요", "잘 모르겠어요"]
STEPS = ["① 자산", "② 부채", "③ 월 수입·지출", "④ 목표·예정"]
EXP_SIMPLE, EXP_DETAIL = "간단히 (한 칸)", "항목별로 자세히"
PAY_AUTO, PAY_MANUAL = "자동 계산 (연 5%·5년 상환 가정)", "직접 입력"
MONTHLY_KEYS = ["income", "rent_income", "other_income", "expense_total", "living_cost", "insurance_premium",
                "other_fixed", "irregular_monthly", "other_payment"]

DEFAULTS = {
    "goal": GOALS[0], "years": 3, "target": 0.0, "already_saved": 0.0,
    # 자산
    "cash": 0.0, "deposits": 0.0, "stocks": 0.0, "volatile": 0.0, "crypto": 0.0, "pension": 0.0,
    "property": 0.0, "other_assets": 0.0,
    # 부채
    "mortgage": 0.0, "credit": 0.0, "other_debt": 0.0, "deposits_owed": 0.0, "near_deposit": 0.0,
    "loan_rate": 4.0, "loan_years": 30.0, "pay_mode": PAY_AUTO, "other_payment": 0.0,
    # 월 수입·지출
    "income": 0.0, "rent_income": 0.0, "other_income": 0.0,
    "exp_mode": EXP_SIMPLE, "expense_total": 0.0,
    "living_cost": 0.0, "insurance_premium": 0.0, "other_fixed": 0.0, "irregular_monthly": 0.0,
    # 예정 지출
    "t1_name": "", "t1_amt": 0.0, "t1_years": 0.0, "t2_name": "", "t2_amt": 0.0, "t2_years": 0.0,
    "one_name": "", "one_amt": 0.0, "one_months": 6.0,
    # 보험
    "has_silson": KNOW[2], "has_life": KNOW[2],
    "checks": {},
}

# (키, 윗줄 태그, 제목, 설명) — 세 카드의 글 길이를 비슷하게 맞춰요
DEMO_INFO = [
    ("young", "예시 1", "🎓 사회초년생", "월 280만 원을 벌고 전세대출이 있어요. 내 집 마련을 준비 중이에요."),
    ("couple", "예시 2", "👫 맞벌이 부부", "월 620만 원 소득에 전세로 살아요. 내 집 마련 자금을 모으는 중이에요."),
    ("case", "가상 고객 사례", "🏢 조기은퇴 임대 가계", "부동산 4채와 투자자산이 있는 3인 가구예요. 1년 안에 보증금 4.5억 원을 돌려줘야 해요."),
]

DEMOS = {
    "young": {
        "goal": "내 집 마련", "years": 5, "target": 5000.0, "already_saved": 1500.0,
        "cash": 300.0, "deposits": 1500.0, "stocks": 500.0, "volatile": 100.0, "pension": 200.0, "other_assets": 5000.0,
        "other_debt": 3000.0, "pay_mode": PAY_MANUAL, "other_payment": 25.0,
        "income": 280.0, "exp_mode": EXP_SIMPLE, "expense_total": 193.0,
        "has_silson": "있어요", "has_life": "잘 모르겠어요",
    },
    "couple": {
        "goal": "내 집 마련", "years": 7, "target": 20000.0, "already_saved": 4000.0,
        "cash": 1500.0, "deposits": 3000.0, "stocks": 2000.0, "volatile": 500.0, "pension": 800.0, "other_assets": 15000.0,
        "other_debt": 12000.0, "pay_mode": PAY_MANUAL, "other_payment": 45.0,
        "income": 620.0, "exp_mode": EXP_SIMPLE, "expense_total": 375.0,
        "one_name": "이사 비용", "one_amt": 800.0, "one_months": 10.0,
        "has_silson": "있어요", "has_life": "있어요",
    },
    "case": {  # 가상 고객: 조기은퇴 임대 가계 (부모 가계 기준, 자녀 명의 자산은 제외)
        "goal": "전반적인 재무 점검", "years": 5,
        "cash": 5000.0, "stocks": 55000.0, "volatile": 55000.0, "crypto": 10000.0, "property": 340000.0,
        "mortgage": 60000.0, "loan_rate": 4.2, "loan_years": 30.0,
        "deposits_owed": 65000.0, "near_deposit": 45000.0,
        "income": 450.0, "rent_income": 240.0, "other_income": 150.0,
        "exp_mode": EXP_DETAIL, "living_cost": 260.0, "insurance_premium": 12.0, "other_fixed": 185.0,
        "t1_name": "자녀 등록금·주거비", "t1_amt": 1200.0, "t1_years": 4.0,
        "t2_name": "주택 수리비", "t2_amt": 1000.0, "t2_years": 2.0,
        "has_silson": "있어요", "has_life": "없어요",
    },
}


def init_state():
    if "mc" not in st.session_state:
        st.session_state["mc"] = copy.deepcopy(DEFAULTS)
    for k, v in DEFAULTS.items():
        st.session_state["mc"].setdefault(k, copy.deepcopy(v))
    st.session_state.setdefault("_step", 0)
    st.session_state.setdefault("nav", "🏠 시작하기")


def _clear_widget_state():
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and (k.startswith("w_") or k in ("step_nav",)):
            st.session_state.pop(k, None)
    st.session_state["_step"] = 0
    st.session_state.pop("ai_result", None)
    st.session_state.pop("ai_sig", None)
    st.session_state.pop("_loaded_file", None)


def load_demo(name: str):
    st.session_state["mc"] = {**copy.deepcopy(DEFAULTS), **copy.deepcopy(DEMOS[name])}
    _clear_widget_state()
    st.session_state["nav"] = "📊 내 재무 한눈에"


def reset_all():
    st.session_state["mc"] = copy.deepcopy(DEFAULTS)
    _clear_widget_state()
    st.session_state["nav"] = "🏠 시작하기"


def goto(page: str):
    st.session_state["nav"] = page


def goto_step(i: int):
    st.session_state["nav"] = "✍️ 내 정보 입력"
    st.session_state["_step"] = i
    st.session_state["step_nav"] = STEPS[i]


def _sync_step():
    st.session_state["_step"] = STEPS.index(st.session_state["step_nav"])


def step_move(delta: int):
    i = max(0, min(len(STEPS) - 1, st.session_state.get("_step", 0) + delta))
    st.session_state["_step"] = i
    st.session_state["step_nav"] = STEPS[i]


def import_json(raw: bytes):
    try:
        obj = json.loads(raw.decode("utf-8"))
        payload = obj.get("data", obj)
        new = copy.deepcopy(DEFAULTS)
        for k, default in DEFAULTS.items():
            if k not in payload:
                continue
            v = payload[k]
            if isinstance(default, int) and not isinstance(default, bool):
                new[k] = int(round(float(v)))
            elif isinstance(default, float):
                new[k] = float(v)
            elif isinstance(default, str):
                new[k] = str(v)
            elif isinstance(default, dict):
                new[k] = dict(v) if isinstance(v, dict) else {}
        st.session_state["mc"] = new
        _clear_widget_state()
        return True, "저장된 입력값을 불러왔어요."
    except Exception as e:  # noqa: BLE001
        return False, f"파일을 읽지 못했어요: {e}"


# ---- 입력 위젯 도우미 (페이지를 이동해도 값이 남도록 S와 동기화) ----
def unit_text(v: float, unit: str) -> str:
    """입력한 값을 사람이 읽기 쉬운 말로 바꿔 보여줘요. (만원 단위 금액은 '1억 2,000만 원'처럼)"""
    if unit == "%":
        return f"연 {v:g}%"
    if unit == "년":
        return f"{v:g}년"
    if unit == "개월":
        return f"{v:g}개월 뒤"
    return won(v)


def num(label, key, S, step=10.0, help=None, max_value=None, container=None, max_hint="", unit="만원"):
    c = container or st
    wk = f"w_{key}"
    if max_value is not None and max_value <= 0:  # 상위 항목이 0이면 입력 자체를 막아 오류를 방지
        c.number_input(label, value=0.0, disabled=True, key=f"{wk}_off", help=help)
        c.caption(max_hint or "먼저 위 항목을 입력하면 열려요.")
        S[key] = 0.0
        return 0.0
    if wk in st.session_state:
        if max_value is not None and st.session_state[wk] is not None and st.session_state[wk] > max_value:
            st.session_state[wk] = float(max_value)
        v = c.number_input(label, min_value=0.0, max_value=max_value, step=step, format="%g", key=wk, help=help)
    else:
        cur = float(S.get(key, 0.0) or 0.0)
        if max_value is not None:
            cur = min(cur, float(max_value))
        v = c.number_input(label, min_value=0.0, max_value=max_value, value=cur, step=step, format="%g", key=wk, help=help)
    v = 0.0 if v is None else float(v)
    S[key] = v
    if v > 0:  # 값을 입력하면 항상 아래에 화살표로 읽기 쉬운 값을 보여줘요
        c.caption(f"→ {unit_text(v, unit)}")
    return v


def sel(label, key, S, options, container=None, help=None):
    c = container or st
    wk = f"w_{key}"
    kw = {} if wk in st.session_state else {"index": options.index(S[key]) if S.get(key) in options else 0}
    v = c.selectbox(label, options, key=wk, help=help, **kw)
    S[key] = v
    return v


def radio_h(label, key, S, options, help=None, container=None, horizontal=True):
    c = container or st
    wk = f"w_{key}"
    kw = {} if wk in st.session_state else {"index": options.index(S[key]) if S.get(key) in options else 0}
    v = c.radio(label, options, horizontal=horizontal, key=wk, help=help, **kw)
    S[key] = v
    return v


def txt(label, key, S, container=None, placeholder=""):
    c = container or st
    wk = f"w_{key}"
    kw = {} if wk in st.session_state else {"value": S.get(key, "")}
    v = c.text_input(label, key=wk, placeholder=placeholder, **kw)
    S[key] = v
    return v


def auto_box(label, text, container=None, help=None):
    """앱이 자동으로 계산한 값을 회색 잠금칸으로 보여줘요. (직접 입력 불가)"""
    c = container or st
    c.text_input(f"🔒 {label}", value=text, disabled=True, help=help or "앱이 자동으로 계산해요. 입력할 필요 없어요.")


def auto_row(items):
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        auto_box(it[0], it[1], col, it[2] if len(it) > 2 else None)


# ============================================================
# 4. 계산 (합계·순자산·월 잉여자금·월 상환액·비상자금 목표 등은 모두 자동 계산)
# ============================================================
def A(S, k) -> float:
    try:
        return float(S.get(k, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def monthly_payment(p, rate_pct, years) -> float:
    """원리금균등 월 상환액."""
    n = int(round(years * 12))
    if p <= 0 or n <= 0:
        return 0.0
    r = rate_pct / 1200
    return p / n if r == 0 else p * r / (1 - (1 + r) ** -n)


def term_items(S):
    """기간 한정 지출: (이름, 연 금액, 지속 연수)"""
    out = []
    for i in (1, 2):
        amt, yrs = A(S, f"t{i}_amt"), int(A(S, f"t{i}_years"))
        if amt > 0 and yrs > 0:
            out.append((S.get(f"t{i}_name") or f"기간 한정 지출 {i}", amt, yrs))
    return out


def market_loss(stocks, volatile, crypto, drop_pct, mult) -> float:
    """시장이 drop_pct% 떨어질 때 줄어드는 금액. 변동이 큰 자산·가상자산은 mult배로 떨어진다고 가정(최대 100%)."""
    d = drop_pct / 100
    plain = max(0.0, stocks - volatile)
    return plain * d + (volatile + crypto) * min(1.0, d * mult)


def calculate(S) -> dict:
    cash, deposits, stocks = A(S, "cash"), A(S, "deposits"), A(S, "stocks")
    volatile, crypto, pension = min(A(S, "volatile"), stocks), A(S, "crypto"), A(S, "pension")
    prop, other_assets = A(S, "property"), A(S, "other_assets")
    financial = cash + deposits + stocks + pension + crypto
    assets = financial + prop + other_assets

    mortgage, credit, other_debt = A(S, "mortgage"), A(S, "credit"), A(S, "other_debt")
    dep_owed = A(S, "deposits_owed")
    near_dep = min(A(S, "near_deposit"), dep_owed)
    debts = mortgage + credit + other_debt + dep_owed

    income = A(S, "income") + A(S, "rent_income") + A(S, "other_income")
    mort_pay = monthly_payment(mortgage, A(S, "loan_rate"), A(S, "loan_years"))  # 자동 계산
    if S.get("pay_mode") == PAY_MANUAL:
        other_pay = A(S, "other_payment")
    else:  # 신용·기타 대출은 연 5%, 5년 원리금균등 상환으로 가정해 자동 계산
        other_pay = monthly_payment(credit + other_debt, 5.0, 5.0)
    pay = mort_pay + other_pay
    if S.get("exp_mode") == EXP_DETAIL:
        fixed = A(S, "living_cost") + A(S, "insurance_premium") + A(S, "other_fixed") + A(S, "irregular_monthly")
    else:
        fixed = A(S, "expense_total")
    outflow = fixed + pay
    surplus = income - outflow
    liquid = cash + deposits
    high_risk = volatile + crypto
    one_amt = A(S, "one_amt")
    one_12m = one_amt if (one_amt > 0 and A(S, "one_months") <= 12) else 0.0
    big_need = near_dep + one_12m

    # 목표: '비상자금 마련'은 월 지출 × 6개월과 현재 현금·예금으로 자동 설정
    target, saved, target_auto = A(S, "target"), A(S, "already_saved"), False
    if S.get("goal") == GOAL_EMERGENCY:
        target_auto = True
        target, saved = (outflow * 6, liquid) if outflow > 0 else (0.0, 0.0)
    target_gap = max(0.0, target - saved)
    months_goal = max(1, int(A(S, "years") or 3) * 12)
    return {
        "cash": cash, "deposits": deposits, "stocks": stocks, "volatile": volatile, "crypto": crypto,
        "pension": pension, "property": prop, "other_assets": other_assets, "financial": financial,
        "assets": assets, "debts": debts, "net": assets - debts,
        "mortgage": mortgage, "credit": credit, "other_debt": other_debt, "deposits_owed": dep_owed, "near_deposit": near_dep,
        "income": income, "fixed": fixed, "mort_pay": mort_pay, "other_pay": other_pay, "debt_payment": pay,
        "outflow": outflow, "surplus": surplus,
        "liquid": liquid, "runway": None if outflow <= 0 else liquid / outflow,
        "debt_ratio": ratio(debts, assets), "repayment_ratio": ratio(pay, income), "savings_rate": ratio(surplus, income),
        "high_risk": high_risk, "high_risk_ratio": ratio(high_risk, financial),
        "one_12m": one_12m, "big_need": big_need,
        "readiness": ratio(liquid, big_need) if big_need > 0 else None,
        "target": target, "saved": saved, "target_auto": target_auto,
        "target_gap": target_gap, "months_goal": months_goal, "required_monthly": target_gap / months_goal,
    }


def has_data(c) -> bool:
    return c["assets"] > 0 or c["income"] > 0 or c["outflow"] > 0


def build_timeline(S, c, years=10, deposit_out=0.0) -> pd.DataFrame:
    """1년차부터 years년차까지의 연도별 현금흐름 추정. deposit_out은 1년차에 돌려줄 보증금."""
    terms = term_items(S)
    one_amt, one_m = A(S, "one_amt"), max(1, int(A(S, "one_months") or 1))
    cum, rows = c["liquid"], []
    for y in range(1, years + 1):
        term_m = sum(a / 12 for _, a, n in terms if y <= n)
        month = c["surplus"] - term_m
        one_y = one_amt if (one_amt > 0 and math.ceil(one_m / 12) == y) else 0.0
        dep_y = deposit_out if y == 1 else 0.0
        annual = month * 12 - one_y - dep_y
        cum += annual
        rows.append({"연차": y, "기간한정지출월": term_m, "월현금흐름": month, "일회성지출": one_y,
                     "보증금반환": dep_y, "연간현금흐름": annual, "잔액": cum})
    return pd.DataFrame(rows)


def apply_scenario(S, c, income_pct=0.0, vacancy_pct=0.0, rate_delta=0.0, expense_delta=0.0,
                   one_off=0.0, market_drop=0.0, vol_mult=2.0, deposit_out=0.0) -> dict:
    """가정 시나리오 계산. deposit_out(보증금 반환)은 현금·예금과 부채가 같이 줄어서 순자산은 그대로예요."""
    rent = A(S, "rent_income")
    new_income = (c["income"] - rent) * (1 + income_pct / 100) + rent * (1 - vacancy_pct / 100)
    pay_delta = 0.0
    if rate_delta and c["mortgage"] > 0:
        pay_delta = (monthly_payment(c["mortgage"], A(S, "loan_rate") + rate_delta, A(S, "loan_years"))
                     - c["mort_pay"])
    new_out = max(0.0, c["outflow"] + expense_delta + pay_delta)
    loss = market_loss(c["stocks"], c["volatile"], c["crypto"], market_drop, vol_mult)
    liquid = c["liquid"] - one_off - deposit_out
    return {"income": new_income, "outflow": new_out, "surplus": new_income - new_out, "liquid": liquid,
            "net": c["net"] - one_off - loss, "runway": None if new_out <= 0 else liquid / new_out}


def scenario_list(S, c):
    """'만약 이런 일이 생기면?'에 쓰는 시나리오 목록: (이름, 가정값, 설명)"""
    items = [("월급·사업소득이 20% 줄면", dict(income_pct=-20), "")]
    if c["mortgage"] > 0:
        items.append(("대출 금리가 2%p 오르면", dict(rate_delta=2.0), ""))
    if A(S, "rent_income") > 0:
        items.append(("월세 수입이 절반으로 줄면", dict(vacancy_pct=50), ""))
    if c["stocks"] + c["crypto"] > 0:
        items.append(("주식시장이 20% 떨어지면", dict(market_drop=20), ""))
    items.append(("1,000만 원이 갑자기 필요하면", dict(one_off=1000), ""))
    if c["near_deposit"] > 0:
        items.append((f"1년 안에 보증금 {won(c['near_deposit'])}을 돌려주면", dict(deposit_out=c["near_deposit"]), ""))

    combo, parts = dict(income_pct=-20), ["소득 −20%"]
    if c["mortgage"] > 0:
        combo["rate_delta"] = 2.0
        parts.append("금리 +2%p")
    if c["stocks"] + c["crypto"] > 0:
        combo["market_drop"] = 20
        parts.append("주식 −20%")
    if c["near_deposit"] > 0:
        combo["deposit_out"] = c["near_deposit"]
        parts.append("보증금 반환")
    if len(parts) >= 3:
        items.append(("여러 일이 한꺼번에 겹치면", combo, " + ".join(parts)))
    return items


def scenario_summary(S, c) -> str:
    lines = []
    for name, kw, _ in scenario_list(S, c):
        s = apply_scenario(S, c, **kw)
        lines.append(f"- {name}: 월 잉여자금 {won(s['surplus'])}, 현금·예금 {won(s['liquid'])}, "
                     f"비상자금 {fmt_runway(s['liquid'], s['runway'])}, 순자산 {won(s['net'])}")
    return "\n".join(lines)


def months_to_reach(target, start, pmt, monthly_rate, cap=1200):
    bal = start
    for m in range(1, cap + 1):
        bal = bal * (1 + monthly_rate) + pmt
        if bal >= target:
            return m
    return None


def req_monthly(target, saved, years, ret_pct) -> float:
    """목표 금액을 채우기 위해 매달 저축해야 하는 금액(연 수익률 ret_pct% 가정)."""
    n, m = max(1, int(years) * 12), ret_pct / 1200
    gap = target - saved * (1 + m) ** n
    if gap <= 0:
        return 0.0
    return gap / n if m == 0 else gap * m / ((1 + m) ** n - 1)


# ============================================================
# 5. 신호등 진단 (🟢 초록 · 🟡 노랑 · 🔴 빨강 세 가지만 사용)
# ============================================================
def make_checks(S, c) -> list[dict]:
    out = []

    def add(key, title, tone, headline, meaning, evidence, action):
        assert tone in ("ok", "warn", "bad")
        out.append({"key": key, "title": title, "tone": tone, "headline": headline,
                    "meaning": meaning, "evidence": evidence, "action": action})

    term_m = sum(a / 12 for _, a, _ in term_items(S))

    # 1) 매달 남는 돈
    if c["income"] > 0 or c["outflow"] > 0:
        ev = f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])} = {won(c['surplus'])}"
        if c["surplus"] < 0:
            add("cashflow", "매달 남는 돈", "bad", f"매달 {won(abs(c['surplus']))}이 모자라요",
                "버는 돈보다 쓰는 돈이 많아요. 이 상태가 이어지면 저축이 줄거나 빚이 늘 수 있어요.", ev,
                "쓰는 돈을 '꼭 필요한 것'과 '줄일 수 있는 것'으로 나눠 보세요. 대출 상환액이 두 번 들어가진 않았는지도 확인하세요.")
        elif (c["savings_rate"] or 0) < 10:
            add("cashflow", "매달 남는 돈", "warn", f"매달 {won(c['surplus'])}이 남아요 (많지 않아요)",
                "남는 돈이 소득의 10%도 안 돼요. 예상 못한 지출이 생기면 곧 적자가 될 수 있어요.", ev,
                "1년에 한두 번 나가는 지출(보험·경조사비 등)이 빠지지 않았는지 확인하고, 줄일 수 있는 지출을 찾아보세요.")
        elif term_m > c["surplus"]:
            add("cashflow", "매달 남는 돈", "warn",
                f"지금은 {won(c['surplus'])} 남지만, 예정 지출을 넣으면 월 {won(term_m - c['surplus'])}이 모자라요",
                "몇 년 동안만 나가는 지출을 넣으면 일정 기간은 적자가 돼요. 그 기간에는 저축이 줄어들 수 있어요.",
                ev + f"  /  기간 한정 지출 월 환산 {won(term_m)}",
                "‘앞으로 시뮬레이션 → 해마다 돈 흐름’에서 언제까지 적자인지, 현금·예금이 버티는지 확인하세요.")
        else:
            add("cashflow", "매달 남는 돈", "ok", f"매달 {won(c['surplus'])}이 남아요",
                "번 돈보다 쓰는 돈이 적어 저축할 여력이 있어요. 다만 계산상 남는 돈과 실제 통장에 남는 돈은 다를 수 있어요.", ev,
                "지난 2~3개월 통장 잔액이 실제로 이만큼 늘었는지 비교해 보세요.")

    # 2) 비상자금
    if c["runway"] is not None:
        ev = f"현금·예금 {won(c['liquid'])} ÷ 월 지출 {won(c['outflow'])} = {c['runway']:.1f}개월"
        mean = "갑자기 소득이 끊겨도 현금·예금으로 버틸 수 있는 기간이에요. 보통 3~6개월치를 목표로 삼지만, 직업 안정성에 따라 달라요."
        if c["runway"] < 1:
            add("emergency", "비상자금", "bad", f"비상자금이 {c['runway']:.1f}개월치예요", mean, ev,
                "먼저 한 달 치 생활비부터 현금·예금으로 모아 보세요. 주식·부동산은 필요할 때 바로 현금이 되지 않을 수 있어요.")
        elif c["runway"] < 3:
            add("emergency", "비상자금", "warn", f"비상자금이 {c['runway']:.1f}개월치예요", mean, ev,
                "3개월치를 첫 목표로 정하고, 매달 남는 돈 일부를 비상자금 통장으로 자동이체해 보세요.")
        else:
            add("emergency", "비상자금", "ok", f"비상자금이 {c['runway']:.1f}개월치예요", mean, ev,
                "이 돈 중 곧 쓸 예정인 돈(보증금·학비 등)을 빼고도 충분한지 확인하세요.")

    # 3) 빚 부담
    if c["debts"] <= 0:
        if has_data(c):
            add("debt", "빚 부담", "ok", "갚아야 할 빚이 없어요", "총부채가 0원으로 입력돼 있어요.", "총부채 0원", "새로 빚을 질 때는 상환 조건을 꼭 확인하세요.")
    else:
        dr, rr = c["debt_ratio"], c["repayment_ratio"]
        tone = "bad" if ((rr or 0) >= 40 or (dr or 0) >= 70) else "warn" if ((rr or 0) >= 30 or (dr or 0) >= 50) else "ok"
        head = f"자산의 {pct(dr)}가 빚이에요" if dr is not None else "빚이 있어요"
        mean = "빚 비율만으로 위험하다고 단정할 수는 없어요. 이자율과 만기, 소득 대비 상환 부담을 함께 봐야 해요."
        if rr is not None and c["debt_payment"] > 0:
            mean = f"매달 소득의 {pct(rr)}를 대출 갚는 데 쓰고 있어요. " + mean
        if c["deposits_owed"] > 0:
            mean += " 세입자에게 받은 보증금은 나중에 돌려줘야 하는 돈이라 빚에 포함했어요."
        add("debt", "빚 부담", tone, head, mean,
            f"총부채 {won(c['debts'])} ÷ 총자산 {won(c['assets'])} = {pct(dr, 1)}  /  월 대출 상환 {won(c['debt_payment'])} ÷ 월 소득 {won(c['income'])} = {pct(rr, 1)} (공식 DSR 아님)",
            "대출마다 금리·만기·상환 방식·중도상환수수료를 한 장으로 정리해 보세요. 금리가 높은 빚부터 갚는 것이 일반적인 출발점이에요.")

    # 4) 투자 쏠림
    if c["financial"] > 0 and (c["stocks"] > 0 or c["crypto"] > 0):
        hr = c["high_risk_ratio"] or 0
        if c["high_risk"] <= 0:
            add("risk", "투자 쏠림", "ok", "변동이 아주 큰 자산은 따로 없어요", "크게 출렁이는 종목이나 가상자산을 입력하지 않았어요.",
                "변동 큰 자산 0원", "투자 비중은 '잃어도 생활에 문제없는 돈' 안에서 정하세요.")
        else:
            tone = "bad" if hr >= 50 else "warn" if hr >= 30 else "ok"
            add("risk", "투자 쏠림", tone, f"금융자산의 {pct(hr)}가 변동이 큰 자산이에요",
                "변동이 큰 자산은 짧은 기간에도 크게 오르내려요. 급락하면 생활비나 곧 써야 할 돈을 마련하기 어려워질 수 있어요.",
                f"(변동 큰 종목 {won(c['volatile'])} + 가상자산 {won(c['crypto'])}) ÷ 금융자산 {won(c['financial'])} = {pct(hr, 1)}",
                "‘앞으로 시뮬레이션 → 만약 이런 일이 생기면?’에서 시장이 떨어지는 경우를, ‘현금 마련해 보기’에서 일부를 현금으로 바꾼 경우를 확인해 보세요.")

    # 5) 곧 나갈 큰돈
    if c["big_need"] > 0:
        r = c["readiness"] or 0
        tone = "bad" if r < 100 else "warn" if r < 150 else "ok"
        parts = []
        if c["near_deposit"] > 0:
            parts.append(f"1년 안에 돌려줄 보증금 {won(c['near_deposit'])}")
        if c["one_12m"] > 0:
            parts.append(f"1년 안의 큰 지출 {won(c['one_12m'])}")
        add("bigmoney", "곧 나갈 큰돈", tone, f"1년 안에 {won(c['big_need'])}이 필요해요",
            f"{' + '.join(parts)}. 지금 현금·예금은 {won(c['liquid'])}이라 준비율은 {pct(r)}예요. 100%보다 낮으면 부족해요.",
            f"현금·예금 {won(c['liquid'])} ÷ 필요한 돈 {won(c['big_need'])} = {pct(r, 1)}",
            "‘앞으로 시뮬레이션 → 현금 마련해 보기’에서 투자자산 일부를 현금으로 바꾸면 얼마나 채워지는지 확인해 보세요. (세금·수수료는 따로 확인하세요.)")

    # 6) 목표 준비
    if c["target"] > 0:
        req, avail = c["required_monthly"], c["surplus"]
        ev = f"필요한 월 저축액 {won(req)} (수익률 0% 기준) / 매달 남는 돈 {won(avail)}"
        if c["target_gap"] <= 0:
            add("goal", "목표 준비", "ok", "목표 금액을 이미 모았어요", "이미 모은 금액이 목표 금액 이상이에요.", ev, "목표를 새로 세우거나 다음 목표로 넘어가세요.")
        elif avail >= req:
            add("goal", "목표 준비", "ok", f"목표까지 매달 {won(req)}이면 돼요", "지금 남는 돈으로 목표 기간 안에 모을 수 있어요.", ev,
                "매달 자동이체로 먼저 떼어 두세요.")
        elif avail > 0:
            add("goal", "목표 준비", "warn", f"목표까지 매달 {won(req - avail)}이 더 필요해요", "지금 남는 돈만으로는 기간 안에 목표를 채우기 어려워요.", ev,
                "‘앞으로 시뮬레이션 → 목표 달성’에서 수익률·기간을 바꿔 보세요.")
        else:
            add("goal", "목표 준비", "bad", "남는 돈이 없어 목표 저축이 어려워요", "매달 남는 돈이 없어서 목표를 위한 저축 여력이 없어요.", ev,
                "먼저 매달 남는 돈을 만드는 것부터 시작하세요.")

    # 7) 보험
    if has_data(c):
        ans = [S.get("has_silson"), S.get("has_life")]
        ev = f"실손보험: {ans[0]} / 사망·질병 보장: {ans[1]}"
        if "없어요" in ans:
            add("insurance", "보험 점검", "warn", "보험 보장을 점검해 보세요",
                "의료비나 소득 중단에 대비한 보험이 없다고 답했어요. 큰 병이나 사고가 나면 저축이 한꺼번에 줄 수 있어요.", ev,
                "필요한 보장이 무엇인지부터 정리해 보세요. 새 보험이 승인되기 전에 기존 보험을 해지하지 마세요.")
        elif "잘 모르겠어요" in ans:
            add("insurance", "보험 점검", "warn", "가입한 보험을 확인해 보세요",
                "내 보험이 무엇을 보장하는지 모르면, 필요할 때 도움이 안 될 수 있어요.", ev,
                "보험사 앱이나 ‘내보험다보여’ 같은 공식 서비스로 가입 내역을 확인해 보세요.")
        else:
            add("insurance", "보험 점검", "ok", "기본 보장이 있다고 답했어요", "실손보험과 사망·질병 보장이 모두 있어요.", ev,
                "보장 금액이 내 상황에 충분한지 1년에 한 번 점검하세요.")

    out.sort(key=lambda x: TONE_ORDER[x["tone"]])
    return out


def score_of(checks) -> int:
    return round(sum(TONE_SCORE[x["tone"]] for x in checks) / len(checks)) if checks else 0


def render_checks(items, limit=None):
    for it in (items[:limit] if limit else items):
        st.markdown(
            f'<div class="check" style="border-left:6px solid {BAR[it["tone"]]}">'
            f'<div class="check-t">{TONE_EMOJI[it["tone"]]} {esc(it["title"])}</div>'
            f'<div class="check-h">{esc(it["headline"])}</div>'
            f'<div class="check-m">{esc(it["meaning"])}</div>'
            f'<div class="check-a">👉 {esc(it["action"])}</div>'
            f'<details><summary>계산 근거 보기</summary>{esc(it["evidence"])}</details></div>',
            unsafe_allow_html=True)


def render_overall(checks):
    """신호등 결과를 한눈에 요약 (참고 점수 포함)."""
    if not checks:
        return
    n = {t: sum(1 for x in checks if x["tone"] == t) for t in ("bad", "warn", "ok")}
    if n["bad"]:
        tone, title = "bad", f"먼저 챙겨볼 것이 {n['bad']}개 있어요"
    elif n["warn"]:
        tone, title = "warn", f"살펴볼 것이 {n['warn']}개 있어요"
    else:
        tone, title = "ok", "전반적으로 무난해요"
    fg, bg, bd = TONES[tone]
    goods = [x["title"] for x in checks if x["tone"] == "ok"]
    good_txt = f"<br>🟢 잘하고 있는 점: {esc(', '.join(goods))}" if goods else ""
    st.markdown(
        f'<div class="overall" style="background:{bg};border:1px solid {bd};border-left:8px solid {BAR[tone]}">'
        f'<div class="o-row"><div><div class="o-t" style="color:{fg}">{TONE_EMOJI[tone]} {esc(title)}</div>'
        f'<div class="o-s">🔴 {n["bad"]}개 &nbsp;·&nbsp; 🟡 {n["warn"]}개 &nbsp;·&nbsp; 🟢 {n["ok"]}개{good_txt}</div></div>'
        f'<div class="o-score"><b style="color:{fg}">{score_of(checks)}</b><span>신호등 점수 / 100<br>(🟢100·🟡55·🔴15점의 평균)</span></div></div></div>',
        unsafe_allow_html=True)


def validate(S, c) -> list[str]:
    """초보자가 흔히 하는 입력 실수를 쉬운 말로 알려줘요."""
    msgs = []
    if c["income"] == 0 and c["outflow"] > 0:
        msgs.append("월 소득이 0원인데 지출이 있어요. 소득을 빠뜨리지 않았는지 확인해 주세요.")
    if c["income"] > 0 and c["outflow"] > c["income"] * 3:
        msgs.append("월 지출이 월 소득의 3배가 넘어요. 금액 단위(만원)가 맞는지 확인해 주세요.")
    if c["debts"] > c["assets"] > 0:
        msgs.append("빚이 자산보다 많아요. 실제 상황이 맞다면 그대로 진행해도 괜찮아요.")
    if (c["credit"] + c["other_debt"]) > 0 and S.get("pay_mode") == PAY_MANUAL and A(S, "other_payment") == 0:
        msgs.append("신용·기타 대출이 있는데 월 상환액이 0원이에요. ② 부채에서 ‘자동 계산’을 고르면 편해요.")
    if c["mortgage"] > 0 and A(S, "loan_years") <= 0:
        msgs.append("주택담보대출의 남은 기간이 0년이에요. ② 부채에서 기간을 확인해 주세요.")
    for k in MONTHLY_KEYS:
        if A(S, k) >= 10000:
            msgs.append("월 금액에 1억 원 이상이 입력된 항목이 있어요. 단위가 '만원'인지 확인해 주세요.")
            break
    if not c["target_auto"] and c["target"] > 0 and c["saved"] > c["target"]:
        msgs.append("목표를 위해 이미 모은 금액이 목표 금액보다 커요. 둘 다 맞는지 확인해 주세요.")
    return msgs


def make_tasks(S, c, checks):
    tasks = []
    for it in checks:
        if it["tone"] in ("bad", "warn"):
            tasks.append((it["key"], it["tone"], it["title"], it["action"]))
    tasks.append(("monthly", "ok", "한 달에 한 번 입력값 새로 고치기", "소득·지출·대출 잔액이 바뀌면 다시 입력해서 변화를 확인하세요."))
    if not any(t[1] in ("bad", "warn") for t in tasks):
        tasks.insert(0, ("keep", "ok", "지금 상태 유지하기", "지금처럼 매달 남는 돈을 꾸준히 모으고, 비상자금을 유지하세요."))
    return tasks


# ============================================================
# 6. 공통 화면 조각 · 그래프
# ============================================================
def need_data(c) -> bool:
    if has_data(c):
        return True
    hero("먼저 내 정보를 입력해 주세요", "자산·부채·월 수입과 지출을 입력하면 이 화면이 자동으로 채워져요.")
    b1, b2 = st.columns(2)
    b1.button("✍️ 내 정보 입력하러 가기", on_click=goto_step, args=(0,), type="primary", **FULL)
    b2.button("🧪 예시로 먼저 둘러보기", on_click=load_demo, args=("young",), **FULL)
    return False


def _alt():
    try:
        import altair as alt
        return alt
    except Exception:  # noqa: BLE001
        return None


def draw(chart):
    try:
        st.altair_chart(chart, **FULL_ALT)
    except TypeError:
        st.altair_chart(chart)


PALETTE = ["#0f766e", "#2563eb", "#7c3aed", "#0891b2"]


def donut(df, label_col, value_col, title):
    if df.empty:
        st.caption(f"{title}: 입력된 항목이 없어요.")
        return
    alt = _alt()
    if alt is None:
        st.markdown(f"**{title}**")
        st.bar_chart(df.set_index(label_col))
        return
    chart = alt.Chart(df).mark_arc(innerRadius=60).encode(
        theta=alt.Theta(f"{value_col}:Q"),
        color=alt.Color(f"{label_col}:N", legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[label_col, value_col],
    ).properties(height=300, title=title)
    draw(chart)


def line_by_year(df: pd.DataFrame, ycols: list, xtitle="몇 년 후", ytitle="금액 (만원)", dashed=(), zero_rule=False, height=340):
    """'연차' 열을 숫자축으로 그려서 항상 0년(지금)부터 순서대로 나와요. 끝점에 금액을 표시해요."""
    alt = _alt()
    if alt is None:
        st.line_chart(df.set_index("연차")[list(ycols)])
        return
    long = df.melt(id_vars=["연차"], value_vars=list(ycols), var_name="구분", value_name="금액")
    xmax = max(1, int(df["연차"].max()))
    last = long[long["연차"] == xmax].copy()
    last["라벨"] = last["금액"].map(won)
    colors, ci = [], 0
    for name in ycols:
        if name in dashed:
            colors.append("#667085")
        else:
            colors.append(PALETTE[ci % len(PALETTE)])
            ci += 1
    color = alt.Color("구분:N", scale=alt.Scale(domain=list(ycols), range=colors), legend=alt.Legend(orient="bottom", title=None))
    xenc = alt.X("연차:Q", title=xtitle, scale=alt.Scale(domain=[0, xmax], nice=False), axis=alt.Axis(tickMinStep=1, format="d"))
    yenc = alt.Y("금액:Q", title=ytitle, scale=alt.Scale(zero=False), axis=alt.Axis(format=",.0f"))
    tip = [alt.Tooltip("연차:Q", title=xtitle), alt.Tooltip("구분:N", title="구분"), alt.Tooltip("금액:Q", title="금액(만원)", format=",.0f")]
    layers = []
    solid = long[~long["구분"].isin(dashed)]
    dash = long[long["구분"].isin(dashed)]
    if not solid.empty:
        layers.append(alt.Chart(solid).mark_line(point=True, strokeWidth=3).encode(x=xenc, y=yenc, color=color, tooltip=tip))
    if not dash.empty:
        layers.append(alt.Chart(dash).mark_line(strokeDash=[6, 4], strokeWidth=2).encode(x=xenc, y=yenc, color=color, tooltip=tip))
    layers.append(alt.Chart(last).mark_text(align="right", dy=-12, fontWeight="bold").encode(x=xenc, y=yenc, text="라벨:N", color=color))
    if zero_rule:
        layers.append(alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#dc2626", strokeDash=[4, 4]).encode(
            y=alt.Y("y:Q", scale=alt.Scale(zero=False))))
    draw(alt.layer(*layers).properties(height=height))


def bars_by_year(df: pd.DataFrame, ycol: str, ytitle: str, xtitle="몇 년차", height=280):
    """해마다 남는 돈(초록)·모자란 돈(빨강) 막대."""
    d = pd.DataFrame({"x": df["연차"].astype(int), "v": df[ycol].astype(float)})
    alt = _alt()
    if alt is None:
        st.bar_chart(d.set_index("x"))
        return
    d["label"] = d["v"].map(won)
    d["color"] = d["v"].map(lambda v: "#dc2626" if v < 0 else "#16a34a")
    chart = alt.Chart(d).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("x:O", title=xtitle, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("v:Q", title=ytitle, axis=alt.Axis(format=",.0f")),
        color=alt.Color("color:N", scale=None, legend=None),
        tooltip=[alt.Tooltip("x:O", title=xtitle), alt.Tooltip("label:N", title="금액")],
    ).properties(height=height)
    draw(chart)


def bars_by_cat(df: pd.DataFrame, vtitle: str, axis_fmt=",.0f"):
    """가로 막대. 열: name·v·label·color. 가로축 범위를 데이터에 맞춰 자동 조정하고 막대 끝에 라벨을 붙여요."""
    alt = _alt()
    if alt is None:
        st.bar_chart(df.set_index("name")[["v"]])
        return
    lo, hi = float(min(0.0, df["v"].min())), float(max(0.0, df["v"].max()))
    pad = ((hi - lo) or 1.0) * 0.35
    dom_lo = lo - pad if lo < 0 else 0.0
    dom_hi = hi + pad if hi > 0 else 0.0
    if dom_lo == dom_hi:
        dom_hi = 1.0
    order = df["name"].tolist()
    xenc = alt.X("v:Q", title=vtitle, scale=alt.Scale(domain=[dom_lo, dom_hi], nice=False), axis=alt.Axis(format=axis_fmt))
    yenc = alt.Y("name:N", sort=order, title=None, axis=alt.Axis(labelLimit=320))
    base = alt.Chart(df)
    bars = base.mark_bar(cornerRadiusEnd=4, size=26).encode(
        x=xenc, y=yenc, color=alt.Color("color:N", scale=None, legend=None),
        tooltip=[alt.Tooltip("name:N", title="상황"), alt.Tooltip("label:N", title="값")])
    pos = base.transform_filter("datum.v >= 0").mark_text(align="left", dx=5, fontWeight="bold", color="#14213d").encode(
        x=xenc, y=yenc, text="label:N")
    neg = base.transform_filter("datum.v < 0").mark_text(align="right", dx=-5, fontWeight="bold", color="#14213d").encode(
        x=xenc, y=yenc, text="label:N")
    zero = alt.Chart(pd.DataFrame({"x": [0.0]})).mark_rule(color="#98a2b3").encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[dom_lo, dom_hi], nice=False)))
    draw(alt.layer(bars, pos, neg, zero).properties(height=46 * len(df) + 56))


# ============================================================
# 7. 시작하기
# ============================================================
GLOSSARY = [
    ("자산", "내가 가진 것. 현금·예금·주식·부동산 등."),
    ("부채(빚)", "나중에 갚아야 하는 돈. 대출, 카드할부, 세입자에게 받은 보증금 등."),
    ("순자산", "자산 − 부채. 빚을 다 갚고 나면 내 몫으로 남는 돈이에요."),
    ("월 잉여자금", "한 달 동안 번 돈에서 쓴 돈을 뺀 값. 마이너스면 적자예요."),
    ("비상자금", "갑자기 소득이 끊겨도 버틸 수 있게 현금·예금으로 모아 둔 돈."),
    ("변동성", "가격이 오르내리는 폭. 클수록 짧은 기간에도 크게 벌거나 잃을 수 있어요."),
    ("레버리지·인버스 ETF", "지수의 2배, 3배 등으로(또는 반대로) 움직이게 만든 상품. 배수는 상품마다 달라요."),
    ("시나리오(가정)", "‘만약 ~라면?’ 하고 가정해서 계산한 결과. 미래를 맞히는 예측이 아니에요."),
    ("DSR", "은행이 대출을 심사할 때 쓰는 ‘소득 대비 원리금 상환 비율’. 이 앱의 상환 비율은 참고용이에요."),
]


def demo_cards():
    cols = st.columns(3)
    for col, (k, tag, title, desc) in zip(cols, DEMO_INFO):
        with col:
            with st.container(border=True):
                st.markdown(
                    f'<div class="demo-tag">{esc(tag)}</div><div class="demo-t">{esc(title)}</div>'
                    f'<div class="demo-d">{esc(desc)}</div>', unsafe_allow_html=True)
                st.button("이 예시로 보기", key=f"demo_{k}", on_click=load_demo, args=(k,), **FULL)


def page_home(S, c):
    hero("내 돈의 상태, 쉽게 확인해요", "어려운 금융 용어 없이, 꼭 필요한 숫자와 지금 할 일만 알려드려요. 입력은 3분이면 충분해요.")
    if not has_data(c):
        cols = st.columns(3)
        steps = [("STEP 1", "내 정보 입력", "자산·부채·월 수입과 지출을 4단계로 입력해요. 합계와 월 상환액은 앱이 자동으로 계산해요."),
                 ("STEP 2", "신호등으로 확인", "🟢🟡🔴 신호등으로 지금 내 상태를 한눈에 보여줘요."),
                 ("STEP 3", "지금 할 일 정하기", "할 일을 순서대로 정리하고, 결과를 파일로 저장할 수 있어요.")]
        for col, (k, t, d) in zip(cols, steps):
            col.markdown(f'<div class="card"><div class="step">{k}</div><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)
        st.write("")
        st.button("✍️ 내 정보 입력 시작하기", on_click=goto_step, args=(0,), type="primary", **FULL)
        st.write("")
        st.markdown("#### 입력이 어렵다면 예시로 먼저 둘러보세요")
        demo_cards()
    else:
        checks = make_checks(S, c)
        render_overall(checks)
        kpi_row([("내 순자산", won(c["net"]), f"자산 {won(c['assets'])} − 부채 {won(c['debts'])}", "ok" if c["net"] >= 0 else "bad"),
                 ("매달 남는 돈", won(c["surplus"]), f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad"),
                 ("비상자금", fmt_months(c["runway"]), "현금·예금 ÷ 월 지출", "ok" if (c["runway"] or 0) >= 3 else "warn")])
        st.write("")
        section("지금 가장 먼저 볼 것")
        render_checks(checks, limit=3)
               n1, n2 = st.columns(2)
        n1.button("📊 전체 결과 보기", on_click=goto, args=("📊 내 재무 한눈에",), type="primary", **FULL)
        n2.button("🔮 앞으로 시뮬레이션", on_click=goto, args=("🔮 앞으로 시뮬레이션",), **FULL)
        with st.expander("다른 예시도 둘러보기 (지금 입력한 내용은 예시로 바뀌어요)"):
            demo_cards()

    st.write("")
    with st.expander("이 앱이 하지 않는 일"):
        st.markdown(
            "- 입력한 숫자는 앱이 **직접 계산**해요(규칙 기반).\n"
            "- 특정 주식·ETF·펀드·보험 상품을 사거나 팔라고 권하지 않아요.\n"
            "- 세금·법률의 최종 판단은 하지 않아요. 필요하면 전문가나 공식 기관에 확인하세요.\n"
            "- 계좌번호·주민등록번호·비밀번호는 입력하지 마세요.")


# ============================================================
# 8. 내 정보 입력 (4단계) — 자동 계산 값은 🔒 잠금칸으로 보여줘요
# ============================================================
def step_assets(S):
    st.markdown("#### 1단계. 지금 가진 **자산**을 알려주세요")
    st.caption("대략적인 금액이면 충분해요. 같은 자산을 두 번 입력하지 마세요. 값을 입력하면 아래에 ‘→ 얼마’인지 바로 보여드려요.")
    with st.container(border=True):
        st.markdown("**💵 바로 쓸 수 있는 돈**")
        a, b = st.columns(2)
        num("현금·입출금 통장", "cash", S, container=a, help="지갑 속 현금과 월급통장 등 언제든 꺼내 쓰는 돈")
        num("예금·적금", "deposits", S, container=b, help="정기예금과 적금 잔액")
    with st.container(border=True):
        st.markdown("**📈 투자와 연금**")
        a, b = st.columns(2)
        num("주식·ETF·펀드 전체", "stocks", S, container=a, help="레버리지·테마주 등도 여기에 모두 포함해서 입력해요.")
        num("가상자산(코인 등)", "crypto", S, container=b, help="비트코인 등 가상자산의 현재 평가액")
        num("연금계좌", "pension", S, container=a, help="연금저축·IRP 평가액. 그 안의 ETF를 위에 또 넣지 마세요.")
        with st.expander("레버리지·테마주처럼 가격이 크게 출렁이는 종목이 있다면 (선택)", expanded=A(S, "volatile") > 0):
            num("주식·ETF 중 변동이 특히 큰 종목", "volatile", S, max_value=A(S, "stocks"),
                max_hint="먼저 ‘주식·ETF·펀드 전체’를 입력하면 열려요.",
                help="레버리지·인버스 ETF, 테마주, 소형주의 합계예요. 모르겠으면 0으로 두세요.")
    with st.container(border=True):
        st.markdown("**🏠 부동산과 기타**")
        a, b = st.columns(2)
        num("부동산 현재 가격", "property", S, step=100.0, container=a, help="대출을 빼기 전 금액이에요. (빚은 다음 단계에 입력해요)")
        num("기타 자산", "other_assets", S, step=10.0, container=b,
            help="내가 세입자로 맡긴 전월세 보증금, 자동차 등. 위에 이미 넣은 것은 빼세요.")
    c = calculate(S)
    auto_row([("총자산 (자동 계산)", won(c["assets"])),
              ("그중 금융자산 (자동 계산)", won(c["financial"])),
              ("그중 바로 쓸 수 있는 돈 (자동 계산)", won(c["liquid"]))])


def step_debts(S):
    st.markdown("#### 2단계. 갚아야 할 돈, **부채(빚)**를 알려주세요")
    st.caption("지금 남아 있는 잔액만 입력하세요. 빚이 없으면 모두 0으로 두면 돼요. 월 상환액은 앱이 계산해요.")
    with st.container(border=True):
        st.markdown("**🏦 대출 잔액**")
        a, b, d = st.columns(3)
        num("주택담보대출", "mortgage", S, step=100.0, container=a, help="집을 담보로 받은 대출의 남은 금액")
        num("신용대출·마이너스통장", "credit", S, container=b)
        num("학자금·전세대출·카드할부 등", "other_debt", S, container=d)
    if A(S, "mortgage") > 0:
        with st.expander("🔧 주택담보대출 조건 (모르면 그대로 두세요. 평균값으로 계산해요)"):
            a, b = st.columns(2)
            num("대출 금리 (연 %)", "loan_rate", S, step=0.1, max_value=30.0, container=a, unit="%")
            num("남은 기간 (년)", "loan_years", S, step=1.0, max_value=50.0, container=b, unit="년")
    if A(S, "credit") + A(S, "other_debt") > 0:
        with st.container(border=True):
            st.markdown("**📆 신용·기타 대출의 월 상환액**")
            mode = radio_h("계산 방법", "pay_mode", S, [PAY_AUTO, PAY_MANUAL], horizontal=False,
                           help="잘 모르겠다면 ‘자동 계산’이 편해요. 실제 상환액을 알면 ‘직접 입력’을 고르세요.")
            if mode == PAY_MANUAL:
                num("매달 갚는 돈 (원금+이자 합계)", "other_payment", S, step=5.0,
                    help="신용대출·학자금·전세대출 등 주택담보대출 외 대출의 월 상환액 합계예요.")
    with st.expander("🏘️ 내 집·상가를 세놓았다면 (해당될 때만 열어 보세요)", expanded=A(S, "deposits_owed") > 0):
        a, b = st.columns(2)
        num("세입자에게 받은 보증금 합계", "deposits_owed", S, step=100.0, container=a,
            help="계약이 끝나면 돌려줘야 하는 돈이라 부채로 계산해요.")
        num("└ 이 중 1년 안에 돌려줄 금액", "near_deposit", S, step=100.0, container=b,
            max_value=A(S, "deposits_owed"), max_hint="먼저 ‘받은 보증금 합계’를 입력하면 열려요.",
            help="계약 만기가 12개월 이내인 보증금")
    c = calculate(S)
    auto_row([("총부채 (자동 계산)", won(c["debts"])),
              ("매달 대출 갚는 돈 (자동 계산)", won(c["debt_payment"]), "주택담보대출은 원리금균등, 기타 대출은 위에서 고른 방법으로 계산해요.")])


def step_flow(S):
    st.markdown("#### 3단계. **한 달**에 들어오고 나가는 돈을 알려주세요")
    st.caption("평균적인 한 달 금액이면 돼요. 대출 상환액은 앞 단계에서 이미 계산했으니 지출에 넣지 마세요.")
    a, b = st.columns(2)
    with a:
        with st.container(border=True):
            st.markdown("**⬇️ 들어오는 돈**")
            num("월급·사업소득 (세금 낸 뒤)", "income", S, help="실제로 통장에 들어오는 금액")
            with st.expander("월세 수입·배당 등 다른 소득이 있어요", expanded=(A(S, "rent_income") + A(S, "other_income")) > 0):
                num("월 임대수입(월세)", "rent_income", S, help="집이나 상가를 빌려주고 매달 받는 월세")
                num("배당·용돈 등 기타 소득", "other_income", S)
    with b:
        with st.container(border=True):
            st.markdown("**⬆️ 나가는 돈**")
            mode = radio_h("입력 방법", "exp_mode", S, [EXP_SIMPLE, EXP_DETAIL],
                           help="모르겠다면 ‘간단히’로 한 칸만 입력해도 괜찮아요.")
            if mode == EXP_DETAIL:
                num("생활비", "living_cost", S, help="식비·교통·통신·공과금·관리비·문화생활 등")
                num("보험료", "insurance_premium", S)
                num("세금·가족 지원 등 기타 정기지출", "other_fixed", S, help="재산세 적립, 가족 용돈 등 매달 나가는 돈")
                num("1년에 한두 번 나가는 돈 ÷ 12", "irregular_monthly", S,
                    help="자동차 보험, 명절·경조사비, 여행 등 연간 예상액을 12로 나눈 금액")
            else:
                num("한 달 총지출 (대출 상환 제외)", "expense_total", S,
                    help="생활비·보험료·세금·용돈 등 매달 쓰는 돈 전체예요. 통장 지출 내역을 보면 쉬워요.")
    c = calculate(S)
    auto_row([("월 소득 합계 (자동 계산)", won(c["income"])),
              ("월 지출 합계 (대출 상환 포함, 자동 계산)", won(c["outflow"])),
              ("매달 남는 돈 (자동 계산)", won(c["surplus"]))])


def step_goal(S):
    st.markdown("#### 4단계. **목표**와 앞으로 나갈 큰돈 (모두 선택이에요)")
    with st.container(border=True):
        st.markdown("**🎯 이루고 싶은 목표**")
        a, b = st.columns(2)
        sel("가장 중요한 목표", "goal", S, GOALS, a)
        yopts = [1, 2, 3, 5, 7, 10, 15, 20, 30]
        wk = "w_years"
        kw = {} if wk in st.session_state else {"index": yopts.index(int(S["years"])) if int(S["years"]) in yopts else 2}
        S["years"] = b.selectbox("목표까지 남은 기간", yopts, format_func=lambda v: f"{v}년", key=wk, **kw)
        a, b = st.columns(2)
        if S.get("goal") == GOAL_EMERGENCY:
            c = calculate(S)
            auto_box("목표 금액 (월 지출 × 6개월, 자동 계산)", won(c["target"]) if c["target"] > 0 else "③에서 지출을 입력하면 계산돼요", a)
            auto_box("이미 모은 금액 (현재 현금·예금, 자동 계산)", won(c["saved"]), b)
        else:
            num("목표에 필요한 총금액", "target", S, step=100.0, container=a, help="0이면 목표 계산은 건너뛰어요.")
            num("목표를 위해 이미 모은 금액", "already_saved", S, container=b)
    with st.expander("📅 몇 년 동안만 나가는 지출이 있어요 (예: 등록금 4년, 수리비 2년)", expanded=len(term_items(S)) > 0):
        for i in (1, 2):
            a, b, d = st.columns([2, 1.3, 1.1])
            txt("이름", f"t{i}_name", S, a, placeholder="예: 등록금")
            num("1년에 드는 돈", f"t{i}_amt", S, step=50.0, container=b)
            num("몇 년 동안", f"t{i}_years", S, step=1.0, max_value=50.0, container=d, unit="년")
    with st.expander("💥 한 번에 크게 나갈 지출이 있어요 (예: 결혼, 이사, 자동차)", expanded=A(S, "one_amt") > 0):
        a, b, d = st.columns([2, 1.3, 1.1])
        txt("이름", "one_name", S, a, placeholder="예: 이사 비용")
        num("금액", "one_amt", S, step=100.0, container=b)
        num("몇 개월 뒤", "one_months", S, step=1.0, max_value=600.0, container=d, unit="개월")
    with st.container(border=True):
        st.markdown("**🛡️ 보험 (대략 알고 있는 만큼만)**")
        radio_h("실손의료보험에 가입했나요?", "has_silson", S, KNOW)
        radio_h("사망·질병 등 소득 보장 보험이 있나요?", "has_life", S, KNOW)


def page_input(S):
    hero("내 정보 입력", "한 단계씩 입력해요. 금액은 ‘만원’ 단위이고, 모르는 항목은 0으로 두면 돼요. 🔒 회색 칸은 앱이 자동으로 계산해요.")
    msg_box = st.container()
    if "step_nav" not in st.session_state:
        st.session_state["step_nav"] = STEPS[st.session_state.get("_step", 0)]
    st.radio("입력 단계", STEPS, horizontal=True, key="step_nav", on_change=_sync_step, label_visibility="collapsed")
    step = STEPS.index(st.session_state["step_nav"])
    st.session_state["_step"] = step
    st.progress((step + 1) / len(STEPS), text=f"{step + 1} / {len(STEPS)} 단계")

    [step_assets, step_debts, step_flow, step_goal][step](S)

    st.write("")
    b1, b2, _ = st.columns([1, 1.4, 2])
    b1.button("← 이전", on_click=step_move, args=(-1,), disabled=(step == 0), **FULL)
    if step < len(STEPS) - 1:
        b2.button("다음 단계 →", on_click=step_move, args=(1,), type="primary", **FULL)
    else:
        b2.button("📊 결과 보러 가기", on_click=goto, args=("📊 내 재무 한눈에",), type="primary", **FULL)

    c = calculate(S)  # 위젯 값이 모두 반영된 뒤 점검
    with msg_box:
        msgs = validate(S, c)
        for m in msgs:
            st.warning(m)
        if has_data(c) and not msgs:
            st.caption("✅ 입력 점검 통과 — 입력값은 자동으로 반영돼요.")


# ============================================================
# 9. 내 재무 한눈에
# ============================================================
def page_snapshot(S, c):
    hero("내 재무 한눈에", "신호등으로 지금 내 상태를 쉽게 살펴봐요.")
    if not need_data(c):
        return
    checks = make_checks(S, c)
    render_overall(checks)
    kpi_row([("내 순자산", won(c["net"]), f"자산 {won(c['assets'])} − 부채 {won(c['debts'])}", "ok" if c["net"] >= 0 else "bad"),
             ("매달 남는 돈", won(c["surplus"]), f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad"),
             ("비상자금", fmt_months(c["runway"]), f"현금·예금 {won(c['liquid'])}", "ok" if (c["runway"] or 0) >= 3 else "warn")])

    st.write("")
    section("신호등으로 보는 내 상태", "🔴 먼저 확인 · 🟡 살펴보기 · 🟢 괜찮아요")
    render_checks(checks)
    note("신호등 기준은 일반적인 참고 범위예요. 사람마다 상황이 달라 ‘정답’이 아니에요.")

    st.divider()
    section("자세히 보기")
    t1, t2, t3 = st.tabs(["재무상태표", "한 달 수입·지출", "자산 구성"])
    plain = max(0.0, c["stocks"] - c["volatile"])
    assets_rows = [("현금·입출금", c["cash"]), ("예금·적금", c["deposits"]), ("주식·ETF (일반)", plain),
                   ("변동이 특히 큰 종목", c["volatile"]), ("가상자산", c["crypto"]), ("연금계좌", c["pension"]),
                   ("부동산", c["property"]), ("기타 자산", c["other_assets"])]
    debt_rows = [("주택담보대출", c["mortgage"]), ("신용대출·마이너스통장", c["credit"]), ("학자금·전세대출 등", c["other_debt"]),
                 ("세입자 보증금(돌려줄 돈)", c["deposits_owed"])]
    with t1:
        left, right = st.columns(2)
        with left:
            st.markdown("**자산**")
            show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in assets_rows if v > 0] + [{"항목": "총자산", "금액": won(c["assets"])}]))
        with right:
            st.markdown("**부채와 순자산**")
            show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in debt_rows if v > 0] +
                                 [{"항목": "총부채", "금액": won(c["debts"])}, {"항목": "순자산", "금액": won(c["net"])}]))
    with t2:
        flow = [("들어오는 돈", "월급·사업소득", A(S, "income")), ("들어오는 돈", "임대수입", A(S, "rent_income")), ("들어오는 돈", "기타 소득", A(S, "other_income"))]
        if S.get("exp_mode") == EXP_DETAIL:
            flow += [("나가는 돈", "생활비", A(S, "living_cost")), ("나가는 돈", "보험료", A(S, "insurance_premium")),
                     ("나가는 돈", "세금·가족 지원 등", A(S, "other_fixed")), ("나가는 돈", "비정기 지출(월 환산)", A(S, "irregular_monthly"))]
        else:
            flow += [("나가는 돈", "생활비·보험료·세금 등 (총액)", c["fixed"])]
        flow += [("나가는 돈", "대출 상환 (자동 계산)", c["debt_payment"])]
        rows = [{"구분": a, "항목": b, "월 금액": won(v)} for a, b, v in flow if v > 0]
        rows += [{"구분": "합계", "항목": "월 소득", "월 금액": won(c["income"])}, {"구분": "합계", "항목": "월 지출", "월 금액": won(c["outflow"])},
                 {"구분": "결과", "항목": "월 잉여자금", "월 금액": won(c["surplus"])}]
        show_df(pd.DataFrame(rows))
    with t3:
        a, b = st.columns(2)
        with a:
            donut(pd.DataFrame([{"자산": k, "금액": v} for k, v in assets_rows if v > 0]), "자산", "금액", "자산 구성")
        with b:
            donut(pd.DataFrame([{"부채": k, "금액": v} for k, v in debt_rows if v > 0]), "부채", "금액", "부채 구성")

    with st.expander("계산 방법 보기"):
        st.markdown(
            "- 총자산 = 현금·예금 + 주식·ETF + 가상자산 + 연금계좌 + 부동산 + 기타 자산\n"
            "- 총부채 = 주택담보대출 + 신용대출 + 기타 대출 + 세입자 보증금\n"
            "- 순자산 = 총자산 − 총부채\n"
            "- 월 대출 상환액 = 주택담보대출 원리금균등 계산값 + 기타 대출 월 상환액\n"
            "- 월 잉여자금 = 월 소득 − 월 지출\n"
            "- 비상자금(개월) = 현금·예금 ÷ 월 지출\n"
            "- ‘변동이 특히 큰 종목’은 ‘주식·ETF’의 일부이므로 총자산에 두 번 더하지 않아요.\n"
            "- 신호등 점수 = 항목별 신호(🟢100·🟡55·🔴15점)의 평균이에요. 참고용 지표예요.")


# ============================================================
# 10. 앞으로 시뮬레이션
# ============================================================
def tab_timeline(S, c):
    st.caption("몇 년 동안만 나가는 지출과 큰 지출까지 넣어서, 해마다 돈이 어떻게 흘러가는지 보여줘요.")
    years = st.slider("몇 년 후까지 볼까요?", 3, 15, 8)
    incl = False
    if c["near_deposit"] > 0:
        incl = st.checkbox(f"1년 안에 돌려줄 보증금 {won(c['near_deposit'])}도 반영하기", value=True, key="w_tl_dep",
                           help="체크하면 1년차에 보증금이 현금·예금에서 빠져나가는 것으로 계산해요.")
    df = build_timeline(S, c, years, c["near_deposit"] if incl else 0.0)
    deficit = df[df["연간현금흐름"] < 0]
    broke = df[df["잔액"] < 0]
    kpi_row([("지금 매달 남는 돈", won(c["surplus"]), "기간 한정 지출 반영 전", "ok" if c["surplus"] > 0 else "bad"),
             ("돈이 모자란 해", f"{len(deficit)}년" if len(deficit) else "없음", f"{years}년 중", "warn" if len(deficit) else "ok"),
             ("현금·예금이 바닥나는 때", f"{int(broke.iloc[0]['연차'])}년차" if len(broke) else "기간 안에는 없음", "투자자산 매도는 반영 안 함", "bad" if len(broke) else "ok")])
    if len(broke) and incl:
        callout("보증금 반환까지 반영하면 현금·예금이 부족해져요. ‘💱 현금 마련해 보기’ 탭에서 투자자산 일부를 현금으로 바꾸면 어떻게 되는지 확인해 보세요.", "warn")
    st.write("")

    st.markdown("**① 해마다 남는 돈(초록) · 모자란 돈(빨강)**")
    bars_by_year(df, "연간현금흐름", "그해 남는 돈 (만원)")
    st.markdown("**② 현금·예금 잔액이 이렇게 변해요**")
    chart_df = pd.concat([pd.DataFrame([{"연차": 0, "현금·예금 잔액": c["liquid"]}]),
                          df[["연차", "잔액"]].rename(columns={"잔액": "현금·예금 잔액"})], ignore_index=True)
    line_by_year(chart_df, ["현금·예금 잔액"], zero_rule=True)
    st.caption("가로축 0은 ‘지금’이에요. 빨간 점선(0원) 아래로 내려가면 현금·예금이 모자란 거예요.")

    with st.expander("표로 보기"):
        seg, start = [], 0
        vals = df["월현금흐름"].round(1).tolist()
        for i in range(1, len(vals) + 1):
            if i == len(vals) or vals[i] != vals[start]:
                y0, y1 = int(df.iloc[start]["연차"]), int(df.iloc[i - 1]["연차"])
                v = vals[start]
                seg.append({"기간": f"{y0}년차" if y0 == y1 else f"{y0}~{y1}년차", "한 달 돈 흐름": f"{'🟢' if v > 0 else '🔴'} {won(v)}",
                            "기간 한정 지출(월 환산)": won(df.iloc[start]["기간한정지출월"])})
                start = i
        show_df(pd.DataFrame(seg))
    note("월 잉여자금과 입력한 예정 지출만 반영한 단순 추정이에요. 투자수익·세금·물가는 넣지 않았어요.")


def short_label(kw: dict) -> str:
    """상황을 '소득 20% 감소'처럼 짧은 명사형으로 줄여요. (요약 문장에서 어색하지 않게)"""
    parts = []
    if kw.get("income_pct"):
        parts.append(f"소득 {abs(kw['income_pct']):g}% 감소")
    if kw.get("rate_delta"):
        parts.append(f"대출 금리 {kw['rate_delta']:g}%p 상승")
    if kw.get("vacancy_pct"):
        v = kw["vacancy_pct"]
        parts.append("월세 수입 절반 감소" if v == 50 else f"월세 수입 {v:g}% 감소")
    if kw.get("market_drop"):
        parts.append(f"주식시장 {kw['market_drop']:g}% 하락")
    if kw.get("one_off"):
        parts.append(f"{won(kw['one_off'])} 갑작스러운 지출")
    if kw.get("deposit_out"):
        parts.append(f"보증금 {won(kw['deposit_out'])} 반환")
    if len(parts) >= 3:
        return "여러 일이 한꺼번에 겹칠 때"
    return " + ".join(parts) or "가정 상황"


def bullet_html(items) -> str:
    li = "".join(f"<li>{esc(x)}</li>" for x in items)
    return f"<ul style='margin:6px 0 0 18px;padding:0'>{li}</ul>"


def tab_whatif(S, c):
    st.caption("실제 입력값은 바꾸지 않고, ‘만약 이런 일이 생기면?’ 하고 가정만 계산해요.")
    scen = scenario_list(S, c)
    results = [("지금", apply_scenario(S, c))]
    for name, kw, _ in scen:
        results.append((name, apply_scenario(S, c, **kw)))
    base = results[0][1]

    table = []
    for i, (name, s) in enumerate(results):
        table.append({
            "상황": name,
            "월 잉여자금": f"{'🟢' if s['surplus'] > 0 else '🔴'} {won(s['surplus'])}",
            "현금·예금": won(s["liquid"]),
            "비상자금": fmt_runway(s["liquid"], s["runway"]),
            "순자산": won(s["net"]),
            "순자산 지금 대비": "기준" if i == 0 else signed(s["net"] - c["net"]),
        })
    show_df(pd.DataFrame(table))
    for name, _, desc in scen:
        if desc:
            st.caption(f"ℹ️ ‘{name}’ = {desc}")

    st.markdown("**그래프로 비교하기**")
    g1, g2, g3 = st.tabs(["💰 매달 남는 돈", "🏦 순자산 변화", "🛟 비상자금"])
    with g1:
        d = pd.DataFrame([{
            "name": n, "v": s["surplus"], "label": won(s["surplus"]),
            "color": NAVY if i == 0 else ("#16a34a" if s["surplus"] > 0 else "#dc2626")} for i, (n, s) in enumerate(results)])
        bars_by_cat(d, "월 잉여자금 (만원)")
        if c["stocks"] + c["crypto"] > 0:
            st.caption("📉 주식시장 하락은 매달 들어오고 나가는 돈을 바꾸지 않아서 이 그래프에서는 ‘지금’과 같아요. "
                       "영향은 ‘🏦 순자산 변화’ 탭에서 확인하세요.")
    with g2:
        rows = []
        for i, (n, s) in enumerate(results):
            dv = s["net"] - c["net"]
            color = NAVY if i == 0 else ("#dc2626" if dv < -0.05 else "#16a34a" if dv > 0.05 else "#98a2b3")
            rows.append({"name": n, "v": dv, "label": "기준" if i == 0 else signed(dv), "color": color})
        bars_by_cat(pd.DataFrame(rows), "순자산이 지금보다 얼마나 달라지나 (만원)")
        st.caption("순자산은 ‘지금보다 얼마나 줄어드는지’로 보여줘요. 주식·가상자산 하락과 갑자기 나가는 큰돈이 순자산을 바꿔요. "
                   "보증금 반환은 현금과 빚이 함께 줄어 순자산은 그대로예요.")
    with g3:
        rows = []
        for i, (n, s) in enumerate(results):
            if s["runway"] is None:
                continue
            val = 0.0 if s["liquid"] < 0 else s["runway"]
            color = "#dc2626" if (s["liquid"] < 0 or val < 1) else "#eab308" if val < 3 else "#16a34a"
            rows.append({"name": n, "v": val, "label": fmt_runway(s["liquid"], s["runway"]), "color": color})
        if rows:
            bars_by_cat(pd.DataFrame(rows), "현금·예금으로 버틸 수 있는 기간 (개월)", axis_fmt=",.0f")
            st.caption("🔴 1개월 미만(또는 현금 부족) · 🟡 3개월 미만 · 🟢 3개월 이상. 현금이 모자라면 막대 대신 ‘현금 얼마 부족’으로 표시해요.")
        else:
            st.info("월 지출을 입력하면 비상자금 비교를 볼 수 있어요.")

    # ---- 한눈에 보는 결과 (자동 요약) ----
    st.markdown("**한눈에 보는 결과**")
    pairs = [(short_label(kw), s) for (_, kw, _), (_, s) in zip(scen, results[1:])]

    if base["surplus"] <= 0:
        callout("지금도 매달 남는 돈이 없어요. 아래 상황은 더 어려울 수 있으니, 먼저 ‘내 재무 한눈에’에서 월 수입·지출부터 점검해 보세요.",
                "bad", "💰 매달 남는 돈")
    else:
        bad = [n for n, s in pairs if s["surplus"] <= 0]
        if bad:
            callout("아래 상황이 생기면 <b>매달 남는 돈이 없거나 모자라게 돼요.</b>" + bullet_html(bad), "bad", "💰 매달 남는 돈")
        else:
            callout("위 상황에서도 매달 남는 돈은 플러스를 유지해요. 다만 여러 일이 겹칠 때를 대비해 비상자금은 따로 챙겨 두세요.",
                    "ok", "💰 매달 남는 돈")

    if base["liquid"] >= 0:
        short = [n for n, s in pairs if s["liquid"] < 0]
        if short:
            callout("아래 상황이 생기면 <b>지금 가진 현금·예금만으로는 부족해요.</b>" + bullet_html(short) +
                    "<div style='margin-top:6px'>‘현금 마련해 보기’ 탭에서 투자자산 일부를 현금으로 바꾸면 얼마나 채워지는지 확인해 보세요.</div>",
                    "warn", "🛟 현금·예금")

    worst_name, worst_s = min(pairs, key=lambda r: r[1]["net"])
    drop = worst_s["net"] - c["net"]
    if drop < -0.05:
        callout(f"순자산이 가장 많이 줄어드는 경우는 <b>{esc(worst_name)}</b>이에요. 지금보다 약 <b>{won(-drop)}</b> 줄어요.",
                "warn", "🏦 순자산")

    if c["stocks"] + c["crypto"] > 0:
        st.caption("📉 주식시장 하락은 일반 주식 20%, 변동이 큰 종목·가상자산은 그 2배(40%) 떨어진다고 가정했어요.")
    base_inc = c["income"] - A(S, "rent_income")
    if c["surplus"] > 0 and base_inc > 0:
        st.caption(f"💡 월급·사업소득이 약 {c['surplus'] / base_inc * 100:.0f}% 줄면 매달 남는 돈이 0원이 돼요.")

    with st.expander("직접 값을 바꿔 보기"):
        a, b = st.columns(2)
        inc = a.slider("월급·사업소득 변화 (%)", -80, 50, 0, step=5)
        exp = a.slider("월 지출 변화 (만원)", -100, 200, 0, step=10)
        rate = 0.0
        if c["mortgage"] > 0:
            rate = a.slider("대출 금리 변화 (%p)", -2.0, 5.0, 0.0, step=0.5)
        vac = 0
        if A(S, "rent_income") > 0:
            vac = a.slider("월세 수입이 줄어드는 비율 (%)", 0, 100, 0, step=10)
        one = b.slider("한 번에 나가는 큰돈 (만원)", 0, 10000, 0, step=100)
        dep = 0.0
        nd = int(c["near_deposit"])
        if nd >= 1:
            dstep = 500 if nd >= 5000 else 100 if nd >= 500 else 10 if nd >= 50 else 1
            dep = float(b.slider("돌려줄 보증금 (만원)", 0, nd, 0, step=dstep))
        drop_pct = b.slider("주식시장 하락률 (%)", 0, 60, 0, step=5)
        mult = b.slider("변동이 큰 자산은 시장보다 몇 배 출렁일까요?", 1.0, 3.0, 2.0, step=0.5,
                        help="레버리지 ETF 배수나 종목 특성에 따라 달라요. 잘 모르면 2배 정도로 두세요.")
        s = apply_scenario(S, c, income_pct=inc, vacancy_pct=vac, rate_delta=rate, expense_delta=exp, one_off=one,
                           market_drop=drop_pct, vol_mult=mult, deposit_out=dep)
        show_df(pd.DataFrame([
            {"지표": "월 소득", "지금": won(c["income"]), "가정 후": won(s["income"])},
            {"지표": "월 지출", "지금": won(c["outflow"]), "가정 후": won(s["outflow"])},
            {"지표": "월 잉여자금", "지금": won(c["surplus"]), "가정 후": won(s["surplus"])},
            {"지표": "현금·예금", "지금": won(c["liquid"]), "가정 후": won(s["liquid"])},
            {"지표": "순자산", "지금": won(c["net"]), "가정 후": won(s["net"])},
            {"지표": "비상자금", "지금": fmt_runway(c["liquid"], c["runway"]), "가정 후": fmt_runway(s["liquid"], s["runway"])},
        ]))
        if s["surplus"] < 0:
            callout(f"이 가정에서는 매달 <b>{won(abs(s['surplus']))}</b>이 모자라요.", "bad")
        if s["liquid"] < 0:
            callout("필요한 큰돈이 현재 현금·예금보다 커요. 자산을 팔거나 빌려야 할 수 있어요.", "warn")

    with st.expander("변동이 큰 자산, 왜 조심해야 하나요?"):
        st.markdown("손실이 커질수록 **본전으로 돌아오기 위해 필요한 수익률은 더 크게** 늘어나요.")
        show_df(pd.DataFrame([{"떨어진 폭": f"−{d}%", "본전까지 필요한 상승률": f"+{d / (100 - d) * 100:.0f}%"} for d in (10, 20, 30, 50, 70)]))
        st.markdown("특히 지수의 2배·3배로 움직이는 상품(레버리지 ETF) 등은 같은 시장 움직임에도 훨씬 크게 출렁이고, "
                    "오르내림이 반복되면 시장이 제자리여도 원금이 줄어들 수 있어요. 배수와 구조는 상품마다 달라요.")
        note("단순한 산술 예시이며 특정 상품의 실제 성과를 예측하지 않아요.")
    note("사용자가 정한 가정의 산술 결과예요. 미래를 예측하거나 일어날 확률을 뜻하지 않아요.")


def tab_rebalance(S, c):
    st.caption("변동이 큰 자산의 일부를 현금·예금으로 바꾸면 비상자금, 큰돈 준비율, 시장 하락 때의 손실이 어떻게 달라지는지 미리 봐요.")
    hr = c["high_risk"]
    if hr <= 0:
        st.info("변동이 큰 종목이나 가상자산을 입력하면, 일부를 현금으로 바꿨을 때의 변화를 볼 수 있어요.")
        st.button("① 자산 입력하러 가기", on_click=goto_step, args=(0,), **FULL)
        return
    default = 30
    if c["big_need"] > 0 and c["liquid"] < c["big_need"]:
        default = min(100, int(math.ceil((c["big_need"] - c["liquid"]) / hr * 100 / 5.0) * 5))
        default = max(5, default)
    p = st.slider("변동이 큰 자산 중 현금·예금으로 바꿀 비율 (%)", 0, 100, default, step=5,
                  help="변동이 큰 종목과 가상자산을 같은 비율로 줄인다고 가정해요.")
    f = p / 100
    sell = hr * f
    liquid2 = c["liquid"] + sell
    vol2, cry2, stocks2 = c["volatile"] * (1 - f), c["crypto"] * (1 - f), c["stocks"] - c["volatile"] * f
    hr2 = hr - sell
    runway2 = None if c["outflow"] <= 0 else liquid2 / c["outflow"]
    loss1 = market_loss(c["stocks"], c["volatile"], c["crypto"], 30, 2.0)
    loss2 = market_loss(stocks2, vol2, cry2, 30, 2.0)

    kpi_row([("현금·예금으로 바꿀 금액", won(sell), f"변동 큰 자산 {won(hr)}의 {p}%", "info"),
             ("바꾼 뒤 현금·예금", won(liquid2), f"지금 {won(c['liquid'])}", "ok"),
             ("바꾼 뒤 비상자금", fmt_months(runway2), f"지금 {fmt_months(c['runway'])}", "ok" if (runway2 or 0) >= 3 else "warn")])
    st.write("")
    rows = [{"지표": "현금·예금", "지금": won(c["liquid"]), "바꾼 뒤": won(liquid2)},
            {"지표": "변동 큰 자산", "지금": won(hr), "바꾼 뒤": won(hr2)},
            {"지표": "금융자산 중 변동 큰 자산 비중", "지금": pct(c["high_risk_ratio"]), "바꾼 뒤": pct(ratio(hr2, c["financial"]))},
            {"지표": "비상자금", "지금": fmt_months(c["runway"]), "바꾼 뒤": fmt_months(runway2)},
            {"지표": "시장 30% 하락 시 줄어드는 금액", "지금": won(loss1), "바꾼 뒤": won(loss2)}]
    if c["big_need"] > 0:
        rows.insert(4, {"지표": f"1년 안에 필요한 {won(c['big_need'])} 준비율", "지금": pct(c["readiness"]), "바꾼 뒤": pct(ratio(liquid2, c["big_need"]))})
    show_df(pd.DataFrame(rows))
    if c["big_need"] > 0:
        short = c["big_need"] - liquid2
        if short > 0:
            callout(f"이 비율로 바꿔도 1년 안에 필요한 돈이 <b>{won(short)}</b> 부족해요. 비율을 더 높이거나 다른 마련 방법(대출 가능 여부, 새 세입자 확보 등)을 함께 살펴보세요.", "warn")
        else:
            callout("이 비율이면 1년 안에 필요한 큰돈을 현금·예금으로 채울 수 있어요. 다만 생활비·비상자금은 따로 남는지 위 표에서 확인하세요.", "ok")
    note("세금·수수료·매도 시점의 가격 변동은 반영하지 않은 단순 계산이에요. 특정 상품을 팔라는 권유가 아니라, 계획을 세울 때 참고하는 계산이에요.")


def tab_goal(S, c):
    target = c["target"]
    if target <= 0:
        st.info("목표 금액을 입력하면 매달 얼마를 모아야 하는지 계산해 드려요.")
        st.button("④ 목표 입력하러 가기", on_click=goto_step, args=(3,), **FULL)
        return
    saved, years = c["saved"], int(S["years"])
    n = years * 12
    if c["target_auto"]:
        st.caption("목표 금액은 ‘월 지출 × 6개월’로, 모은 금액은 ‘현재 현금·예금’으로 자동 계산했어요.")
    ret = st.slider("예상 연 수익률 (%)", 0.0, 15.0, 3.0, step=0.5,
                    help="저축·투자로 매년 얼마나 늘어난다고 가정할지예요. 0%는 이자 없이 저금만 하는 경우예요. 수익률은 보장되지 않아요.")
    if ret > 8:
        st.caption("⚠️ 높은 수익률은 큰 손실 가능성과 함께 와요. 연 8%가 넘는 가정은 참고용으로만 보세요.")
    m = ret / 1200
    req = req_monthly(target, saved, years, ret)
    avail = c["surplus"]
    kpi_row([("목표 금액", won(target), f"{years}년 뒤", "info"), ("이미 모은 금액", won(saved), "", "neutral"),
             ("필요한 월 저축액", won(req), f"연 {ret:.1f}% 가정", "warn" if req > avail else "ok"),
             ("지금 매달 남는 돈", won(avail), "월 잉여자금", "ok" if avail >= req else "warn")])
    st.write("")
    if c["target_gap"] <= 0:
        callout("이미 목표 금액을 모았어요! 🎉", "ok")
    elif avail <= 0:
        callout("지금은 매달 남는 돈이 없어서 저축으로 목표를 모으기 어려워요. 먼저 ‘내 재무 한눈에’에서 현금흐름을 점검해 보세요.", "bad")
    elif avail >= req:
        mths = months_to_reach(target, saved, avail, m)
        callout(f"지금 남는 돈을 전부 저축한다고 가정하면 목표 기간 안에 달성할 수 있어요 (약 {mths}개월). 다만 비상자금과 예정 지출은 따로 챙기세요.", "ok")
    else:
        mths = months_to_reach(target, saved, avail, m)
        when = f"약 {mths}개월({mths / 12:.1f}년)" if mths else "100년 안에는 어려워요"
        callout(f"매달 <b>{won(req - avail)}</b>이 더 필요해요. 지금 남는 돈만으로는 목표 달성까지 {when} 걸려요. 수익률·기간·목표 금액을 바꿔 보세요.", "warn")

    avail_pos = max(avail, 0.0)
    rows = [{"연차": 0, "지금 남는 돈만 저축": saved, "목표에 맞춰 저축": saved, "목표 금액": target}]
    b_a, b_r = saved, saved
    for k in range(1, n + 1):
        b_a = b_a * (1 + m) + avail_pos
        b_r = b_r * (1 + m) + req
        if k % 12 == 0:
            rows.append({"연차": k // 12, "지금 남는 돈만 저축": b_a, "목표에 맞춰 저축": b_r, "목표 금액": target})
    st.markdown(f"**모은 돈이 이렇게 늘어나요 (연 {ret:.1f}% 가정)**")
    line_by_year(pd.DataFrame(rows), ["지금 남는 돈만 저축", "목표에 맞춰 저축", "목표 금액"], dashed=("목표 금액",))

    with st.expander("수익률에 따라 필요한 월 저축액이 얼마나 달라질까요?"):
        show_df(pd.DataFrame([{"연 수익률": f"{r}%", "필요한 월 저축액": won(req_monthly(target, saved, years, r))} for r in (0, 2, 3, 5, 7, 10)]))
        note("수익률이 높을수록 적게 모아도 되지만, 높은 수익률은 손실 위험도 함께 커요.")
    note("매달 같은 금액을 저축한다고 가정한 단순 계산이에요. 세금·수수료·물가·소득 변화는 넣지 않았어요.")


def page_sim(S, c):
    hero("앞으로 시뮬레이션", "해마다 돈 흐름, 만약의 상황, 현금 마련, 목표 달성까지 미리 계산해 봐요.")
    if not need_data(c):
        return
    t1, t2, t3, t4 = st.tabs(["📅 해마다 돈 흐름", "⚠️ 만약 이런 일이 생기면?", "💱 현금 마련해 보기", "🎯 목표 달성"])
    with t1:
        tab_timeline(S, c)
    with t2:
        tab_whatif(S, c)
    with t3:
        tab_rebalance(S, c)
    with t4:
        tab_goal(S, c)


# ============================================================


# ============================================================
# 12. 실행 계획·저장
# ============================================================
def build_report_html(S, c, checks) -> str:
    def tbl(rows, cols):
        return pd.DataFrame(rows, columns=cols).to_html(index=False, escape=True, border=0, classes="t")
    asset_rows = [["현금·예금", won(c["liquid"])], ["주식·ETF", won(c["stocks"])], ["가상자산", won(c["crypto"])], ["연금계좌", won(c["pension"])],
                  ["부동산", won(c["property"])], ["기타", won(c["other_assets"])], ["총자산", won(c["assets"])]]
    debt_rows = [["주택담보대출", won(c["mortgage"])], ["신용·기타 대출", won(c["credit"] + c["other_debt"])],
                 ["세입자 보증금(돌려줄 돈)", won(c["deposits_owed"])], ["총부채", won(c["debts"])], ["순자산(자산−부채)", won(c["net"])]]
    flow_rows = [["월 소득", won(c["income"])], ["월 지출(대출 상환 포함)", won(c["outflow"])], ["월 잉여자금", won(c["surplus"])]]
    tl = build_timeline(S, c, 8, c["near_deposit"])
    tl_rows = [[f"{int(r['연차'])}년차", won(r["연간현금흐름"]), won(r["잔액"])] for _, r in tl.iterrows()]

    sc_rows = [["지금", won(c["surplus"]), won(c["liquid"]), fmt_runway(c["liquid"], c["runway"]), "기준"]]
    for name, kw, _ in scenario_list(S, c):
        s = apply_scenario(S, c, **kw)
        sc_rows.append([name, won(s["surplus"]), won(s["liquid"]), fmt_runway(s["liquid"], s["runway"]), signed(s["net"] - c["net"])])

    cards = "".join(f"<div class='d' style='border-left:6px solid {BAR[x['tone']]}'><b>{TONE_EMOJI[x['tone']]} {esc(x['title'])} — {esc(x['headline'])}</b><br>{esc(x['meaning'])}<br>"
                    f"<small>계산: {esc(x['evidence'])}<br>다음 행동: {esc(x['action'])}</small></div>" for x in checks)
    dep_note = "<li>해마다 돈 흐름 표는 1년 안에 돌려줄 보증금이 1년차에 빠져나가는 것으로 계산했습니다.</li>" if c["near_deposit"] > 0 else ""
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>머니체크 재무 리포트</title>
<style>body{{font-family:'Pretendard','Malgun Gothic',sans-serif;max-width:820px;margin:30px auto;color:#14213d;line-height:1.65;padding:0 16px}}
h1{{color:#0f766e}}h2{{border-bottom:2px solid #0f766e;padding-bottom:4px;margin-top:28px}}
table.t{{border-collapse:collapse;width:100%;margin:8px 0}}table.t th,table.t td{{border:1px solid #d0d5dd;padding:6px 10px;text-align:left}}
table.t th{{background:#f2f4f7}}.d{{border:1px solid #e4e7ec;border-radius:10px;padding:10px 14px;margin:8px 0}}small,.f{{color:#667085}}</style></head><body>
<h1>머니체크 재무 리포트</h1><p class="f">작성일 {date.today().isoformat()} · 금액 단위 만원 · 입력값 기반 참고 자료</p>
<h2>1. 재무상태</h2><p>총자산 {esc(won(c['assets']))} − 총부채 {esc(won(c['debts']))} = <b>순자산 {esc(won(c['net']))}</b> · 신호등 점수 {score_of(checks)}/100</p>
{tbl(asset_rows, ['자산', '금액'])}{tbl(debt_rows, ['부채·순자산', '금액'])}
<h2>2. 한 달 수입·지출</h2>{tbl(flow_rows, ['항목', '월 금액'])}
<h2>3. 해마다 돈 흐름</h2>{tbl(tl_rows, ['연차', '그해 남는 돈', '현금·예금 잔액(추정)'])}
<h2>4. 만약 이런 일이 생기면? (가정 계산)</h2>{tbl(sc_rows, ['상황', '월 잉여자금', '현금·예금', '비상자금', '순자산 지금 대비'])}
<h2>5. 신호등 진단과 다음 행동</h2>{cards}
<h2>6. 알아두세요</h2><ul><li>입력값을 바탕으로 한 참고 자료이며 세무·법률·투자 판단을 대신하지 않습니다.</li>
<li>세금·수수료·투자수익·물가는 반영하지 않았습니다.</li><li>가정 계산은 미래 예측이나 발생 확률이 아닙니다.</li>
<li>월 상환액/월 소득은 참고 비율이며 금융기관의 DSR이 아닙니다.</li>{dep_note}</ul></body></html>"""


def page_plan(S, c):
    hero("실행 계획·저장", "지금 할 일을 순서대로 정리하고, 입력한 내용을 파일로 저장해요.")
    if not need_data(c):
        return
    checks = make_checks(S, c)
    tasks = make_tasks(S, c, checks)
    done = sum(1 for t in tasks if S["checks"].get(t[0]))
    st.progress(done / len(tasks) if tasks else 0.0, text=f"실행 진행률 {done} / {len(tasks)}")
    groups = [("bad", "🔴 먼저 할 일"), ("warn", "🟡 이어서 할 일"), ("ok", "🟢 꾸준히 할 일")]
    for tone, title in groups:
        items = [t for t in tasks if t[1] == tone]
        if not items:
            continue
        st.markdown(f"#### {title}")
        for tid, _, name, desc in items:
            with st.container(border=True):
                ck = st.checkbox(f"**{name}**", value=bool(S["checks"].get(tid, False)), key=f"w_chk_{tid}")
                S["checks"][tid] = ck
                st.caption(desc)
    st.divider()
    section("저장하기", "이 앱은 새로고침하면 입력값이 사라져요. 파일로 저장해 두면 다음에 이어서 쓸 수 있어요.")
    a, b = st.columns(2)
    a.download_button("📄 결과 리포트 (HTML)", data=build_report_html(S, c, checks).encode("utf-8"),
                      file_name=f"머니체크_리포트_{date.today().isoformat()}.html", mime="text/html", type="primary", **FULL_DL)
    b.download_button("💾 입력값 저장 (JSON)", data=json.dumps({"app": "moneycheck", "version": 7, "data": S}, ensure_ascii=False, indent=2, default=float).encode("utf-8"),
                      file_name=f"머니체크_입력값_{date.today().isoformat()}.json", mime="application/json", **FULL_DL)
    st.caption("리포트는 브라우저에서 열어 인쇄(Ctrl+P) → ‘PDF로 저장’을 고르면 PDF로 보관할 수 있어요.")
    up = st.file_uploader("저장해 둔 입력값(JSON) 불러오기", type=["json"])
    if up is not None:
        fid = f"{up.name}-{up.size}"
        if st.session_state.get("_loaded_file") != fid:
            ok, msg = import_json(up.getvalue())
            if ok:
                st.session_state["_loaded_file"] = fid
                st.rerun()
            else:
                st.error(msg)
        else:
            st.success("저장된 입력값을 불러왔어요.")


# ============================================================
# 13. 사이드바 · 화면 연결
# ============================================================
P_HOME, P_INPUT, P_SNAP = "🏠 시작하기", "✍️ 내 정보 입력", "📊 내 재무 한눈에"
P_SIM, P_PLAN = "🔮 앞으로 시뮬레이션", "✅ 실행 계획·저장"
PAGES = [P_HOME, P_INPUT, P_SNAP, P_SIM, P_PLAN]

init_state()
S = st.session_state["mc"]

st.sidebar.markdown('<div class="brand">💚 머니체크</div><div class="brand-sub">내 돈을 이해하는 가장 쉬운 첫걸음</div>', unsafe_allow_html=True)
page = st.sidebar.radio("메뉴", PAGES, key="nav", label_visibility="collapsed")
side_summary = st.sidebar.container()
with st.sidebar.expander("📖 쉬운 용어 사전"):
    for term, desc in GLOSSARY:
        st.markdown(f"**{term}** — {desc}")
st.sidebar.button("입력 정보 모두 지우기", on_click=reset_all, **FULL)
st.sidebar.caption("계좌번호·주민등록번호·비밀번호는 입력하지 마세요.")

_c = calculate(S)
if page == P_HOME:
    page_home(S, _c)
elif page == P_INPUT:
    page_input(S)
else:
        {P_SNAP: page_snapshot, P_SIM: page_sim, P_PLAN: page_plan}[page](S, _c)
    
_cf = calculate(S)  # 입력 화면에서 바뀐 최신 값으로 사이드바 요약 갱신
if has_data(_cf):
    with side_summary:
        st.divider()
        st.caption("내 요약")
        st.markdown(f"**순자산** {won(_cf['net'])}  \n**월 잉여** {won(_cf['surplus'])}  \n**비상자금** {fmt_runway(_cf['liquid'], _cf['runway'])}")

st.divider()
st.caption("머니체크 · 사용자의 이해와 선택을 돕는 재무 점검 도구 (참고용)")
