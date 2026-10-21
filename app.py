from __future__ import annotations

import copy
import html
import inspect
import json
import math
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
from google import genai

# ============================================================
# 머니체크 v2 | 이해하기 쉬운 가계 재무진단 · 재무설계 6단계 도우미
# 규칙 기반 프로토타입 (외부 생성형 AI / 계좌 연동 없음)
# 모든 금액 단위: 만원
# ============================================================

st.set_page_config(
    page_title="머니체크 | 내 돈을 쉽게 이해하기",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded",
)
# Gemini API 연결
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

def ask_gemini(prompt):
    if gemini_client is None:
        return "Gemini API 키가 설정되지 않았습니다."

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Gemini API 오류: {e}"

# Gemini 연결 테스트
with st.expander("🤖 Gemini API 연결 테스트"):
    if st.button("Gemini 테스트"):
        result = ask_gemini("안녕하세요. 한 문장으로 자기소개를 해주세요.")
        st.write(result)
        
# Streamlit 버전별 width 옵션 호환 (use_container_width → width="stretch")
_HAS_WIDTH = "width" in inspect.signature(st.button).parameters
FULL = {"width": "stretch"} if _HAS_WIDTH else {"use_container_width": True}


# ============================================================
# 1. 디자인 시스템 (CSS)
# ============================================================
st.markdown(
    """
    <style>
      @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
      :root{
        --ink:#14213d; --sub:#475467; --mute:#667085; --line:#e4e7ec; --soft:#f8fafc;
        --brand:#0f766e; --brand-d:#115e59; --navy:#17324d;
      }
      .stApp{ font-family:'Pretendard',-apple-system,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif; }
      .block-container{ max-width:1180px; padding-top:1.2rem; padding-bottom:4rem; }
      h1,h2,h3,h4{ letter-spacing:-.025em; color:var(--ink); }
      h3{ margin-top:.4rem; }
      [data-testid="stSidebar"]{ background:#f6f8fb; border-right:1px solid var(--line); }
      [data-testid="stSidebar"] .block-container{ padding-top:1.2rem; }
      [data-testid="stSidebar"] [role="radiogroup"] label{
        padding:7px 10px; border-radius:10px; margin-bottom:2px; width:100%;
      }
      [data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:#e8f1f0; }
      .brand{ font-size:1.25rem; font-weight:800; letter-spacing:-.03em; color:var(--navy); }
      .brand-sub{ color:var(--mute); font-size:.82rem; margin:-2px 0 10px 0; }

      /* hero */
      .hero{ background:linear-gradient(120deg,#17324d 0%,#0f766e 100%); color:#fff;
             border-radius:20px; padding:26px 30px; margin:0 0 18px 0; }
      .hero .eyebrow{ color:#bce8df; font-size:.76rem; font-weight:800; letter-spacing:.1em; margin-bottom:8px; }
      .hero h1{ color:#fff; font-size:1.85rem; line-height:1.3; margin:0 0 8px 0; }
      .hero p{ color:#eaf7f5; margin:0; font-size:1rem; line-height:1.65; }

      /* kpi */
      .kpi{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px 16px; height:100%; }
      .kpi-l{ color:var(--mute); font-size:.82rem; font-weight:600; margin-bottom:4px; }
      .kpi-v{ color:var(--ink); font-size:1.45rem; font-weight:800; letter-spacing:-.03em; line-height:1.25; }
      .kpi-s{ color:var(--mute); font-size:.78rem; margin-top:4px; line-height:1.45; }

      /* cards / callouts */
      .card{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 18px; height:100%; }
      .card h4{ margin:0 0 6px 0; font-size:1rem; color:var(--ink); }
      .card p{ margin:0; color:var(--sub); font-size:.9rem; line-height:1.6; }
      .card .step{ color:var(--brand); font-weight:800; font-size:.75rem; letter-spacing:.06em; margin-bottom:4px; }
      .callout{ border-radius:14px; padding:14px 16px; line-height:1.7; font-size:.94rem; margin:6px 0; }
      .callout b.t{ display:block; margin-bottom:2px; }
      .tiny{ color:var(--mute); font-size:.8rem; line-height:1.55; }
      .pill{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.76rem; font-weight:700; border:1px solid; }

      /* score */
      .ring{ width:132px; height:132px; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:auto; }
      .ring-in{ width:98px; height:98px; border-radius:50%; background:#fff; display:flex; flex-direction:column;
                align-items:center; justify-content:center; }
      .ring-in b{ font-size:1.9rem; color:var(--ink); line-height:1; }
      .ring-in span{ font-size:.72rem; color:var(--mute); margin-top:3px; }
      .bar-row{ display:flex; align-items:center; gap:10px; margin:9px 0; font-size:.88rem; color:var(--sub); }
      .bar-row .lab{ width:108px; flex:none; font-weight:600; color:var(--ink); }
      .bar-row .track{ flex:1; height:9px; background:#eef2f6; border-radius:99px; overflow:hidden; }
      .bar-row .fill{ height:100%; border-radius:99px; }
      .bar-row .num{ width:54px; text-align:right; font-weight:700; color:var(--ink); }

      /* widgets */
      div[data-testid="stExpander"]{ border:1px solid var(--line); border-radius:13px; background:#fff; }
      div.stButton > button, div[data-testid="stDownloadButton"] button{ border-radius:11px; min-height:2.6rem; font-weight:650; }
      button[data-baseweb="tab"]{ font-weight:650; }
      hr{ border-color:var(--line); }
      @media (max-width:720px){ .hero{padding:20px 18px;} .hero h1{font-size:1.45rem;} .kpi-v{font-size:1.2rem;} }
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
TONE_EMOJI = {"ok": "🟢", "warn": "🟠", "bad": "🔴", "info": "🔵", "neutral": "⚪"}


def esc(x) -> str:
    return html.escape(str(x))


def kpi(label, value, sub="", tone="neutral") -> str:
    fg = TONES[tone][0]
    return (
        f'<div class="kpi" style="border-top:4px solid {fg}"><div class="kpi-l">{esc(label)}</div>'
        f'<div class="kpi-v">{esc(value)}</div><div class="kpi-s">{esc(sub)}</div></div>'
    )


def kpi_row(items):
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        col.markdown(kpi(*it), unsafe_allow_html=True)


def pill(text, tone="neutral") -> str:
    fg, bg, bd = TONES[tone]
    return f'<span class="pill" style="color:{fg};background:{bg};border-color:{bd}">{esc(text)}</span>'


def callout(body_html: str, tone="info", title: str | None = None):
    fg, bg, bd = TONES[tone]
    head = f'<b class="t" style="color:{fg}">{esc(title)}</b>' if title else ""
    st.markdown(
        f'<div class="callout" style="background:{bg};border:1px solid {bd};color:#1d2939">{head}{body_html}</div>',
        unsafe_allow_html=True,
    )


def hero(kicker, title, subtitle):
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{esc(kicker)}</div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def section(title, subtitle=None):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def show_df(df: pd.DataFrame):
    try:
        st.dataframe(df, hide_index=True, **FULL)
    except TypeError:
        st.dataframe(df, hide_index=True)


def show_chart(chart):
    try:
        st.altair_chart(chart, **FULL)
    except TypeError:
        st.altair_chart(chart)


# ============================================================
# 2. 숫자 표기 함수
# ============================================================
def won(v) -> str:
    """만원 단위 값을 읽기 쉬운 표현(만 원/억 원)으로 변환."""
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


def pct(v, d=1) -> str:
    return "계산할 수 없음" if v is None or not math.isfinite(v) else f"{v:.{d}f}%"


def ratio(n, d):
    return None if d is None or d <= 0 else n / d * 100


def fmt_months(v) -> str:
    if v is None:
        return "지출 입력 필요"
    return "계산할 수 없음" if not math.isfinite(v) else f"{v:.1f}개월"


# ============================================================
# 3. 상태(State) 관리
# ============================================================
GOALS = ["전반적인 재무 점검", "비상자금 마련", "부채 상환", "결혼 자금", "주택 마련",
         "자녀 교육비", "은퇴 준비", "경제적 독립(FIRE)", "자산 증식"]
HOUSEHOLDS = ["1인 가구", "부부·2인 가구", "자녀가 있는 가구", "기타"]
STAGES = ["사회초년기", "가족 형성기", "자녀 양육기", "중장년기", "은퇴 전후", "기타"]
LOAN_METHODS = ["원리금균등", "원금균등", "만기일시"]

PROP_COLS = ["이름", "용도", "평가액", "담보대출", "임대형태", "보증금", "월세", "보증금 만기(개월 후)"]
PROP_NUM = ["평가액", "담보대출", "보증금", "월세", "보증금 만기(개월 후)"]
TERM_COLS = ["항목", "연 금액", "시작 연차", "기간(년)"]
TERM_NUM = ["연 금액", "시작 연차", "기간(년)"]
ONE_COLS = ["항목", "금액", "몇 개월 후"]
ONE_NUM = ["금액", "몇 개월 후"]

DEFAULTS = {
    # 나의 상황·목표
    "household": HOUSEHOLDS[0], "life_stage": STAGES[0], "age": 30.0,
    "goal": GOALS[0], "years": 3, "target": 0.0, "already_saved": 0.0, "extra_monthly": 0.0,
    "expected_return": 3.0, "inflation": 2.0,
    # 금융·기타 자산
    "cash": 0.0, "deposits": 0.0, "stocks": 0.0, "leverage": 0.0, "crypto": 0.0,
    "pension": 0.0, "other_assets": 0.0, "rent_deposit_paid": 0.0,
    "child_assets": 0.0, "include_child": False,
    # 부채
    "credit": 0.0, "other_debt": 0.0,
    "debt_mode": "직접 입력", "debt_payment": 0.0, "loan_rate": 4.0, "loan_years": 30.0,
    "loan_method": LOAN_METHODS[0], "borrower_income": 0.0,
    # 월 수입·지출
    "income": 0.0, "dividend_income": 0.0, "other_income": 0.0,
    "living_cost": 0.0, "tax_reserve": 0.0, "insurance_premium": 0.0, "family_support": 0.0,
    "irregular_monthly": 0.0,
    # 보장
    "earner_income": 0.0, "cover_years": 10.0, "cover_replace": 70.0, "cover_count_loans": True,
    "coverage_death": 0.0, "cover_asset_pct": 50.0, "has_silson": False,
    # 표 데이터
    "props": [], "term_exp": [], "oneoffs": [],
    # 실행·점검
    "checks": {}, "history": [], "next_review": "",
}

DEMO = {
    "household": "자녀가 있는 가구", "life_stage": "중장년기", "age": 49.0,
    "goal": "전반적인 재무 점검", "years": 5, "target": 50000.0, "already_saved": 5000.0,
    "extra_monthly": 0.0, "expected_return": 3.0, "inflation": 2.0,
    "cash": 5000.0, "deposits": 0.0, "stocks": 45000.0, "leverage": 45000.0, "crypto": 20000.0,
    "pension": 0.0, "other_assets": 0.0, "rent_deposit_paid": 0.0,
    "child_assets": 12000.0, "include_child": False,
    "credit": 0.0, "other_debt": 0.0,
    "debt_mode": "대출조건으로 자동 계산", "debt_payment": 293.4, "loan_rate": 4.2, "loan_years": 30.0,
    "loan_method": "원리금균등", "borrower_income": 0.0,
    "income": 450.0, "dividend_income": 150.0, "other_income": 0.0,
    "living_cost": 260.0, "tax_reserve": 145.0, "insurance_premium": 12.0, "family_support": 40.0,
    "irregular_monthly": 0.0,
    "earner_income": 450.0, "cover_years": 10.0, "cover_replace": 70.0, "cover_count_loans": True,
    "coverage_death": 0.0, "cover_asset_pct": 50.0, "has_silson": True,
    "props": [
        {"이름": "A 아파트(실거주)", "용도": "실거주", "평가액": 160000.0, "담보대출": 60000.0,
         "임대형태": "없음", "보증금": 0.0, "월세": 0.0, "보증금 만기(개월 후)": 0.0},
        {"이름": "B 오피스텔", "용도": "임대", "평가액": 40000.0, "담보대출": 0.0,
         "임대형태": "월세", "보증금": 10000.0, "월세": 90.0, "보증금 만기(개월 후)": 24.0},
        {"이름": "C 아파트", "용도": "임대", "평가액": 90000.0, "담보대출": 0.0,
         "임대형태": "전세", "보증금": 45000.0, "월세": 0.0, "보증금 만기(개월 후)": 12.0},
        {"이름": "D 상가", "용도": "임대", "평가액": 50000.0, "담보대출": 0.0,
         "임대형태": "월세", "보증금": 10000.0, "월세": 150.0, "보증금 만기(개월 후)": 24.0},
    ],
    "term_exp": [
        {"항목": "자녀 등록금·주거비", "연 금액": 1200.0, "시작 연차": 1.0, "기간(년)": 4.0},
        {"항목": "A 아파트 수리비", "연 금액": 1000.0, "시작 연차": 1.0, "기간(년)": 2.0},
    ],
    "oneoffs": [],
}


def init_state():
    if "mc" not in st.session_state:
        st.session_state["mc"] = copy.deepcopy(DEFAULTS)
    for k, v in DEFAULTS.items():
        st.session_state["mc"].setdefault(k, copy.deepcopy(v))
    st.session_state.setdefault("nav", "🏠 홈")


def _clear_widget_state():
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and (k.startswith("w_") or k.startswith("_base_") or k.startswith("ed_")):
            st.session_state.pop(k, None)


def load_demo():
    st.session_state["mc"] = {**copy.deepcopy(DEFAULTS), **copy.deepcopy(DEMO)}
    _clear_widget_state()
    st.session_state["nav"] = "📊 재무현황"


def reset_all():
    st.session_state["mc"] = copy.deepcopy(DEFAULTS)
    _clear_widget_state()
    st.session_state["nav"] = "🏠 홈"


def goto(page: str):
    st.session_state["nav"] = page


def import_json(raw: bytes) -> tuple[bool, str]:
    try:
        obj = json.loads(raw.decode("utf-8"))
        payload = obj.get("data", obj)
        new = copy.deepcopy(DEFAULTS)
        for k, default in DEFAULTS.items():
            if k not in payload:
                continue
            v = payload[k]
            if isinstance(default, bool):
                new[k] = bool(v)
            elif isinstance(default, int):
                new[k] = int(round(float(v)))
            elif isinstance(default, float):
                new[k] = float(v)
            elif isinstance(default, str):
                new[k] = str(v)
            elif isinstance(default, list):
                new[k] = list(v) if isinstance(v, list) else []
            elif isinstance(default, dict):
                new[k] = dict(v) if isinstance(v, dict) else {}
        st.session_state["mc"] = new
        _clear_widget_state()
        return True, "저장된 입력값을 불러왔어요."
    except Exception as e:  # noqa: BLE001
        return False, f"파일을 읽지 못했어요: {e}"


# ---- 위젯 헬퍼: 페이지를 이동해도 입력값이 유지되도록 dict(S)에 동기화 ----
def num(label, key, S, step=10.0, help=None, container=None, max_value=None, fmt="%g"):
    c = container or st
    v = c.number_input(
        label, min_value=0.0, max_value=max_value, value=float(S.get(key, 0.0) or 0.0),
        step=step, format=fmt, key=f"w_{key}", help=help,
    )
    S[key] = float(v)
    return v


def sel(label, key, S, options, container=None, help=None):
    c = container or st
    cur = S.get(key, options[0])
    idx = options.index(cur) if cur in options else 0
    v = c.selectbox(label, options, index=idx, key=f"w_{key}", help=help)
    S[key] = v
    return v


def chk(label, key, S, container=None, help=None):
    c = container or st
    v = c.checkbox(label, value=bool(S.get(key, False)), key=f"w_{key}", help=help)
    S[key] = bool(v)
    return v


def table_editor(name, S, cols, numcols, column_config, help_text=None):
    """data_editor 편집값이 리런 중 초기화되지 않도록 원본 DF를 세션에 고정."""
    base_key = f"_base_{name}"
    if base_key not in st.session_state:
        st.session_state[base_key] = rows_to_df(S[name], cols, numcols)
    kwargs = dict(num_rows="dynamic", column_config=column_config, hide_index=True, key=f"ed_{name}")
    try:
        edited = st.data_editor(st.session_state[base_key], **FULL, **kwargs)
    except TypeError:
        edited = st.data_editor(st.session_state[base_key], **kwargs)
    S[name] = clean_rows(edited, cols, numcols)
    return S[name]


def rows_to_df(rows, cols, numcols) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=cols)
    for c in cols:
        if c in numcols:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).astype(float)
        else:
            df[c] = df[c].fillna("").astype(str)
    return df


def clean_rows(df, cols, numcols):
    d = rows_to_df(df.to_dict("records"), cols, numcols)
    out = []
    for r in d.to_dict("records"):
        text_empty = all((str(r[c]).strip() in ("", "없음", "nan", "None")) for c in cols if c not in numcols)
        num_empty = all(float(r[c]) == 0 for c in numcols)
        if text_empty and num_empty:
            continue
        out.append({c: (float(r[c]) if c in numcols else str(r[c])) for c in cols})
    return out


# ============================================================
# 4. 금융 계산 함수
# ============================================================
def A(S, k) -> float:
    try:
        return float(S.get(k, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def monthly_payment(p, rate_pct, years) -> float:
    """원리금균등 월 상환액(첫 달 기준)."""
    n = int(round(years * 12))
    if p <= 0 or n <= 0:
        return 0.0
    r = rate_pct / 1200
    return p / n if r == 0 else p * r / (1 - (1 + r) ** -n)


def amort_schedule(p, rate_pct, years, method="원리금균등", extra=0.0):
    """연도별 상환 스케줄. extra=매월 추가 상환액(만기일시 제외)."""
    n = int(round(years * 12))
    r = rate_pct / 1200
    cols = ["연차", "상환 원금", "납부 이자", "연말 잔액"]
    if p <= 0 or n <= 0:
        return pd.DataFrame(columns=cols), {"first": 0.0, "interest": 0.0, "months": 0, "total": 0.0}
    annuity = monthly_payment(p, rate_pct, years)
    bal, month, total_int, first = p, 0, 0.0, 0.0
    yearly: dict[int, list[float]] = {}
    while bal > 1e-9 and month < n:
        month += 1
        interest = bal * r
        if method == "원리금균등":
            princ = annuity - interest
        elif method == "원금균등":
            princ = p / n
        else:
            princ = bal if month == n else 0.0
        if method != "만기일시":
            princ += extra
        princ = min(princ, bal)
        if month == 1:
            first = interest + (princ - (extra if method != "만기일시" else 0.0))
        bal -= princ
        total_int += interest
        y = (month - 1) // 12 + 1
        row = yearly.setdefault(y, [0.0, 0.0, 0.0])
        row[0] += princ
        row[1] += interest
        row[2] = bal
    df = pd.DataFrame([[y, *v] for y, v in yearly.items()], columns=cols)
    return df, {"first": first, "interest": total_int, "months": month, "total": p + total_int}


def prop_metrics(S) -> dict:
    df = rows_to_df(S.get("props", []), PROP_COLS, PROP_NUM)
    rented = df[df["임대형태"].isin(["전세", "월세"])]
    near = rented[(rented["보증금"] > 0) & (rented["보증금 만기(개월 후)"] <= 12)]
    return {
        "df": df,
        "value": float(df["평가액"].sum()),
        "loans": float(df["담보대출"].sum()),
        "deposits_owed": float(rented["보증금"].sum()),
        "rent_income": float(df[df["임대형태"] == "월세"]["월세"].sum()),
        "near_deposit": float(near["보증금"].sum()),
        "rented": rented,
    }


def calculate(S) -> dict:
    pm = prop_metrics(S)
    cash, deposits = A(S, "cash"), A(S, "deposits")
    stocks, leverage, crypto, pension = A(S, "stocks"), A(S, "leverage"), A(S, "crypto"), A(S, "pension")
    other_assets = A(S, "other_assets") + A(S, "rent_deposit_paid")
    child = A(S, "child_assets") if S.get("include_child") else 0.0
    financial = cash + deposits + stocks + pension + crypto
    assets = financial + pm["value"] + other_assets + child
    debts = pm["loans"] + A(S, "credit") + A(S, "other_debt") + pm["deposits_owed"]

    income = A(S, "income") + A(S, "dividend_income") + A(S, "other_income") + pm["rent_income"]
    if S.get("debt_mode") == "대출조건으로 자동 계산":
        debt_payment = monthly_payment(pm["loans"], A(S, "loan_rate"), A(S, "loan_years"))
    else:
        debt_payment = A(S, "debt_payment")
    core = A(S, "living_cost") + A(S, "tax_reserve") + A(S, "insurance_premium") + A(S, "family_support")
    irregular = A(S, "irregular_monthly")
    outflow = core + debt_payment + irregular
    surplus = income - outflow
    liquid = cash + deposits
    high_risk = leverage + crypto
    target_gap = max(0.0, A(S, "target") - A(S, "already_saved"))
    months_goal = max(1, int(A(S, "years") or 3) * 12)

    return {
        "props": pm["df"], "rented": pm["rented"],
        "loans": pm["loans"], "deposits_owed": pm["deposits_owed"], "rent_income": pm["rent_income"],
        "near_deposit": pm["near_deposit"], "prop_value": pm["value"],
        "cash": cash, "deposits": deposits, "stocks": stocks, "leverage": leverage, "crypto": crypto,
        "pension": pension, "financial": financial, "other_assets": other_assets, "child": child,
        "assets": assets, "debts": debts, "net": assets - debts, "liquid": liquid,
        "income": income, "core": core, "debt_payment": debt_payment, "irregular": irregular,
        "outflow": outflow, "surplus": surplus,
        "runway": None if outflow <= 0 else liquid / outflow,
        "debt_ratio": ratio(debts, assets),
        "repayment_ratio": ratio(debt_payment, income),
        "savings_rate": ratio(surplus, income),
        "high_risk": high_risk,
        "high_risk_ratio": ratio(high_risk, financial),
        "leverage_ratio": ratio(leverage, financial),
        "liquid_ratio": ratio(liquid, financial),
        "readiness": ratio(liquid, pm["near_deposit"]) if pm["near_deposit"] > 0 else None,
        "target_gap": target_gap, "months_goal": months_goal,
        "required_monthly": target_gap / months_goal,
        "child_raw": A(S, "child_assets"),
    }


def has_data(c) -> bool:
    return c["assets"] > 0 or c["income"] > 0 or c["outflow"] > 0


def build_timeline(S, c, years=10, include_oneoffs=True) -> pd.DataFrame:
    term = rows_to_df(S.get("term_exp", []), TERM_COLS, TERM_NUM)
    one = rows_to_df(S.get("oneoffs", []), ONE_COLS, ONE_NUM)
    cum, rows = c["liquid"], []
    for y in range(1, years + 1):
        term_m = 0.0
        for r in term.to_dict("records"):
            s, d = int(max(1, r["시작 연차"])), int(r["기간(년)"])
            if s <= y < s + d:
                term_m += r["연 금액"] / 12
        month = c["surplus"] - term_m
        one_y = 0.0
        if include_oneoffs:
            for r in one.to_dict("records"):
                if r["금액"] > 0 and math.ceil(max(r["몇 개월 후"], 1) / 12) == y:
                    one_y += r["금액"]
        cum += month * 12 - one_y
        rows.append({"연차": y, "기간한정 지출(월)": term_m, "월 현금흐름": month,
                     "연 현금흐름": month * 12, "일회성 지출": one_y, "현금·예금 잔액(추정)": cum})
    return pd.DataFrame(rows)


def protection_need(S, c) -> dict:
    income_need = A(S, "earner_income") * 12 * A(S, "cover_replace") / 100 * A(S, "cover_years")
    loan_need = (c["loans"] + A(S, "credit") + A(S, "other_debt")) if S.get("cover_count_loans") else 0.0
    invest_ok = max(0.0, c["stocks"] - c["leverage"]) * A(S, "cover_asset_pct") / 100
    offset = c["liquid"] + invest_ok
    need = income_need + loan_need
    existing = A(S, "coverage_death")
    gap = max(0.0, need - existing - offset)
    return {"income_need": income_need, "loan_need": loan_need, "need": need, "offset": offset,
            "existing": existing, "gap": gap,
            "cover_ratio": ratio(existing + offset, need) if need > 0 else None}


def apply_scenario(S, c, income_pct=0.0, vacancy_pct=0.0, rate_delta=0.0,
                   expense_delta=0.0, one_off=0.0, invest_drop=0.0) -> dict:
    rent = c["rent_income"]
    new_income = (c["income"] - rent) * (1 + income_pct / 100) + rent * (1 - vacancy_pct / 100)
    pay_delta = 0.0
    if rate_delta and c["loans"] > 0:
        pay_delta = (monthly_payment(c["loans"], A(S, "loan_rate") + rate_delta, A(S, "loan_years"))
                     - monthly_payment(c["loans"], A(S, "loan_rate"), A(S, "loan_years")))
    new_out = max(0.0, c["outflow"] + expense_delta + pay_delta)
    d = invest_drop / 100
    plain = max(0.0, c["stocks"] - c["leverage"])
    loss = plain * d + min(c["leverage"], c["leverage"] * 3 * d) + c["crypto"] * d
    liquid = c["liquid"] - one_off
    return {
        "income": new_income, "outflow": new_out, "surplus": new_income - new_out,
        "liquid": liquid, "net": c["net"] - one_off - loss, "invest_loss": loss,
        "runway": None if new_out <= 0 else liquid / new_out,
        "pay_delta": pay_delta,
    }


def path_example(returns_pct, mult, start=100.0):
    und, etf = start, start
    rows = [{"단계": 0, "기초지수": und, "레버리지 ETF": etf}]
    for i, r in enumerate(returns_pct, 1):
        und *= 1 + r / 100
        etf *= max(0.0, 1 + mult * r / 100)
        rows.append({"단계": i, "기초지수": und, "레버리지 ETF": etf})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def simulate_lev(mu, sigma, mult, fee, years, n_sims, seed=7):
    steps = int(round(years * 252))
    dt = 1 / 252
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_sims, steps), dtype=np.float32)
    r = np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * z) - 1
    del z
    lev = np.maximum(mult * r - fee * dt, -0.999)
    und = np.cumprod(1 + r, axis=1)
    etf = np.cumprod(1 + lev, axis=1)
    und_end, etf_end = und[:, -1], etf[:, -1]
    mdd = (etf / np.maximum.accumulate(etf, axis=1)).min(axis=1) - 1
    pts = np.unique(np.append(np.arange(20, steps, 21), steps - 1))
    q = lambda a, p: np.percentile(a[:, pts], p, axis=0) * 100  # noqa: E731
    chart = pd.DataFrame({
        "기초지수 중앙값": q(und, 50), "레버리지 ETF 중앙값": q(etf, 50),
        "레버리지 ETF 하위 10%": q(etf, 10), "레버리지 ETF 상위 10%": q(etf, 90),
    }, index=np.round((pts + 1) / 252, 2))
    chart.index.name = "경과 연수"
    return {
        "chart": chart,
        "p_loss": float((etf_end < 1).mean() * 100),
        "p_half": float((mdd <= -0.5).mean() * 100),
        "p_gap": float(((und_end > 1) & (etf_end < 1)).mean() * 100),
        "etf_med": float(np.median(etf_end) * 100), "etf_p10": float(np.percentile(etf_end, 10) * 100),
        "etf_p90": float(np.percentile(etf_end, 90) * 100), "und_med": float(np.median(und_end) * 100),
        "mdd_med": float(np.median(mdd) * 100),
    }


# ============================================================
# 5. 점수 · 진단 · 질문 · 실행과제
# ============================================================
def _interp(x, pts):
    xs, ys = zip(*pts)
    return float(np.interp(x, xs, ys))


def health_scores(S, c) -> dict:
    sc: dict[str, float | None] = {}
    if c["savings_rate"] is None:
        sc["현금흐름"] = 0.0 if c["outflow"] > 0 else None
    else:
        sc["현금흐름"] = _interp(c["savings_rate"], [(-20, 0), (0, 35), (10, 65), (20, 90), (30, 100)])
    if c["runway"] is None:
        sc["유동성"] = None
    else:
        s = _interp(c["runway"], [(0, 0), (1, 25), (3, 60), (6, 90), (9, 100)])
        if c["readiness"] is not None:
            s = min(s, _interp(c["readiness"], [(0, 0), (50, 40), (100, 100)]))
        sc["유동성"] = s
    if c["debt_ratio"] is None:
        sc["부채 부담"] = None if c["debts"] <= 0 else 0.0
    else:
        s = _interp(c["debt_ratio"], [(0, 100), (30, 90), (50, 65), (70, 35), (100, 5)])
        if c["repayment_ratio"] is not None:
            s -= _interp(c["repayment_ratio"], [(30, 0), (50, 25)])
        sc["부채 부담"] = max(0.0, s)
    sc["투자 집중도"] = None if c["high_risk_ratio"] is None else _interp(
        c["high_risk_ratio"], [(0, 100), (10, 95), (30, 70), (50, 40), (80, 10)])
    pn = protection_need(S, c)
    sc["소득 보장"] = None if pn["cover_ratio"] is None else _interp(
        pn["cover_ratio"], [(0, 10), (50, 50), (100, 100)])
    vals = [v for v in sc.values() if v is not None]
    overall = sum(vals) / len(vals) if vals else None
    return {"parts": sc, "overall": overall}


def grade(score):
    if score is None:
        return "정보 부족", "neutral"
    if score >= 80:
        return "양호", "ok"
    if score >= 60:
        return "보통", "info"
    if score >= 40:
        return "주의", "warn"
    return "우선 점검", "bad"


LEVEL_TONE = {"우선 점검": "bad", "확인 권장": "warn", "위험 이해": "warn", "예정 지출": "info",
              "기회": "ok", "유지·관리": "ok", "정보 확인": "neutral"}
LEVEL_ORDER = ["우선 점검", "확인 권장", "위험 이해", "예정 지출", "기회", "유지·관리", "정보 확인"]


def _it(level, title, finding, evidence, why, action):
    return {"level": level, "title": title, "finding": finding, "evidence": evidence, "why": why, "action": action}


def make_diagnosis(S, c) -> list[dict]:
    items = []
    if c["surplus"] < 0:
        items.append(_it("우선 점검", "매달 현금흐름이 부족해요",
                         f"입력값 기준으로 매달 {won(abs(c['surplus']))}이 부족합니다.",
                         f"월 소득 {won(c['income'])} − 월 정기지출 {won(c['outflow'])} = {won(c['surplus'])}",
                         "적자가 지속되면 비상자금이 줄거나 추가 차입이 필요해질 수 있습니다.",
                         "지출을 필수·조정 가능 항목으로 나누고, 대출 상환액·세금 적립·비정기 지출이 중복되거나 빠지지 않았는지 확인하세요."))
    elif c["surplus"] == 0 and c["income"] > 0:
        items.append(_it("우선 점검", "매달 남는 돈이 거의 없어요", "월 소득과 월 지출이 같습니다.",
                         f"월 소득 {won(c['income'])} − 월 정기지출 {won(c['outflow'])} = 0",
                         "예상하지 못한 지출이 생기면 곧바로 적자로 전환될 수 있습니다.",
                         "비정기 지출이 빠지지 않았는지 확인하고 조정 가능한 지출을 찾아보세요."))
    elif c["surplus"] > 0:
        items.append(_it("유지·관리", "월 잉여자금이 발생하고 있어요", f"입력값 기준으로 매달 {won(c['surplus'])}이 남습니다.",
                         f"월 소득 {won(c['income'])} − 월 정기지출 {won(c['outflow'])} = {won(c['surplus'])}",
                         "계산상 남는 돈과 실제 통장에 남는 돈은 다를 수 있습니다.",
                         "지난 2~3개월 통장 잔액 변화와 비교해 누락된 지출이 없는지 확인하세요."))
    if c["runway"] is not None:
        ev = f"현금·예금 {won(c['liquid'])} ÷ 월 정기지출 {won(c['outflow'])}"
        if c["runway"] < 1:
            items.append(_it("우선 점검", "현금·예금 여력이 매우 짧아요", f"현금·예금은 월 지출의 약 {c['runway']:.1f}개월분입니다.", ev,
                             "주식·부동산 등은 원하는 시점에 손실 없이 현금화하기 어려울 수 있습니다.",
                             "가까운 시기의 지출·대출 상환 일정을 확인하고, 투자자산을 즉시 현금화할 수 있다고 가정하지 마세요."))
        elif c["runway"] < 3:
            items.append(_it("확인 권장", "비상자금 목표를 점검해 보세요", f"현금·예금은 월 지출의 약 {c['runway']:.1f}개월분입니다.", ev,
                             "필요한 비상자금 수준은 소득 안정성과 지출 구조에 따라 달라집니다.",
                             "고용 안정성·부양가족·예정 지출을 고려해 목표를 정하세요. 3~6개월은 참고 범위일 뿐 정답이 아닙니다."))
        else:
            items.append(_it("유지·관리", "현금·예금 완충 여력을 확인했어요", f"현금·예금은 월 지출의 약 {c['runway']:.1f}개월분입니다.", ev,
                             "비상자금은 예정된 큰 지출·보증금 반환과 별도로 생각하는 편이 안전합니다.",
                             "이 금액에서 가까운 시기에 쓸 돈을 빼고도 여유가 있는지 '유동성·보증금 반환' 메뉴에서 확인하세요."))
    if c["near_deposit"] > 0:
        ready = c["readiness"] or 0
        tone_level = "우선 점검" if ready < 100 else "확인 권장"
        items.append(_it(tone_level, "1년 안에 돌려줄 임대보증금이 있어요",
                         f"12개월 내 만기 보증금 {won(c['near_deposit'])} 대비 현금·예금은 {pct(ready, 0)}입니다.",
                         f"현금·예금 {won(c['liquid'])} ÷ 12개월 내 만기 보증금 {won(c['near_deposit'])}",
                         "보증금은 만기에 한꺼번에 돌려줘야 하는 부채이며 생활비 비상자금과 따로 준비해야 합니다.",
                         "'유동성·보증금 반환' 메뉴에서 매도·대출·신규 임차인 확보 시나리오별 부족액을 비교하세요."))
    elif c["deposits_owed"] > 0:
        items.append(_it("확인 권장", "임대보증금 반환 의무가 있어요", f"반환 의무 합계는 {won(c['deposits_owed'])}입니다.",
                         "부동산 표의 임대형태가 전세·월세인 보증금 합계",
                         "만기가 가까워지기 전에 반환 재원을 정해 두어야 합니다.",
                         "각 보증금의 만기와 반환 재원을 표로 정리하세요."))
    if c["debt_ratio"] is not None and c["debt_ratio"] >= 50:
        items.append(_it("확인 권장", "자산 대비 부채 비중이 높아요", f"총부채는 총자산의 {c['debt_ratio']:.1f}%입니다.",
                         f"총부채 {won(c['debts'])} ÷ 총자산 {won(c['assets'])}",
                         "부채 비율만으로 위험을 단정할 수 없고 금리·만기·소득 대비 상환 부담을 함께 봐야 합니다.",
                         "대출별 금리·만기·상환 방식·중도상환수수료를 한 장으로 정리해 상환 우선순위를 검토하세요."))
    if c["repayment_ratio"] is not None and c["repayment_ratio"] >= 30:
        items.append(_it("확인 권장", "월 소득 중 대출 상환액 비중을 살펴보세요", f"월 대출 상환액은 월 소득의 {c['repayment_ratio']:.1f}%입니다.",
                         f"월 대출 상환액 {won(c['debt_payment'])} ÷ 월 소득 {won(c['income'])}",
                         "이 비율은 가계 전체 소득 기준의 참고값이며 금융기관 심사의 DSR과 다릅니다.",
                         "차주 본인의 인정소득과 모든 금융부채의 연간 원리금 기준으로 별도 확인하세요."))
    if c["high_risk_ratio"] is not None and c["high_risk_ratio"] >= 30:
        items.append(_it("위험 이해", "고위험 자산 비중이 높아요", f"금융자산 중 레버리지 ETF·가상자산·테마주 비중은 {c['high_risk_ratio']:.1f}%입니다.",
                         f"(레버리지 {won(c['leverage'])} + 가상자산·테마주 {won(c['crypto'])}) ÷ 금융자산 {won(c['financial'])}",
                         "변동성이 큰 자산이 많으면 급락 시 생활비·보증금 반환 재원이 함께 줄 수 있습니다.",
                         "'투자위험' 메뉴에서 하락 충격과 레버리지 ETF 경로 시뮬레이션을 확인하세요."))
    elif c["leverage"] > 0:
        items.append(_it("위험 이해", "레버리지 ETF의 변동성을 별도로 확인하세요", f"레버리지 ETF 입력 금액은 {won(c['leverage'])}입니다.",
                         f"금융자산 중 비중 {pct(c['leverage_ratio'])}",
                         "일일 수익률 배수 상품은 장기 수익률이 기초지수 누적수익률의 단순 배수와 달라질 수 있습니다.",
                         "보유 목적·기간과 큰 폭 하락을 감당할 수 있는지 확인하세요."))
    pn = protection_need(S, c)
    if A(S, "earner_income") > 0 and pn["gap"] > 0:
        items.append(_it("확인 권장", "소득자 보장 공백 가능성이 있어요", f"단순 계산상 보장 부족액은 {won(pn['gap'])}입니다.",
                         f"필요액 {won(pn['need'])} − 기존 보장 {won(pn['existing'])} − 차감 자산 {won(pn['offset'])}",
                         "소득이 중단되면 생활비와 대출 상환을 이어가기 어려울 수 있습니다.",
                         "기존 계약 조건과 가입 가능 여부를 확인한 뒤 필요한 보장만 설계하세요. 새 계약 승인 전에 기존 보장을 해지하지 마세요."))
    if c["child_raw"] > 0:
        items.append(_it("확인 권장", "자녀 명의 자금의 출처를 정리해 두세요", f"자녀 명의 자산 {won(c['child_raw'])}이 입력되어 있습니다.",
                         "부모 가계 자산·상환 재원 계산에서는 기본적으로 제외합니다.",
                         "자금 이전은 시기·출처·신고 여부에 따라 세무 확인이 필요할 수 있습니다.",
                         "이전 시기·금액·계좌 내역을 정리해 세무 전문가나 국세청 공식 안내로 확인하세요."))
    if c["savings_rate"] is not None and c["savings_rate"] >= 20:
        items.append(_it("기회", "목표를 위한 저축 여력이 있어요", f"계산상 월 잉여자금은 월 소득의 {c['savings_rate']:.1f}%입니다.",
                         f"월 잉여자금 {won(c['surplus'])} ÷ 월 소득 {won(c['income'])}",
                         "잉여자금 전부를 저축할 수 있다고 가정하면 비정기 지출로 계획이 흔들릴 수 있습니다.",
                         "비상자금과 예정 지출을 먼저 고려한 뒤 지속 가능한 저축액을 정하세요."))
    if not items:
        items.append(_it("정보 확인", "입력값이 부족해 진단이 제한적이에요", "소득·지출·자산 정보를 입력해 주세요.",
                         "입력 항목이 0이면 관련 지표를 계산할 수 없습니다.",
                         "정보가 부족한 상태에서 단정적인 진단을 하지 않도록 했습니다.",
                         "'정보 입력' 메뉴에서 합계 금액을 입력하세요. 계좌번호 같은 개인정보는 입력하지 마세요."))
    items.sort(key=lambda x: LEVEL_ORDER.index(x["level"]))
    return items[:9]


def make_questions(S, c) -> list[str]:
    qs = ["매월 정기지출 외에 앞으로 3~5년 안에 예정된 큰 지출(교육·주거·수리·결혼 등)은 무엇이고 언제 얼마가 필요한가요?"]
    if c["deposits_owed"] > 0:
        qs.append("임대보증금의 만기는 각각 언제이며, 세입자가 퇴거를 요구하면 즉시 반환할 현금이나 대출 여력이 있나요?")
    if c["leverage"] > 0 or c["crypto"] > 0:
        qs.append("과거 보유 자산이 30% 이상 하락했을 때 어떻게 대응했고, 같은 상황이 오면 생활비·대출 상환에 문제가 없나요?")
    if c["child_raw"] > 0:
        qs.append("자녀 명의 자금의 출처는 무엇이고, 최근 10년 안에 자녀에게 이전한 다른 자산과 신고 이력이 있나요?")
    if c["debts"] > 0:
        qs.append("대출별 금리 유형(고정·변동), 만기, 상환 방식, 중도상환수수료와 차주(명의자)는 어떻게 되나요?")
    if A(S, "earner_income") > 0:
        qs.append("주 소득자가 질병·사고로 일하지 못하면 가계는 몇 개월을 버틸 수 있고, 기존 보험은 어떤 보장이 남아 있나요?")
    qs.append("가장 이루고 싶은 재무목표 1~2개와 그 시기, 그리고 포기할 수 없는 지출은 무엇인가요?")
    return qs


def make_tasks(S, c) -> list[tuple[str, str, str, str]]:
    """(id, 단계, 제목, 설명)"""
    T = []
    S1, S2, S3, S4 = "단기 (1개월 이내)", "중기 (1~3개월)", "장기 (4개월 이후)", "상시 점검"
    pn = protection_need(S, c)
    if c["surplus"] < 0:
        T.append(("deficit", S1, "월 적자 원인 구분하기", f"월 {won(abs(c['surplus']))}이 부족합니다. 필수 생활비·선택 지출·대출 상환·세금·비정기 지출을 나눠 확인하세요."))
    elif c["income"] > 0:
        T.append(("compare", S1, "계산상 잉여자금과 실제 저축액 비교", f"계산상 월 {won(c['surplus'])}이 남습니다. 최근 2~3개월 통장 잔액 변화와 비교해 보세요."))
    if c["runway"] is not None and c["runway"] < 3:
        T.append(("emergency", S1, "비상자금 목표 정하기", "현금·예금이 월 지출의 3개월분보다 적습니다. 소득 안정성과 가족 상황에 맞춰 목표를 정하세요."))
    if c["debts"] > 0:
        T.append(("loantable", S1, "대출 조건표 한 장으로 정리", "대출별 잔액·금리·만기·월 상환액·중도상환수수료·차주를 한곳에 정리하세요."))
    if c["child_raw"] > 0:
        T.append(("child", S1, "자녀 명의 자금 이전 내역 정리", "이전 시기·금액·출처·과거 증여 내역을 정리하고 세무 전문가 확인 후 신고 필요성을 판단하세요."))
    if A(S, "earner_income") > 0 and pn["gap"] > 0:
        T.append(("protect", S1, "보장 공백 확인", "기존 계약 조건과 가입 가능 여부를 먼저 확인하세요. 새 계약 승인 전 기존 보장을 임의로 해지하지 마세요."))
    if c["deposits_owed"] > 0:
        T.append(("depositplan", S2, "임대보증금 반환 시나리오 확정", "만기별 반환 재원(현금·매도·대출·신규 임차인)을 정하고 부족액을 확인하세요."))
    if c["high_risk_ratio"] is not None and c["high_risk_ratio"] >= 30:
        T.append(("derisk", S2, "고위험 자산 분할 축소 계획", "한 번에 처분하기보다 세금·거래비용·시장 상황을 확인해 분할 실행 계획을 세우세요."))
    if A(S, "target") > 0:
        T.append(("goal", S2, "목표 저축액을 월 예산에 반영", f"목표 기간에 필요한 월 저축액은 단순 계산 약 {won(c['required_monthly'])}입니다. 지속 가능한 금액인지 확인하세요."))
    if c["surplus"] > 0:
        T.append(("pension", S3, "연금저축·IRP 납입 가능액 결정", "생활비·세금·보증금 반환 재원을 먼저 확보한 범위에서 납입액을 정하고, 공제 요건은 현행 규정으로 확인하세요."))
    T.append(("monthly", S4, "매월 현금흐름·현금성 자산 확인", "소득·지출·대출 잔액이 바뀌면 입력값을 갱신하고 '스냅샷 기록'을 남기세요."))
    T.append(("semi", S4, "반기별 자산배분·부채·보험·예정 지출 점검", "6개월마다 자산 비중, 대출 조건, 보장 내용, 기간 한정 지출 집행 상황을 점검하세요."))
    T.append(("yearly", S4, "연 1회 세금 자료·금융소득 확인", "연말 전에 소득·세액공제 자료와 이자·배당소득 합산 여부를 확인하세요."))
    return T


# ============================================================
# 6. 공통 화면 조각
# ============================================================
def score_block(sc):
    label, tone = grade(sc["overall"])
    fg = TONES[tone][0]
    ov = sc["overall"]
    ring = (f'<div class="ring" style="background:conic-gradient({fg} {0 if ov is None else ov}%, #e8edf3 0)">'
            f'<div class="ring-in"><b>{"-" if ov is None else round(ov)}</b><span>{esc(label)}</span></div></div>')
    bars = ""
    for name, v in sc["parts"].items():
        if v is None:
            bars += (f'<div class="bar-row"><div class="lab">{esc(name)}</div><div class="track"></div>'
                     f'<div class="num" style="color:#98a2b3">정보 부족</div></div>')
        else:
            _, t = grade(v)
            bars += (f'<div class="bar-row"><div class="lab">{esc(name)}</div><div class="track">'
                     f'<div class="fill" style="width:{v:.0f}%;background:{TONES[t][0]}"></div></div>'
                     f'<div class="num">{v:.0f}점</div></div>')
    c1, c2 = st.columns([1, 2.4])
    c1.markdown(ring, unsafe_allow_html=True)
    c1.markdown('<div class="tiny" style="text-align:center;margin-top:8px">재무 건강 점검 점수<br>(참고용 · 100점 만점)</div>',
                unsafe_allow_html=True)
    c2.markdown(bars, unsafe_allow_html=True)


def render_diagnosis(items):
    for i, it in enumerate(items, 1):
        tone = LEVEL_TONE[it["level"]]
        with st.expander(f"{TONE_EMOJI[tone]} {i}. {it['level']} · {it['title']}", expanded=(i == 1)):
            st.markdown(pill(it["level"], tone), unsafe_allow_html=True)
            st.markdown(f"**무슨 뜻인가요?**  \n{it['finding']}")
            st.markdown(f"**계산 근거**  \n`{it['evidence']}`")
            st.markdown(f"**왜 확인해야 하나요?**  \n{it['why']}")
            st.markdown(f"**다음 행동**  \n{it['action']}")


def donut(df, label_col, value_col, title):
    if df.empty:
        st.caption(f"{title}: 입력된 항목이 없습니다.")
        return
    try:
        import altair as alt
        chart = alt.Chart(df).mark_arc(innerRadius=55).encode(
            theta=alt.Theta(f"{value_col}:Q"),
            color=alt.Color(f"{label_col}:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[label_col, value_col],
        ).properties(height=270, title=title)
        show_chart(chart)
    except Exception:  # noqa: BLE001
        st.markdown(f"**{title}**")
        st.bar_chart(df.set_index(label_col))


def need_data(c) -> bool:
    if has_data(c):
        return True
    hero("START HERE", "먼저 내 재무정보를 입력해 주세요", "자산·부채·월 수입과 지출을 입력하면 이 메뉴의 분석이 자동으로 채워져요.")
    b1, b2 = st.columns(2)
    b1.button("✍️ 직접 입력하러 가기", on_click=goto, args=("✍️ 정보 입력",), type="primary", **FULL)
    b2.button("🧪 예시 가계로 둘러보기", on_click=load_demo, **FULL)
    return False


def note(text):
    st.markdown(f'<div class="tiny">※ {esc(text)}</div>', unsafe_allow_html=True)


# ============================================================
# 7. 페이지: 홈
# ============================================================
def page_home(S, c):
    hero("MONEY CHECK", "내 돈의 상태, 쉽게 확인해요.",
         "복잡한 금융 용어 대신 꼭 필요한 숫자와 다음 행동을 알려드려요. 입력한 정보는 이 브라우저 세션에만 머뭅니다.")
    if not has_data(c):
        cols = st.columns(3)
        steps = [("STEP 1", "내 정보 입력", "자산·부채·부동산·월 수입과 지출을 7개 탭에 나눠 입력해요. 모르는 항목은 0으로 두면 돼요."),
                 ("STEP 2", "한눈에 진단", "순자산, 월 잉여자금, 비상자금 여력, 재무 건강 점수를 자동 계산해요."),
                 ("STEP 3", "다음 행동 찾기", "기간별 현금흐름·보증금 반환·투자위험·목표를 시뮬레이션하고 실행 체크리스트를 만들어요.")]
        for col, (k, t, d) in zip(cols, steps):
            col.markdown(f'<div class="card"><div class="step">{k}</div><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)
        st.write("")
        b1, b2 = st.columns(2)
        b1.button("✍️ 내 정보 입력 시작하기", on_click=goto, args=("✍️ 정보 입력",), type="primary", **FULL)
        b2.button("🧪 예시 가계(가상 사례)로 먼저 둘러보기", on_click=load_demo, **FULL)
    else:
        sc = health_scores(S, c)
        kpi_row([
            ("내 순자산", won(c["net"]), f"총자산 {won(c['assets'])} − 총부채 {won(c['debts'])}", "ok" if c["net"] >= 0 else "bad"),
            ("매달 남는 돈", won(c["surplus"]), f"월 소득 {won(c['income'])} · 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad"),
            ("현금·예금 여력", fmt_months(c["runway"]), "월 정기지출 기준", "ok" if (c["runway"] or 0) >= 3 else "warn"),
            ("재무 건강 점수", "-" if sc["overall"] is None else f"{sc['overall']:.0f}점", grade(sc["overall"])[0], grade(sc["overall"])[1]),
        ])
        st.write("")
        section("지금 가장 먼저 볼 것", "진단 결과 중 우선순위가 높은 항목입니다.")
        top = make_diagnosis(S, c)[:3]
        for it in top:
            t = LEVEL_TONE[it["level"]]
            callout(f"{esc(it['finding'])}<br><span class='tiny'>다음 행동: {esc(it['action'])}</span>", t, f"{it['level']} · {it['title']}")
        n1, n2, n3, n4 = st.columns(4)
        n1.button("📊 재무현황 보기", on_click=goto, args=("📊 재무현황",), **FULL)
        n2.button("📅 기간별 현금흐름", on_click=goto, args=("📅 기간별 현금흐름",), **FULL)
        n3.button("🧪 스트레스 테스트", on_click=goto, args=("🧪 스트레스 테스트",), **FULL)
        n4.button("✅ 실행·점검", on_click=goto, args=("✅ 실행·점검",), **FULL)

    st.write("")
    section("재무설계 6단계와 머니체크 기능", "AFPK 재무설계 프로세스에 맞춰 각 단계를 도와주는 기능을 연결했어요.")
    mapping = [
        ("1단계 · 관계 정립", "서비스 범위와 한계 안내", "이 앱이 하는 일과 하지 않는 일(세무·법률 확정, 상품 추천)을 명시해요."),
        ("2단계 · 목표·자료수집", "정보 입력 · 상담 질문", "7개 탭 입력과 입력 내용에 맞춘 '상담 전 확인 질문'을 제공해요."),
        ("3단계 · 분석·평가", "재무현황 · 기간별 현금흐름", "재무상태표·현금흐름표·건강 점수·기간 한정 지출 반영 분석을 보여줘요."),
        ("4단계 · 설계안 제시", "보증금 반환 · 투자위험 · 목표 · 보장", "시나리오별 부족액, 레버리지 경로, 목표 역산, 보장 공백을 계산해요."),
        ("5단계 · 실행", "실행·점검 로드맵", "단기·중기·장기 과제를 자동 생성하고 완료 여부를 체크해요."),
        ("6단계 · 점검", "스냅샷 기록 · 스트레스 테스트", "정기·수시 점검 기준과 시점별 변화 기록을 남겨요."),
    ]
    for row in (mapping[:3], mapping[3:]):
        cols = st.columns(3)
        for col, (k, t, d) in zip(cols, row):
            col.markdown(f'<div class="card"><div class="step">{k}</div><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)
        st.write("")

    with st.expander("이 도구가 하지 않는 일 (서비스 범위와 한계)"):
        st.markdown(
            "- 입력값을 바탕으로 한 **규칙 기반 계산·안내 도구**이며 외부 생성형 AI나 금융기관 계좌에 연결하지 않습니다.\n"
            "- 특정 금융상품·종목의 매수·매도를 권유하지 않으며, **세금·법률의 최종 판단을 대신하지 않습니다.**\n"
            "- 세법·금융규정은 자주 바뀌므로 세액·공제·한도는 계산하지 않고 확인 과제로 안내합니다.\n"
            "- 계좌번호·주민등록번호·비밀번호 등 민감한 개인정보는 입력하지 마세요."
        )


# ============================================================
# 8. 페이지: 정보 입력
# ============================================================
def page_input(S):
    hero("MY INFO", "내 재무정보 입력", "금액은 모두 만원 단위예요. 예: 500 = 500만 원, 10000 = 1억 원. 모르는 항목은 0으로 두세요.")
    summary = st.container()
    st.write("")
    tabs = st.tabs(["① 나의 상황·목표", "② 금융자산", "③ 부동산·임대", "④ 부채", "⑤ 월 수입·지출", "⑥ 예정 지출", "⑦ 소득자 보장"])

    with tabs[0]:
        a, b, d = st.columns(3)
        sel("가구 형태", "household", S, HOUSEHOLDS, a)
        sel("현재 생활 단계", "life_stage", S, STAGES, b)
        num("나이 (만)", "age", S, step=1.0, container=d, max_value=120.0)
        st.markdown("**재무목표**")
        g1, g2, g3 = st.columns(3)
        sel("가장 중요한 목표", "goal", S, GOALS, g1)
        yopts = [1, 2, 3, 5, 7, 10, 15, 20, 30]
        cur = int(S.get("years", 3)) if int(S.get("years", 3)) in yopts else 3
        S["years"] = g2.selectbox("목표까지 남은 기간", yopts, index=yopts.index(cur), format_func=lambda v: f"{v}년", key="w_years")
        num("목표에 필요한 총금액 (만원)", "target", S, step=100.0, container=g3, help="입력하지 않으면 목표 계산은 생략돼요.")
        h1, h2, h3 = st.columns(3)
        num("목표를 위해 이미 모은 금액 (만원)", "already_saved", S, container=h1)
        num("계획 중인 추가 월 저축액 (만원)", "extra_monthly", S, container=h2)
        num("기대 연수익률 (%)", "expected_return", S, step=0.5, container=h3, max_value=30.0,
            help="목표 플래너에서 수익률을 반영할 때 쓰는 가정값이에요. 보장되는 수익률이 아닙니다.")
        num("물가상승률 (%)", "inflation", S, step=0.5, max_value=20.0, help="목표금액을 미래 가치로 환산할 때 사용합니다.")

    with tabs[1]:
        st.caption("현재 기준의 대략적인 평가액을 입력하세요. 같은 자산을 두 번 입력하지 마세요.")
        l, r = st.columns(2)
        num("현금·입출금 계좌 (만원)", "cash", S, container=l)
        num("예금·적금 (만원)", "deposits", S, container=l)
        num("주식·ETF 전체 (만원)", "stocks", S, container=l, help="레버리지 ETF를 포함한 전체 금액입니다.")
        num("└ 이 중 레버리지 ETF (만원)", "leverage", S, container=l, help="2배·3배 등 일일 수익률 배수 상품. 주식·ETF 전체의 일부로 입력하세요.")
        num("가상자산·테마주 등 고변동 자산 (만원)", "crypto", S, container=r)
        num("연금계좌 (만원)", "pension", S, container=r, help="연금저축·IRP 평가액. 계좌 안의 ETF를 주식·ETF에 중복 입력하지 마세요.")
        num("내가 낸 전월세 보증금 (만원)", "rent_deposit_paid", S, container=r, help="본인이 세입자로 맡겨둔 보증금은 자산입니다.")
        num("기타 자산 (만원)", "other_assets", S, container=r)
        if S["leverage"] > S["stocks"]:
            st.error("레버리지 ETF 금액은 주식·ETF 전체보다 클 수 없어요. 일부로 입력해 주세요.")
        st.markdown("---")
        st.markdown("**자녀 명의 자산 (선택)**")
        k1, k2 = st.columns(2)
        num("자녀 명의 금융자산 (만원)", "child_assets", S, container=k1)
        chk("내 가계 총자산에 포함하기", "include_child", S, k2,
            help="기본값은 제외입니다. 자녀 명의 자산은 부모가 자유롭게 쓸 수 있는 상환 재원으로 보지 않는 것이 보수적이에요.")

    with tabs[2]:
        st.caption("부동산별로 한 줄씩 입력하세요. 임대 중이면 임대형태·받은 보증금·월세·보증금 만기를 입력하면 임대수입과 반환 의무가 자동 계산돼요. 표 아래의 빈 줄을 눌러 행을 추가할 수 있어요.")
        cfg = {
            "이름": st.column_config.TextColumn("이름", width="medium"),
            "용도": st.column_config.SelectboxColumn("용도", options=["실거주", "임대", "기타"], required=True),
            "평가액": st.column_config.NumberColumn("평가액(만원)", min_value=0, step=100, format="%g"),
            "담보대출": st.column_config.NumberColumn("담보대출 잔액(만원)", min_value=0, step=100, format="%g"),
            "임대형태": st.column_config.SelectboxColumn("임대형태", options=["없음", "전세", "월세"], required=True),
            "보증금": st.column_config.NumberColumn("받은 보증금(만원)", min_value=0, step=100, format="%g",
                                                  help="세입자에게 받은 보증금 = 만기에 돌려줘야 할 돈"),
            "월세": st.column_config.NumberColumn("월세(만원)", min_value=0, step=5, format="%g"),
            "보증금 만기(개월 후)": st.column_config.NumberColumn("보증금 만기(개월 후)", min_value=0, step=1, format="%g",
                                                            help="오늘부터 계약 만기까지 남은 개월 수"),
        }
        table_editor("props", S, PROP_COLS, PROP_NUM, cfg)
        pm = prop_metrics(S)
        kpi_row([("부동산 평가액", won(pm["value"]), "", "neutral"), ("담보대출 잔액", won(pm["loans"]), "", "neutral"),
                 ("임대보증금 반환 의무", won(pm["deposits_owed"]), f"12개월 내 만기 {won(pm['near_deposit'])}", "warn" if pm["near_deposit"] else "neutral"),
                 ("월 임대수입", won(pm["rent_income"]), "세금·수선비·공실 차감 전", "info")])

    with tabs[3]:
        pm = prop_metrics(S)
        st.caption(f"부동산 표에서 가져온 담보대출 잔액: **{won(pm['loans'])}** · 임대보증금 반환 의무: **{won(pm['deposits_owed'])}** (자동으로 부채에 포함)")
        l, r = st.columns(2)
        num("신용대출·마이너스통장 (만원)", "credit", S, container=l)
        num("기타 부채(학자금·카드할부 등) (만원)", "other_debt", S, container=r)
        st.markdown("**월 대출 상환액**")
        mode = st.radio("입력 방식", ["직접 입력", "대출조건으로 자동 계산"], index=0 if S["debt_mode"] == "직접 입력" else 1,
                        horizontal=True, key="w_debt_mode")
        S["debt_mode"] = mode
        if mode == "직접 입력":
            num("월 대출 상환액 — 원금+이자 합계 (만원)", "debt_payment", S, step=5.0)
        else:
            q1, q2, q3 = st.columns(3)
            num("대출 금리 (연 %)", "loan_rate", S, step=0.1, container=q1, max_value=30.0)
            num("남은 만기 (년)", "loan_years", S, step=1.0, container=q2, max_value=50.0)
            sel("상환 방식", "loan_method", S, LOAN_METHODS, q3)
            pay = monthly_payment(pm["loans"], S["loan_rate"], S["loan_years"])
            callout(f"담보대출 {won(pm['loans'])}, 연 {S['loan_rate']:.2f}%, {S['loan_years']:.0f}년 <b>원리금균등</b> 기준 "
                    f"월 상환액은 약 <b>{won(pay)}</b>입니다. (신용대출 등 다른 부채 상환액은 직접 입력 방식으로 합산하세요.)", "info")
        num("대출 차주 본인의 연 소득 (만원, 선택)", "borrower_income", S, step=100.0,
            help="대출 계산기에서 본인 소득 기준 상환 부담을 참고로 볼 때만 쓰입니다. 공식 DSR이 아닙니다.")

    with tabs[4]:
        st.caption("월평균 금액을 입력하세요. 생활비에는 대출 상환액을 포함하지 마세요(자동으로 따로 더해져요).")
        l, m, r = st.columns(3)
        l.markdown("**들어오는 돈**")
        num("월 세후 소득(근로·사업) (만원)", "income", S, container=l)
        num("금융 분배금·배당금 (만원)", "dividend_income", S, container=l)
        num("기타 월 소득 (만원)", "other_income", S, container=l)
        l.caption(f"임대수입(부동산 표 자동 반영): {won(prop_metrics(S)['rent_income'])}")
        m.markdown("**나가는 돈**")
        num("월 생활비 (만원)", "living_cost", S, container=m, help="식비·공과금·교통·통신·문화·생필품 등")
        num("월 세금 적립금 (만원)", "tax_reserve", S, container=m, help="재산세·종합소득세 등 매월 적립하는 금액")
        num("월 보험료 (만원)", "insurance_premium", S, container=m)
        r.markdown("**기타**")
        num("가족 지원·용돈 (만원)", "family_support", S, container=r)
        num("비정기 지출 월 환산액 (만원)", "irregular_monthly", S, container=r,
            help="자동차 보험·경조사비·수리비 등 연간 예상액 ÷ 12")
        with st.expander("비정기 지출은 무엇인가요?"):
            st.write("매달 나가지 않지만 1년 단위로 반복되는 지출입니다(자동차 보험, 명절·경조사비, 건강검진, 가전 교체 등). 연간 예상액을 12로 나눠 입력하면 월 잉여자금이 과대평가되는 것을 줄일 수 있어요.")

    with tabs[5]:
        st.markdown("**기간 한정 지출** — 몇 년 동안만 매년 반복되는 지출 (예: 등록금 4년, 수리비 2년)")
        cfg = {
            "항목": st.column_config.TextColumn("항목"),
            "연 금액": st.column_config.NumberColumn("연 금액(만원)", min_value=0, step=50, format="%g"),
            "시작 연차": st.column_config.NumberColumn("시작 연차", min_value=1, step=1, format="%g", help="1 = 지금부터"),
            "기간(년)": st.column_config.NumberColumn("지속 기간(년)", min_value=0, step=1, format="%g"),
        }
        table_editor("term_exp", S, TERM_COLS, TERM_NUM, cfg)
        st.markdown("**일회성 큰 지출** — 한 번에 나가는 지출 (결혼·이사·자동차 구입 등)")
        cfg2 = {
            "항목": st.column_config.TextColumn("항목"),
            "금액": st.column_config.NumberColumn("금액(만원)", min_value=0, step=100, format="%g"),
            "몇 개월 후": st.column_config.NumberColumn("몇 개월 후", min_value=1, step=1, format="%g"),
        }
        table_editor("oneoffs", S, ONE_COLS, ONE_NUM, cfg2)
        note("임대보증금 반환은 이 표가 아니라 '부동산·임대' 탭의 보증금과 만기로 입력하세요.")

    with tabs[6]:
        st.caption("주 소득자에게 질병·사고가 생겼을 때 가계가 얼마나 버틸 수 있는지 단순 계산하기 위한 입력입니다.")
        l, r = st.columns(2)
        num("주 소득자의 월 소득 (만원)", "earner_income", S, container=l)
        num("보장이 필요한 기간 (년)", "cover_years", S, step=1.0, container=l, max_value=50.0)
        num("대체하고 싶은 소득 비율 (%)", "cover_replace", S, step=5.0, container=l, max_value=100.0)
        num("기존 사망·고도장해 보장금액 합계 (만원)", "coverage_death", S, container=r)
        num("차감 인정할 일반 투자자산 비율 (%)", "cover_asset_pct", S, step=10.0, container=r, max_value=100.0,
            help="레버리지·가상자산은 제외하고 일반 주식·ETF만 대상으로 합니다.")
        chk("대출 잔액도 보장 필요액에 포함", "cover_count_loans", S, l)
        chk("실손의료보험을 유지하고 있어요", "has_silson", S, r)

    # ---- 맨 위 요약 (위젯 값이 모두 반영된 뒤 채움) ----
    c = calculate(S)
    with summary:
        kpi_row([("총자산", won(c["assets"]), "", "neutral"), ("총부채", won(c["debts"]), f"임대보증금 {won(c['deposits_owed'])} 포함", "neutral"),
                 ("순자산(자동)", won(c["net"]), "총자산 − 총부채", "ok" if c["net"] >= 0 else "bad"),
                 ("월 잉여자금(자동)", won(c["surplus"]), f"소득 {won(c['income'])} − 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad")])
        errs, warns = validate(S, c)
        for e in errs:
            st.error(e)
        for w in warns:
            st.warning(w)
        if not errs and has_data(c):
            st.caption("✅ 입력은 자동 저장돼요. 왼쪽 메뉴에서 분석 화면으로 이동하세요. (브라우저를 새로고침하면 사라지니 '리포트·데이터'에서 파일로 저장해 두세요.)")


def validate(S, c):
    errs, warns = [], []
    if S["leverage"] > S["stocks"]:
        errs.append("레버리지 ETF 금액이 주식·ETF 전체보다 큽니다. 일부로 입력해 주세요.")
    if c["income"] == 0 and c["outflow"] > 0:
        warns.append("월 소득이 0인데 지출이 있어요. 소득 공백인지, 입력 누락인지 확인해 주세요.")
    if c["income"] > 0 and c["outflow"] > c["income"] * 3:
        warns.append("월 지출이 소득의 3배를 넘어요. 단위(만원)와 입력값을 확인해 주세요.")
    if c["debts"] > c["assets"] > 0:
        warns.append("총부채가 총자산보다 커요. 실제 상황일 수 있으니 입력값을 확인하고 계속 진행하세요.")
    if S["already_saved"] > S["target"] > 0:
        warns.append("이미 모은 금액이 목표 금액보다 커요.")
    for k in ["cash", "deposits", "stocks", "crypto", "income", "living_cost"]:
        if S[k] > 10_000_000:
            warns.append(f"{k} 금액이 매우 큽니다. 입력 단위가 만원인지 확인해 주세요.")
    df = c["props"]
    if not df.empty and ((df["임대형태"] != "없음") & (df["용도"] == "실거주")).any():
        warns.append("용도가 '실거주'인데 임대형태가 전세·월세로 입력된 부동산이 있어요.")
    if not df.empty and ((df["임대형태"] == "월세") & (df["월세"] == 0)).any():
        warns.append("임대형태가 월세인데 월세가 0인 부동산이 있어요.")
    if not df.empty and (df["담보대출"] > df["평가액"]).any():
        warns.append("평가액보다 담보대출이 큰 부동산이 있어요.")
    return errs, warns


# ============================================================
# 9. 페이지: 재무현황
# ============================================================
def page_snapshot(S, c):
    hero("MY SNAPSHOT", "내 재무현황", "핵심 숫자 → 건강 점수 → 재무상태표·현금흐름표 → 진단 순서로 확인해요.")
    if not need_data(c):
        return
    kpi_row([("총자산", won(c["assets"]), "", "neutral"), ("총부채", won(c["debts"]), "", "neutral"),
             ("내 순자산", won(c["net"]), "총자산 − 총부채", "ok" if c["net"] >= 0 else "bad"),
             ("월 잉여자금", won(c["surplus"]), "월 소득 − 월 정기지출", "ok" if c["surplus"] > 0 else "bad")])
    callout(f"순자산 = {won(c['assets'])} − {won(c['debts'])} = <b>{won(c['net'])}</b><br>"
            "<span class='tiny'>입력한 평가액 기준이며 매각가격·세금·수수료는 반영하지 않았습니다. 임대보증금은 반환해야 하므로 부채에 포함했습니다.</span>", "info")
    if c["child"] == 0 and c["child_raw"] > 0:
        st.caption(f"자녀 명의 자산 {won(c['child_raw'])}은 부모 가계 계산에서 제외했어요. (정보 입력 → ② 금융자산에서 변경)")

    st.write("")
    section("재무 건강 점검 점수", "5개 영역을 0~100점으로 환산한 참고용 점수예요. 산식은 아래에서 확인할 수 있어요.")
    sc = health_scores(S, c)
    score_block(sc)
    with st.expander("점수는 어떻게 계산했나요?"):
        st.markdown(
            "- **현금흐름**: 월 잉여자금 ÷ 월 소득 (−20% → 0점, 0% → 35점, 10% → 65점, 20% → 90점, 30% 이상 → 100점)\n"
            "- **유동성**: 현금·예금 ÷ 월 정기지출 (1개월 25점, 3개월 60점, 6개월 90점, 9개월 이상 100점). 12개월 내 만기 보증금이 있으면 '보증금 반환 준비율'과 비교해 더 낮은 점수를 사용\n"
            "- **부채 부담**: 총부채 ÷ 총자산 (30% 90점, 50% 65점, 70% 35점) − 월 상환액/월 소득이 30%를 넘으면 감점\n"
            "- **투자 집중도**: (레버리지 ETF + 가상자산·테마주) ÷ 금융자산 (10% 95점, 30% 70점, 50% 40점)\n"
            "- **소득 보장**: (기존 보장 + 차감 인정 자산) ÷ 필요 보장액 (50% 50점, 100% 100점)\n"
            "- 입력이 없는 영역은 평균에서 제외합니다. 기준 구간은 일반적인 참고 범위이며 개인 상황에 따라 다를 수 있어요.")

    st.divider()
    section("재무상태표", "가진 것(자산)과 갚아야 할 것(부채)을 정리한 표예요.")
    left, right = st.columns(2)
    asset_rows = [("현금·입출금", c["cash"]), ("예금·적금", c["deposits"]), ("주식·ETF", c["stocks"]), ("가상자산·테마주", c["crypto"]),
                  ("연금계좌", c["pension"]), ("부동산", c["prop_value"]), ("기타 자산·내가 낸 보증금", c["other_assets"])]
    if c["child"] > 0:
        asset_rows.append(("자녀 명의 자산(포함)", c["child"]))
    debt_rows = [("주택담보대출", c["loans"]), ("신용대출·마이너스통장", A(S, "credit")), ("기타 부채", A(S, "other_debt")),
                 ("임대보증금 반환 의무", c["deposits_owed"])]
    with left:
        st.markdown("**자산**")
        show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in asset_rows] + [{"항목": "총자산", "금액": won(c["assets"])}]))
    with right:
        st.markdown("**부채와 순자산**")
        show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in debt_rows] +
                             [{"항목": "총부채", "금액": won(c["debts"])}, {"항목": "순자산(자동 계산)", "금액": won(c["net"])}]))
    with st.expander("자산·부채 구성 그래프 보기"):
        x, y = st.columns(2)
        with x:
            donut(pd.DataFrame([{"자산": k, "금액": v} for k, v in asset_rows if v > 0]), "자산", "금액", "자산 구성")
        with y:
            donut(pd.DataFrame([{"부채": k, "금액": v} for k, v in debt_rows if v > 0]), "부채", "금액", "부채 구성")
    note("재무상태표는 사용자가 입력한 평가액 기준의 참고용 요약이며 공인 회계보고서나 금융기관 제출 자료가 아닙니다.")

    st.divider()
    section("현금흐름표", "매달 들어오고 나가는 돈을 비교해요.")
    f1, f2 = st.columns([1.2, 1])
    with f1:
        flow = [("수입", "근로·사업 소득", A(S, "income")), ("수입", "임대수입(자동)", c["rent_income"]),
                ("수입", "분배금·배당금", A(S, "dividend_income")), ("수입", "기타 소득", A(S, "other_income")),
                ("지출", "생활비", A(S, "living_cost")), ("지출", "세금 적립", A(S, "tax_reserve")),
                ("지출", "보험료", A(S, "insurance_premium")), ("지출", "가족 지원", A(S, "family_support")),
                ("지출", "대출 상환", c["debt_payment"]), ("지출", "비정기 지출", c["irregular"])]
        rows = [{"구분": a, "항목": b, "월 금액": won(v)} for a, b, v in flow if v != 0]
        rows += [{"구분": "합계", "항목": "월 총소득", "월 금액": won(c["income"])}, {"구분": "합계", "항목": "월 정기지출", "월 금액": won(c["outflow"])},
                 {"구분": "결과", "항목": "월 잉여자금(자동)", "월 금액": won(c["surplus"])}]
        show_df(pd.DataFrame(rows))
    with f2:
        exp_df = pd.DataFrame([{"항목": b, "월 금액": v} for a, b, v in flow if a == "지출" and v > 0])
        if not exp_df.empty:
            donut(exp_df, "항목", "월 금액", "월 지출 구성")
    if c["surplus"] < 0:
        callout(f"입력값 기준으로 매달 <b>{won(abs(c['surplus']))}</b>이 부족해요. 아래 ‘기간별 현금흐름’에서 앞으로의 변화도 확인해 보세요.", "bad")
    elif c["surplus"] == 0:
        callout("계산상 남는 돈이 없어요. 비정기 지출과 실제 저축액을 확인해 보세요.", "warn")
    else:
        callout(f"입력값 기준으로 매달 <b>{won(c['surplus'])}</b>이 남아요. 실제 통장에 남는 금액과 비교해 보세요.", "ok")

    st.divider()
    section("핵심 지표 해설", "숫자가 무슨 뜻인지 계산식과 참고 기준을 함께 보여줘요.")
    ind = [
        ("월 잉여자금률", pct(c["savings_rate"]), "월 잉여자금 ÷ 월 소득", "10~20% 이상이면 비교적 여유(참고)"),
        ("현금·예금 여력", fmt_months(c["runway"]), "현금·예금 ÷ 월 정기지출", "3~6개월은 참고 범위(소득 안정성에 따라 달라짐)"),
        ("보증금 반환 준비율", pct(c["readiness"], 0) if c["readiness"] is not None else "해당 없음", "현금·예금 ÷ 12개월 내 만기 보증금", "100% 미만이면 반환 재원 계획 필요"),
        ("총부채/총자산", pct(c["debt_ratio"]), "총부채 ÷ 총자산", "비율만으로 위험을 단정할 수 없음"),
        ("월 상환액/월 소득", pct(c["repayment_ratio"]), "월 대출 상환액 ÷ 월 총소득", "참고 비율(공식 DSR 아님)"),
        ("고위험 자산 비중", pct(c["high_risk_ratio"]), "(레버리지+가상자산·테마주) ÷ 금융자산", "급락 시 유동성 영향 확인"),
        ("금융자산 중 현금성 비중", pct(c["liquid_ratio"]), "현금·예금 ÷ 금융자산", "낮을수록 즉시 쓸 수 있는 돈이 적음"),
    ]
    show_df(pd.DataFrame(ind, columns=["지표", "내 값", "계산식", "참고 기준"]))

    st.divider()
    section("쉬운 재무진단", "각 진단은 계산 근거와 다음 행동을 함께 보여줘요.")
    diag = make_diagnosis(S, c)
    st.markdown(f"**확인할 항목 {len(diag)}개**")
    render_diagnosis(diag)

    with st.expander("📝 상담 전 확인 질문 (내 상황에 맞춰 자동 생성)"):
        for i, q in enumerate(make_questions(S, c), 1):
            st.markdown(f"{i}. {q}")


# ============================================================
# 10. 페이지: 기간별 현금흐름
# ============================================================
def page_timeline(S, c):
    hero("CASH FLOW OVER TIME", "기간별 현금흐름", "몇 년 동안만 나가는 지출(등록금·수리비 등)을 반영하면 해마다 현금흐름이 어떻게 달라지는지 봐요.")
    if not need_data(c):
        return
    a, b = st.columns([2, 1])
    years = a.slider("살펴볼 기간 (년)", 3, 15, 10)
    inc = b.checkbox("일회성 큰 지출 포함", value=True)
    df = build_timeline(S, c, years, inc)

    first_neg = df[df["월 현금흐름"] < 0]
    broke = df[df["현금·예금 잔액(추정)"] < 0]
    kpi_row([
        ("기본 월 잉여자금", won(c["surplus"]), "기간 한정 지출 반영 전", "ok" if c["surplus"] > 0 else "bad"),
        ("가장 낮은 월 현금흐름", won(df["월 현금흐름"].min()), f"{int(df.loc[df['월 현금흐름'].idxmin(), '연차'])}년차", "bad" if df["월 현금흐름"].min() < 0 else "ok"),
        ("월 적자 구간", f"{len(first_neg)}년" if len(first_neg) else "없음", "기간 한정 지출 반영", "warn" if len(first_neg) else "ok"),
        ("현금·예금 소진", f"{int(broke.iloc[0]['연차'])}년차" if len(broke) else "기간 내 없음", "임대보증금 반환 제외", "bad" if len(broke) else "ok"),
    ])
    st.write("")
    section("구간별 월 현금흐름")
    seg, start = [], 0
    vals = df["월 현금흐름"].round(1).tolist()
    for i in range(1, len(vals) + 1):
        if i == len(vals) or vals[i] != vals[start]:
            y0, y1 = int(df.iloc[start]["연차"]), int(df.iloc[i - 1]["연차"])
            seg.append({"구간": f"{y0}년차" if y0 == y1 else f"{y0}~{y1}년차", "기간한정 지출(월 환산)": won(df.iloc[start]["기간한정 지출(월)"]),
                        "월 현금흐름": won(vals[start]), "연 현금흐름": won(vals[start] * 12)})
            start = i
    show_df(pd.DataFrame(seg))
    if len(first_neg):
        callout("기간 한정 지출이 끝나는 시점에 현금흐름이 회복되는지 확인하세요. 적자 구간에서는 <b>현금·예금이 줄어드는 속도</b>도 함께 봐야 해요.", "warn")

    x, y = st.columns(2)
    chart = df.assign(연차=df["연차"].astype(int).astype(str) + "년차").set_index("연차")
    with x:
        st.markdown("**연간 현금흐름 (만원)**")
        st.bar_chart(chart[["연 현금흐름"]])
    with y:
        st.markdown("**현금·예금 잔액 추정 (만원)**")
        st.line_chart(chart[["현금·예금 잔액(추정)"]])
    with st.expander("상세 표 보기"):
        v = df.copy()
        v["연차"] = v["연차"].astype(int).astype(str) + "년차"
        for col in v.columns[1:]:
            v[col] = v[col].apply(won)
        show_df(v)
    note("월 잉여자금과 기간 한정 지출만 반영한 단순 추정입니다. 투자수익·세금·물가·임대보증금 반환·소득 변화는 반영하지 않았어요. 보증금은 ‘유동성·보증금 반환’ 메뉴에서 따로 확인하세요.")


# ============================================================
# 11. 페이지: 유동성·보증금 반환
# ============================================================
def page_liquidity(S, c):
    hero("LIQUIDITY PLANNER", "유동성·보증금 반환 플래너", "만기에 돌려줘야 할 보증금을 무엇으로 마련할지 시나리오별로 부족액을 계산해요.")
    if not need_data(c):
        return
    rented = c["rented"]
    if c["deposits_owed"] <= 0:
        callout("입력된 임대보증금 반환 의무가 없어요. ‘정보 입력 → ③ 부동산·임대’에서 임대형태와 보증금을 입력하면 이 분석을 쓸 수 있어요. "
                "임대가 없어도 아래의 ‘비상자금’ 관점으로 현금·예금 여력은 확인할 수 있어요.", "info")
    section("1. 만기별 반환 의무")
    if not rented.empty and c["deposits_owed"] > 0:
        t = rented[rented["보증금"] > 0].sort_values("보증금 만기(개월 후)")
        show_df(pd.DataFrame({"부동산": t["이름"], "임대형태": t["임대형태"], "반환할 보증금": t["보증금"].apply(won),
                              "만기(개월 후)": t["보증금 만기(개월 후)"].astype(int)}))
    horizon = st.slider("몇 개월 안에 만기가 도래하는 보증금을 대상으로 볼까요?", 3, 60, 12, step=1)
    due = rented[(rented["보증금"] > 0) & (rented["보증금 만기(개월 후)"] <= horizon)]["보증금"].sum() if not rented.empty else 0.0

    st.divider()
    section("2. 반환 재원 가정", "슬라이더를 움직이며 부족액이 어떻게 변하는지 확인해 보세요.")
    l, r = st.columns(2)
    with l:
        em_months = st.slider("따로 남겨둘 비상자금 (월 정기지출의 몇 개월분)", 0, 12, 3)
        include_term = st.checkbox("향후 12개월 기간 한정·일회성 지출도 따로 남기기", value=True)
        tenant = st.slider("신규 임차인 확보로 보증금을 대체할 비율 (%)", 0, 100, 0, step=10,
                           help="새 세입자의 보증금으로 돌려줄 수 있다고 가정하는 비율. 확정되지 않았다면 0%로 보수적으로 두세요.")
    with r:
        plain = max(0.0, c["stocks"] - c["leverage"])
        sell_lev = st.slider("레버리지 ETF 매도액 (만원)", 0, int(c["leverage"]), 0, step=500) if c["leverage"] >= 500 else 0.0
        sell_plain = st.slider("일반 주식·ETF 매도액 (만원)", 0, int(plain), 0, step=500) if plain >= 500 else 0.0
        sell_crypto = st.slider("가상자산·테마주 매도액 (만원)", 0, int(c["crypto"]), 0, step=500) if c["crypto"] >= 500 else 0.0
        cost = st.slider("매도 시 세금·수수료·슬리피지 가정 (%)", 0.0, 10.0, 1.0, step=0.1,
                         help="실제 세금과 비용은 상품·계좌·보유기간에 따라 달라요. 가정값으로 확인하세요.")
        new_loan = st.number_input("추가로 조달 가능한 대출·차입 (만원)", min_value=0.0, value=0.0, step=1000.0, format="%g",
                                   help="금융기관 확인 전에는 0으로 두는 것이 안전해요.")

    sells = (sell_lev + sell_plain + sell_crypto)
    net_sell = sells * (1 - cost / 100)
    term_12 = 0.0
    if include_term:
        tl = build_timeline(S, {**c, "surplus": 0.0, "liquid": 0.0}, 1, True)
        term_12 = max(0.0, float(tl["기간한정 지출(월)"].iloc[0]) * 12 + float(tl["일회성 지출"].iloc[0]))
    reserve = em_months * c["outflow"] + term_12
    required = due * (1 - tenant / 100)
    available = c["liquid"] + net_sell + new_loan
    usable = available - reserve
    gap = max(0.0, required - usable)
    readiness = ratio(usable, required) if required > 0 else None

    st.divider()
    section("3. 결과")
    kpi_row([
        ("반환 필요 보증금", won(required), f"{horizon}개월 내 만기 {won(due)}" + (f" − 신규 임차 {tenant}%" if tenant else ""), "warn" if required else "neutral"),
        ("쓸 수 있는 재원", won(max(usable, 0)), f"현금·예금 + 매도(세후) + 차입 − 비상자금 {won(reserve)}", "info"),
        ("부족액", won(gap), "0이면 가정상 반환 가능" if gap == 0 else "추가 재원 필요", "ok" if gap == 0 else "bad"),
        ("반환 준비율", "해당 없음" if readiness is None else pct(min(readiness, 999), 0), "쓸 수 있는 재원 ÷ 필요 보증금", "ok" if (readiness or 0) >= 100 else "bad"),
    ])
    src = pd.DataFrame({"항목": ["현금·예금", "매도대금(세후)", "추가 차입", "따로 남길 돈(−)", "필요 보증금"],
                        "금액": [c["liquid"], net_sell, new_loan, -reserve, required]}).set_index("항목")
    st.bar_chart(src)
    if required == 0:
        callout("대상 기간에 반환할 보증금이 없어요. 비상자금과 예정 지출만 기준으로 남는 돈을 확인하세요.", "info")
    elif gap == 0:
        callout(f"이 가정에서는 비상자금과 예정 지출을 남기고도 보증금을 돌려줄 수 있어요(여유 {won(usable - required)}). "
                "다만 시장 하락·거래 지연 가능성을 고려해 여유를 두세요.", "ok")
    else:
        sellable = c["leverage"] + plain + c["crypto"]
        need_sell = gap / (1 - cost / 100) if cost < 100 else gap
        extra = (f"추가로 약 <b>{won(need_sell)}</b>어치를 더 팔면 닫을 수 있지만, 매도 가능한 투자자산 전체({won(sellable)})를 넘으면 불가능해요."
                 if need_sell <= (sellable - sells) else
                 f"남은 매도 가능 투자자산({won(max(0, sellable - sells))})을 모두 팔아도 부족해요. 담보 대출·부동산 처분·계약 조건 협의 등 다른 방법을 전문가와 검토해야 해요.")
        callout(f"부족액 <b>{won(gap)}</b>이 남아요. {extra}", "bad")

    after_risk = max(0.0, c["high_risk"] - sell_lev - sell_crypto)
    fin_after = max(1.0, c["financial"] - sells)
    st.caption(f"매도 후 금융자산 중 고위험 자산 비중: {pct(ratio(after_risk, fin_after))} (현재 {pct(c['high_risk_ratio'])})")

    st.divider()
    section("4. 시나리오 한눈에 비교")
    scen = []
    for name, sl, sp, sc_ in [("현금만 사용", 0, 0, 0), ("레버리지 50% 매도", c["leverage"] * .5, 0, 0),
                              ("레버리지 전부 매도", c["leverage"], 0, 0), ("고위험 자산 전부 매도", c["leverage"], 0, c["crypto"])]:
        net = (sl + sp + sc_) * (1 - cost / 100)
        us = c["liquid"] + net + new_loan - reserve
        g = max(0.0, required - us)
        scen.append({"시나리오": name, "매도대금(세후)": won(net), "쓸 수 있는 재원": won(max(us, 0)),
                     "부족액": won(g), "준비율": "-" if required == 0 else pct(min(ratio(us, required) or 0, 999), 0)})
    show_df(pd.DataFrame(scen))
    note("세금·수수료는 입력한 가정 비율로만 반영했고 시장 가격 변동은 반영하지 않았습니다. 매도·대출 실행 전에는 실제 비용과 조건을 확인하세요.")


# ============================================================
# 12. 페이지: 대출 계산기
# ============================================================
def page_loan(S, c):
    hero("LOAN LAB", "대출 계산기", "상환 방식별 월 납입액·총이자·잔액 변화와 금리 상승 영향을 확인해요.")
    l, m, r = st.columns(3)
    default_p = float(round(c["loans"])) if c["loans"] > 0 else 0.0
    p = l.number_input("대출 원금(잔액) (만원)", min_value=0.0, value=default_p, step=100.0, format="%g",
                       key=f"loan_p_{int(default_p)}", help="기본값은 부동산 표의 담보대출 합계예요.")
    rate = m.number_input("연 금리 (%)", min_value=0.0, max_value=30.0, value=float(S["loan_rate"]), step=0.1, format="%g", key="loan_rate_in")
    yrs = r.number_input("상환 기간 (년)", min_value=1.0, max_value=50.0, value=float(S["loan_years"]), step=1.0, format="%g", key="loan_years_in")
    mth = st.radio("상환 방식", LOAN_METHODS, horizontal=True,
                   index=LOAN_METHODS.index(S["loan_method"]) if S["loan_method"] in LOAN_METHODS else 0, key="loan_method_in")
    extra = st.slider("매월 추가 상환 (만원)", 0, 500, 0, step=10, disabled=(mth == "만기일시"),
                      help="매달 원금을 더 갚았을 때 이자와 기간이 얼마나 줄어드는지 비교해요.")
    if p <= 0:
        callout("대출 원금을 입력하면 계산 결과가 나와요. 부동산 표에 담보대출을 입력했다면 자동으로 채워져요.", "info")
        return
    base_df, base = amort_schedule(p, rate, yrs, mth, 0.0)
    ext_df, ext = amort_schedule(p, rate, yrs, mth, float(extra))
    kpi_row([("월 상환액(첫 달)", won(base["first"]), mth, "info"), ("총 이자", won(base["interest"]), f"원금의 {base['interest'] / p * 100:.0f}%", "warn"),
             ("총 상환액", won(base["total"]), "원금 + 이자", "neutral"),
             ("월 소득 대비", pct(ratio(base["first"], c["income"])), "가계 소득 기준 참고", "neutral")])
    if extra > 0 and mth != "만기일시":
        saved = base["interest"] - ext["interest"]
        callout(f"매월 {won(extra)}을 더 갚으면 총이자 <b>{won(saved)}</b>을 줄이고, 기간이 <b>{base['months']}개월 → {ext['months']}개월</b>로 단축돼요. "
                "<span class='tiny'>중도상환수수료와 그 돈의 다른 사용처(비상자금 등)도 함께 고려하세요.</span>", "ok", "추가 상환 효과")
    st.markdown("**연도별 잔액**")
    bal = (ext_df if extra > 0 else base_df).copy()
    st.line_chart(bal.assign(연차=bal["연차"].astype(int)).set_index("연차")[["연말 잔액"]])
    with st.expander("연도별 상환 표"):
        v = bal.copy()
        v["연차"] = v["연차"].astype(int).astype(str) + "년차"
        for col in ["상환 원금", "납부 이자", "연말 잔액"]:
            v[col] = v[col].apply(won)
        show_df(v)

    st.divider()
    section("금리가 오르면?", "변동금리라면 같은 조건에서 월 부담이 어떻게 바뀌는지 봐요.")
    rows = []
    for d in [-1, 0, 1, 2, 3]:
        rr = max(0.0, rate + d)
        pay = monthly_payment(p, rr, yrs) if mth == "원리금균등" else (p / (yrs * 12) + p * rr / 1200 if mth == "원금균등" else p * rr / 1200)
        rows.append({"금리": f"{rr:.2f}% ({d:+d}%p)" if d else f"{rr:.2f}% (현재)", "월 상환액(첫 달)": won(pay),
                     "현재 대비": won(pay - base["first"]), "월 소득 대비": pct(ratio(pay, c["income"]))})
    show_df(pd.DataFrame(rows))

    st.divider()
    section("상환 부담 참고 비율", "금융기관의 공식 DSR이 아니라 입력값으로 단순 계산한 참고값이에요.")
    annual = base["first"] * 12
    bi = A(S, "borrower_income")
    k1, k2 = st.columns(2)
    k1.markdown(kpi("가계 월 소득 대비", pct(ratio(base["first"], c["income"])), "이 대출 월 상환액 ÷ 가계 월 총소득", "neutral"), unsafe_allow_html=True)
    k2.markdown(kpi("차주 연소득 대비", pct(ratio(annual, bi)) if bi > 0 else "연소득 입력 필요",
                    "연 상환액 ÷ 차주 연소득", "neutral"), unsafe_allow_html=True)
    note("실제 DSR은 차주별 인정소득과 모든 금융부채의 연간 원리금 상환액을 기준으로 산정됩니다. 임대보증금은 금융기관 대출이 아니므로 별도로 관리하세요.")


# ============================================================
# 13. 페이지: 투자위험(레버리지)
# ============================================================
def page_risk(S, c):
    hero("INVESTMENT RISK", "투자위험 이해하기", "레버리지 ETF의 ‘경로 의존성’과 시장 급락이 내 유동성에 미치는 영향을 확인해요.")
    t1, t2, t3 = st.tabs(["① 내 자산 충격 테스트", "② 경로 예시(100→110→100)", "③ 시뮬레이션"])
    with t1:
        if not need_data(c):
            pass
        else:
            l, r = st.columns(2)
            drop = l.slider("기초지수(일반 주식시장) 하락률 (%)", 0, 60, 30, step=5)
            cdrop = r.slider("가상자산·테마주 하락률 (%)", 0, 90, 50, step=5)
            mult = st.selectbox("레버리지 배수", [2, 3], index=1)
            d = drop / 100
            plain = max(0.0, c["stocks"] - c["leverage"])
            lev_loss = min(c["leverage"], c["leverage"] * mult * d)
            loss = plain * d + lev_loss + c["crypto"] * cdrop / 100
            rows = [("일반 주식·ETF", plain, plain * d), (f"레버리지 ETF({mult}배)", c["leverage"], lev_loss),
                    ("가상자산·테마주", c["crypto"], c["crypto"] * cdrop / 100)]
            show_df(pd.DataFrame([{"자산": n, "현재": won(v), "가정 손실": won(-ls), "충격 후": won(v - ls)} for n, v, ls in rows]))
            fin_after = c["financial"] - loss
            kpi_row([("총 가정 손실", won(-loss), f"금융자산의 {pct(ratio(loss, c['financial']))}", "bad" if loss else "neutral"),
                     ("충격 후 순자산", won(c["net"] - loss), f"현재 {won(c['net'])}", "warn"),
                     ("충격 후 금융자산", won(fin_after), "", "neutral"),
                     ("보증금 준비율(충격 후)", "해당 없음" if c["near_deposit"] <= 0 else pct(ratio(c["liquid"], c["near_deposit"]), 0),
                      "현금·예금은 그대로 가정", "neutral")])
            if mult * drop >= 100:
                callout(f"기초지수가 {drop}% 하락하면 {mult}배 상품은 이론상 <b>전액 손실</b> 수준이에요(하루에 {100 // mult}% 이상 하락하는 경우 등).", "bad")
            note("기초지수 하락이 짧은 기간에 한 번에 발생한다는 단순 가정입니다. 실제 ETF는 일별 수익률 경로, 추적오차, 보수 등에 따라 달라집니다.")
    with t2:
        st.markdown("기초지수가 **+10% → −9.09%**로 변해 제자리로 돌아와도, 일일 수익률 배수 상품은 손실이 날 수 있어요.")
        l, r = st.columns([1, 2])
        mult2 = l.selectbox("배수", [2, 3], index=1, key="path_mult")
        raw = r.text_input("기간별 기초지수 수익률(%) — 쉼표로 구분", "10, -9.09")
        try:
            rets = [float(x) for x in raw.replace("，", ",").split(",") if x.strip()]
            rets = rets[:60]
        except ValueError:
            rets = []
            st.error("숫자와 쉼표만 입력해 주세요. 예: 10, -9.09")
        if rets:
            pdf = path_example(rets, mult2)
            show_df(pdf.assign(**{"기초지수": pdf["기초지수"].round(2), "레버리지 ETF": pdf["레버리지 ETF"].round(2)}))
            st.line_chart(pdf.set_index("단계")[["기초지수", "레버리지 ETF"]])
            u, e = pdf["기초지수"].iloc[-1], pdf["레버리지 ETF"].iloc[-1]
            callout(f"기초지수 누적 {u - 100:+.2f}% / 레버리지 ETF 누적 <b>{e - 100:+.2f}%</b>. 단순히 ‘기초지수 수익률 × 배수’가 아니에요.", "info")
        note("보수·추적오차·환율은 반영하지 않은 수학적 예시이며 실제 성과를 예측하지 않습니다.")
    with t3:
        st.caption("기초지수가 무작위로 움직인다고 가정한 시뮬레이션(일간 252회/년)이에요. 미래 예측이 아니라 ‘이런 분포가 나올 수 있다’는 감각을 얻기 위한 도구예요.")
        a, b, d = st.columns(3)
        mult3 = a.selectbox("배수", [1, 2, 3], index=2, key="sim_mult")
        mu = b.slider("기초지수 기대 연수익률 (%)", -5.0, 15.0, 7.0, step=0.5) / 100
        sg = d.slider("기초지수 연 변동성 (%)", 10.0, 50.0, 20.0, step=1.0) / 100
        e, f, g = st.columns(3)
        yrs = e.slider("투자 기간 (년)", 1, 10, 5)
        fee = f.slider("연 보수·비용 (%)", 0.0, 3.0, 1.0, step=0.1) / 100
        nsim = g.selectbox("시뮬레이션 횟수", [500, 1000, 2000], index=1)
        res = simulate_lev(mu, sg, mult3, fee, yrs, nsim)
        kpi_row([("ETF 중앙값", f"{res['etf_med']:.0f}", f"시작=100 · 기초지수 {res['und_med']:.0f}", "info"),
                 ("원금 손실 확률", pct(res["p_loss"], 0), "기간 종료 시점", "warn"),
                 ("고점 대비 −50% 경험", pct(res["p_half"], 0), "기간 중 한 번이라도", "bad" if res["p_half"] > 30 else "warn"),
                 ("지수는 올랐는데 ETF는 손실", pct(res["p_gap"], 1), "경로 의존성", "warn")])
        st.line_chart(res["chart"])
        st.caption(f"하위 10% 시나리오 종료값 {res['etf_p10']:.0f} · 상위 10% {res['etf_p90']:.0f} · 최대낙폭 중앙값 {res['mdd_med']:.0f}%")
        note("로그정규 분포·일정한 변동성을 가정한 모의실험이며 실제 시장의 급락·변동성 군집·거래비용 차이를 반영하지 않습니다. 투자 권유가 아닙니다.")


# ============================================================
# 14. 페이지: 보장 점검
# ============================================================
def page_protection(S, c):
    hero("PROTECTION CHECK", "소득자 보장 점검", "주 소득자에게 소득 중단이 생겼을 때 부족해질 수 있는 금액을 단순 계산해요.")
    pn = protection_need(S, c)
    if A(S, "earner_income") <= 0:
        callout("‘정보 입력 → ⑦ 소득자 보장’에서 주 소득자의 월 소득을 입력하면 계산할 수 있어요.", "info")
        st.button("✍️ 입력하러 가기", on_click=goto, args=("✍️ 정보 입력",), **FULL)
        return
    kpi_row([("필요 보장액(단순)", won(pn["need"]), "소득 대체 + 대출", "info"), ("차감할 재원", won(pn["offset"]), "기존 보장 제외", "neutral"),
             ("기존 보장", won(pn["existing"]), "사망·고도장해 합계", "neutral"),
             ("보장 부족액", won(pn["gap"]), "0이면 가정상 충족", "bad" if pn["gap"] > 0 else "ok")])
    st.markdown("**계산 과정**")
    show_df(pd.DataFrame([
        {"항목": "소득 대체 필요액", "계산": f"월 {won(A(S, 'earner_income'))} × 12 × {A(S, 'cover_replace'):.0f}% × {A(S, 'cover_years'):.0f}년", "금액": won(pn["income_need"])},
        {"항목": "대출 상환 필요액", "계산": "대출 잔액 합계(포함 선택 시)", "금액": won(pn["loan_need"])},
        {"항목": "필요 보장액", "계산": "위 두 항목의 합", "금액": won(pn["need"])},
        {"항목": "차감: 현금·예금 + 일반 투자자산 일부", "계산": f"현금·예금 {won(c['liquid'])} + 일반 주식·ETF의 {A(S, 'cover_asset_pct'):.0f}%", "금액": won(-pn["offset"])},
        {"항목": "차감: 기존 보장", "계산": "입력값", "금액": won(-pn["existing"])},
        {"항목": "보장 부족액", "계산": "필요액 − 차감 재원 − 기존 보장", "금액": won(pn["gap"])},
    ]))
    if pn["gap"] > 0:
        callout("부족액이 곧바로 ‘가입해야 할 보험금’은 아니에요. 부동산 처분·임대수입·배우자 소득 등 다른 재원과 보험 가입 가능 여부·보험료를 함께 비교해야 해요. "
                "<b>새 계약이 승인되기 전에 기존 보장을 해지하지 마세요.</b>", "warn", "해석 시 주의")
    else:
        callout("입력한 가정에서는 필요 보장액을 기존 보장과 차감 재원으로 충당할 수 있어요.", "ok")
    if not S.get("has_silson"):
        callout("실손의료보험 유지 여부가 ‘아니오’로 입력되어 있어요. 의료비 위험에 대한 대비가 있는지 확인해 보세요.", "warn")
    a, b = st.columns(2)
    years = a.slider("보장 기간별 필요액 비교 (년)", 1, 30, int(A(S, "cover_years") or 10))
    rep = b.slider("소득 대체율별 비교 (%)", 10, 100, int(A(S, "cover_replace") or 70), step=5)
    need2 = A(S, "earner_income") * 12 * rep / 100 * years + pn["loan_need"]
    st.caption(f"→ {years}년·{rep}% 가정 시 필요액 {won(need2)}, 부족액 {won(max(0, need2 - pn['existing'] - pn['offset']))}")
    note("단순 합산 모형이며 물가·할인율·세금·배우자 소득·국민연금 등 다른 재원은 반영하지 않습니다. 보험 상품 추천이 아닙니다.")


# ============================================================
# 15. 페이지: 목표 플래너
# ============================================================
def months_to_reach(target, start, pmt, monthly_rate, cap=1200):
    bal = start
    for m in range(1, cap + 1):
        bal = bal * (1 + monthly_rate) + pmt
        if bal >= target:
            return m
    return None


def page_goal(S, c):
    hero("GOAL PLANNER", "목표 역산 플래너", "목표 금액을 정하고 필요한 월 저축액과 달성 시점을 수익률 가정별로 비교해요.")
    if A(S, "target") <= 0:
        callout("‘정보 입력 → ① 나의 상황·목표’에서 목표에 필요한 총금액을 입력하면 계산돼요.", "info")
        st.button("✍️ 입력하러 가기", on_click=goto, args=("✍️ 정보 입력",), **FULL)
        return
    years = int(S["years"])
    n = years * 12
    a, b = st.columns(2)
    adj = a.checkbox("물가상승률을 반영해 목표금액을 미래가치로 환산", value=False)
    ret = b.slider("연 수익률 가정 (%)", 0.0, 10.0, float(min(S["expected_return"], 10.0)), step=0.5)
    target = A(S, "target") * ((1 + A(S, "inflation") / 100) ** years if adj else 1)
    saved = A(S, "already_saved")
    mr = ret / 1200
    fv_saved = saved * (1 + mr) ** n
    gap = max(0.0, target - fv_saved)
    req = gap / n if mr == 0 else gap * mr / ((1 + mr) ** n - 1)
    kpi_row([("목표 금액", won(target), f"{years}년 후" + (" (물가 반영)" if adj else ""), "info"), ("이미 모은 금액", won(saved), f"수익률 반영 시 {won(fv_saved)}", "neutral"),
             ("필요 월 저축액", won(req), f"연 {ret:.1f}% 가정", "warn"), ("단순 계산(수익률 0%)", won(max(0, A(S, 'target') - saved) / n), "", "neutral")])
    st.write("")
    section("저축 가능 금액과 비교")
    extra = st.slider("현재 월 잉여자금 외에 추가로 저축할 금액 (만원)", 0, 500, int(min(A(S, "extra_monthly"), 500)), step=10)
    avail = c["surplus"] + extra
    x, y = st.columns(2)
    x.markdown(kpi("현재 월 잉여자금", won(c["surplus"]), "기간 한정 지출 반영 전", "neutral"), unsafe_allow_html=True)
    y.markdown(kpi("가정 후 월 저축 여력", won(avail), "잉여자금 + 추가 저축", "ok" if avail >= req else "warn"), unsafe_allow_html=True)
    if avail <= 0:
        callout("지금 가정으로는 매달 저축할 수 있는 금액이 0 이하예요. 목표를 늘리기 전에 현금흐름을 먼저 점검하세요.", "bad")
    elif avail >= req:
        callout("이 가정에서는 목표 기간 안에 필요한 금액을 모을 수 있어요. 비상자금과 예정 지출은 별도로 확인하세요.", "ok")
    else:
        callout(f"목표 기간 내 달성하려면 월 <b>{won(req - avail)}</b>이 더 필요해요. 목표 금액·기간 조정과 비교해 보세요.", "warn")
    st.divider()
    section("수익률 가정별 달성 시점")
    rows, curves = [], {}
    for lab, rr in [("보수 (수익률 −2%p)", max(0.0, ret - 2)), ("기준", ret), ("낙관 (+2%p)", ret + 2)]:
        m = rr / 1200
        mths = months_to_reach(target, saved, max(avail, 0), m) if avail > 0 else None
        rows.append({"가정": lab, "연 수익률": f"{rr:.1f}%", "목표 달성 예상": "달성 어려움(저축 0 이하)" if avail <= 0 else (f"약 {mths}개월 ({mths / 12:.1f}년)" if mths else "100년 내 달성 어려움"),
                     "목표 기간 종료 시 예상 금액": won(saved * (1 + m) ** n + max(avail, 0) * (((1 + m) ** n - 1) / m if m else n))})
        bal, series = saved, []
        for k in range(1, n + 1):
            bal = bal * (1 + m) + max(avail, 0)
            if k % 12 == 0:
                series.append(bal)
        curves[lab] = series
    show_df(pd.DataFrame(rows))
    cdf = pd.DataFrame(curves, index=[f"{i}년" for i in range(1, years + 1)])
    cdf["목표 금액"] = target
    st.line_chart(cdf)
    note("월 저축을 매월 말 일정하게 한다고 가정한 단순 모형이며 세금·수수료·소득 변화·물가(체크하지 않은 경우)는 반영하지 않습니다. 수익률은 보장되지 않습니다.")


# ============================================================
# 16. 페이지: 스트레스 테스트
# ============================================================
PRESETS = {
    "소득 20% 감소": dict(income_pct=-20),
    "금리 +2%p": dict(rate_delta=2.0),
    "임대 공실(월세 −50%)": dict(vacancy_pct=50),
    "큰 지출 1,000만 원": dict(one_off=1000),
    "투자자산 −30%": dict(invest_drop=30),
    "복합(소득−20%·금리+1%p·공실30%)": dict(income_pct=-20, rate_delta=1.0, vacancy_pct=30),
}


def _set_preset(vals):
    keys = {"income_pct": "sx_inc", "vacancy_pct": "sx_vac", "rate_delta": "sx_rate", "expense_delta": "sx_exp",
            "one_off": "sx_one", "invest_drop": "sx_inv"}
    base = {"income_pct": 0, "vacancy_pct": 0, "rate_delta": 0.0, "expense_delta": 0, "one_off": 0, "invest_drop": 0}
    base.update(vals)
    for k, widget in keys.items():
        st.session_state[widget] = base[k]


def page_stress(S, c):
    hero("STRESS TEST", "재무 스트레스 테스트", "실제 입력값은 바꾸지 않고, 가정한 변화가 월 현금흐름과 여력에 미치는 영향만 계산해요.")
    if not need_data(c):
        return
    section("한 번에 비교하기", "대표 상황별 결과예요. 아래에서 직접 값을 조절해 볼 수도 있어요.")
    rows = [{"상황": "현재", "월 소득": won(c["income"]), "월 지출": won(c["outflow"]), "월 잉여자금": won(c["surplus"]),
             "현금·예금 여력": fmt_months(c["runway"]), "순자산": won(c["net"])}]
    for name, v in PRESETS.items():
        s = apply_scenario(S, c, **v)
        rows.append({"상황": name, "월 소득": won(s["income"]), "월 지출": won(s["outflow"]), "월 잉여자금": won(s["surplus"]),
                     "현금·예금 여력": fmt_months(s["runway"]), "순자산": won(s["net"])})
    show_df(pd.DataFrame(rows))
    if c["income"] > 0:
        be = c["surplus"] / (c["income"] - c["rent_income"]) * 100 if (c["income"] - c["rent_income"]) > 0 else None
        if be is not None and c["surplus"] > 0:
            st.caption(f"💡 근로·사업 등 비임대 소득이 약 {be:.0f}% 줄면 월 잉여자금이 0이 돼요(다른 조건 동일).")

    st.divider()
    section("직접 시험해 보기")
    st.markdown("**빠른 선택**")
    cols = st.columns(3)
    for i, (name, v) in enumerate(PRESETS.items()):
        cols[i % 3].button(name, key=f"preset_{i}", on_click=_set_preset, args=(v,), **FULL)
    for _k, _v in {"sx_inc": 0, "sx_vac": 0, "sx_rate": 0.0, "sx_exp": 0, "sx_one": 0, "sx_inv": 0}.items():
        st.session_state.setdefault(_k, _v)
    l, r = st.columns(2)
    with l:
        inc = st.slider("근로·사업 등 소득 변화 (%)", -80, 50, step=5, key="sx_inc")
        vac = st.slider("임대 월세 감소 — 공실 (%)", 0, 100, step=10, key="sx_vac")
        rate = st.slider("대출 금리 변화 (%p)", -2.0, 5.0, step=0.5, key="sx_rate")
    with r:
        exp = st.slider("월 지출 변화 (만원)", -200, 300, step=10, key="sx_exp")
        one = st.slider("한 번에 나가는 큰 지출 (만원)", 0, 10000, step=100, key="sx_one")
        inv = st.slider("투자자산 하락률 (%)", 0, 60, step=5, key="sx_inv")
    s = apply_scenario(S, c, inc, vac, rate, exp, one, inv)
    comp = pd.DataFrame([
        {"지표": "월 소득", "현재": won(c["income"]), "가정 후": won(s["income"]), "변화": won(s["income"] - c["income"])},
        {"지표": "월 지출", "현재": won(c["outflow"]), "가정 후": won(s["outflow"]), "변화": won(s["outflow"] - c["outflow"])},
        {"지표": "월 잉여자금", "현재": won(c["surplus"]), "가정 후": won(s["surplus"]), "변화": won(s["surplus"] - c["surplus"])},
        {"지표": "현금·예금", "현재": won(c["liquid"]), "가정 후": won(s["liquid"]), "변화": won(s["liquid"] - c["liquid"])},
        {"지표": "순자산", "현재": won(c["net"]), "가정 후": won(s["net"]), "변화": won(s["net"] - c["net"])},
        {"지표": "현금·예금 여력", "현재": fmt_months(c["runway"]), "가정 후": fmt_months(s["runway"]), "변화": ""},
    ])
    show_df(comp)
    if s["surplus"] < 0:
        callout(f"이 가정에서는 매달 <b>{won(abs(s['surplus']))}</b>이 부족해요. 현금·예금으로는 약 {fmt_months(None if s['surplus'] >= 0 else (s['liquid'] / abs(s['surplus']) if s['liquid'] > 0 else 0))} 버틸 수 있어요.", "bad")
    elif s["surplus"] < c["surplus"]:
        callout(f"월 잉여자금이 {won(c['surplus'] - s['surplus'])} 줄지만 여전히 흑자예요.", "warn")
    else:
        callout("이 가정에서는 월 현금흐름이 현재보다 나빠지지 않아요.", "ok")
    if s["liquid"] < 0:
        callout("큰 지출이 현재 현금·예금보다 커요. 실제로는 자산 매각이나 차입이 필요할 수 있어요.", "warn")
    note("사용자가 정한 가정의 산술 결과이며 미래 예측이나 발생 확률이 아닙니다. 일회성 지출은 현금·예금에서 차감하고 새 부채는 가정하지 않았습니다.")


# ============================================================
# 17. 페이지: 실행·점검
# ============================================================
def page_action(S, c):
    hero("ACTION & REVIEW", "실행 로드맵과 점검", "진단 결과를 이번 달 행동으로 바꾸고, 정기적으로 점검하며 변화를 기록해요.")
    if not need_data(c):
        return
    tasks = make_tasks(S, c)
    done = sum(1 for t in tasks if S["checks"].get(t[0]))
    st.progress(done / len(tasks) if tasks else 0.0, text=f"실행 진행률 {done}/{len(tasks)}")
    phases = list(dict.fromkeys(t[1] for t in tasks))
    tabs = st.tabs(phases)
    for tab, ph in zip(tabs, phases):
        with tab:
            for tid, _, title, desc in [t for t in tasks if t[1] == ph]:
                with st.container(border=True):
                    ck = st.checkbox(f"**{title}**", value=bool(S["checks"].get(tid, False)), key=f"w_chk_{tid}")
                    S["checks"][tid] = ck
                    st.caption(desc)

    st.divider()
    section("정기·수시 점검 기준", "아래 조건 중 하나라도 해당하면 입력값을 갱신하고 계획을 다시 계산하세요.")
    show_df(pd.DataFrame([
        {"구분": "매월", "점검 항목": "현금흐름·현금성 자산", "현재 값": f"잉여 {won(c['surplus'])} / 여력 {fmt_months(c['runway'])}"},
        {"구분": "반기", "점검 항목": "자산배분·부채·보험 보장·기간 한정 지출 집행", "현재 값": f"고위험 비중 {pct(c['high_risk_ratio'])} / 부채비율 {pct(c['debt_ratio'])}"},
        {"구분": "연 1회", "점검 항목": "세금 신고자료·금융소득 합산", "현재 값": "-"},
        {"구분": "수시", "점검 항목": "임대차 만기·신규 임차인 확보 실패", "현재 값": f"12개월 내 만기 보증금 {won(c['near_deposit'])}"},
        {"구분": "수시", "점검 항목": "금리 급변·소득 감소·큰 의료비·세법 개정", "현재 값": "해당 시 입력값 갱신"},
    ]))

    st.divider()
    section("스냅샷 기록", "지금 상태를 저장해 두면 시간에 따른 변화를 볼 수 있어요. (데이터 파일로 내려받아 보관하세요)")
    s1, s2 = st.columns([1, 2])
    nxt = s1.date_input("다음 점검일", value=date.fromisoformat(S["next_review"]) if S.get("next_review") else date.today(), key="w_next_review")
    S["next_review"] = nxt.isoformat()
    if s2.button("📸 현재 상태 기록하기", **FULL):
        S["history"].append({"날짜": date.today().isoformat(), "총자산": round(c["assets"], 1), "순자산": round(c["net"], 1),
                             "월 잉여자금": round(c["surplus"], 1), "현금·예금 여력(개월)": None if c["runway"] is None else round(c["runway"], 2)})
        st.success("기록했어요.")
    if S["history"]:
        h = pd.DataFrame(S["history"])
        show_df(h)
        if len(h) >= 2:
            st.line_chart(h.set_index("날짜")[["총자산", "순자산"]])
        if st.button("기록 모두 지우기"):
            S["history"] = []
            st.rerun()
    else:
        st.caption("아직 기록이 없어요.")


# ============================================================
# 18. 리포트 · 데이터
# ============================================================
def make_csv(S, c) -> bytes:
    rows = [("재무상태표", "자산", "총자산", c["assets"]), ("재무상태표", "부채", "총부채", c["debts"]),
            ("재무상태표", "합계", "순자산", c["net"]), ("재무상태표", "부채", "임대보증금 반환 의무", c["deposits_owed"]),
            ("현금흐름표", "수입", "월 총소득", c["income"]), ("현금흐름표", "지출", "월 정기지출", c["outflow"]),
            ("현금흐름표", "지출", "월 대출 상환액", c["debt_payment"]), ("현금흐름표", "합계", "월 잉여자금", c["surplus"]),
            ("지표", "유동성", "현금·예금 여력(개월)", c["runway"]), ("지표", "부채", "총부채/총자산(%)", c["debt_ratio"]),
            ("지표", "부채", "월 상환액/월 소득(%, 참고)", c["repayment_ratio"]), ("지표", "투자", "고위험 자산 비중(%)", c["high_risk_ratio"]),
            ("지표", "유동성", "12개월 내 만기 보증금", c["near_deposit"]), ("지표", "유동성", "보증금 반환 준비율(%)", c["readiness"]),
            ("목표", "금액", "목표 금액", A(S, "target")), ("목표", "계산", "필요 월 저축액(수익률 0%)", c["required_monthly"])]
    return pd.DataFrame(rows, columns=["표", "구분", "항목", "값(만원 단위)"]).to_csv(index=False).encode("utf-8-sig")


def build_report_html(S, c) -> str:
    sc = health_scores(S, c)
    diag = make_diagnosis(S, c)
    tl = build_timeline(S, c, 10)

    def tbl(rows, cols):
        return pd.DataFrame(rows, columns=cols).to_html(index=False, escape=True, border=0, classes="t")

    asset_rows = [["현금·예금", won(c["liquid"])], ["주식·ETF", won(c["stocks"])], ["가상자산·테마주", won(c["crypto"])], ["연금계좌", won(c["pension"])],
                  ["부동산", won(c["prop_value"])], ["기타", won(c["other_assets"] + c["child"])], ["총자산", won(c["assets"])]]
    debt_rows = [["주택담보대출", won(c["loans"])], ["신용·기타 부채", won(A(S, "credit") + A(S, "other_debt"))],
                 ["임대보증금 반환 의무", won(c["deposits_owed"])], ["총부채", won(c["debts"])], ["순자산", won(c["net"])]]
    flow_rows = [["월 총소득", won(c["income"])], ["월 정기지출", won(c["outflow"])], ["월 잉여자금", won(c["surplus"])]]
    tl_rows = [[f"{int(r['연차'])}년차", won(r["월 현금흐름"]), won(r["현금·예금 잔액(추정)"])] for _, r in tl.iterrows()]
    diag_html = "".join(
        f"<div class='d'><b>[{esc(d['level'])}] {esc(d['title'])}</b><br>{esc(d['finding'])}<br><small>근거: {esc(d['evidence'])}<br>다음 행동: {esc(d['action'])}</small></div>"
        for d in diag)
    score_rows = [[k, "정보 부족" if v is None else f"{v:.0f}점"] for k, v in sc["parts"].items()]
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>머니체크 재무 리포트</title>
<style>body{{font-family:'Pretendard','Malgun Gothic',sans-serif;max-width:860px;margin:30px auto;color:#14213d;line-height:1.6;padding:0 16px}}
h1{{color:#0f766e}}h2{{border-bottom:2px solid #0f766e;padding-bottom:4px;margin-top:30px}}
table.t{{border-collapse:collapse;width:100%;margin:8px 0}}table.t th,table.t td{{border:1px solid #d0d5dd;padding:6px 10px;text-align:left}}
table.t th{{background:#f2f4f7}}.d{{border:1px solid #e4e7ec;border-radius:10px;padding:10px 14px;margin:8px 0}}
.k{{display:flex;gap:10px;flex-wrap:wrap}}.k div{{flex:1;min-width:150px;border:1px solid #e4e7ec;border-radius:10px;padding:10px}}
.k b{{display:block;font-size:1.2em}}small,.f{{color:#667085}}@media print{{body{{margin:0}}}}</style></head><body>
<h1>머니체크 재무 리포트</h1><p class="f">작성일 {date.today().isoformat()} · 금액 단위 만원 · 입력값 기반 참고 자료</p>
<div class="k"><div>순자산<b>{esc(won(c['net']))}</b></div><div>월 잉여자금<b>{esc(won(c['surplus']))}</b></div>
<div>현금·예금 여력<b>{esc(fmt_months(c['runway']))}</b></div><div>재무 건강 점수<b>{'-' if sc['overall'] is None else round(sc['overall'])}점</b></div></div>
<h2>1. 재무상태표</h2>{tbl(asset_rows, ['자산', '금액'])}{tbl(debt_rows, ['부채·순자산', '금액'])}
<h2>2. 현금흐름표</h2>{tbl(flow_rows, ['항목', '월 금액'])}
<h2>3. 기간별 현금흐름(기간 한정 지출 반영)</h2>{tbl(tl_rows, ['연차', '월 현금흐름', '현금·예금 잔액(추정)'])}
<h2>4. 영역별 점수</h2>{tbl(score_rows, ['영역', '점수'])}
<h2>5. 진단과 다음 행동</h2>{diag_html}
<h2>6. 계산 기준과 한계</h2><ul><li>순자산 = 총자산 − 총부채(임대보증금 반환 의무 포함)</li><li>월 잉여자금 = 월 총소득 − 월 정기지출</li>
<li>현금·예금 여력 = 현금·예금 ÷ 월 정기지출</li><li>월 상환액/월 소득은 참고 비율이며 금융기관의 DSR이 아닙니다.</li>
<li>세금·수수료·투자수익·물가는 반영하지 않았으며 세무·법률 판단은 전문가 확인이 필요합니다.</li></ul></body></html>"""


def page_report(S, c):
    hero("REPORT & DATA", "리포트·데이터", "분석 결과를 파일로 내려받고, 입력한 정보를 저장하거나 불러와요.")
    section("내려받기")
    a, b, d = st.columns(3)
    a.download_button("📄 HTML 리포트 (인쇄→PDF 가능)", data=build_report_html(S, c).encode("utf-8"),
                      file_name=f"머니체크_리포트_{date.today().isoformat()}.html", mime="text/html", type="primary", **FULL)
    b.download_button("📊 요약 CSV", data=make_csv(S, c), file_name=f"머니체크_요약_{date.today().isoformat()}.csv", mime="text/csv", **FULL)
    d.download_button("💾 입력값 저장(JSON)", data=json.dumps({"app": "moneycheck", "version": 2, "data": S}, ensure_ascii=False, indent=2, default=float).encode("utf-8"),
                      file_name=f"머니체크_입력값_{date.today().isoformat()}.json", mime="application/json", **FULL)
    st.caption("HTML 리포트는 브라우저에서 열어 인쇄(Ctrl+P) → ‘PDF로 저장’을 선택하면 PDF로 보관할 수 있어요.")
    st.divider()
    section("저장한 입력값 불러오기")
    up = st.file_uploader("이전에 저장한 JSON 파일", type=["json"])
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
    st.divider()
    section("데이터 삭제")
    st.caption("이 앱은 입력값을 서버에 저장하지 않고 현재 브라우저 세션에만 보관해요.")
    st.button("🗑️ 입력 정보 모두 지우기", on_click=reset_all, **FULL)


# ============================================================
# 19. 사이드바 · 라우터
# ============================================================
P_HOME, P_INPUT, P_SNAP = "🏠 홈", "✍️ 정보 입력", "📊 재무현황"
P_TIME, P_LIQ, P_LOAN = "📅 기간별 현금흐름", "💧 유동성·보증금 반환", "🏦 대출 계산기"
P_RISK, P_PROT, P_GOAL = "⚡ 투자위험", "🛡️ 보장 점검", "🎯 목표 플래너"
P_STRESS, P_ACT, P_REP = "🧪 스트레스 테스트", "✅ 실행·점검", "📄 리포트·데이터"
PAGES = [P_HOME, P_INPUT, P_SNAP, P_TIME, P_LIQ, P_LOAN, P_RISK, P_PROT, P_GOAL, P_STRESS, P_ACT, P_REP]

init_state()
S = st.session_state["mc"]

st.sidebar.markdown('<div class="brand">💚 머니체크</div><div class="brand-sub">내 돈을 이해하는 가장 쉬운 첫걸음</div>', unsafe_allow_html=True)
page = st.sidebar.radio("메뉴", PAGES, key="nav", label_visibility="collapsed")

# 입력 페이지를 벗어나면 표 편집용 임시 상태를 정리 (다음 방문 때 최신값으로 시작)
if page != P_INPUT:
    for _k in ("_base_props", "_base_term_exp", "_base_oneoffs"):
        st.session_state.pop(_k, None)

_c0 = calculate(S)
side_summary = st.sidebar.container()
st.sidebar.divider()
st.sidebar.caption("계좌번호·주민등록번호·비밀번호는 입력하지 마세요.")
st.sidebar.button("입력 정보 지우기", on_click=reset_all, **FULL)

if page == P_HOME:
    page_home(S, _c0)
elif page == P_INPUT:
    page_input(S)
else:
    _c = calculate(S)  # 입력 이후 최신 값
    {P_SNAP: page_snapshot, P_TIME: page_timeline, P_LIQ: page_liquidity, P_LOAN: page_loan,
     P_RISK: page_risk, P_PROT: page_protection, P_GOAL: page_goal, P_STRESS: page_stress,
     P_ACT: page_action, P_REP: page_report}[page](S, _c)

_cf = calculate(S)
if has_data(_cf):
    with side_summary:
        st.divider()
        st.caption("내 요약")
        st.markdown(f"**순자산** {won(_cf['net'])}  \n**월 잉여** {won(_cf['surplus'])}  \n**여력** {fmt_months(_cf['runway'])}")

st.divider()
with st.expander("계산 기준과 한계 확인하기"):
    st.markdown(
        """
        **계산 기준**
        - 총자산 = 현금·예금 + 주식·ETF + 가상자산·테마주 + 연금계좌 + 부동산 + 기타 자산(+ 선택 시 자녀 명의 자산)
        - 총부채 = 주택담보대출 + 신용대출 + 기타 부채 + 임대보증금 반환 의무
        - 순자산 = 총자산 − 총부채 · 월 잉여자금 = 월 총소득 − 월 정기지출
        - 월 정기지출 = 생활비 + 세금 적립 + 보험료 + 가족 지원 + 대출 상환 + 비정기 지출(월 환산)
        - 현금·예금 여력 = 현금·예금 ÷ 월 정기지출

        **중요한 한계**
        - 입력값이 틀리거나 자산이 중복 입력되면 결과도 달라집니다.
        - 투자수익률·세금·보험 보장 분석·연금 수령액·부동산 거래비용·물가는 기본 계산에 반영하지 않습니다.
        - 시나리오·시뮬레이션은 가정값에 대한 단순 계산이며 미래를 예측하거나 결과를 보장하지 않습니다.
        - 월 상환액/월 소득은 참고 비율로 금융기관의 공식 DSR과 다릅니다.
        - 중요한 투자·대출·세금 결정 전에는 최신 공식 정보를 확인하고 필요하면 전문가와 상담하세요.
        """
    )
st.caption("머니체크 · 사용자의 이해와 선택을 돕는 재무 점검 프로토타입")
