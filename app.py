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
from google import genai

# ============================================================
# 머니체크 | 처음 해보는 사람도 쉽게 쓰는 내 돈 점검 서비스
# - 숫자 계산은 앱이 직접(규칙 기반) 하고, 설명은 Gemini AI 재무코치가 도와줘요.
# - 모든 금액 단위: 만원
# ============================================================

st.set_page_config(
    page_title="머니체크 | 내 돈을 쉽게 이해하기",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded",
)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

def ask_gemini(prompt):
    if gemini_client is None:
        return "현재 AI 재무코치를 사용할 수 없습니다. 잠시 후 다시 시도해주세요."

    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
            )

            if response.text:
                return response.text

            return "AI가 분석 결과를 생성하지 못했습니다. 잠시 후 다시 시도해주세요."

        except Exception as e:
            error_message = str(e)

            # 일시적인 서버 과부하 또는 요청 제한인 경우 재시도
            if ("503" in error_message or "UNAVAILABLE" in error_message
                    or "429" in error_message or "RESOURCE_EXHAUSTED" in error_message):

                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue

                return (
                    "현재 AI 분석 요청이 많아 분석을 완료하지 못했습니다. "
                    "잠시 후 다시 시도해주세요."
                )

            # API 키 또는 인증 관련 오류
            if "401" in error_message or "403" in error_message:
                return (
                    "AI 서비스 인증에 문제가 발생했습니다. "
                    "관리자 설정을 확인해주세요."
                )

            # 모델 또는 API 설정 관련 오류
            if "404" in error_message:
                return (
                    "현재 AI 모델을 사용할 수 없습니다. "
                    "잠시 후 다시 시도해주세요."
                )

            # 그 외의 오류
            return (
                "AI 분석 중 일시적인 문제가 발생했습니다. "
                "잠시 후 다시 시도해주세요."
            )


# Streamlit 버전별 width 옵션 호환 (use_container_width → width="stretch")
_HAS_WIDTH = "width" in inspect.signature(st.button).parameters
FULL = {"width": "stretch"} if _HAS_WIDTH else {"use_container_width": True}


# ============================================================
# 1. 디자인 — 신호등은 반드시 빨강·노랑·초록만 사용
# ============================================================
st.markdown(
    """
    <style>
      @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
      :root{ --ink:#0f172a; --sub:#475569; --mute:#64748b; --line:#e2e8f0; --brand:#0f766e; --navy:#134e4a; }
      .stApp{ font-family:'Pretendard',-apple-system,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif; }
      .block-container{ max-width:960px; padding-top:1.2rem; padding-bottom:4rem; }
      h1,h2,h3,h4{ letter-spacing:-.025em; color:var(--ink); }
      h3{ font-size:1.35rem; margin-top:.6rem; }
      p, li{ line-height:1.7; }
      [data-testid="stWidgetLabel"] p{ font-size:1.02rem; font-weight:650; color:var(--ink); }
      [data-testid="stSidebar"]{ background:#f8fafc; border-right:1px solid var(--line); }
      [data-testid="stSidebar"] [role="radiogroup"] label{ padding:10px 12px; border-radius:12px; margin-bottom:3px; width:100%; }
      [data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:#e6f4f1; }
      .brand{ font-size:1.35rem; font-weight:800; color:var(--navy); }
      .brand-sub{ color:var(--mute); font-size:.86rem; margin:-2px 0 12px 0; }

      .hero{ background:linear-gradient(120deg,#115e59 0%,#0f766e 60%,#14b8a6 100%); color:#fff; border-radius:20px; padding:26px 30px; margin:0 0 18px 0; }
      .hero h1{ color:#fff; font-size:1.8rem; line-height:1.35; margin:0 0 8px 0; }
      .hero p{ color:#e6fffb; margin:0; font-size:1.05rem; line-height:1.7; }

      .kpi{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 18px; height:100%; }
      .kpi-l{ color:var(--mute); font-size:.9rem; font-weight:650; margin-bottom:4px; }
      .kpi-v{ color:var(--ink); font-size:1.6rem; font-weight:800; letter-spacing:-.03em; line-height:1.25; }
      .kpi-s{ color:var(--mute); font-size:.84rem; margin-top:5px; line-height:1.5; }

      .card{ background:#fff; border:1px solid var(--line); border-radius:18px; padding:18px 20px; height:100%; }
      .card .ico{ font-size:1.7rem; margin-bottom:6px; }
      .card h4{ margin:0 0 6px 0; font-size:1.1rem; }
      .card p{ margin:0; color:var(--sub); font-size:.96rem; line-height:1.65; }
      .callout{ border-radius:14px; padding:14px 18px; line-height:1.7; font-size:1rem; margin:8px 0; }
      .callout b.t{ display:block; margin-bottom:2px; }
      .tiny{ color:var(--mute); font-size:.84rem; line-height:1.6; }

      /* 신호등 */
      .dot{ display:inline-block; width:14px; height:14px; border-radius:50%; flex:none; }
      .banner{ border-radius:16px; padding:16px 20px; display:flex; gap:12px; align-items:center; font-size:1.12rem; font-weight:750; margin:6px 0 14px 0; line-height:1.5; }
      .banner .dot{ width:20px; height:20px; }
      .strip{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 8px 0; }
      .chip{ display:inline-flex; align-items:center; gap:8px; padding:7px 14px; border-radius:999px; background:#fff; border:1px solid var(--line); font-size:.92rem; font-weight:650; color:#334155; }
      .sig{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 20px; margin:12px 0; }
      .sig-top{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
      .sig-title{ font-weight:800; color:#334155; font-size:1rem; }
      .sig-badge{ margin-left:auto; font-size:.8rem; font-weight:700; padding:2px 11px; border-radius:999px; }
      .sig-h{ font-size:1.26rem; font-weight:800; color:var(--ink); margin:8px 0 6px 0; line-height:1.45; }
      .sig-m{ color:var(--sub); font-size:1rem; line-height:1.75; }
      .sig-a{ margin-top:10px; padding:11px 15px; background:#f8fafc; border-radius:12px; color:var(--ink); font-size:.98rem; line-height:1.7; }
      .sig details{ margin-top:9px; color:var(--mute); font-size:.85rem; }
      .sig summary{ cursor:pointer; }

      div[data-testid="stExpander"]{ border:1px solid var(--line); border-radius:14px; background:#fff; }
      div.stButton > button, div[data-testid="stDownloadButton"] button{ border-radius:12px; min-height:2.8rem; font-weight:700; }
      button[data-baseweb="tab"]{ font-weight:700; font-size:1rem; }
      @media (max-width:720px){ .hero{padding:20px;} .hero h1{font-size:1.45rem;} .kpi-v{font-size:1.35rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)

# 신호등 색: 초록 / 노랑 / 빨강 (+ 회색은 ‘신호가 아닌 일반 안내’용)
TONES = {
    "ok": {"fg": "#166534", "bg": "#f0fdf4", "bd": "#bbf7d0", "bar": "#22c55e"},
    "warn": {"fg": "#854d0e", "bg": "#fefce8", "bd": "#fde047", "bar": "#eab308"},
    "bad": {"fg": "#991b1b", "bg": "#fef2f2", "bd": "#fecaca", "bar": "#ef4444"},
    "neutral": {"fg": "#334155", "bg": "#f8fafc", "bd": "#e2e8f0", "bar": "#94a3b8"},
}
TONES["info"] = TONES["neutral"]
TONE_EMOJI = {"ok": "🟢", "warn": "🟡", "bad": "🔴", "neutral": "⚪"}
TONE_LABEL = {"ok": "괜찮아요", "warn": "살펴보세요", "bad": "먼저 확인", "neutral": "참고"}
TONE_ORDER = {"bad": 0, "warn": 1, "ok": 2, "neutral": 3}


def esc(x) -> str:
    return html.escape(str(x))


def dot(tone: str) -> str:
    return f'<span class="dot" style="background:{TONES[tone]["bar"]}"></span>'


def kpi(label, value, sub="", tone="neutral") -> str:
    bar = TONES.get(tone, TONES["neutral"])["bar"]
    return (f'<div class="kpi" style="border-top:5px solid {bar}"><div class="kpi-l">{esc(label)}</div>'
            f'<div class="kpi-v">{esc(value)}</div><div class="kpi-s">{esc(sub)}</div></div>')


def kpi_row(items):
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        col.markdown(kpi(*it), unsafe_allow_html=True)


def callout(body_html: str, tone="neutral", title: str | None = None):
    t = TONES.get(tone, TONES["neutral"])
    head = f'<b class="t" style="color:{t["fg"]}">{esc(title)}</b>' if title else ""
    st.markdown(f'<div class="callout" style="background:{t["bg"]};border:1px solid {t["bd"]};color:#1e293b">{head}{body_html}</div>',
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


def show_altair(chart):
    try:
        st.altair_chart(chart, **FULL)
    except TypeError:
        st.altair_chart(chart)


def year_chart(df: pd.DataFrame, x: str, ys: list[str], zero_line=True, height=300):
    """x(년)는 숫자로 그려서 1년·2년·…10년 순서로 정확히 나오게 해요."""
    d = df[[x] + ys].rename(columns={x: "year"})
    try:
        import altair as alt
        long = d.melt(id_vars=["year"], var_name="구분", value_name="금액")
        line = alt.Chart(long).mark_line(point=True, strokeWidth=3).encode(
            x=alt.X("year:Q", title="지금부터 몇 년 후", axis=alt.Axis(tickMinStep=1, format="d")),
            y=alt.Y("금액:Q", title="만원"),
            color=alt.Color("구분:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[alt.Tooltip("year:Q", title="몇 년 후"), alt.Tooltip("구분:N"), alt.Tooltip("금액:Q", format=",.0f", title="만원")],
        )
        layers = [line]
        if zero_line:
            layers.append(alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#94a3b8", strokeDash=[5, 4]).encode(y="y:Q"))
        show_altair(alt.layer(*layers).properties(height=height))
    except Exception:  # noqa: BLE001
        st.line_chart(d.set_index("year")[ys])


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
P_HOME, P_INPUT, P_RESULT = "🏠 처음 화면", "✍️ 내 정보 입력", "📊 내 재무 결과"
P_SIM, P_AI, P_PLAN = "🔮 미리 계산해 보기", "🤖 AI 재무코치", "✅ 할 일·저장"
PAGES = [P_HOME, P_INPUT, P_RESULT, P_SIM, P_AI, P_PLAN]

GOALS = ["전반적인 재무 점검", "비상자금 마련", "빚 갚기", "결혼 자금", "내 집 마련", "자녀 교육비", "은퇴 준비", "자산 불리기"]
KNOW = ["있어요", "없어요", "잘 모르겠어요"]
KINDS = ["한 번만", "매년 반복"]
STEPS = ["① 가진 것", "② 갚을 것", "③ 한 달 수입·지출", "④ 앞으로의 계획"]
MONTHLY_KEYS = ["income", "other_income", "living_cost", "insurance_premium", "other_fixed", "irregular_monthly", "debt_payment"]

DEFAULTS = {
    "goal": GOALS[0], "years": 3, "target": 0.0, "already_saved": 0.0,
    # 가진 것
    "cash": 0.0, "deposits": 0.0, "invest": 0.0, "volatile": 0.0, "pension": 0.0, "property": 0.0, "other_assets": 0.0,
    # 갚을 것
    "mortgage": 0.0, "credit": 0.0, "other_debt": 0.0, "deposits_owed": 0.0, "near_deposit": 0.0,
    "debt_mode": "자동 계산", "debt_payment": 0.0, "loan_rate": 4.5, "loan_years": 10.0,
    # 한 달 수입·지출
    "income": 0.0, "other_income": 0.0, "living_cost": 0.0, "insurance_premium": 0.0, "other_fixed": 0.0, "irregular_monthly": 0.0,
    # 예정된 큰 지출 3칸
    **{f"ev{i}_{k}": v for i in (1, 2, 3) for k, v in (("name", ""), ("kind", KINDS[0]), ("amt", 0.0), ("months", 12.0), ("years", 3.0))},
    # 보험
    "has_silson": KNOW[2], "has_life": KNOW[2],
    "checks": {},
}


def _ev(i, name, kind, amt, when):
    out = {f"ev{i}_name": name, f"ev{i}_kind": kind, f"ev{i}_amt": float(amt)}
    out[f"ev{i}_months" if kind == KINDS[0] else f"ev{i}_years"] = float(when)
    return out


DEMOS = {
    "young": {  # 사회초년생
        "goal": "내 집 마련", "years": 5, "target": 5000.0, "already_saved": 1500.0,
        "cash": 300.0, "deposits": 1500.0, "invest": 500.0, "pension": 200.0, "other_assets": 5000.0,
        "other_debt": 3000.0, "debt_mode": "직접 입력", "debt_payment": 25.0,
        "income": 280.0, "living_cost": 150.0, "insurance_premium": 8.0, "other_fixed": 20.0, "irregular_monthly": 15.0,
        **_ev(1, "이사 비용", KINDS[0], 200, 10),
        "has_silson": "있어요", "has_life": "잘 모르겠어요",
    },
    "family": {  # 맞벌이 가정
        "goal": "자녀 교육비", "years": 7, "target": 10000.0, "already_saved": 2000.0,
        "cash": 800.0, "deposits": 3000.0, "invest": 4000.0, "volatile": 500.0, "pension": 2500.0, "property": 45000.0,
        "mortgage": 22000.0, "loan_rate": 4.0, "loan_years": 20.0,
        "income": 620.0, "other_income": 30.0, "living_cost": 280.0, "insurance_premium": 35.0, "other_fixed": 40.0, "irregular_monthly": 30.0,
        **_ev(1, "자녀 교육비", KINDS[1], 1200, 6), **_ev(2, "자동차 교체", KINDS[0], 3000, 24),
        "has_silson": "있어요", "has_life": "없어요",
    },
    "rich": {  # 자산은 많지만 현금이 부족한 가계
        "goal": "전반적인 재무 점검", "years": 5, "target": 50000.0, "already_saved": 5000.0,
        "cash": 5000.0, "volatile": 65000.0, "property": 340000.0,
        "mortgage": 60000.0, "deposits_owed": 65000.0, "near_deposit": 45000.0, "loan_rate": 4.2, "loan_years": 30.0,
        "income": 450.0, "other_income": 390.0, "living_cost": 260.0, "insurance_premium": 12.0, "other_fixed": 185.0,
        **_ev(1, "자녀 등록금·주거비", KINDS[1], 1200, 4), **_ev(2, "주택 수리비", KINDS[1], 1000, 2),
        "has_silson": "있어요", "has_life": "없어요",
    },
}


def init_state():
    if "mc" not in st.session_state:
        st.session_state["mc"] = copy.deepcopy(DEFAULTS)
    for k, v in DEFAULTS.items():
        st.session_state["mc"].setdefault(k, copy.deepcopy(v))
    st.session_state.setdefault("_step", 0)
    st.session_state.setdefault("nav", P_HOME)


def _clear_widget_state():
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and (k.startswith("w_") or k == "step_nav"):
            st.session_state.pop(k, None)
    st.session_state["_step"] = 0
    st.session_state.pop("ai_result", None)


def load_demo(name: str):
    st.session_state["mc"] = {**copy.deepcopy(DEFAULTS), **copy.deepcopy(DEMOS[name])}
    _clear_widget_state()
    st.session_state["nav"] = P_RESULT


def reset_all():
    st.session_state["mc"] = copy.deepcopy(DEFAULTS)
    _clear_widget_state()
    st.session_state["nav"] = P_HOME


def goto(page: str):
    st.session_state["nav"] = page


def goto_step(i: int):
    st.session_state["nav"] = P_INPUT
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
        payload = dict(obj.get("data", obj))
        # 이전 버전 파일 호환 (주식·레버리지·코인 → 일반 투자 / 변동성 큰 투자)
        if "invest" not in payload and any(k in payload for k in ("stocks", "leverage", "crypto")):
            stocks, lev, crypto = (float(payload.get(k, 0) or 0) for k in ("stocks", "leverage", "crypto"))
            payload["invest"], payload["volatile"] = max(0.0, stocks - lev), lev + crypto
        if "rent_income" in payload:
            payload["other_income"] = float(payload.get("other_income", 0) or 0) + float(payload["rent_income"] or 0)
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


def radio_h(label, key, S, options, help=None, container=None):
    c = container or st
    wk = f"w_{key}"
    kw = {} if wk in st.session_state else {"index": options.index(S[key]) if S.get(key) in options else 0}
    v = c.radio(label, options, horizontal=True, key=wk, help=help, **kw)
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
# 4. 계산 (합계·순자산·남는 돈은 모두 자동 계산)
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


def events(S) -> list[dict]:
    """예정된 큰 지출: 한 번만(once) / 매년 반복(repeat)"""
    out = []
    for i in (1, 2, 3):
        amt = A(S, f"ev{i}_amt")
        if amt <= 0:
            continue
        name = S.get(f"ev{i}_name") or f"예정 지출 {i}"
        if S.get(f"ev{i}_kind") == KINDS[1]:
            yrs = int(A(S, f"ev{i}_years"))
            if yrs > 0:
                out.append({"name": name, "kind": "repeat", "amt": amt, "years": yrs})
        else:
            out.append({"name": name, "kind": "once", "amt": amt, "months": max(1, int(A(S, f"ev{i}_months")))})
    return out


def calculate(S) -> dict:
    cash, deposits = A(S, "cash"), A(S, "deposits")
    invest, volatile, pension = A(S, "invest"), A(S, "volatile"), A(S, "pension")
    prop, other_assets = A(S, "property"), A(S, "other_assets")
    financial = cash + deposits + invest + volatile + pension
    assets = financial + prop + other_assets

    mortgage, credit, other_debt = A(S, "mortgage"), A(S, "credit"), A(S, "other_debt")
    loans = mortgage + credit + other_debt
    dep_owed = A(S, "deposits_owed")
    near_dep = min(A(S, "near_deposit"), dep_owed)
    debts = loans + dep_owed

    income = A(S, "income") + A(S, "other_income")
    pay = monthly_payment(loans, A(S, "loan_rate"), A(S, "loan_years")) if S.get("debt_mode") == "자동 계산" else A(S, "debt_payment")
    fixed = A(S, "living_cost") + A(S, "insurance_premium") + A(S, "other_fixed") + A(S, "irregular_monthly")
    outflow = fixed + pay
    surplus = income - outflow
    liquid = cash + deposits

    evs = events(S)
    repeat_m = sum(e["amt"] / 12 for e in evs if e["kind"] == "repeat")
    one_12m = sum(e["amt"] for e in evs if e["kind"] == "once" and e["months"] <= 12)
    big_need = near_dep + one_12m

    target_gap = max(0.0, A(S, "target") - A(S, "already_saved"))
    months_goal = max(1, int(A(S, "years") or 3) * 12)
    return {
        "cash": cash, "deposits": deposits, "invest": invest, "volatile": volatile, "pension": pension,
        "property": prop, "other_assets": other_assets, "financial": financial, "assets": assets,
        "mortgage": mortgage, "credit": credit, "other_debt": other_debt, "loans": loans,
        "deposits_owed": dep_owed, "near_deposit": near_dep, "debts": debts, "net": assets - debts,
        "income": income, "debt_payment": pay, "outflow": outflow, "surplus": surplus,
        "liquid": liquid, "runway": None if outflow <= 0 else liquid / outflow,
        "debt_ratio": ratio(debts, assets), "repayment_ratio": ratio(pay, income), "savings_rate": ratio(surplus, income),
        "volatile_ratio": ratio(volatile, financial),
        "nonfin_ratio": ratio(prop + other_assets, assets),
        "repeat_m": repeat_m, "one_12m": one_12m, "big_need": big_need,
        "readiness": ratio(liquid, big_need) if big_need > 0 else None,
        "dep_readiness": ratio(liquid, near_dep) if near_dep > 0 else None,
        "liquid_ratio": ratio(liquid, financial),
        "target_gap": target_gap, "months_goal": months_goal, "required_monthly": target_gap / months_goal,
    }


def has_data(c) -> bool:
    return c["assets"] > 0 or c["income"] > 0 or c["outflow"] > 0


def build_timeline(S, c, years=10) -> pd.DataFrame:
    evs = events(S)
    cum, rows = c["liquid"], []
    for y in range(1, years + 1):
        term_m = sum(e["amt"] / 12 for e in evs if e["kind"] == "repeat" and y <= e["years"])
        month = c["surplus"] - term_m
        one_y = sum(e["amt"] for e in evs if e["kind"] == "once" and math.ceil(e["months"] / 12) == y)
        cum += month * 12 - one_y
        rows.append({"연차": y, "예정 지출(월 환산)": term_m, "월 현금흐름": month, "일회성 지출": one_y, "현금·예금 잔액": cum})
    return pd.DataFrame(rows)


def apply_scenario(S, c, income_pct=0.0, rate_delta=0.0, expense_delta=0.0, one_off=0.0, invest_drop=0.0, vol_drop=0.0) -> dict:
    new_income = c["income"] * (1 + income_pct / 100)
    pay_delta = 0.0
    if rate_delta and c["loans"] > 0 and S.get("debt_mode") == "자동 계산":
        pay_delta = (monthly_payment(c["loans"], A(S, "loan_rate") + rate_delta, A(S, "loan_years"))
                     - monthly_payment(c["loans"], A(S, "loan_rate"), A(S, "loan_years")))
    new_out = max(0.0, c["outflow"] + expense_delta + pay_delta)
    loss = c["invest"] * invest_drop / 100 + c["volatile"] * vol_drop / 100
    liquid = c["liquid"] - one_off
    return {"income": new_income, "outflow": new_out, "surplus": new_income - new_out, "liquid": liquid,
            "net": c["net"] - one_off - loss, "runway": None if new_out <= 0 else liquid / new_out}


def recovery_table() -> pd.DataFrame:
    """떨어진 만큼이 아니라 ‘더’ 올라야 본전이 된다는 것을 보여줘요."""
    return pd.DataFrame([{"떨어진 폭": f"−{d}%", "본전이 되려면": f"+{(1 / (1 - d / 100) - 1) * 100:.0f}% 상승 필요"} for d in (10, 30, 50, 70)])


def months_to_reach(target, start, pmt, monthly_rate, cap=1200):
    bal = start
    for m in range(1, cap + 1):
        bal = bal * (1 + monthly_rate) + pmt
        if bal >= target:
            return m
    return None


# ============================================================
# 5. 신호등 진단 (쉬운 말 + 지금 할 일 + 계산 근거)
# ============================================================
def make_checks(S, c) -> list[dict]:
    out = []

    def add(key, title, tone, headline, meaning, evidence, action):
        out.append({"key": key, "title": title, "tone": tone, "headline": headline,
                    "meaning": meaning, "evidence": evidence, "action": action})

    # 1) 매달 남는 돈
    if c["income"] > 0 or c["outflow"] > 0:
        ev = f"월 수입 {won(c['income'])} − 월 지출 {won(c['outflow'])} = {won(c['surplus'])}"
        if c["surplus"] < 0:
            add("cashflow", "매달 남는 돈", "bad", f"매달 {won(abs(c['surplus']))}이 모자라요",
                "버는 돈보다 쓰는 돈이 많아요. 이 상태가 이어지면 저축이 줄거나 빚이 늘 수 있어요.", ev,
                "쓰는 돈을 ‘꼭 필요한 것’과 ‘줄일 수 있는 것’으로 나눠 보세요. 빠지거나 중복된 항목이 없는지도 확인해 보세요.")
        elif (c["savings_rate"] or 0) < 10:
            add("cashflow", "매달 남는 돈", "warn", f"매달 {won(c['surplus'])}이 남지만 많지는 않아요",
                "남는 돈이 수입의 10%도 안 돼요. 예상 못한 지출이 생기면 바로 적자가 될 수 있어요.", ev,
                "1년에 한두 번 나가는 돈(보험·경조사비 등)이 빠지지 않았는지 보고, 줄일 수 있는 지출을 찾아보세요.")
        elif c["repeat_m"] > c["surplus"]:
            add("cashflow", "매달 남는 돈", "warn",
                f"지금은 {won(c['surplus'])} 남지만, 예정된 지출이 있으면 월 {won(c['repeat_m'] - c['surplus'])}이 모자라요",
                "등록금·수리비처럼 몇 년 동안 매년 나가는 돈을 넣으면 그 기간에는 적자가 돼요.",
                ev + f"  /  매년 나가는 예정 지출 월 환산 {won(c['repeat_m'])}",
                "‘미리 계산해 보기 → 해마다 돈 흐름’에서 언제까지 적자인지, 현금·예금이 버티는지 확인하세요.")
        else:
            add("cashflow", "매달 남는 돈", "ok", f"매달 {won(c['surplus'])}이 남아요",
                "버는 돈보다 쓰는 돈이 적어서 저축할 여력이 있어요. 다만 계산상 남는 돈과 실제 통장에 남는 돈은 다를 수 있어요.", ev,
                "지난 2~3개월 동안 통장 잔액이 실제로 이만큼 늘었는지 비교해 보세요.")

    # 2) 비상자금
    if c["runway"] is not None:
        ev = f"현금·예금 {won(c['liquid'])} ÷ 월 지출 {won(c['outflow'])} = {c['runway']:.1f}개월"
        mean = "갑자기 수입이 끊겨도 현금·예금으로 버틸 수 있는 기간이에요. 보통 3~6개월치를 목표로 삼지만, 직업 안정성에 따라 달라요."
        gap3 = max(0.0, 3 * c["outflow"] - c["liquid"])
        if c["runway"] < 1:
            add("emergency", "비상자금", "bad", f"비상자금이 {c['runway']:.1f}개월치예요", mean, ev,
                f"먼저 한 달 치 생활비부터 모아 보세요. 3개월치까지는 {won(gap3)}이 더 필요해요.")
        elif c["runway"] < 3:
            add("emergency", "비상자금", "warn", f"비상자금이 {c['runway']:.1f}개월치예요", mean, ev,
                f"3개월치까지 {won(gap3)}이 더 필요해요. 매달 남는 돈 일부를 비상자금 통장으로 자동이체해 보세요.")
        else:
            add("emergency", "비상자금", "ok", f"비상자금이 {c['runway']:.1f}개월치예요", mean, ev,
                "이 돈 중 곧 쓸 예정인 돈(보증금·학비 등)은 빼고도 충분한지 확인해 보세요.")

    # 3) 빚 부담
    if c["debts"] <= 0:
        if has_data(c):
            add("debt", "빚 부담", "ok", "갚아야 할 빚이 없어요", "입력한 부채가 없어요.", "총부채 0원", "새로 빚을 질 때는 금리와 상환 조건을 꼭 확인하세요.")
    else:
        dr, rr = c["debt_ratio"], c["repayment_ratio"]
        tone = "bad" if ((rr or 0) >= 40 or (dr or 0) >= 70) else "warn" if ((rr or 0) >= 30 or (dr or 0) >= 50) else "ok"
        head = f"가진 자산의 {pct(dr)}가 빚이에요" if dr is not None else "갚아야 할 빚이 있어요"
        mean = "빚 비율만으로 위험하다고 단정할 수는 없어요. 금리와 갚는 기간, 수입 대비 상환 부담을 함께 봐야 해요."
        if rr is not None and c["debt_payment"] > 0:
            mean = f"매달 수입의 {pct(rr)}를 대출 갚는 데 쓰고 있어요. " + mean
        if c["deposits_owed"] > 0:
            mean += " 세입자에게 받은 보증금은 돌려줘야 하는 돈이라 빚에 포함했어요."
        add("debt", "빚 부담", tone, head, mean,
            f"총부채 {won(c['debts'])} ÷ 총자산 {won(c['assets'])} = {pct(dr, 1)}  /  월 상환 {won(c['debt_payment'])} ÷ 월 수입 {won(c['income'])} = {pct(rr, 1)} (은행의 공식 DSR과는 달라요)",
            "대출마다 금리·만기·중도상환수수료를 한 장으로 정리해 보세요. 금리가 높은 빚부터 갚는 것이 일반적인 출발점이에요.")

    # 4) 투자 쏠림
    if c["financial"] > 0:
        vr = c["volatile_ratio"] or 0
        if c["volatile"] <= 0:
            add("risk", "투자 쏠림", "ok", "변동이 아주 큰 투자는 없어요", "가격이 크게 출렁이는 자산을 입력하지 않았어요.", "변동성 큰 투자 0원",
                "투자는 ‘잃어도 생활에 지장이 없는 돈’ 안에서 하는 것이 기본이에요.")
        else:
            tone = "bad" if vr >= 50 else "warn" if vr >= 30 else "ok"
            add("risk", "투자 쏠림", tone, f"금융자산의 {pct(vr)}가 변동이 큰 투자예요",
                "가격이 크게 오르내리는 자산은 한 번 크게 떨어지면 생활비나 곧 갚을 돈을 마련하기 어려워질 수 있어요.",
                f"변동성 큰 투자 {won(c['volatile'])} ÷ 금융자산 {won(c['financial'])} = {pct(vr, 1)}",
                "‘미리 계산해 보기 → 만약 이런 일이 생기면?’에서 투자가 크게 떨어졌을 때 내 순자산이 어떻게 변하는지 확인해 보세요.")

    # 5) 자산이 묶여 있는 정도
    if c["assets"] > 0 and (c["nonfin_ratio"] or 0) >= 80 and (c["runway"] is None or c["runway"] < 6):
        add("illiquid", "급할 때 쓸 수 있는 돈", "warn", f"자산의 {pct(c['nonfin_ratio'])}가 부동산·기타 자산이에요",
            "자산은 많아도 부동산은 급할 때 바로 현금으로 바꾸기 어려워요. 그래서 현금·예금 여력을 따로 챙겨 두는 것이 중요해요.",
            f"(부동산 {won(c['property'])} + 기타 {won(c['other_assets'])}) ÷ 총자산 {won(c['assets'])} = {pct(c['nonfin_ratio'], 1)}",
            "비상자금을 먼저 채우고, 부동산 외에 바로 쓸 수 있는 자산의 비중을 조금씩 늘리는 계획을 세워 보세요.")

    # 6) 곧 나갈 큰돈
    if c["big_need"] > 0:
        r = c["readiness"] or 0
        tone = "bad" if r < 100 else "warn" if r < 150 else "ok"
        parts = []
        if c["near_deposit"] > 0:
            parts.append(f"1년 안에 돌려줄 보증금 {won(c['near_deposit'])}")
        if c["one_12m"] > 0:
            parts.append(f"1년 안의 큰 지출 {won(c['one_12m'])}")
        add("bigmoney", "곧 나갈 큰돈", tone, f"1년 안에 {won(c['big_need'])}이 필요해요",
            f"{' + '.join(parts)}. 지금 현금·예금은 {won(c['liquid'])}이라 준비율은 {pct(r)}예요. 100%보다 낮으면 모자란다는 뜻이에요.",
            f"현금·예금 {won(c['liquid'])} ÷ 필요한 돈 {won(c['big_need'])} = {pct(r, 1)}",
            "모자라다면 일정을 조정하거나, 일부 투자자산을 현금으로 바꿀 계획을 미리 세워 두세요. (세금·수수료·시장 상황도 함께 확인해요)")

    # 7) 보험
    if has_data(c):
        ans = [S.get("has_silson"), S.get("has_life")]
        ev = f"실손의료보험: {ans[0]} / 소득 보장 보험: {ans[1]}"
        if "없어요" in ans:
            add("insurance", "보험", "warn", "보험이 부족할 수 있어요",
                "의료비나 소득 중단에 대비한 보험이 없다고 했어요. 큰 병이나 사고가 나면 저축이 한꺼번에 줄 수 있어요.", ev,
                "내게 꼭 필요한 보장이 무엇인지부터 정리해 보세요. 새 보험이 승인되기 전에는 기존 보험을 해지하지 마세요.")
        elif "잘 모르겠어요" in ans:
            add("insurance", "보험", "warn", "내 보험을 한 번 확인해 보세요",
                "내 보험이 무엇을 보장하는지 모르면 필요할 때 도움이 안 될 수 있어요.", ev,
                "보험사 앱이나 ‘내보험다보여’ 같은 공식 서비스에서 가입 내역을 확인해 보세요.")
        else:
            add("insurance", "보험", "ok", "기본 보장이 있어요", "실손의료보험과 소득 보장 보험이 모두 있다고 했어요.", ev,
                "보장 금액이 내 상황에 충분한지 1년에 한 번 점검해 보세요.")

    out.sort(key=lambda x: TONE_ORDER[x["tone"]])
    return out


def overall_banner(checks):
    if not checks:
        return
    nb = sum(1 for x in checks if x["tone"] == "bad")
    nw = sum(1 for x in checks if x["tone"] == "warn")
    if nb:
        tone, text = "bad", f"먼저 확인할 항목이 {nb}개 있어요. 아래 빨간 신호부터 살펴보세요."
    elif nw:
        tone, text = "warn", f"조금만 손보면 더 탄탄해져요. 살펴볼 항목이 {nw}개 있어요."
    else:
        tone, text = "ok", "지금 입력한 내용에서는 큰 문제가 보이지 않아요."
    t = TONES[tone]
    st.markdown(f'<div class="banner" style="background:{t["bg"]};border:1px solid {t["bd"]};color:{t["fg"]}">{dot(tone)}<span>{esc(text)}</span></div>',
                unsafe_allow_html=True)


def signal_strip(checks):
    chips = "".join(f'<span class="chip">{dot(x["tone"])}{esc(x["title"])}</span>' for x in checks)
    st.markdown(f'<div class="strip">{chips}</div>', unsafe_allow_html=True)


def render_checks(items, limit=None):
    for it in (items[:limit] if limit else items):
        t = TONES[it["tone"]]
        st.markdown(
            f'<div class="sig" style="border-left:8px solid {t["bar"]}">'
            f'<div class="sig-top">{dot(it["tone"])}<span class="sig-title">{esc(it["title"])}</span>'
            f'<span class="sig-badge" style="background:{t["bg"]};color:{t["fg"]};border:1px solid {t["bd"]}">{TONE_LABEL[it["tone"]]}</span></div>'
            f'<div class="sig-h">{esc(it["headline"])}</div>'
            f'<div class="sig-m">{esc(it["meaning"])}</div>'
            f'<div class="sig-a"><b>👉 지금 할 일</b><br>{esc(it["action"])}</div>'
            f'<details><summary>계산 근거 보기</summary>{esc(it["evidence"])}</details></div>',
            unsafe_allow_html=True)


def validate(S, c) -> list[str]:
    """초보자가 흔히 하는 입력 실수를 쉬운 말로 알려줘요."""
    msgs = []
    if c["income"] == 0 and c["outflow"] > 0:
        msgs.append("월 수입이 0원인데 지출이 있어요. 수입을 빠뜨리지 않았는지 확인해 주세요.")
    if c["income"] > 0 and c["outflow"] > c["income"] * 3:
        msgs.append("월 지출이 월 수입의 3배가 넘어요. 금액 단위(만원)가 맞는지 확인해 주세요.")
    if c["debts"] > c["assets"] > 0:
        msgs.append("빚이 자산보다 많아요. 실제 상황이 맞다면 그대로 진행해도 괜찮아요.")
    if S.get("debt_mode") == "직접 입력" and A(S, "debt_payment") > 0 and c["loans"] == 0:
        msgs.append("매달 갚는 돈은 있는데 대출 잔액이 0원이에요. ② 갚을 것에서 남은 대출금도 입력해 주세요.")
    if c["loans"] > 0 and c["debt_payment"] == 0:
        msgs.append("대출이 있는데 매달 갚는 돈이 0원이에요. ② 갚을 것에서 확인해 주세요.")
    for k in MONTHLY_KEYS:
        if A(S, k) >= 10000:
            msgs.append("한 달 금액에 1억 원 이상이 입력된 칸이 있어요. 단위가 ‘만원’인지 확인해 주세요.")
            break
    if A(S, "target") > 0 and A(S, "already_saved") > A(S, "target"):
        msgs.append("목표를 위해 이미 모은 금액이 목표 금액보다 커요. 둘 다 맞는지 확인해 주세요.")
    return msgs


def make_tasks(S, c, checks):
    tasks = [(x["key"], x["tone"], x["title"], x["action"]) for x in checks if x["tone"] in ("bad", "warn")]
    if A(S, "target") > 0:
        tasks.append(("goal", "ok", "목표 저축 시작하기", f"목표까지 월 약 {won(c['required_monthly'])}(수익률 0% 기준)이 필요해요. 월급날 자동이체로 먼저 떼어 두세요."))
    tasks.append(("monthly", "ok", "한 달에 한 번 내 정보 새로 고치기", "수입·지출·대출 잔액이 바뀌면 다시 입력해서 변화를 확인하세요."))
    return tasks


def money_order(S, c) -> list[tuple[str, str]]:
    """남는 돈을 어디에 먼저 쓰면 좋은지 순서를 알려줘요."""
    steps = []
    target_em = 3 * c["outflow"]
    gap = max(0.0, target_em - c["liquid"])
    if c["outflow"] > 0:
        if gap > 0:
            when = (f" 매달 남는 {won(c['surplus'])}을 모두 쓰면 약 {math.ceil(gap / c['surplus'])}개월 걸려요." if c["surplus"] > 0
                    else " 먼저 매달 남는 돈을 만드는 것이 필요해요.")
            steps.append(("비상자금 3개월치 만들기", f"목표 {won(target_em)}까지 {won(gap)}이 더 필요해요.{when}"))
        else:
            steps.append(("비상자금 3개월치 만들기 ✔", f"이미 {fmt_months(c['runway'])}치가 있어요."))
    pricey = c["credit"] + c["other_debt"]
    if pricey > 0:
        steps.append(("비싼 빚 먼저 갚기", f"신용대출·카드할부 등 {won(pricey)}이 있어요. 금리가 높은 것부터 갚으면 이자를 줄일 수 있어요."))
    if A(S, "target") > 0:
        steps.append(("목표 저축 시작하기", f"목표까지 월 약 {won(c['required_monthly'])}이 필요해요(수익률 0% 기준)."))
    steps.append(("연금·장기 투자 늘리기", "위 순서를 챙긴 뒤 남는 돈으로 연금저축·장기 투자를 고려하세요. (세제 혜택과 한도는 최신 공식 자료로 확인해요)"))
    return steps


# ============================================================
# 6. 공통 화면 조각
# ============================================================
GLOSSARY = [
    ("자산", "내가 가진 것. 현금·예금·투자·부동산 등."),
    ("부채(빚)", "나중에 갚아야 하는 돈. 대출, 카드할부, 세입자에게 받은 보증금 등."),
    ("순자산", "가진 것에서 갚을 것을 뺀 값. 빚을 다 갚고 나면 내 몫으로 남는 돈이에요."),
    ("월 잉여자금", "한 달 동안 번 돈에서 쓴 돈을 뺀 값. 마이너스면 적자예요."),
    ("비상자금", "갑자기 수입이 끊겨도 버틸 수 있게 현금·예금으로 모아 둔 돈. 보통 3~6개월치를 권해요."),
    ("변동성이 큰 투자", "가격이 짧은 기간에 크게 오르내리는 자산. 레버리지·인버스 ETF, 코인, 급등락이 잦은 테마주 등."),
    ("레버리지 ETF", "지수의 하루 움직임을 2배·3배 등으로 따라가도록 만든 상품. 배수와 종류가 다양하고 오르내림이 커요."),
    ("DSR", "은행이 대출을 심사할 때 보는 ‘수입 대비 원리금 상환 비율’. 이 앱의 상환 비율은 참고용이에요."),
]


def need_data(c) -> bool:
    if has_data(c):
        return True
    hero("먼저 내 정보를 입력해 주세요", "입력하면 이 화면이 자동으로 채워져요. 3분이면 충분해요.")
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
        show_altair(chart)
    except Exception:  # noqa: BLE001
        st.markdown(f"**{title}**")
        st.bar_chart(df.set_index(label_col))


# ============================================================
# 7. 처음 화면
# ============================================================
def page_home(S, c):
    hero("내 돈, 3분이면 한눈에 볼 수 있어요", "어려운 금융 용어 없이, 지금 내 상태와 다음에 할 일을 알려드려요.")
    if not has_data(c):
        cols = st.columns(3)
        steps = [("✍️", "1. 내 정보 입력", "가진 것·갚을 것·한 달 수입과 지출을 4단계로 나눠 입력해요. 모르는 칸은 0으로 두세요."),
                 ("🚦", "2. 신호등으로 확인", "🟢🟡🔴 신호등으로 지금 내 상태를 쉽게 보여드려요."),
                 ("✅", "3. 할 일 정하기", "먼저 할 일을 순서대로 정리하고, AI 재무코치에게 쉬운 설명도 들을 수 있어요.")]
        for col, (ico, t, d) in zip(cols, steps):
            col.markdown(f'<div class="card"><div class="ico">{ico}</div><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)
        st.write("")
        st.button("✍️ 내 정보 입력 시작하기", on_click=goto_step, args=(0,), type="primary", **FULL)
        st.caption("회원가입·계좌 연결 없이 바로 쓸 수 있어요.")
        st.write("")
        st.markdown("**입력이 어렵다면 예시로 먼저 둘러보세요**")
        b1, b2, b3 = st.columns(3)
        b1.button("🎓 사회초년생", on_click=load_demo, args=("young",), **FULL)
        b2.button("👨‍👩‍👧 맞벌이 가정", on_click=load_demo, args=("family",), **FULL)
        b3.button("📉 자산은 많지만 현금이 부족한 가계", on_click=load_demo, args=("rich",), **FULL)
    else:
        checks = make_checks(S, c)
        overall_banner(checks)
        kpi_row([("내 순자산", won(c["net"]), f"가진 것 {won(c['assets'])} − 갚을 것 {won(c['debts'])}", "ok" if c["net"] >= 0 else "bad"),
                 ("매달 남는 돈", won(c["surplus"]), f"수입 {won(c['income'])} − 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad"),
                 ("비상자금", fmt_months(c["runway"]), "현금·예금으로 버틸 수 있는 기간",
                  "bad" if (c["runway"] or 0) < 1 else "warn" if (c["runway"] or 0) < 3 else "ok")])
        st.write("")
        section("가장 먼저 볼 것")
        render_checks(checks, limit=2)
        n1, n2, n3 = st.columns(3)
        n1.button("📊 전체 결과 보기", on_click=goto, args=(P_RESULT,), type="primary", **FULL)
        n2.button("🔮 미리 계산해 보기", on_click=goto, args=(P_SIM,), **FULL)
        n3.button("🤖 AI 재무코치에게 물어보기", on_click=goto, args=(P_AI,), **FULL)
    st.write("")
    with st.expander("이 서비스가 하지 않는 일"):
        st.markdown(
            "- 입력한 숫자는 앱이 **직접 계산**해요. AI 재무코치는 그 결과를 **쉽게 설명**해 줄 뿐이에요.\n"
            "- 특정 주식·ETF·펀드·보험 상품을 사거나 팔라고 권하지 않아요.\n"
            "- 세금·법률의 최종 판단은 하지 않아요. 필요하면 전문가나 공식 기관에 확인하세요.\n"
            "- 계좌번호·주민등록번호·비밀번호는 입력하지 마세요.")


# ============================================================
# 8. 내 정보 입력 (4단계)
# ============================================================
def step_have(S):
    st.markdown("#### 지금 **가진 것**을 알려주세요")
    st.caption("대략적인 지금 금액이면 충분해요. 같은 자산을 두 번 넣지 마세요.")
    with st.container(border=True):
        st.markdown("**💵 바로 꺼내 쓸 수 있는 돈**")
        a, b = st.columns(2)
        num("현금·입출금 통장", "cash", S, container=a, help="지갑 속 현금, 월급 통장 등 언제든 쓸 수 있는 돈")
        num("예금·적금", "deposits", S, container=b, help="정기예금과 적금 잔액")
    with st.container(border=True):
        st.markdown("**📈 투자와 연금**")
        a, b = st.columns(2)
        num("일반 투자 (주식·ETF·펀드)", "invest", S, container=a,
            help="대형주, 지수 ETF, 일반 펀드처럼 흔한 투자. 아래 ‘변동성이 큰 투자’에 해당하지 않는 것을 넣어요.")
        num("변동성이 큰 투자", "volatile", S, container=b,
            help="가격이 짧은 기간에 크게 오르내리는 자산이에요. 예) 레버리지·인버스 ETF, 코인, 급등락이 잦은 테마주·소형주, 한 종목에 몰아 넣은 투자. 헷갈리면 ‘일반 투자’에 넣어도 괜찮아요.")
        num("연금계좌 (연금저축·IRP)", "pension", S, container=a, help="연금 계좌 안의 ETF를 위 칸에 또 넣지 마세요.")
    with st.container(border=True):
        st.markdown("**🏠 부동산과 기타**")
        a, b = st.columns(2)
        num("부동산 (지금 가격)", "property", S, step=100.0, container=a, help="대출을 빼기 전 금액이에요. 빚은 다음 단계에서 입력해요.")
        num("기타 자산", "other_assets", S, container=b, help="내가 세입자로 맡겨 둔 전월세 보증금, 자동차 등")


def step_owe(S):
    st.markdown("#### 갚아야 할 돈, **빚**을 알려주세요")
    st.caption("지금 남아 있는 금액을 넣어 주세요. 빚이 없다면 모두 0으로 두고 다음으로 넘어가면 돼요.")
    with st.container(border=True):
        st.markdown("**🏦 대출**")
        a, b, d = st.columns(3)
        num("주택담보대출", "mortgage", S, step=100.0, container=a, help="집을 담보로 받은 대출의 남은 금액")
        num("신용대출·마이너스통장", "credit", S, container=b)
        num("학자금·전세대출·카드할부 등", "other_debt", S, container=d)
    loans = A(S, "mortgage") + A(S, "credit") + A(S, "other_debt")
    with st.container(border=True):
        st.markdown("**📆 매달 갚는 돈**")
        if loans <= 0 and A(S, "debt_payment") <= 0:
            st.caption("대출이 없다면 이 칸은 건너뛰어도 돼요.")
        mode = radio_h("매달 갚는 돈을 어떻게 알려주실래요?", "debt_mode", S, ["자동 계산", "직접 입력"],
                       help="자동 계산은 위 대출 전체를 ‘원리금균등’ 방식으로 계산해요. 실제 금액을 알면 직접 입력이 더 정확해요.")
        if mode == "직접 입력":
            num("매달 갚는 금액 (원금+이자 합계)", "debt_payment", S, step=5.0, help="모든 대출의 한 달 상환액을 합쳐서 넣어 주세요.")
        else:
            a, b = st.columns(2)
            num("대출 평균 금리 (연 %)", "loan_rate", S, step=0.1, max_value=30.0, container=a, help="정확히 모르면 대략 입력해도 돼요.")
            num("평균 남은 기간 (년)", "loan_years", S, step=1.0, max_value=50.0, container=b, help="정확히 모르면 대략 입력해도 돼요.")
            pay = monthly_payment(loans, A(S, "loan_rate"), A(S, "loan_years"))
            if loans > 0:
                callout(f"대출 {won(loans)}, 연 {A(S, 'loan_rate'):.1f}%, {A(S, 'loan_years'):.0f}년 기준으로 매달 약 <b>{won(pay)}</b>을 갚는 걸로 계산했어요.")
    with st.expander("집이나 방을 빌려주고 보증금을 받은 게 있나요? (해당될 때만)", expanded=A(S, "deposits_owed") > 0):
        st.caption("세입자에게 받은 보증금은 계약이 끝나면 돌려줘야 하는 돈이라 빚으로 계산해요.")
        a, b = st.columns(2)
        num("세입자에게 받은 보증금 합계", "deposits_owed", S, step=100.0, container=a)
        num("└ 이 중 1년 안에 돌려줄 금액", "near_deposit", S, step=100.0, container=b, max_value=A(S, "deposits_owed"),
            max_hint="먼저 ‘받은 보증금 합계’를 입력하면 열려요.", help="계약 만기가 12개월 이내인 보증금이에요. 전체 보증금보다 클 수 없어요.")


def step_flow(S):
    st.markdown("#### **한 달**에 들어오고 나가는 돈을 알려주세요")
    st.caption("평균적인 한 달 금액이면 돼요. 대출 상환액은 앞 단계에서 이미 반영되니 여기에는 넣지 마세요.")
    a, b = st.columns(2)
    with a:
        with st.container(border=True):
            st.markdown("**⬇️ 들어오는 돈**")
            num("월급·사업소득 (세금 낸 뒤)", "income", S, help="실제로 통장에 들어오는 금액")
            num("그 밖의 수입", "other_income", S, help="월세 수입, 배당, 용돈, 부수입 등")
    with b:
        with st.container(border=True):
            st.markdown("**⬆️ 나가는 돈**")
            num("생활비", "living_cost", S, help="식비·교통·통신·공과금·월세·문화생활 등")
            num("보험료", "insurance_premium", S)
            num("그 밖의 정기 지출", "other_fixed", S, help="세금 적립, 가족 용돈, 구독료 등 매달 나가는 돈")
            num("1년에 한두 번 나가는 돈 ÷ 12", "irregular_monthly", S, help="자동차 보험, 명절·경조사비, 여행 등 연간 예상액을 12로 나눈 금액")


def step_plan(S):
    st.markdown("#### **앞으로의 계획**을 알려주세요 (모두 선택이에요)")
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
    any_ev = any(A(S, f"ev{i}_amt") > 0 for i in (1, 2, 3))
    with st.expander("앞으로 큰돈이 나갈 일이 있나요? (결혼·이사·등록금 등)", expanded=any_ev):
        st.caption("적어 두면 ‘미리 계산해 보기’에 반영돼요. 한 번에 나가는 돈은 ‘한 번만’, 등록금처럼 몇 년간 매년 나가는 돈은 ‘매년 반복’을 고르세요.")
        for i in (1, 2, 3):
            with st.container(border=True):
                a, b = st.columns([2, 2])
                txt(f"이름 {i}", f"ev{i}_name", S, a, placeholder="예: 이사 비용, 자녀 등록금")
                kind = radio_h("종류", f"ev{i}_kind", S, KINDS, container=b)
                a, b = st.columns(2)
                num("금액", f"ev{i}_amt", S, step=50.0, container=a, help="‘한 번만’이면 총액, ‘매년 반복’이면 1년에 드는 금액")
                if kind == KINDS[0]:
                    num("몇 개월 뒤?", f"ev{i}_months", S, step=1.0, max_value=600.0, container=b)
                else:
                    num("몇 년 동안?", f"ev{i}_years", S, step=1.0, max_value=50.0, container=b)
    with st.container(border=True):
        st.markdown("**🛡️ 보험 (아는 만큼만 답해 주세요)**")
        radio_h("실손의료보험에 가입했나요?", "has_silson", S, KNOW)
        radio_h("아프거나 다쳐서 일을 못 할 때를 대비한 보험(소득 보장)이 있나요?", "has_life", S, KNOW)


def page_input(S):
    hero("내 정보 입력", "총 4단계예요. 금액은 ‘만원’ 단위이고, 모르는 칸은 0으로 두고 넘어가도 괜찮아요. (예: 500 = 500만 원, 10000 = 1억 원)")
    summary = st.container()
    if "step_nav" not in st.session_state:
        st.session_state["step_nav"] = STEPS[st.session_state.get("_step", 0)]
    st.radio("입력 단계", STEPS, horizontal=True, key="step_nav", on_change=_sync_step, label_visibility="collapsed")
    step = STEPS.index(st.session_state["step_nav"])
    st.session_state["_step"] = step
    st.progress((step + 1) / len(STEPS), text=f"{step + 1} / {len(STEPS)} 단계")

    [step_have, step_owe, step_flow, step_plan][step](S)

    st.write("")
    b1, b2, _ = st.columns([1, 1.5, 2])
    b1.button("← 이전", on_click=step_move, args=(-1,), disabled=(step == 0), **FULL)
    if step < len(STEPS) - 1:
        b2.button("다음 단계 →", on_click=step_move, args=(1,), type="primary", **FULL)
    else:
        b2.button("📊 결과 보러 가기", on_click=goto, args=(P_RESULT,), type="primary", **FULL)

    # 위젯 값이 모두 반영된 뒤 맨 위 요약을 채움
    c = calculate(S)
    with summary:
        if step <= 1:
            kpi_row([("가진 것 합계", won(c["assets"]), "", "neutral"), ("갚을 것 합계", won(c["debts"]), "", "neutral"),
                     ("내 순자산", won(c["net"]), "", "ok" if c["net"] >= 0 else "bad")])
        else:
            kpi_row([("한 달 수입", won(c["income"]), "", "neutral"), ("한 달 지출", won(c["outflow"]), "대출 상환 포함", "neutral"),
                     ("매달 남는 돈", won(c["surplus"]), "", "ok" if c["surplus"] > 0 else "bad")])
        msgs = validate(S, c)
        for m in msgs:
            st.warning(m)
        if has_data(c) and not msgs:
            st.caption("✅ 입력 내용에 이상한 점이 없어요. 입력값은 자동으로 저장돼요.")


# ============================================================
# 9. 내 재무 결과
# ============================================================
def page_result(S, c):
    hero("내 재무 결과", "지금 내 돈의 상태를 신호등으로 쉽게 알려드려요.")
    if not need_data(c):
        return
    checks = make_checks(S, c)
    overall_banner(checks)
    kpi_row([("내 순자산", won(c["net"]), f"가진 것 {won(c['assets'])} − 갚을 것 {won(c['debts'])}", "ok" if c["net"] >= 0 else "bad"),
             ("매달 남는 돈", won(c["surplus"]), f"수입 {won(c['income'])} − 지출 {won(c['outflow'])}", "ok" if c["surplus"] > 0 else "bad"),
             ("비상자금", fmt_months(c["runway"]), "현금·예금으로 버틸 수 있는 기간",
              "bad" if (c["runway"] or 0) < 1 else "warn" if (c["runway"] or 0) < 3 else "ok")])
    st.write("")
    section("신호등으로 보는 내 상태", "🔴 먼저 확인 · 🟡 살펴보기 · 🟢 괜찮아요")
    signal_strip(checks)
    render_checks(checks)
    note("신호등 기준은 일반적인 참고 범위예요. 사람마다 상황이 달라서 정답은 아니에요.")

    st.divider()
    section("자세히 보기")
    t1, t2, t3 = st.tabs(["가진 것·갚을 것", "한 달 수입·지출", "자산 구성"])
    assets_rows = [("현금·입출금", c["cash"]), ("예금·적금", c["deposits"]), ("일반 투자", c["invest"]), ("변동성이 큰 투자", c["volatile"]),
                   ("연금계좌", c["pension"]), ("부동산", c["property"]), ("기타 자산", c["other_assets"])]
    debt_rows = [("주택담보대출", c["mortgage"]), ("신용대출·마이너스통장", c["credit"]), ("학자금·기타 대출", c["other_debt"]),
                 ("세입자 보증금(돌려줄 돈)", c["deposits_owed"])]
    with t1:
        left, right = st.columns(2)
        with left:
            st.markdown("**가진 것**")
            show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in assets_rows if v > 0] + [{"항목": "합계", "금액": won(c["assets"])}]))
        with right:
            st.markdown("**갚을 것**")
            show_df(pd.DataFrame([{"항목": k, "금액": won(v)} for k, v in debt_rows if v > 0] +
                                 [{"항목": "합계", "금액": won(c["debts"])}, {"항목": "순자산", "금액": won(c["net"])}]))
    with t2:
        flow = [("들어오는 돈", "월급·사업소득", A(S, "income")), ("들어오는 돈", "그 밖의 수입", A(S, "other_income")),
                ("나가는 돈", "생활비", A(S, "living_cost")), ("나가는 돈", "보험료", A(S, "insurance_premium")),
                ("나가는 돈", "그 밖의 정기 지출", A(S, "other_fixed")), ("나가는 돈", "1년 단위 지출(월 환산)", A(S, "irregular_monthly")),
                ("나가는 돈", "대출 상환", c["debt_payment"])]
        rows = [{"구분": a, "항목": b, "한 달 금액": won(v)} for a, b, v in flow if v > 0]
        rows += [{"구분": "합계", "항목": "수입", "한 달 금액": won(c["income"])}, {"구분": "합계", "항목": "지출", "한 달 금액": won(c["outflow"])},
                 {"구분": "결과", "항목": "매달 남는 돈", "한 달 금액": won(c["surplus"])}]
        show_df(pd.DataFrame(rows))
    with t3:
        a, b = st.columns(2)
        with a:
            donut(pd.DataFrame([{"자산": k, "금액": v} for k, v in assets_rows if v > 0]), "자산", "금액", "가진 것 구성")
        with b:
            donut(pd.DataFrame([{"부채": k, "금액": v} for k, v in debt_rows if v > 0]), "부채", "금액", "갚을 것 구성")
    with st.expander("계산 방법 보기"):
        st.markdown(
            "- 가진 것 = 현금·예금 + 일반 투자 + 변동성이 큰 투자 + 연금 + 부동산 + 기타 자산\n"
            "- 갚을 것 = 주택담보대출 + 신용대출 + 학자금·기타 대출 + 세입자 보증금\n"
            "- 순자산 = 가진 것 − 갚을 것\n"
            "- 매달 남는 돈 = 한 달 수입 − 한 달 지출(대출 상환 포함)\n"
            "- 비상자금(개월) = 현금·예금 ÷ 한 달 지출")


# ============================================================
# 10. 미리 계산해 보기
# ============================================================
def tab_timeline(S, c):
    st.caption("앞으로 몇 년 동안 현금·예금이 어떻게 변할지 보여줘요. ‘내 정보 입력 → ④ 앞으로의 계획’에 적은 큰 지출도 반영돼요.")
    years = st.slider("몇 년 후까지 볼까요?", 3, 15, 8)
    df = build_timeline(S, c, years)
    neg = df[df["월 현금흐름"] < 0]
    broke = df[df["현금·예금 잔액"] < 0]
    kpi_row([("지금 매달 남는 돈", won(c["surplus"]), "예정 지출을 넣기 전", "ok" if c["surplus"] > 0 else "bad"),
             ("월 적자인 해", f"{len(neg)}년" if len(neg) else "없음", "예정 지출까지 반영", "warn" if len(neg) else "ok"),
             ("현금·예금이 바닥나는 때", f"{int(broke.iloc[0]['연차'])}년 뒤" if len(broke) else "기간 안에는 없음", "보증금 반환은 제외한 추정", "bad" if len(broke) else "ok")])
    st.write("")
    st.markdown("**현금·예금 잔액 (만원)**")
    bal = pd.DataFrame({"year": [0] + df["연차"].tolist(), "현금·예금": [c["liquid"]] + df["현금·예금 잔액"].tolist()})
    year_chart(bal, "year", ["현금·예금"])
    st.markdown("**기간별 한 달 돈 흐름**")
    seg, start = [], 0
    vals = df["월 현금흐름"].round(1).tolist()
    for i in range(1, len(vals) + 1):
        if i == len(vals) or vals[i] != vals[start]:
            y0, y1 = int(df.iloc[start]["연차"]), int(df.iloc[i - 1]["연차"])
            v = vals[start]
            seg.append({"기간": f"{y0}년차" if y0 == y1 else f"{y0}~{y1}년차", "한 달 돈 흐름": f"{'🟢' if v > 0 else '🔴'} {won(v)}",
                        "예정 지출(월 환산)": won(df.iloc[start]["예정 지출(월 환산)"])})
            start = i
    show_df(pd.DataFrame(seg))
    note("지금의 수입·지출이 그대로 이어지고 입력한 예정 지출만 더해진다고 본 단순 추정이에요. 투자수익·세금·물가·보증금 반환은 넣지 않았어요.")


def tab_whatif(S, c):
    st.caption("내가 입력한 값은 그대로 두고, ‘만약 이런 일이 생기면?’ 하고 가정만 계산해요.")
    presets = {"월급·사업소득이 끊기면": dict(income_pct=-100), "수입이 20% 줄면": dict(income_pct=-20)}
    if c["loans"] > 0 and S.get("debt_mode") == "자동 계산":
        presets["대출 금리가 2%p 오르면"] = dict(rate_delta=2.0)
    if c["invest"] > 0:
        presets["일반 투자가 20% 떨어지면"] = dict(invest_drop=20)
    if c["volatile"] > 0:
        presets["변동성 큰 투자가 50% 떨어지면"] = dict(vol_drop=50)
    presets["1,000만 원이 갑자기 필요하면"] = dict(one_off=1000)

    def row(name, s):
        return {"상황": name, "매달 남는 돈": f"{'🟢' if s['surplus'] > 0 else '🔴'} {won(s['surplus'])}",
                "현금·예금으로 버티는 기간": fmt_months(s["runway"]), "순자산": won(s["net"])}

    show_df(pd.DataFrame([row("지금", {"surplus": c["surplus"], "runway": c["runway"], "net": c["net"]})] +
                         [row(n, apply_scenario(S, c, **v)) for n, v in presets.items()]))
    if c["income"] > 0 and c["surplus"] > 0:
        st.caption(f"💡 수입이 약 {c['surplus'] / c['income'] * 100:.0f}% 줄면 매달 남는 돈이 0원이 돼요.")

    with st.expander("직접 값을 바꿔 보기"):
        a, b = st.columns(2)
        inc = a.slider("수입 변화 (%)", -100, 50, 0, step=5)
        exp = a.slider("한 달 지출 변화 (만원)", -100, 200, 0, step=10)
        one = a.slider("한 번에 필요한 큰돈 (만원)", 0, 10000, 0, step=100)
        inv = b.slider("일반 투자 하락률 (%)", 0, 60, 0, step=5)
        vol = b.slider("변동성 큰 투자 하락률 (%)", 0, 100, 0, step=5)
        s = apply_scenario(S, c, income_pct=inc, expense_delta=exp, one_off=one, invest_drop=inv, vol_drop=vol)
        show_df(pd.DataFrame([
            {"항목": "한 달 수입", "지금": won(c["income"]), "가정 후": won(s["income"])},
            {"항목": "한 달 지출", "지금": won(c["outflow"]), "가정 후": won(s["outflow"])},
            {"항목": "매달 남는 돈", "지금": won(c["surplus"]), "가정 후": won(s["surplus"])},
            {"항목": "현금·예금", "지금": won(c["liquid"]), "가정 후": won(s["liquid"])},
            {"항목": "순자산", "지금": won(c["net"]), "가정 후": won(s["net"])},
            {"항목": "버티는 기간", "지금": fmt_months(c["runway"]), "가정 후": fmt_months(s["runway"])},
        ]))
        if s["surplus"] < 0:
            callout(f"이 가정에서는 매달 <b>{won(abs(s['surplus']))}</b>이 모자라요.", "bad")
        if s["liquid"] < 0:
            callout("필요한 큰돈이 현재 현금·예금보다 커요. 자산을 팔거나 빌려야 할 수 있어요.", "warn")

    with st.expander("변동성이 큰 투자는 왜 조심해야 하나요?"):
        st.markdown("가격이 크게 떨어지면, **떨어진 폭보다 더 많이 올라야** 본전이 돼요. 변동성이 클수록 이 부담이 커져요.")
        show_df(recovery_table())
        st.markdown("레버리지·인버스 ETF처럼 **매일의 수익률을 기준으로 움직이는 상품**은 오르락내리락이 반복되면 기간이 길수록 지수와 다르게 움직일 수 있어요. 배수와 상품 구조는 제각각이니 투자 전에 설명서를 꼭 확인하세요.")
    note("내가 정한 가정의 계산 결과예요. 미래를 예측하거나 일어날 확률을 뜻하지 않아요.")


def tab_goal(S, c):
    if A(S, "target") <= 0:
        st.info("목표 금액을 입력하면 매달 얼마를 모아야 하는지 계산해 드려요.")
        st.button("④ 목표 입력하러 가기", on_click=goto_step, args=(3,), **FULL)
        return
    years = int(S["years"])
    n = years * 12
    ret = st.slider("예상 연 수익률 (%)", 0.0, 8.0, 0.0, step=0.5, help="0%는 ‘이자나 수익 없이 저금만 한다’는 뜻이에요. 수익률은 보장되지 않아요.")
    m = ret / 1200
    saved, target = A(S, "already_saved"), A(S, "target")
    gap = max(0.0, target - saved * (1 + m) ** n)
    req = gap / n if m == 0 else gap * m / ((1 + m) ** n - 1)
    avail = c["surplus"]
    kpi_row([("목표 금액", won(target), f"{years}년 뒤", "neutral"), ("이미 모은 금액", won(saved), "", "neutral"),
             ("매달 모아야 할 돈", won(req), f"연 {ret:.1f}% 가정", "neutral"),
             ("지금 매달 남는 돈", won(avail), "", "ok" if avail >= req else "warn")])
    st.write("")
    if avail <= 0:
        callout("지금은 매달 남는 돈이 없어서 저축만으로 목표를 모으기 어려워요. 먼저 ‘내 재무 결과’에서 현금흐름을 살펴보세요.", "bad")
    else:
        mths = months_to_reach(target, saved, avail, m)
        if avail >= req:
            callout(f"지금 남는 돈을 모두 저축한다면 목표 기간 안에 달성할 수 있어요 (약 {mths}개월). 단, 비상자금과 예정 지출은 따로 챙기세요.", "ok")
        else:
            when = f"약 {mths}개월({mths / 12:.1f}년)" if mths else "100년 안에는 어려워요"
            callout(f"매달 <b>{won(req - avail)}</b>이 더 필요해요. 지금 남는 돈만으로는 목표까지 {when} 걸려요. 목표 금액이나 기간을 조정해 보세요.", "warn")
        rows = []
        b0, b1 = saved, saved
        for k in range(0, n + 1):
            if k > 0:
                b0 += avail
                b1 = b1 * (1 + m) + avail
            if k % 12 == 0:
                rows.append({"year": k // 12, "수익률 0%": b0, f"수익률 {ret:.1f}%": b1, "목표 금액": target})
        cols = ["수익률 0%", f"수익률 {ret:.1f}%", "목표 금액"] if ret > 0 else ["수익률 0%", "목표 금액"]
        year_chart(pd.DataFrame(rows), "year", cols, zero_line=False)
    note("매달 같은 금액을 저축한다고 가정한 단순 계산이에요. 세금·수수료·물가·소득 변화는 넣지 않았어요.")


def page_sim(S, c):
    hero("미리 계산해 보기", "앞으로의 돈 흐름, 만약의 상황, 목표 달성까지 미리 계산해 봐요.")
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
    diag = [{"항목": x["title"], "신호": TONE_EMOJI[x["tone"]], "결론": x["headline"], "설명": x["meaning"],
             "계산 근거": x["evidence"], "다음 행동": x["action"]} for x in checks]
    evs = "; ".join(
        f"{e['name']} {won(e['amt'])} ({'약 ' + str(e['months']) + '개월 뒤 한 번' if e['kind'] == 'once' else '매년 ' + str(e['years']) + '년 동안'})"
        for e in events(S)) or "입력 없음"
    goal_txt = (f"{S.get('goal')} / 목표 금액 {won(A(S, 'target'))} / {int(A(S, 'years'))}년 / 이미 모은 금액 {won(A(S, 'already_saved'))}"
                if A(S, "target") > 0 else f"{S.get('goal')} (목표 금액 입력 없음)")
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
9. 기존 머니체크 메뉴와 기능을 활용할 수 있는 경우 해당 기능을 안내하세요.
10. 전문용어를 사용할 경우 짧고 쉽게 설명하세요.
11. 제공된 데이터만으로 판단하기 어려운 사항은 추측하지 말고
    '추가 확인이 필요합니다'라고 명확하게 표시하세요.

[머니체크 메뉴]
내 정보 입력 / 내 재무 결과 / 미리 계산해 보기 / AI 재무코치 / 할 일·저장
(위 메뉴에 없는 기능은 안내하지 마세요.)

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
고위험 자산 비중: {pct(c["volatile_ratio"])}
금융자산 중 현금성 비중: {pct(c["liquid_ratio"])}

보증금 반환 준비율:
{pct(c["dep_readiness"], 0) if c["dep_readiness"] is not None else "해당 없음"}

예정된 큰 지출: {evs}
목표: {goal_txt}

[머니체크 기존 재무진단 결과]
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
    hero("AI 재무코치", "머니체크가 계산한 재무상태를 Gemini가 이해하기 쉽게 설명해줘요.")
    if not need_data(c):
        return

    st.info(
        "AI는 머니체크의 계산 결과를 바탕으로 설명과 점검 방향을 제시합니다. "
        "투자상품의 매수·매도나 세무·법률 판단을 직접 결정하지 않습니다."
    )
    st.caption("🔐 버튼을 누르면 합계 금액과 진단 문장만 Google Gemini로 전송돼요. 이름·계좌번호 등은 입력하지 않으니 전송되지 않아요.")
    if gemini_client is None:
        st.warning("AI 재무코치를 쓰려면 Gemini API 키가 필요해요. `.streamlit/secrets.toml`(또는 Streamlit Cloud의 Secrets)에 "
                   "`GEMINI_API_KEY = \"발급받은_키\"` 를 넣어 주세요.")

    checks = make_checks(S, c)
    sig = hashlib.md5(json.dumps({k: v for k, v in S.items() if k != "checks"}, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

    if st.button("✨ 현재 재무상태 AI 분석하기", **FULL):
        with st.spinner("AI가 현재 재무상태를 분석하고 있어요..."):
            ai_prompt = build_ai_prompt(S, c, checks)
            st.session_state["ai_result"] = ask_gemini(ai_prompt)
            st.session_state["ai_sig"] = sig

    if st.session_state.get("ai_result"):
        if st.session_state.get("ai_sig") != sig:
            st.warning("입력값이 바뀌었어요. 최신 내용으로 보려면 위 버튼을 다시 눌러 주세요.")
        st.markdown("### ✨ AI 재무코치 분석")
        st.markdown(st.session_state["ai_result"])
        note("AI 답변은 참고용이에요. 숫자는 머니체크가 계산한 값을 기준으로 하며, 실행 전에는 공식 자료와 전문가 확인이 필요해요.")


# ============================================================
# 12. 할 일·저장
# ============================================================
def build_report_html(S, c, checks) -> str:
    def tbl(rows, cols):
        return pd.DataFrame(rows, columns=cols).to_html(index=False, escape=True, border=0, classes="t")
    asset_rows = [["현금·예금", won(c["liquid"])], ["일반 투자", won(c["invest"])], ["변동성이 큰 투자", won(c["volatile"])], ["연금계좌", won(c["pension"])],
                  ["부동산", won(c["property"])], ["기타", won(c["other_assets"])], ["합계", won(c["assets"])]]
    debt_rows = [["주택담보대출", won(c["mortgage"])], ["신용·기타 대출", won(c["credit"] + c["other_debt"])],
                 ["세입자 보증금(돌려줄 돈)", won(c["deposits_owed"])], ["합계", won(c["debts"])], ["순자산", won(c["net"])]]
    flow_rows = [["한 달 수입", won(c["income"])], ["한 달 지출", won(c["outflow"])], ["매달 남는 돈", won(c["surplus"])]]
    tl = build_timeline(S, c, 8)
    tl_rows = [[f"{int(r['연차'])}년 뒤", won(r["월 현금흐름"]), won(r["현금·예금 잔액"])] for _, r in tl.iterrows()]
    cards = "".join(f"<div class='d' style='border-left:8px solid {TONES[x['tone']]['bar']}'><b>{TONE_EMOJI[x['tone']]} {esc(x['title'])} — {esc(x['headline'])}</b><br>{esc(x['meaning'])}<br>"
                    f"<small>계산: {esc(x['evidence'])}<br>지금 할 일: {esc(x['action'])}</small></div>" for x in checks)
    order = "".join(f"<li><b>{esc(t)}</b> — {esc(d)}</li>" for t, d in money_order(S, c))
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>머니체크 재무 리포트</title>
<style>body{{font-family:'Pretendard','Malgun Gothic',sans-serif;max-width:820px;margin:30px auto;color:#0f172a;line-height:1.65;padding:0 16px}}
h1{{color:#0f766e}}h2{{border-bottom:2px solid #0f766e;padding-bottom:4px;margin-top:28px}}
table.t{{border-collapse:collapse;width:100%;margin:8px 0}}table.t th,table.t td{{border:1px solid #d0d5dd;padding:6px 10px;text-align:left}}
table.t th{{background:#f2f4f7}}.d{{border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;margin:8px 0}}small,.f{{color:#64748b}}</style></head><body>
<h1>머니체크 재무 리포트</h1><p class="f">작성일 {date.today().isoformat()} · 금액 단위 만원 · 입력값 기반 참고 자료</p>
<h2>1. 한눈에 보기</h2><p>순자산 <b>{esc(won(c['net']))}</b> · 매달 남는 돈 <b>{esc(won(c['surplus']))}</b> · 비상자금 <b>{esc(fmt_months(c['runway']))}</b></p>
{tbl(asset_rows, ['가진 것', '금액'])}{tbl(debt_rows, ['갚을 것', '금액'])}
<h2>2. 한 달 수입·지출</h2>{tbl(flow_rows, ['항목', '한 달 금액'])}
<h2>3. 해마다 돈 흐름</h2>{tbl(tl_rows, ['시점', '한 달 돈 흐름', '현금·예금 잔액'])}
<h2>4. 신호등 진단과 지금 할 일</h2>{cards}
<h2>5. 남는 돈은 이 순서로</h2><ol>{order}</ol>
<h2>6. 알아두세요</h2><ul><li>입력값을 바탕으로 한 참고 자료이며 세무·법률·투자 판단을 대신하지 않습니다.</li>
<li>세금·수수료·투자수익·물가는 반영하지 않았습니다.</li><li>월 상환액/월 수입은 참고 비율이며 금융기관의 DSR이 아닙니다.</li></ul></body></html>"""


def page_plan(S, c):
    hero("할 일·저장", "지금 할 일을 순서대로 정리하고, 입력한 내용을 파일로 저장해요.")
    if not need_data(c):
        return
    checks = make_checks(S, c)
    section("남는 돈은 이 순서로 쓰면 좋아요")
    with st.container(border=True):
        for i, (t, d) in enumerate(money_order(S, c), 1):
            st.markdown(f"**{i}. {t}**  \n{d}")
    tasks = make_tasks(S, c, checks)
    done = sum(1 for t in tasks if S["checks"].get(t[0]))
    st.write("")
    section("해야 할 일 체크리스트")
    st.progress(done / len(tasks) if tasks else 0.0, text=f"실천 진행률 {done} / {len(tasks)}")
    for tone, title in (("bad", "🔴 먼저 할 일"), ("warn", "🟡 이어서 할 일"), ("ok", "🟢 꾸준히 할 일")):
        items = [t for t in tasks if t[1] == tone]
        if not items:
            continue
        st.markdown(f"#### {title}")
        for tid, _, name, desc in items:
            with st.container(border=True):
                S["checks"][tid] = st.checkbox(f"**{name}**", value=bool(S["checks"].get(tid, False)), key=f"w_chk_{tid}")
                st.caption(desc)
    st.divider()
    section("저장하기", "새로고침하면 입력값이 사라져요. 파일로 저장해 두면 다음에 이어서 쓸 수 있어요.")
    a, b = st.columns(2)
    a.download_button("📄 결과 리포트 (HTML)", data=build_report_html(S, c, checks).encode("utf-8"),
                      file_name=f"머니체크_리포트_{date.today().isoformat()}.html", mime="text/html", type="primary", **FULL)
    b.download_button("💾 입력값 저장 (JSON)", data=json.dumps({"app": "moneycheck", "version": 4, "data": S}, ensure_ascii=False, indent=2, default=float).encode("utf-8"),
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
    {P_RESULT: page_result, P_SIM: page_sim, P_AI: page_ai, P_PLAN: page_plan}[page](S, _c)

_cf = calculate(S)  # 입력 화면에서 바뀐 최신 값으로 사이드바 요약 갱신
if has_data(_cf):
    with side_summary:
        st.divider()
        st.caption("내 요약")
        st.markdown(f"**순자산** {won(_cf['net'])}  \n**매달 남는 돈** {won(_cf['surplus'])}  \n**비상자금** {fmt_months(_cf['runway'])}")

st.divider()
st.caption("머니체크 · 입력한 내용을 바탕으로 한 참고용 재무 점검 도구예요.")
