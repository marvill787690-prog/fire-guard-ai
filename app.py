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

try:  # AI 재무코치용 (설치되어 있지 않아도 앱이 멈추지 않도록)
    from google import genai
except Exception:  # noqa: BLE001
    genai = None

# ============================================================
# 머니체크 v3 | 처음 해보는 사람도 쉽게 쓰는 가계 재무진단
# - 재무 계산은 규칙 기반(직접 계산), 설명은 선택적으로 Gemini AI 코치가 도와줘요.
# - 모든 금액 단위: 만원
# ============================================================

st.set_page_config(
    page_title="머니체크 | 내 돈을 쉽게 이해하기",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- Gemini 설정 ----------------
GEMINI_MODEL = "gemini-3.5-flash-lite"  # 사용 가능한 다른 모델명으로 바꿔도 돼요


def _read_api_key() -> str:
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:  # secrets.toml이 없을 때도 앱이 죽지 않게
        return ""


GEMINI_API_KEY = _read_api_key()
gemini_client = None
if genai is not None and GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:  # noqa: BLE001
        gemini_client = None


def ask_gemini(prompt: str) -> str:
    if gemini_client is None:
        return "현재 AI 재무코치를 사용할 수 없습니다. 잠시 후 다시 시도해주세요."

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            if response.text:
                return response.text
            return "AI가 분석 결과를 생성하지 못했습니다. 잠시 후 다시 시도해주세요."
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            # 일시적인 서버 과부하 또는 요청 제한 → 재시도
            if "503" in msg or "UNAVAILABLE" in msg or "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                return "현재 AI 분석 요청이 많아 분석을 완료하지 못했습니다. 잠시 후 다시 시도해주세요."
            if "401" in msg or "403" in msg:
                return "AI 서비스 인증에 문제가 발생했습니다. 관리자 설정을 확인해주세요."
            if "404" in msg:
                return "현재 AI 모델을 사용할 수 없습니다. 모델 이름(GEMINI_MODEL)을 확인해주세요."
            return "AI 분석 중 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
    return "AI 분석 중 일시적인 문제가 발생했습니다."


# Streamlit 버전별 width 옵션 호환 (use_container_width → width="stretch")
_HAS_WIDTH = "width" in inspect.signature(st.button).parameters
FULL = {"width": "stretch"} if _HAS_WIDTH else {"use_container_width": True}


# ============================================================
# 1. 디자인 (읽기 쉽고 단순하게)
# ============================================================
st.markdown(
    """
    <style>
      @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
      :root{ --ink:#14213d; --sub:#475467; --mute:#667085; --line:#e4e7ec; --brand:#0f766e; --navy:#17324d; }
      .stApp{ font-family:'Pretendard',-apple-system,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif; }
      .block-container{ max-width:1020px; padding-top:1.2rem; padding-bottom:4rem; }
      h1,h2,h3,h4{ letter-spacing:-.025em; color:var(--ink); }
      [data-testid="stWidgetLabel"] p{ font-size:1rem; font-weight:600; color:var(--ink); }
      [data-testid="stSidebar"]{ background:#f6f8fb; border-right:1px solid var(--line); }
      [data-testid="stSidebar"] [role="radiogroup"] label{ padding:9px 12px; border-radius:11px; margin-bottom:3px; width:100%; }
      [data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:#e8f1f0; }
      .brand{ font-size:1.3rem; font-weight:800; color:var(--navy); }
      .brand-sub{ color:var(--mute); font-size:.85rem; margin:-2px 0 12px 0; }

      .hero{ background:linear-gradient(120deg,#17324d 0%,#0f766e 100%); color:#fff; border-radius:18px; padding:24px 28px; margin:0 0 18px 0; }
      .hero h1{ color:#fff; font-size:1.7rem; line-height:1.35; margin:0 0 6px 0; }
      .hero p{ color:#eaf7f5; margin:0; font-size:1.02rem; line-height:1.65; }

      .kpi{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px 16px; height:100%; }
      .kpi-l{ color:var(--mute); font-size:.85rem; font-weight:600; margin-bottom:4px; }
      .kpi-v{ color:var(--ink); font-size:1.5rem; font-weight:800; letter-spacing:-.03em; line-height:1.25; }
      .kpi-s{ color:var(--mute); font-size:.8rem; margin-top:4px; line-height:1.45; }

      .card{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 18px; height:100%; }
      .card h4{ margin:0 0 6px 0; font-size:1.05rem; }
      .card p{ margin:0; color:var(--sub); font-size:.93rem; line-height:1.6; }
      .card .step{ color:var(--brand); font-weight:800; font-size:.78rem; letter-spacing:.06em; margin-bottom:4px; }
      .callout{ border-radius:14px; padding:14px 16px; line-height:1.7; font-size:.97rem; margin:8px 0; }
      .callout b.t{ display:block; margin-bottom:2px; }
      .tiny{ color:var(--mute); font-size:.82rem; line-height:1.55; }

      /* 신호등 카드 */
      .check{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px 18px; margin:10px 0; }
      .check-t{ color:var(--mute); font-size:.85rem; font-weight:700; }
      .check-h{ color:var(--ink); font-size:1.18rem; font-weight:800; margin:2px 0 6px 0; line-height:1.4; }
      .check-m{ color:var(--sub); font-size:.95rem; line-height:1.65; }
      .check-a{ margin-top:8px; padding:8px 12px; background:#f8fafc; border-radius:10px; color:var(--ink); font-size:.93rem; line-height:1.6; }
      .check-e{ margin-top:6px; color:var(--mute); font-size:.8rem; }

      /* 자산 − 부채 = 순자산 */
      .eq{ display:flex; align-items:stretch; gap:10px; flex-wrap:wrap; margin:6px 0 10px 0; }
      .eqbox{ flex:1; min-width:150px; background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
      .eqbox span{ display:block; color:var(--mute); font-size:.85rem; font-weight:600; }
      .eqbox b{ font-size:1.45rem; color:var(--ink); letter-spacing:-.03em; }
      .eqbox.net{ background:#f0faf8; border:2px solid var(--brand); }
      .op{ display:flex; align-items:center; justify-content:center; font-size:1.7rem; font-weight:800; color:var(--mute); }
      .oplock{ text-align:center; font-size:1.6rem; font-weight:800; color:var(--mute); padding-top:1.7rem; }

      div[data-testid="stExpander"]{ border:1px solid var(--line); border-radius:13px; background:#fff; }
      div.stButton > button, div[data-testid="stDownloadButton"] button{ border-radius:11px; min-height:2.7rem; font-weight:650; }
      button[data-baseweb="tab"]{ font-weight:650; font-size:1rem; }
      @media (max-width:720px){ .hero{padding:18px;} .hero h1{font-size:1.4rem;} .op{display:none;} }
    </style>
    """,
    unsafe_allow_html=True,
)

TONES = {  # (글자색, 배경색, 테두리색)
    "ok": ("#067647", "#ecfdf3", "#abefc6"),
    "warn": ("#b54708", "#fffaeb", "#fedf89"),
    "bad": ("#b42318", "#fef3f2", "#fecdca"),
    "info": ("#175cd3", "#eff8ff", "#b2ddff"),
    "neutral": ("#344054", "#f2f4f7", "#d0d5dd"),
}
TONE_EMOJI = {"ok": "🟢", "warn": "🟡", "bad": "🔴", "info": "🔵", "neutral": "⚪"}
TONE_ORDER = {"bad": 0, "warn": 1, "info": 2, "ok": 3, "neutral": 4}


def esc(x) -> str:
    return html.escape(str(x))


def kpi(label, value, sub="", tone="neutral") -> str:
    fg = TONES[tone][0]
    return (f'<div class="kpi" style="border-top:4px solid {fg}"><div class="kpi-l">{esc(label)}</div>'
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
        st.dataframe(df, hide_index=True, **FULL)
    except TypeError:
        st.dataframe(df, hide_index=True)


def equation_html(a_label, a_val, b_label, b_val, r_label, r_val) -> str:
    return (f'<div class="eq"><div class="eqbox"><span>{esc(a_label)}</span><b>{esc(a_val)}</b></div><div class="op">−</div>'
            f'<div class="eqbox"><span>{esc(b_label)}</span><b>{esc(b_val)}</b></div><div class="op">=</div>'
            f'<div class="eqbox net"><span>{esc(r_label)}</span><b>{esc(r_val)}</b></div></div>')


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


def pct(v, d=0) -> str:
    return "해당 없음" if v is None or not math.isfinite(v) else f"{v:.{d}f}%"


def ratio(n, d):
    return None if d is None or d <= 0 else n / d * 100


def fmt_months(v) -> str:
    if v is None:
        return "지출 입력 필요"
    return "계산할 수 없음" if not math.isfinite(v) else f"{v:.1f}개월"


# ============================================================
# 3. 상태 관리
# ============================================================
GOALS = ["전반적인 재무 점검", "비상자금 마련", "빚 갚기", "결혼 자금", "내 집 마련", "자녀 교육비", "은퇴 준비", "자산 불리기"]
KNOW = ["있어요", "없어요", "잘 모르겠어요"]
STEPS = ["① 자산", "② 부채", "③ 월 수입·지출", "④ 목표·예정"]
MONTHLY_KEYS = ["income", "rent_income", "other_income", "living_cost", "insurance_premium", "other_fixed", "irregular_monthly", "debt_payment"]

DEFAULTS = {
    "goal": GOALS[0], "years": 3, "target": 0.0, "already_saved": 0.0,
    # 자산
    "cash": 0.0, "deposits": 0.0, "stocks": 0.0, "leverage": 0.0, "crypto": 0.0, "pension": 0.0,
    "property": 0.0, "other_assets": 0.0,
    # 부채
    "mortgage": 0.0, "credit": 0.0, "other_debt": 0.0, "deposits_owed": 0.0, "near_deposit": 0.0,
    "debt_mode": "직접 입력", "debt_payment": 0.0, "loan_rate": 4.0, "loan_years": 30.0,
    # 월 수입·지출
    "income": 0.0, "rent_income": 0.0, "other_income": 0.0,
    "living_cost": 0.0, "insurance_premium": 0.0, "other_fixed": 0.0, "irregular_monthly": 0.0,
    # 예정 지출
    "t1_name": "", "t1_amt": 0.0, "t1_years": 0.0, "t2_name": "", "t2_amt": 0.0, "t2_years": 0.0,
    "one_name": "", "one_amt": 0.0, "one_months": 6.0,
    # 보험
    "has_silson": KNOW[2], "has_life": KNOW[2],
    "checks": {},
}

DEMOS = {
    "young": {
        "goal": "내 집 마련", "years": 5, "target": 5000.0, "already_saved": 1500.0,
        "cash": 300.0, "deposits": 1500.0, "stocks": 500.0, "pension": 200.0, "other_assets": 5000.0,
        "other_debt": 3000.0, "debt_payment": 25.0,
        "income": 280.0, "living_cost": 150.0, "insurance_premium": 8.0, "other_fixed": 20.0, "irregular_monthly": 15.0,
        "has_silson": "있어요", "has_life": "잘 모르겠어요",
    },
    "family": {  # 공모전 가상 사례(부모 가계)
        "goal": "전반적인 재무 점검", "years": 5, "target": 50000.0, "already_saved": 5000.0,
        "cash": 5000.0, "stocks": 45000.0, "leverage": 45000.0, "crypto": 20000.0, "property": 340000.0,
        "mortgage": 60000.0, "deposits_owed": 65000.0, "near_deposit": 45000.0,
        "debt_mode": "자동 계산", "loan_rate": 4.2, "loan_years": 30.0,
        "income": 450.0, "rent_income": 240.0, "other_income": 150.0,
        "living_cost": 260.0, "insurance_premium": 12.0, "other_fixed": 185.0,
        "t1_name": "자녀 등록금·주거비", "t1_amt": 1200.0, "t1_years": 4.0,
        "t2_name": "아파트 수리비", "t2_amt": 1000.0, "t2_years": 2.0,
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
def num(label, key, S, step=10.0, help=None, max_value=None, container=None, max_hint=""):
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
    if v >= 1000:
        c.caption(f"→ {won(v)}")
    return v


def sel(label, key, S, options, container=None, help=None):
    c = container or st
    wk = f"w_{key}"
    kw = {} if wk in st.session_state else {"index": options.index(S[key]) if S.get(key) in options else 0}
    v = c.selectbox(label, options, key=wk, help=help, **kw)
    S[key] = v
    return v


def radio_h(label, key, S, options, help=None):
    wk = f"w_{key}"
    kw = {} if wk in st.session_state else {"index": options.index(S[key]) if S.get(key) in options else 0}
    v = st.radio(label, options, horizontal=True, key=wk, help=help, **kw)
    S[key] = v
    return v


def txt(label, key, S, container=None, placeholder=""):
    c = container or st
    wk = f"w_{key}"
    kw = {} if wk in st.session_state else {"value": S.get(key, "")}
    v = c.text_input(label, key=wk, placeholder=placeholder, **kw)
    S[key] = v
    return v


# ============================================================
# 4. 계산 (모든 합계는 자동 계산 — 사용자가 직접 바꿀 수 없음)
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


def calculate(S) -> dict:
    cash, deposits, stocks = A(S, "cash"), A(S, "deposits"), A(S, "stocks")
    leverage, crypto, pension = min(A(S, "leverage"), stocks), A(S, "crypto"), A(S, "pension")
    prop, other_assets = A(S, "property"), A(S, "other_assets")
    financial = cash + deposits + stocks + pension + crypto
    assets = financial + prop + other_assets

    mortgage, credit, other_debt = A(S, "mortgage"), A(S, "credit"), A(S, "other_debt")
    dep_owed = A(S, "deposits_owed")
    near_dep = min(A(S, "near_deposit"), dep_owed)
    debts = mortgage + credit + other_debt + dep_owed

    income = A(S, "income") + A(S, "rent_income") + A(S, "other_income")
    pay = monthly_payment(mortgage, A(S, "loan_rate"), A(S, "loan_years")) if S.get("debt_mode") == "자동 계산" else A(S, "debt_payment")
    fixed = A(S, "living_cost") + A(S, "insurance_premium") + A(S, "other_fixed") + A(S, "irregular_monthly")
    outflow = fixed + pay
    surplus = income - outflow
    liquid = cash + deposits
    high_risk = leverage + crypto
    one_amt = A(S, "one_amt")
    one_12m = one_amt if (one_amt > 0 and A(S, "one_months") <= 12) else 0.0
    big_need = near_dep + one_12m

    target_gap = max(0.0, A(S, "target") - A(S, "already_saved"))
    months_goal = max(1, int(A(S, "years") or 3) * 12)
    return {
        "cash": cash, "deposits": deposits, "stocks": stocks, "leverage": leverage, "crypto": crypto,
        "pension": pension, "property": prop, "other_assets": other_assets, "financial": financial,
        "assets": assets, "debts": debts, "net": assets - debts,
        "mortgage": mortgage, "credit": credit, "other_debt": other_debt, "deposits_owed": dep_owed, "near_deposit": near_dep,
        "income": income, "fixed": fixed, "debt_payment": pay, "outflow": outflow, "surplus": surplus,
        "liquid": liquid, "runway": None if outflow <= 0 else liquid / outflow,
        "debt_ratio": ratio(debts, assets), "repayment_ratio": ratio(pay, income), "savings_rate": ratio(surplus, income),
        "high_risk": high_risk, "high_risk_ratio": ratio(high_risk, financial),
        "one_12m": one_12m, "big_need": big_need,
        "readiness": ratio(liquid, big_need) if big_need > 0 else None,
        "target_gap": target_gap, "months_goal": months_goal, "required_monthly": target_gap / months_goal,
    }


def has_data(c) -> bool:
    return c["assets"] > 0 or c["income"] > 0 or c["outflow"] > 0


def build_timeline(S, c, years=10) -> pd.DataFrame:
    terms = term_items(S)
    one_amt, one_m = A(S, "one_amt"), max(1, int(A(S, "one_months") or 1))
    cum, rows = c["liquid"], []
    for y in range(1, years + 1):
        term_m = sum(a / 12 for _, a, n in terms if y <= n)
        month = c["surplus"] - term_m
        one_y = one_amt if (one_amt > 0 and math.ceil(one_m / 12) == y) else 0.0
        cum += month * 12 - one_y
        rows.append({"연차": y, "기간 한정 지출(월)": term_m, "월 현금흐름": month, "일회성 지출": one_y, "현금·예금 잔액(추정)": cum})
    return pd.DataFrame(rows)


def apply_scenario(S, c, income_pct=0.0, vacancy_pct=0.0, rate_delta=0.0, expense_delta=0.0, one_off=0.0, invest_drop=0.0) -> dict:
    rent = A(S, "rent_income")
    new_income = (c["income"] - rent) * (1 + income_pct / 100) + rent * (1 - vacancy_pct / 100)
    pay_delta = 0.0
    if rate_delta and c["mortgage"] > 0:
        pay_delta = (monthly_payment(c["mortgage"], A(S, "loan_rate") + rate_delta, A(S, "loan_years"))
                     - monthly_payment(c["mortgage"], A(S, "loan_rate"), A(S, "loan_years")))
    new_out = max(0.0, c["outflow"] + expense_delta + pay_delta)
    d = invest_drop / 100
    plain = max(0.0, c["stocks"] - c["leverage"])
    loss = plain * d + min(c["leverage"], c["leverage"] * 3 * d) + c["crypto"] * d  # 레버리지는 3배 가정
    liquid = c["liquid"] - one_off
    return {"income": new_income, "outflow": new_out, "surplus": new_income - new_out, "liquid": liquid,
            "net": c["net"] - one_off - loss, "runway": None if new_out <= 0 else liquid / new_out}


def path_example(returns_pct, mult=3, start=100.0) -> pd.DataFrame:
    und, etf = start, start
    rows = [{"단계": 0, "지수": und, "레버리지 ETF": etf}]
    for i, r in enumerate(returns_pct, 1):
        und *= 1 + r / 100
        etf *= max(0.0, 1 + mult * r / 100)
        rows.append({"단계": i, "지수": und, "레버리지 ETF": etf})
    return pd.DataFrame(rows)


def months_to_reach(target, start, pmt, monthly_rate, cap=1200):
    bal = start
    for m in range(1, cap + 1):
        bal = bal * (1 + monthly_rate) + pmt
        if bal >= target:
            return m
    return None


# ============================================================
# 5. 신호등 진단 (쉬운 말 + 계산 근거 + 다음 행동)
# ============================================================
def make_checks(S, c) -> list[dict]:
    out = []

    def add(key, title, tone, headline, meaning, evidence, action):
        out.append({"key": key, "title": title, "tone": tone, "headline": headline,
                    "meaning": meaning, "evidence": evidence, "action": action})

    # 1) 매달 남는 돈
    if c["income"] > 0 or c["outflow"] > 0:
        ev = f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])} = {won(c['surplus'])}"
        if c["surplus"] < 0:
            add("cashflow", "매달 남는 돈", "bad", f"매달 {won(abs(c['surplus']))}이 모자라요",
                "버는 돈보다 쓰는 돈이 많아요. 이 상태가 이어지면 저축이 줄거나 빚이 늘 수 있어요.", ev,
                "쓰는 돈을 '꼭 필요한 것'과 '줄일 수 있는 것'으로 나눠 보세요. 대출 상환액이나 세금이 빠지거나 중복되지 않았는지도 확인하세요.")
        elif (c["savings_rate"] or 0) < 10:
            add("cashflow", "매달 남는 돈", "warn", f"매달 {won(c['surplus'])}이 남아요 (많지 않아요)",
                "남는 돈이 소득의 10%도 안 돼요. 예상 못한 지출이 생기면 곧 적자가 될 수 있어요.", ev,
                "1년에 한두 번 나가는 지출(보험·경조사비 등)이 빠지지 않았는지 확인하고, 줄일 수 있는 지출을 찾아보세요.")
        elif sum(a / 12 for _, a, _ in term_items(S)) > c["surplus"]:
            term_m = sum(a / 12 for _, a, _ in term_items(S))
            add("cashflow", "매달 남는 돈", "warn",
                f"지금은 {won(c['surplus'])} 남지만, 예정 지출을 넣으면 월 {won(term_m - c['surplus'])}이 모자라요",
                "등록금·수리비처럼 몇 년 동안만 나가는 지출을 넣으면 일정 기간은 적자가 돼요. 그 기간에는 저축이 줄어들 수 있어요.",
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
                "이 돈에서 곧 쓸 예정인 돈(보증금·학비 등)은 빼고도 충분한지 확인하세요.")

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
            mean += " 임대보증금은 나중에 돌려줘야 하는 돈이라 빚에 포함했어요."
        add("debt", "빚 부담", tone, head, mean,
            f"총부채 {won(c['debts'])} ÷ 총자산 {won(c['assets'])} = {pct(dr, 1)}  /  월 대출 상환 {won(c['debt_payment'])} ÷ 월 소득 {won(c['income'])} = {pct(rr, 1)} (공식 DSR 아님)",
            "대출마다 금리·만기·상환 방식·중도상환수수료를 한 장으로 정리해 보세요. 금리가 높은 빚부터 갚는 것이 일반적인 출발점이에요.")

    # 4) 투자 쏠림
    if c["financial"] > 0 and (c["stocks"] > 0 or c["crypto"] > 0):
        hr = c["high_risk_ratio"] or 0
        if c["high_risk"] <= 0:
            add("risk", "투자 쏠림", "ok", "변동이 아주 큰 자산은 없어요", "레버리지 ETF·가상자산·테마주가 입력되지 않았어요.",
                "고위험 자산 0원", "투자 비중은 '잃어도 생활에 문제없는 돈' 안에서 정하세요.")
        else:
            tone = "bad" if hr >= 50 else "warn" if hr >= 30 else "ok"
            add("risk", "투자 쏠림", tone, f"금융자산의 {pct(hr)}가 변동이 큰 자산이에요",
                "레버리지 ETF·가상자산·테마주는 짧은 기간에도 크게 오르내려요. 급락하면 생활비나 곧 갚을 돈을 마련하기 어려워질 수 있어요.",
                f"(레버리지 {won(c['leverage'])} + 가상자산·테마주 {won(c['crypto'])}) ÷ 금융자산 {won(c['financial'])} = {pct(hr, 1)}",
                "‘앞으로 이만큼 떨어지면?’ 시뮬레이션에서 투자자산이 30% 떨어지는 경우를 확인해 보세요.")

    # 5) 곧 나갈 큰돈
    if c["big_need"] > 0:
        r = c["readiness"] or 0
        tone = "bad" if r < 100 else "warn" if r < 150 else "ok"
        parts = []
        if c["near_deposit"] > 0:
            parts.append(f"1년 안에 돌려줄 보증금 {won(c['near_deposit'])}")
        if c["one_12m"] > 0:
            parts.append(f"1년 안의 큰 지출 {won(c['one_12m'])}")
        head = f"1년 안에 {won(c['big_need'])}이 필요해요"
        add("bigmoney", "곧 나갈 큰돈", tone, head,
            f"{' + '.join(parts)}. 지금 현금·예금은 {won(c['liquid'])}이라 준비율은 {pct(r)}예요. 100%보다 낮으면 부족해요.",
            f"현금·예금 {won(c['liquid'])} ÷ 필요한 돈 {won(c['big_need'])} = {pct(r, 1)}",
            "부족하다면 투자자산 일부를 미리 현금으로 바꾸는 계획을 세우세요. (세금·수수료는 따로 확인하고, 한꺼번에 팔지 말고 나눠서 실행하는 방법도 있어요.)")

    # 6) 보험
    if has_data(c):
        ans = [S.get("has_silson"), S.get("has_life")]
        if "없어요" in ans:
            add("insurance", "보험 점검", "warn", "보험 보장을 점검해 보세요",
                "의료비나 소득 중단에 대비한 보험이 없다고 답했어요. 큰 병이나 사고가 나면 저축이 한꺼번에 줄 수 있어요.",
                f"실손보험: {ans[0]} / 사망·질병 보장: {ans[1]}",
                "필요한 보장이 무엇인지부터 정리해 보세요. 새 보험이 승인되기 전에 기존 보험을 해지하지 마세요.")
        elif "잘 모르겠어요" in ans:
            add("insurance", "보험 점검", "info", "가입한 보험을 확인해 보세요",
                "내 보험이 무엇을 보장하는지 모르면, 필요할 때 도움이 안 될 수 있어요.",
                f"실손보험: {ans[0]} / 사망·질병 보장: {ans[1]}",
                "보험사 앱이나 ‘내보험다보여’ 같은 공식 서비스로 가입 내역을 확인해 보세요.")
        else:
            add("insurance", "보험 점검", "ok", "기본 보장이 있다고 답했어요", "실손보험과 사망·질병 보장이 모두 있어요.",
                f"실손보험: {ans[0]} / 사망·질병 보장: {ans[1]}", "보장 금액이 내 상황에 충분한지 1년에 한 번 점검하세요.")

    out.sort(key=lambda x: TONE_ORDER[x["tone"]])
    return out


def render_checks(items, limit=None):
    for it in (items[:limit] if limit else items):
        fg = TONES[it["tone"]][0]
        st.markdown(
            f'<div class="check" style="border-left:6px solid {fg}">'
            f'<div class="check-t">{TONE_EMOJI[it["tone"]]} {esc(it["title"])}</div>'
            f'<div class="check-h">{esc(it["headline"])}</div>'
            f'<div class="check-m">{esc(it["meaning"])}</div>'
            f'<div class="check-a">👉 {esc(it["action"])}</div>'
            f'<div class="check-e">계산: {esc(it["evidence"])}</div></div>',
            unsafe_allow_html=True)


def validate(S, c) -> list[str]:
    """초보자가 흔히 하는 입력 실수를 쉬운 말로 알려줘요."""
    msgs = []
    if c["income"] == 0 and c["outflow"] > 0:
        msgs.append("월 소득이 0원인데 지출이 있어요. 소득을 빠뜨리지 않았는지 확인해 주세요.")
    if c["income"] > 0 and c["outflow"] > c["income"] * 3:
        msgs.append("월 지출이 월 소득의 3배가 넘어요. 금액 단위(만원)가 맞는지 확인해 주세요.")
    if c["debts"] > c["assets"] > 0:
        msgs.append("빚이 자산보다 많아서 순자산이 마이너스예요. 실제 상황이 맞다면 그대로 진행해도 괜찮아요.")
    if S.get("debt_mode") == "직접 입력" and A(S, "debt_payment") > 0 and (c["mortgage"] + c["credit"] + c["other_debt"]) == 0:
        msgs.append("월 대출 상환액은 있는데 대출 잔액이 0원이에요. ② 부채에서 남은 대출금도 입력해 주세요.")
    if c["mortgage"] > 0 and c["debt_payment"] == 0:
        msgs.append("주택담보대출이 있는데 월 상환액이 0원이에요. ② 부채에서 월 상환액을 확인해 주세요.")
    for k in MONTHLY_KEYS:
        if A(S, k) >= 10000:
            msgs.append("월 금액에 1억 원 이상이 입력된 항목이 있어요. 단위가 '만원'인지 확인해 주세요.")
            break
    if A(S, "target") > 0 and A(S, "already_saved") > A(S, "target"):
        msgs.append("목표를 위해 이미 모은 금액이 목표 금액보다 커요. 둘 다 맞는지 확인해 주세요.")
    return msgs


def make_tasks(S, c, checks):
    tasks = []
    for it in checks:
        if it["tone"] in ("bad", "warn", "info"):
            tasks.append((it["key"], it["tone"], it["title"], it["action"]))
    if A(S, "target") > 0:
        tasks.append(("goal", "info", "목표 저축 계획 세우기", f"목표까지 월 약 {won(c['required_monthly'])}(수익률 0% 기준)이 필요해요. 매달 자동이체로 먼저 떼어 두세요."))
    tasks.append(("monthly", "ok", "한 달에 한 번 입력값 새로 고치기", "소득·지출·대출 잔액이 바뀌면 다시 입력해서 변화를 확인하세요."))
    return tasks


# ============================================================
# 6. 공통 화면 조각
# ============================================================
def need_data(c) -> bool:
    if has_data(c):
        return True
    hero("먼저 내 정보를 입력해 주세요", "자산·부채·월 수입과 지출을 입력하면 이 화면이 자동으로 채워져요.")
    b1, b2 = st.columns(2)
    b1.button("✍️ 내 정보 입력하러 가기", on_click=goto_step, args=(0,), type="primary", **FULL)
    b2.button("🧪 예시로 먼저 둘러보기", on_click=load_demo, args=("young",), **FULL)
    return False


def donut(df, label_col, value_col, title):
    if df.empty:
        st.caption(f"{title}: 입력된 항목이 없어요.")
        return
    try:
        import altair as alt
        chart = alt.Chart(df).mark_arc(innerRadius=60).encode(
            theta=alt.Theta(f"{value_col}:Q"),
            color=alt.Color(f"{label_col}:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[label_col, value_col],
        ).properties(height=300, title=title)
        try:
            st.altair_chart(chart, **FULL)
        except TypeError:
            st.altair_chart(chart)
    except Exception:  # noqa: BLE001
        st.markdown(f"**{title}**")
        st.bar_chart(df.set_index(label_col))


# ============================================================
# 7. 시작하기
# ============================================================
GLOSSARY = [
    ("자산", "내가 가진 것. 현금·예금·주식·부동산 등."),
    ("부채(빚)", "나중에 갚아야 하는 돈. 대출, 카드할부, 임대보증금 등."),
    ("순자산", "자산 − 부채. 빚을 다 갚고 나면 진짜 내 몫으로 남는 돈이에요."),
    ("월 잉여자금", "한 달 동안 번 돈에서 쓴 돈을 뺀 값. 마이너스면 적자예요."),
    ("비상자금", "갑자기 소득이 끊겨도 버틸 수 있게 현금·예금으로 모아 둔 돈."),
    ("임대보증금", "내 집을 빌려주고 세입자에게 받은 보증금. 계약이 끝나면 돌려줘야 해요."),
    ("레버리지 ETF", "지수가 하루에 움직이는 폭의 2~3배로 움직이도록 만든 상품. 오르내림이 매우 커요."),
    ("DSR", "은행이 대출을 심사할 때 쓰는 ‘소득 대비 원리금 상환 비율’. 이 앱의 상환 비율은 참고용이에요."),
]


def page_home(S, c):
    hero("내 돈의 상태, 쉽게 확인해요", "복잡한 금융 용어 없이, 꼭 필요한 숫자와 지금 할 일만 알려드려요.")
    if not has_data(c):
        cols = st.columns(3)
        steps = [("STEP 1", "내 정보 입력", "자산·부채·월 수입과 지출을 4단계로 나눠 입력해요. 모르면 0으로 두세요."),
                 ("STEP 2", "신호등으로 확인", "🟢🟡🔴 신호등으로 지금 내 상태를 쉽게 보여줘요."),
                 ("STEP 3", "지금 할 일 정하기", "해야 할 일을 순서대로 정리하고, AI 코치에게 설명도 들을 수 있어요.")]
        for col, (k, t, d) in zip(cols, steps):
            col.markdown(f'<div class="card"><div class="step">{k}</div><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)
        st.write("")
        st.button("✍️ 내 정보 입력 시작하기", on_click=goto_step, args=(0,), type="primary", **FULL)
        st.write("")
        st.markdown("**입력이 어렵다면 예시로 먼저 둘러보세요**")
        b1, b2 = st.columns(2)
        b1.button("🎓 사회초년생 예시 보기", on_click=load_demo, args=("young",), **FULL)
        b2.button("🏠 자산가 가계 예시 보기 (공모전 가상 사례)", on_click=load_demo, args=("family",), **FULL)
    else:
        kpi_row([("내 순자산", won(c["net"]), f"자산 {won(c['assets'])} − 부채 {won(c['debts'])}", "ok" if c["net"] >= 0 else "bad"),
                 ("매달 남는 돈", won(c["surplus"]), f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad"),
                 ("비상자금", fmt_months(c["runway"]), "현금·예금 ÷ 월 지출", "ok" if (c["runway"] or 0) >= 3 else "warn")])
        st.write("")
        section("지금 가장 먼저 볼 것")
        render_checks(make_checks(S, c), limit=3)
        n1, n2, n3 = st.columns(3)
        n1.button("📊 전체 결과 보기", on_click=goto, args=("📊 내 재무 한눈에",), type="primary", **FULL)
        n2.button("🔮 앞으로 시뮬레이션", on_click=goto, args=("🔮 앞으로 시뮬레이션",), **FULL)
        n3.button("🤖 AI 코치에게 설명 듣기", on_click=goto, args=("🤖 AI 재무코치",), **FULL)

    st.write("")
    with st.expander("📖 재무설계 6단계(AFPK)와 머니체크의 연결"):
        show_df(pd.DataFrame([
            {"단계": "1. 관계 정립", "머니체크에서는": "‘하지 않는 일’ 안내(아래), 개인정보 입력 금지 안내"},
            {"단계": "2. 목표·자료수집", "머니체크에서는": "내 정보 입력(4단계), 입력 실수 방지 점검"},
            {"단계": "3. 재무상태 분석", "머니체크에서는": "순자산 자동 계산, 신호등 진단, 해마다 돈 흐름"},
            {"단계": "4. 설계안 제시", "머니체크에서는": "‘만약 이런 일이 생기면?’, 목표 달성 계산, AI 코치 설명"},
            {"단계": "5. 실행", "머니체크에서는": "실행 계획 체크리스트"},
            {"단계": "6. 점검", "머니체크에서는": "입력값 저장·불러오기로 정기 점검"},
        ]))
    with st.expander("이 앱이 하지 않는 일"):
        st.markdown(
            "- 입력한 숫자는 앱이 **직접 계산**해요(규칙 기반). AI 코치는 그 결과를 **설명**만 도와줘요.\n"
            "- 특정 주식·ETF·펀드·보험 상품을 사거나 팔라고 권하지 않아요.\n"
            "- 세금·법률의 최종 판단은 하지 않아요. 필요하면 전문가나 공식 기관에 확인하세요.\n"
            "- 계좌번호·주민등록번호·비밀번호는 입력하지 마세요.")


# ============================================================
# 8. 내 정보 입력 (4단계 마법사)
# ============================================================
def step_assets(S):
    st.markdown("#### 지금 가진 **자산**을 알려주세요")
    st.caption("대략적인 지금 금액이면 충분해요. 같은 자산을 두 번 입력하지 마세요.")
    with st.container(border=True):
        st.markdown("**💵 바로 쓸 수 있는 돈**")
        a, b = st.columns(2)
        num("현금·입출금 통장", "cash", S, container=a, help="지갑 속 현금과 월급통장 등 언제든 꺼내 쓰는 돈")
        num("예금·적금", "deposits", S, container=b, help="정기예금과 적금 잔액")
    with st.container(border=True):
        st.markdown("**📈 투자와 연금**")
        a, b = st.columns(2)
        num("주식·ETF 전체", "stocks", S, container=a, help="레버리지 ETF도 여기에 포함해서 입력해요.")
        num("└ 이 중 레버리지 ETF", "leverage", S, container=a, max_value=A(S, "stocks"),
            max_hint="먼저 ‘주식·ETF 전체’를 입력하면 열려요. (레버리지 ETF는 주식·ETF의 일부예요)",
            help="지수의 2~3배로 움직이는 상품. ‘주식·ETF 전체’보다 클 수 없어요.")
        num("가상자산·테마주 등", "crypto", S, container=b, help="가격 변동이 큰 코인, 소형 테마주 등")
        num("연금계좌", "pension", S, container=b, help="연금저축·IRP 평가액. 그 안의 ETF를 위에 또 넣지 마세요.")
    with st.container(border=True):
        st.markdown("**🏠 부동산과 기타**")
        a, b = st.columns(2)
        num("부동산 현재 가격", "property", S, step=100.0, container=a, help="대출을 빼기 전 금액이에요. (빚은 다음 단계에 입력해요)")
        num("기타 자산", "other_assets", S, step=10.0, container=b,
            help="내가 세입자로 맡긴 전월세 보증금, 자동차 등. 위에 이미 넣은 것은 빼세요.")


def step_debts(S):
    st.markdown("#### 갚아야 할 돈, **부채(빚)**를 알려주세요")
    st.caption("지금 남아 있는 잔액을 입력하세요. 빚이 없으면 모두 0으로 두면 돼요.")
    with st.container(border=True):
        st.markdown("**🏦 대출**")
        a, b, d = st.columns(3)
        num("주택담보대출", "mortgage", S, step=100.0, container=a, help="집을 담보로 받은 대출의 남은 금액")
        num("신용대출·마이너스통장", "credit", S, container=b)
        num("학자금·전세대출·카드할부 등", "other_debt", S, container=d)
    with st.container(border=True):
        st.markdown("**🏘️ 내 집을 세놓은 경우 (없으면 0)**")
        a, b = st.columns(2)
        num("세입자에게 받은 보증금 합계", "deposits_owed", S, step=100.0, container=a,
            help="계약이 끝나면 돌려줘야 하는 돈이라 부채로 계산해요.")
        num("└ 이 중 1년 안에 돌려줄 금액", "near_deposit", S, step=100.0, container=b,
            max_value=A(S, "deposits_owed"), max_hint="먼저 ‘받은 보증금 합계’를 입력하면 열려요.",
            help="계약 만기가 12개월 이내인 보증금. 전체 보증금보다 클 수 없어요.")
    with st.container(border=True):
        st.markdown("**📆 매달 갚는 돈**")
        mode = radio_h("월 대출 상환액을 어떻게 입력할까요?", "debt_mode", S, ["직접 입력", "자동 계산"],
                       help="자동 계산은 ‘주택담보대출’만 원리금균등 방식으로 계산해요. 다른 대출도 갚고 있다면 직접 입력을 쓰세요.")
        if mode == "직접 입력":
            num("월 대출 상환액 (원금+이자 합계)", "debt_payment", S, step=5.0, help="모든 대출의 매달 갚는 금액을 합해서 입력하세요.")
        else:
            if A(S, "mortgage") <= 0:
                st.caption("주택담보대출 금액을 먼저 입력하면 자동으로 계산돼요.")
            a, b = st.columns(2)
            num("대출 금리 (연 %)", "loan_rate", S, step=0.1, max_value=30.0, container=a)
            num("남은 기간 (년)", "loan_years", S, step=1.0, max_value=50.0, container=b)
            pay = monthly_payment(A(S, "mortgage"), A(S, "loan_rate"), A(S, "loan_years"))
            callout(f"주택담보대출 {won(A(S, 'mortgage'))}, 연 {A(S, 'loan_rate'):.2f}%, {A(S, 'loan_years'):.0f}년 기준 월 상환액은 약 <b>{won(pay)}</b>이에요.", "info")


def step_flow(S):
    st.markdown("#### **한 달**에 들어오고 나가는 돈을 알려주세요")
    st.caption("평균적인 한 달 금액이면 돼요. 생활비에는 대출 상환액을 넣지 마세요(앞 단계에서 이미 반영돼요).")
    a, b = st.columns(2)
    with a:
        with st.container(border=True):
            st.markdown("**⬇️ 들어오는 돈**")
            num("월급·사업소득 (세금 낸 뒤)", "income", S, help="실제로 통장에 들어오는 금액")
            num("월 임대수입(월세)", "rent_income", S, help="집이나 상가를 빌려주고 매달 받는 월세")
            num("배당·용돈 등 기타 소득", "other_income", S)
    with b:
        with st.container(border=True):
            st.markdown("**⬆️ 나가는 돈**")
            num("생활비", "living_cost", S, help="식비·교통·통신·공과금·관리비·문화생활 등")
            num("보험료", "insurance_premium", S)
            num("세금·가족 지원 등 기타 정기지출", "other_fixed", S, help="재산세 적립, 가족 용돈 등 매달 나가는 돈")
            num("1년에 한두 번 나가는 돈 ÷ 12", "irregular_monthly", S,
                help="자동차 보험, 명절·경조사비, 여행 등 연간 예상액을 12로 나눈 금액")


def step_goal(S):
    st.markdown("#### **목표**와 앞으로 나갈 큰돈 (모두 선택이에요)")
    with st.container(border=True):
        st.markdown("**🎯 이루고 싶은 목표**")
        a, b = st.columns(2)
        sel("가장 중요한 목표", "goal", S, GOALS, a)
        yopts = [1, 2, 3, 5, 7, 10, 15, 20, 30]
        wk = "w_years"
        kw = {} if wk in st.session_state else {"index": yopts.index(int(S["years"])) if int(S["years"]) in yopts else 2}
        S["years"] = b.selectbox("목표까지 남은 기간", yopts, format_func=lambda v: f"{v}년", key=wk, **kw)
        a, b = st.columns(2)
        num("목표에 필요한 총금액", "target", S, step=100.0, container=a, help="0이면 목표 계산은 건너뛰어요.")
        num("목표를 위해 이미 모은 금액", "already_saved", S, container=b)
    with st.container(border=True):
        st.markdown("**📅 몇 년 동안만 나가는 지출** (예: 등록금 4년, 수리비 2년)")
        for i in (1, 2):
            a, b, d = st.columns([2, 1.3, 1.1])
            txt("이름", f"t{i}_name", S, a, placeholder="예: 등록금")
            num("1년에 드는 돈", f"t{i}_amt", S, step=50.0, container=b)
            num("몇 년 동안", f"t{i}_years", S, step=1.0, max_value=50.0, container=d)
    with st.container(border=True):
        st.markdown("**💥 한 번에 크게 나가는 지출** (예: 결혼, 이사, 자동차)")
        a, b, d = st.columns([2, 1.3, 1.1])
        txt("이름", "one_name", S, a, placeholder="예: 이사 비용")
        num("금액", "one_amt", S, step=100.0, container=b)
        num("몇 개월 뒤", "one_months", S, step=1.0, max_value=600.0, container=d)
    with st.container(border=True):
        st.markdown("**🛡️ 보험 (대략 알고 있는 만큼만)**")
        radio_h("실손의료보험에 가입했나요?", "has_silson", S, KNOW)
        radio_h("사망·질병 등 소득 보장 보험이 있나요?", "has_life", S, KNOW)


def page_input(S):
    hero("내 정보 입력", "한 단계씩 입력해요. 금액은 ‘만원’ 단위이고, 모르는 항목은 0으로 두면 돼요. (예: 500 = 500만 원, 10000 = 1억 원)")
    summary = st.container()
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

    # ---- 위젯 값이 모두 반영된 뒤 맨 위 요약을 채움 ----
    c = calculate(S)
    with summary:
        if step <= 1:
            callout("🔒 <b>순자산은 직접 적을 수 없어요.</b> ‘자산 − 부채’로 자동 계산돼요. (예: 자산 100억 − 부채 50억 = 순자산 50억)", "info")
            st.markdown(equation_html("총자산 (자동 합계)", won(c["assets"]), "총부채 (자동 합계)", won(c["debts"]), "순자산 🔒 자동 계산", won(c["net"])),
                        unsafe_allow_html=True)
        else:
            callout("🔒 <b>월 잉여자금도 자동 계산돼요.</b> ‘월 소득 − 월 지출’이에요. 직접 적을 필요가 없어요.", "info")
            st.markdown(equation_html("월 소득 (자동 합계)", won(c["income"]), "월 지출 (자동 합계)", won(c["outflow"]), "월 잉여자금 🔒 자동 계산", won(c["surplus"])),
                        unsafe_allow_html=True)
        msgs = validate(S, c)
        for m in msgs:
            st.warning(m)
        if has_data(c) and not msgs:
            st.caption("✅ 입력 점검 통과 — 입력값은 자동으로 저장돼요.")


# ============================================================
# 9. 내 재무 한눈에
# ============================================================
def page_snapshot(S, c):
    hero("내 재무 한눈에", "먼저 순자산을 확인하고, 신호등으로 지금 내 상태를 살펴봐요.")
    if not need_data(c):
        return
    st.markdown(equation_html("총자산", won(c["assets"]), "총부채(빚)", won(c["debts"]), "순자산 🔒 자동 계산", won(c["net"])), unsafe_allow_html=True)
    st.caption("순자산은 직접 입력하지 않고 ‘자산 − 부채’로 자동 계산해요. 입력한 가격 기준이며 세금·수수료는 반영하지 않았어요.")
    kpi_row([("매달 남는 돈", won(c["surplus"]), f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad"),
             ("비상자금", fmt_months(c["runway"]), f"현금·예금 {won(c['liquid'])}", "ok" if (c["runway"] or 0) >= 3 else "warn")])

    st.write("")
    section("신호등으로 보는 내 상태", "🔴 먼저 확인 · 🟡 살펴보기 · 🟢 괜찮아요")
    checks = make_checks(S, c)
    if checks:
        counts = {t: sum(1 for x in checks if x["tone"] == t) for t in ("bad", "warn", "ok")}
        st.markdown(f"🔴 {counts['bad']}개 &nbsp; 🟡 {counts['warn']}개 &nbsp; 🟢 {counts['ok']}개")
        render_checks(checks)
    note("신호등 기준은 일반적인 참고 범위예요. 사람마다 상황이 달라 ‘정답’이 아니에요.")

    st.divider()
    section("자세히 보기")
    t1, t2, t3 = st.tabs(["재무상태표", "한 달 수입·지출", "자산 구성"])
    plain = max(0.0, c["stocks"] - c["leverage"])
    assets_rows = [("현금·입출금", c["cash"]), ("예금·적금", c["deposits"]), ("주식·ETF (레버리지 제외)", plain),
                   ("레버리지 ETF", c["leverage"]), ("가상자산·테마주", c["crypto"]), ("연금계좌", c["pension"]),
                   ("부동산", c["property"]), ("기타 자산", c["other_assets"])]
    debt_rows = [("주택담보대출", c["mortgage"]), ("신용대출·마이너스통장", c["credit"]), ("학자금·전세대출 등", c["other_debt"]),
                 ("임대보증금(돌려줄 돈)", c["deposits_owed"])]
    with t1:
        left, right = st.columns(2)
        with left:
            st.markdown("**자산**")
            show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in assets_rows if v > 0] + [{"항목": "총자산", "금액": won(c["assets"])}]))
        with right:
            st.markdown("**부채와 순자산**")
            show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in debt_rows if v > 0] +
                                 [{"항목": "총부채", "금액": won(c["debts"])}, {"항목": "순자산 🔒", "금액": won(c["net"])}]))
    with t2:
        flow = [("들어오는 돈", "월급·사업소득", A(S, "income")), ("들어오는 돈", "임대수입", A(S, "rent_income")), ("들어오는 돈", "기타 소득", A(S, "other_income")),
                ("나가는 돈", "생활비", A(S, "living_cost")), ("나가는 돈", "보험료", A(S, "insurance_premium")), ("나가는 돈", "세금·가족 지원 등", A(S, "other_fixed")),
                ("나가는 돈", "비정기 지출(월 환산)", A(S, "irregular_monthly")), ("나가는 돈", "대출 상환", c["debt_payment"])]
        rows = [{"구분": a, "항목": b, "월 금액": won(v)} for a, b, v in flow if v > 0]
        rows += [{"구분": "합계", "항목": "월 소득", "월 금액": won(c["income"])}, {"구분": "합계", "항목": "월 지출", "월 금액": won(c["outflow"])},
                 {"구분": "결과 🔒", "항목": "월 잉여자금", "월 금액": won(c["surplus"])}]
        show_df(pd.DataFrame(rows))
    with t3:
        a, b = st.columns(2)
        with a:
            donut(pd.DataFrame([{"자산": k, "금액": v} for k, v in assets_rows if v > 0]), "자산", "금액", "자산 구성")
        with b:
            donut(pd.DataFrame([{"부채": k, "금액": v} for k, v in debt_rows if v > 0]), "부채", "금액", "부채 구성")

    with st.expander("계산 방법 보기"):
        st.markdown(
            "- 총자산 = 현금·예금 + 주식·ETF + 가상자산·테마주 + 연금계좌 + 부동산 + 기타 자산\n"
            "- 총부채 = 주택담보대출 + 신용대출 + 기타 대출 + 임대보증금\n"
            "- **순자산 = 총자산 − 총부채** (자동 계산)\n"
            "- 월 잉여자금 = 월 소득 − 월 지출 (자동 계산)\n"
            "- 비상자금(개월) = 현금·예금 ÷ 월 지출\n"
            "- 레버리지 ETF는 ‘주식·ETF’의 일부이므로 총자산에 두 번 더하지 않아요.")


# ============================================================
# 10. 앞으로 시뮬레이션
# ============================================================
def tab_timeline(S, c):
    st.caption("몇 년 동안만 나가는 지출(등록금·수리비 등)까지 넣으면 해마다 돈 흐름이 어떻게 달라지는지 보여줘요.")
    years = st.slider("몇 년 후까지 볼까요?", 3, 15, 8)
    df = build_timeline(S, c, years)
    neg = df[df["월 현금흐름"] < 0]
    broke = df[df["현금·예금 잔액(추정)"] < 0]
    kpi_row([("지금 매달 남는 돈", won(c["surplus"]), "기간 한정 지출 반영 전", "ok" if c["surplus"] > 0 else "bad"),
             ("적자인 해", f"{len(neg)}년" if len(neg) else "없음", "기간 한정 지출 반영", "warn" if len(neg) else "ok"),
             ("현금·예금이 바닥나는 때", f"{int(broke.iloc[0]['연차'])}년차" if len(broke) else "기간 안에는 없음", "큰돈 제외 추정", "bad" if len(broke) else "ok")])
    st.write("")
    seg, start = [], 0
    vals = df["월 현금흐름"].round(1).tolist()
    for i in range(1, len(vals) + 1):
        if i == len(vals) or vals[i] != vals[start]:
            y0, y1 = int(df.iloc[start]["연차"]), int(df.iloc[i - 1]["연차"])
            v = vals[start]
            seg.append({"기간": f"{y0}년차" if y0 == y1 else f"{y0}~{y1}년차", "한 달 돈 흐름": f"{'🟢' if v > 0 else '🔴'} {won(v)}",
                        "기간 한정 지출(월 환산)": won(df.iloc[start]["기간 한정 지출(월)"])})
            start = i
    show_df(pd.DataFrame(seg))
    chart = df.assign(연차=df["연차"].astype(int).astype(str) + "년차").set_index("연차")
    st.markdown("**현금·예금 잔액 추정 (만원)**")
    st.line_chart(chart[["현금·예금 잔액(추정)"]])
    note("월 잉여자금과 입력한 예정 지출만 반영한 단순 추정이에요. 투자수익·세금·물가·보증금 반환은 넣지 않았어요.")


def tab_whatif(S, c):
    st.caption("실제 입력값은 바꾸지 않고, ‘만약 이런 일이 생기면?’ 하고 가정만 계산해요.")
    presets = {"월급·사업소득이 20% 줄면": dict(income_pct=-20)}
    if c["mortgage"] > 0:
        presets["대출 금리가 2%p 오르면"] = dict(rate_delta=2.0)
    if A(S, "rent_income") > 0:
        presets["월세 수입이 절반으로 줄면"] = dict(vacancy_pct=50)
    if c["stocks"] + c["crypto"] > 0:
        presets["투자자산이 30% 떨어지면"] = dict(invest_drop=30)
    presets["1,000만 원이 갑자기 필요하면"] = dict(one_off=1000)
    rows = [{"상황": "지금", "월 잉여자금": f"{'🟢' if c['surplus'] > 0 else '🔴'} {won(c['surplus'])}", "비상자금": fmt_months(c["runway"]), "순자산": won(c["net"])}]
    for name, v in presets.items():
        s = apply_scenario(S, c, **v)
        rows.append({"상황": name, "월 잉여자금": f"{'🟢' if s['surplus'] > 0 else '🔴'} {won(s['surplus'])}", "비상자금": fmt_months(s["runway"]), "순자산": won(s["net"])})
    show_df(pd.DataFrame(rows))
    if c["income"] > 0 and c["surplus"] > 0 and (c["income"] - A(S, "rent_income")) > 0:
        st.caption(f"💡 월급·사업소득이 약 {c['surplus'] / (c['income'] - A(S, 'rent_income')) * 100:.0f}% 줄면 매달 남는 돈이 0원이 돼요.")

    with st.expander("직접 값을 바꿔 보기"):
        a, b = st.columns(2)
        inc = a.slider("월급·사업소득 변화 (%)", -80, 50, 0, step=5)
        exp = a.slider("월 지출 변화 (만원)", -100, 200, 0, step=10)
        one = b.slider("한 번에 나가는 큰돈 (만원)", 0, 10000, 0, step=100)
        inv = b.slider("투자자산 하락률 (%)", 0, 60, 0, step=5)
        s = apply_scenario(S, c, income_pct=inc, expense_delta=exp, one_off=one, invest_drop=inv)
        show_df(pd.DataFrame([
            {"지표": "월 소득", "지금": won(c["income"]), "가정 후": won(s["income"])},
            {"지표": "월 지출", "지금": won(c["outflow"]), "가정 후": won(s["outflow"])},
            {"지표": "월 잉여자금", "지금": won(c["surplus"]), "가정 후": won(s["surplus"])},
            {"지표": "현금·예금", "지금": won(c["liquid"]), "가정 후": won(s["liquid"])},
            {"지표": "순자산", "지금": won(c["net"]), "가정 후": won(s["net"])},
            {"지표": "비상자금", "지금": fmt_months(c["runway"]), "가정 후": fmt_months(s["runway"])},
        ]))
        if s["surplus"] < 0:
            callout(f"이 가정에서는 매달 <b>{won(abs(s['surplus']))}</b>이 모자라요.", "bad")
        if s["liquid"] < 0:
            callout("큰돈이 현재 현금·예금보다 커요. 자산을 팔거나 빌려야 할 수 있어요.", "warn")

    with st.expander("레버리지 ETF는 왜 조심해야 하나요?"):
        st.markdown("지수가 **+10% → −9.09%** 로 움직여 **제자리(100)로 돌아와도**, 하루 수익률의 3배로 움직이는 상품은 원금보다 줄어들 수 있어요.")
        pdf = path_example([10, -9.09], 3)
        show_df(pdf.assign(지수=pdf["지수"].round(2), **{"레버리지 ETF": pdf["레버리지 ETF"].round(2)}))
        note("보수·추적오차 등을 뺀 단순 수학 예시이며 실제 성과를 예측하지 않아요.")
    note("사용자가 정한 가정의 산술 결과예요. 미래를 예측하거나 일어날 확률을 뜻하지 않아요.")


def tab_goal(S, c):
    if A(S, "target") <= 0:
        st.info("목표 금액을 입력하면 매달 얼마를 모아야 하는지 계산해 드려요.")
        st.button("④ 목표 입력하러 가기", on_click=goto_step, args=(3,), **FULL)
        return
    years = int(S["years"])
    n = years * 12
    ret = st.slider("예상 연 수익률 (%)", 0.0, 8.0, 0.0, step=0.5, help="0%는 ‘이자·수익 없이 저금만 한다’는 뜻이에요. 수익률은 보장되지 않아요.")
    m = ret / 1200
    saved, target = A(S, "already_saved"), A(S, "target")
    gap = max(0.0, target - saved * (1 + m) ** n)
    req = gap / n if m == 0 else gap * m / ((1 + m) ** n - 1)
    avail = c["surplus"]
    kpi_row([("목표 금액", won(target), f"{years}년 뒤", "info"), ("이미 모은 금액", won(saved), "", "neutral"),
             ("필요한 월 저축액", won(req), f"연 {ret:.1f}% 가정", "warn"), ("지금 매달 남는 돈", won(avail), "월 잉여자금", "ok" if avail >= req else "warn")])
    st.write("")
    if avail <= 0:
        callout("지금은 매달 남는 돈이 없어서 저축으로 목표를 모으기 어려워요. 먼저 ‘내 재무 한눈에’에서 현금흐름을 점검해 보세요.", "bad")
    elif avail >= req:
        mths = months_to_reach(target, saved, avail, m)
        callout(f"지금 남는 돈을 전부 저축한다고 가정하면 목표 기간 안에 달성할 수 있어요 (약 {mths}개월). 다만 비상자금과 예정 지출은 따로 챙기세요.", "ok")
    else:
        mths = months_to_reach(target, saved, avail, m)
        when = f"약 {mths}개월({mths / 12:.1f}년)" if mths else "100년 안에는 어려워요"
        callout(f"매달 <b>{won(req - avail)}</b>이 더 필요해요. 지금 남는 돈만으로는 목표 달성까지 {when} 걸려요. 목표 금액이나 기간을 조정해 보세요.", "warn")
    if avail > 0:
        series = {"수익률 0%": [], f"수익률 {ret:.1f}%": [], "목표 금액": []}
        b0, b1 = saved, saved
        for k in range(1, n + 1):
            b0 = b0 + avail
            b1 = b1 * (1 + m) + avail
            if k % 12 == 0:
                series["수익률 0%"].append(b0)
                series[f"수익률 {ret:.1f}%"].append(b1)
                series["목표 금액"].append(target)
        st.line_chart(pd.DataFrame(series, index=[f"{i}년" for i in range(1, years + 1)]))
    note("매달 같은 금액을 저축한다고 가정한 단순 계산이에요. 세금·수수료·물가·소득 변화는 넣지 않았어요.")


def page_sim(S, c):
    hero("앞으로 시뮬레이션", "해마다 돈 흐름, 만약의 상황, 목표 달성까지 미리 계산해 봐요.")
    if not need_data(c):
        return
    t1, t2, t3 = st.tabs(["📅 해마다 돈 흐름", "⚠️ 만약 이런 일이 생기면?", "🎯 목표 달성"])
    with t1:
        tab_timeline(S, c)
    with t2:
        tab_whatif(S, c)
    with t3:
        tab_goal(S, c)


# ============================================================
# 11. AI 재무코치 (Gemini)
# ============================================================
def build_ai_prompt(S, c, checks) -> str:
    diag = [{"항목": x["title"], "신호": TONE_EMOJI[x["tone"]], "결론": x["headline"], "설명": x["meaning"], "계산 근거": x["evidence"], "다음 행동": x["action"]} for x in checks]
    ready = pct(c["readiness"], 0) if c["readiness"] is not None else "해당 없음"
    return f"""
당신은 대학생과 사회초년생의 재무관리를 돕는 '머니체크'의 AI 재무코치입니다.

머니체크는 사용자의 입력값을 바탕으로 재무상태를 자체적으로 계산합니다.
당신의 역할은 새롭게 재무상태를 계산하는 것이 아니라,
머니체크가 계산한 결과를 사용자가 이해하기 쉽게 설명하고
확인할 사항과 다음 행동을 안내하는 것입니다.

[가장 중요한 원칙]

1. 아래에 제공된 숫자와 진단 결과를 사실 그대로 사용하세요.
2. 제공된 숫자를 임의로 변경하거나 새롭게 계산하지 마세요.
3. 계산 결과에 없는 숫자나 사실을 추측해서 만들어내지 마세요.
4. 재무상태를 '좋다', '나쁘다', '안정적이다'라고 단정하지 말고,
   어떤 수치가 어떤 의미를 가지는지 설명하세요.
5. '위험하다'라고 단정하기보다는 '주의해서 확인할 필요가 있습니다',
   '추가적인 점검이 필요합니다'와 같이 표현하세요.
6. 특정 주식, ETF, 코인, 펀드, 보험상품 또는 대출상품의
   매수·매도·가입을 직접 권유하지 마세요.
7. 세무·법률 문제는 확정적인 판단을 하지 말고,
   필요한 경우 전문가 또는 공식 기관의 확인이 필요하다고 안내하세요.
8. 사용자가 실제로 실행할 수 있는 행동을 우선적으로 제시하세요.
9. 머니체크에 있는 메뉴(내 정보 입력, 내 재무 한눈에, 앞으로 시뮬레이션, 실행 계획·저장)만 안내하고,
   없는 기능을 만들어내지 마세요.
10. 전문용어를 사용할 경우 짧고 쉽게 설명하세요.
11. 제공된 데이터만으로 판단하기 어려운 사항은 추측하지 말고
    '추가 확인이 필요합니다'라고 명확하게 표시하세요.

[현재 재무상태]

총자산: {won(c["assets"])}
총부채: {won(c["debts"])}
순자산: {won(c["net"])}

월 총소득: {won(c["income"])}
월 정기지출: {won(c["outflow"])}
월 잉여자금: {won(c["surplus"])}

현금·예금: {won(c["liquid"])}
현금·예금 여력: {fmt_months(c["runway"])}

총부채/총자산: {pct(c["debt_ratio"])}
월 상환액/월 소득: {pct(c["repayment_ratio"])}
고위험 자산 비중: {pct(c["high_risk_ratio"])}

1년 안에 필요한 큰돈 대비 현금·예금 준비율: {ready}

[머니체크 재무진단 결과]
{json.dumps(diag, ensure_ascii=False, indent=2)}

[답변 작성 형식]

### 1. 현재 재무상태 한눈에 보기
사용자의 현재 재무상태에서 눈여겨볼 핵심 내용을
3~4문장으로 간결하게 설명하세요.
단순히 '좋다/나쁘다'고 평가하지 말고 주요 수치를 중심으로 설명하세요.

### 2. 가장 먼저 확인할 부분
중요도가 높은 항목을 최대 3개까지 제시하세요.

각 항목은 다음 형식으로 작성하세요.

1. **항목명**
   - 현재 상황: 제공된 계산 결과를 설명
   - 확인 이유: 왜 확인할 필요가 있는지 설명

### 3. 지금 할 수 있는 행동
사용자가 실제로 실행할 수 있는 행동을 최대 3개 제시하세요.

가능하면 머니체크의 기존 메뉴나 기능을 활용할 수 있도록 안내하세요.

### 4. 주의할 점
현재 데이터만으로 확정하기 어려운 부분이나
추가 확인이 필요한 사항을 간단하게 설명하세요.

답변은 전체적으로 이해하기 쉽고 실용적으로 작성하세요.
불필요한 인사말이나 장황한 설명은 생략하세요.
"""


def page_ai(S, c):
    hero("AI 재무코치", "머니체크가 계산한 결과를 AI가 쉬운 말로 설명해 줘요.")
    if not need_data(c):
        return
    callout("AI는 머니체크의 <b>계산 결과를 설명</b>하고 점검 방향을 안내해요. 투자상품의 매수·매도나 세무·법률 판단을 대신하지 않아요.<br>"
            "<span class='tiny'>🔐 버튼을 누르면 합계 금액과 진단 결과(숫자·문장)만 Google Gemini로 전송돼요. 이름·계좌번호 등은 입력하지 않으니 전송되지 않아요.</span>", "info")
    if gemini_client is None:
        callout("AI 코치를 쓰려면 Gemini API 키가 필요해요. 프로젝트 폴더의 <code>.streamlit/secrets.toml</code> 파일에 "
                "<code>GEMINI_API_KEY = \"발급받은_키\"</code> 를 적고, <code>pip install google-genai</code> 를 실행한 뒤 앱을 다시 시작하세요. "
                "(Streamlit Cloud라면 Settings → Secrets에 같은 내용을 넣어요.)", "warn", "AI 코치 설정이 필요해요")
        return
    checks = make_checks(S, c)
    sig = hashlib.md5(json.dumps({k: v for k, v in S.items() if k != "checks"}, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    if st.button("✨ 내 재무상태 AI로 설명받기", type="primary", **FULL):
        with st.spinner("AI가 현재 재무상태를 분석하고 있어요..."):
            st.session_state["ai_result"] = ask_gemini(build_ai_prompt(S, c, checks))
            st.session_state["ai_sig"] = sig
    if st.session_state.get("ai_result"):
        if st.session_state.get("ai_sig") != sig:
            st.warning("입력값이 바뀌었어요. 최신 결과로 설명받으려면 위 버튼을 다시 눌러 주세요.")
        st.markdown("### ✨ AI 재무코치 분석")
        st.markdown(st.session_state["ai_result"])
        note("AI 답변은 참고용이에요. 숫자는 머니체크가 계산한 값을 기준으로 하며, 실행 전에는 공식 자료와 전문가 확인이 필요해요.")


# ============================================================
# 12. 실행 계획·저장
# ============================================================
def build_report_html(S, c, checks) -> str:
    def tbl(rows, cols):
        return pd.DataFrame(rows, columns=cols).to_html(index=False, escape=True, border=0, classes="t")
    asset_rows = [["현금·예금", won(c["liquid"])], ["주식·ETF", won(c["stocks"])], ["가상자산·테마주", won(c["crypto"])], ["연금계좌", won(c["pension"])],
                  ["부동산", won(c["property"])], ["기타", won(c["other_assets"])], ["총자산", won(c["assets"])]]
    debt_rows = [["주택담보대출", won(c["mortgage"])], ["신용·기타 대출", won(c["credit"] + c["other_debt"])],
                 ["임대보증금(돌려줄 돈)", won(c["deposits_owed"])], ["총부채", won(c["debts"])], ["순자산(자산−부채)", won(c["net"])]]
    flow_rows = [["월 소득", won(c["income"])], ["월 지출", won(c["outflow"])], ["월 잉여자금", won(c["surplus"])]]
    tl = build_timeline(S, c, 8)
    tl_rows = [[f"{int(r['연차'])}년차", won(r["월 현금흐름"]), won(r["현금·예금 잔액(추정)"])] for _, r in tl.iterrows()]
    cards = "".join(f"<div class='d'><b>{TONE_EMOJI[x['tone']]} {esc(x['title'])} — {esc(x['headline'])}</b><br>{esc(x['meaning'])}<br>"
                    f"<small>계산: {esc(x['evidence'])}<br>다음 행동: {esc(x['action'])}</small></div>" for x in checks)
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>머니체크 재무 리포트</title>
<style>body{{font-family:'Pretendard','Malgun Gothic',sans-serif;max-width:820px;margin:30px auto;color:#14213d;line-height:1.65;padding:0 16px}}
h1{{color:#0f766e}}h2{{border-bottom:2px solid #0f766e;padding-bottom:4px;margin-top:28px}}
table.t{{border-collapse:collapse;width:100%;margin:8px 0}}table.t th,table.t td{{border:1px solid #d0d5dd;padding:6px 10px;text-align:left}}
table.t th{{background:#f2f4f7}}.d{{border:1px solid #e4e7ec;border-radius:10px;padding:10px 14px;margin:8px 0}}small,.f{{color:#667085}}</style></head><body>
<h1>머니체크 재무 리포트</h1><p class="f">작성일 {date.today().isoformat()} · 금액 단위 만원 · 입력값 기반 참고 자료</p>
<h2>1. 순자산 (자동 계산)</h2><p>총자산 {esc(won(c['assets']))} − 총부채 {esc(won(c['debts']))} = <b>{esc(won(c['net']))}</b></p>
{tbl(asset_rows, ['자산', '금액'])}{tbl(debt_rows, ['부채·순자산', '금액'])}
<h2>2. 한 달 수입·지출</h2>{tbl(flow_rows, ['항목', '월 금액'])}
<h2>3. 해마다 돈 흐름</h2>{tbl(tl_rows, ['연차', '월 현금흐름', '현금·예금 잔액(추정)'])}
<h2>4. 신호등 진단과 다음 행동</h2>{cards}
<h2>5. 알아두세요</h2><ul><li>입력값을 바탕으로 한 참고 자료이며 세무·법률·투자 판단을 대신하지 않습니다.</li>
<li>세금·수수료·투자수익·물가는 반영하지 않았습니다.</li><li>월 상환액/월 소득은 참고 비율이며 금융기관의 DSR이 아닙니다.</li></ul></body></html>"""


def page_plan(S, c):
    hero("실행 계획·저장", "지금 할 일을 순서대로 정리하고, 입력한 내용을 파일로 저장해요.")
    if not need_data(c):
        return
    checks = make_checks(S, c)
    tasks = make_tasks(S, c, checks)
    done = sum(1 for t in tasks if S["checks"].get(t[0]))
    st.progress(done / len(tasks) if tasks else 0.0, text=f"실행 진행률 {done} / {len(tasks)}")
    groups = [("bad", "🔴 먼저 할 일"), ("warn", "🟡 이어서 할 일"), ("info", "🔵 알아두면 좋은 일"), ("ok", "🟢 꾸준히 할 일")]
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
                      file_name=f"머니체크_리포트_{date.today().isoformat()}.html", mime="text/html", type="primary", **FULL)
    b.download_button("💾 입력값 저장 (JSON)", data=json.dumps({"app": "moneycheck", "version": 3, "data": S}, ensure_ascii=False, indent=2, default=float).encode("utf-8"),
                      file_name=f"머니체크_입력값_{date.today().isoformat()}.json", mime="application/json", **FULL)
    st.caption("리포트는 브라우저에서 열어 인쇄(Ctrl+P) → ‘PDF로 저장’을 고르면 PDF로 보관할 수 있어요.")
    up = st.file_uploader("저장해 둔 입력값(JSON) 불러오기", type=["json"])
    if up is not None:
        fid = f"{up.name}-{up.size}"
        if st.session_state.get("_loaded_file") != fid:
            ok, msg = import_json(up.getvalue())
            st.session_state["_loaded_file"] = fid
            if ok:
                st.rerun()
            else:
                st.error(msg)
        else:
            st.success("저장된 입력값을 불러왔어요.")


# ============================================================
# 13. 사이드바 · 화면 연결
# ============================================================
P_HOME, P_INPUT, P_SNAP = "🏠 시작하기", "✍️ 내 정보 입력", "📊 내 재무 한눈에"
P_SIM, P_AI, P_PLAN = "🔮 앞으로 시뮬레이션", "🤖 AI 재무코치", "✅ 실행 계획·저장"
PAGES = [P_HOME, P_INPUT, P_SNAP, P_SIM, P_AI, P_PLAN]

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
    {P_SNAP: page_snapshot, P_SIM: page_sim, P_AI: page_ai, P_PLAN: page_plan}[page](S, _c)

_cf = calculate(S)  # 입력 화면에서 바뀐 최신 값으로 사이드바 요약 갱신
if has_data(_cf):
    with side_summary:
        st.divider()
        st.caption("내 요약 (자동 계산)")
        st.markdown(f"**순자산** {won(_cf['net'])}  \n**월 잉여** {won(_cf['surplus'])}  \n**비상자금** {fmt_months(_cf['runway'])}")

st.divider()
st.caption("머니체크 · 사용자의 이해와 선택을 돕는 재무 점검 도구 (참고용)")
