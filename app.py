from __future__ import annotations

from datetime import date
from io import BytesIO
import math
import pandas as pd
import streamlit as st

# ============================================================
# 머니체크 | 이해하기 쉬운 가계 재무진단
# 무료 규칙 기반 프로토타입: 외부 AI API / 계좌 연동 없음
# ============================================================

st.set_page_config(
    page_title="머니체크 | 내 돈을 쉽게 이해하기",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------- 디자인 ----------------------------
st.markdown(
    """
    <style>
      :root { --ink:#172b4d; --muted:#64748b; --line:#e4eaf1; --soft:#f5f8fb; --teal:#0f766e; }
      .block-container { max-width: 1120px; padding-top: 1.35rem; padding-bottom: 3.5rem; }
      [data-testid="stSidebar"] { background: #f5f8fb; border-right: 1px solid #e5eaf0; }
      [data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
      .brand { font-size:1.15rem; font-weight:800; letter-spacing:-.03em; color:#17324d; }
      .hero { background:linear-gradient(120deg,#17324d 0%,#0f766e 100%); color:white; border-radius:22px; padding:28px 30px; margin:0 0 20px 0; }
      .hero .eyebrow { color:#bce8df; font-size:.78rem; font-weight:800; letter-spacing:.08em; margin-bottom:9px; }
      .hero h1 { color:white; font-size:2rem; line-height:1.25; margin:0 0 9px 0; letter-spacing:-.04em; }
      .hero p { color:#edf8f7; margin:0; font-size:1rem; line-height:1.6; }
      .section-kicker { color:#0f766e; font-size:.78rem; font-weight:800; letter-spacing:.06em; margin-bottom:4px; }
      .soft-card { border:1px solid #e5ebf2; border-radius:16px; padding:17px 18px; background:white; min-height:100px; }
      .soft-card h4 { margin:0 0 7px 0; color:#172b4d; font-size:1rem; }
      .soft-card p { margin:0; color:#5b6b7f; font-size:.91rem; line-height:1.55; }
      .callout { background:#f2f8f7; border:1px solid #d5eae6; border-radius:15px; padding:15px 17px; line-height:1.65; }
      .tiny-note { color:#64748b; font-size:.82rem; line-height:1.55; }
      div[data-testid="stMetric"] { background:#f7f9fc; border:1px solid #e7edf4; border-radius:15px; padding:14px 16px; }
      div[data-testid="stForm"] { border:1px solid #e6ebf2; border-radius:17px; padding:18px; }
      div.stButton > button, div[data-testid="stDownloadButton"] button, div[data-testid="stFormSubmitButton"] button { border-radius:12px; min-height:2.7rem; font-weight:650; }
      div[data-testid="stExpander"] { border:1px solid #e5ebf2; border-radius:13px; }
      h1,h2,h3,h4 { letter-spacing:-.025em; }
      hr { border-color:#e6ebf2; }
      @media (max-width: 720px) { .hero {padding:22px 20px;} .hero h1 {font-size:1.6rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- 상수 ----------------------------
ASSET_FIELDS = {
    "cash": "현금·입출금 계좌",
    "deposits": "예금·적금",
    "stocks": "주식·ETF",
    "pension": "연금계좌",
    "property": "부동산 현재 평가액",
    "other_assets": "기타 자산",
}
DEBT_FIELDS = {
    "mortgage": "주택담보대출 등",
    "credit": "신용대출·마이너스통장",
    "other_debt": "기타 부채",
}
GOALS = [
    "전반적인 재무 점검", "비상자금 마련", "부채 상환", "결혼 자금",
    "주택 마련", "자녀 교육비", "은퇴 준비", "경제적 독립(FIRE)", "자산 증식",
]
DEFAULT_DATA = {
    **{k: 0 for k in ASSET_FIELDS},
    **{k: 0 for k in DEBT_FIELDS},
    "income": 0, "living_cost": 0, "debt_payment": 0,
    "goal": "전반적인 재무 점검", "years": 3, "target": 0,
    "already_saved": 0, "extra_monthly": 0,
    "leverage": 0, "planned_expense": 0, "planned_expense_months": 6,
    "household": "1인 가구", "life_stage": "사회초년기",
    "other_income": 0, "irregular_monthly": 0,
}

# ---------------------------- 공통 함수 ----------------------------
def won(value: float | int | None) -> str:
    """입력 단위인 만원을 사람이 읽기 쉬운 만원/억원 표현으로 변환."""
    if value is None:
        return "계산할 수 없음"
    n = int(round(float(value)))
    sign = "−" if n < 0 else ""
    n = abs(n)
    if n >= 10000:
        eok, rest = divmod(n, 10000)
        if rest == 0:
            return f"{sign}{eok:,}억 원"
        return f"{sign}{eok:,}억 {rest:,}만 원"
    return f"{sign}{n:,}만 원"


def pct(value: float | None, digits: int = 1) -> str:
    return "계산할 수 없음" if value is None or not math.isfinite(value) else f"{value:.{digits}f}%"


def ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator * 100


def fmt_months(value: float | None) -> str:
    if value is None:
        return "지출 입력 필요"
    if not math.isfinite(value):
        return "계산할 수 없음"
    return f"{value:.1f}개월"


def calculate(data: dict) -> dict:
    """모든 금액은 만원 단위. 순자산은 사용자 입력을 받지 않고 계산한다."""
    assets = sum(float(data.get(k, 0) or 0) for k in ASSET_FIELDS)
    debts = sum(float(data.get(k, 0) or 0) for k in DEBT_FIELDS)
    income = float(data.get("income", 0) or 0) + float(data.get("other_income", 0) or 0)
    core_expenses = float(data.get("living_cost", 0) or 0)
    debt_payment = float(data.get("debt_payment", 0) or 0)
    irregular_monthly = float(data.get("irregular_monthly", 0) or 0)
    total_monthly_outflow = core_expenses + debt_payment + irregular_monthly
    liquid = float(data.get("cash", 0) or 0) + float(data.get("deposits", 0) or 0)
    surplus = income - total_monthly_outflow
    target_gap = max(0.0, float(data.get("target", 0) or 0) - float(data.get("already_saved", 0) or 0))
    months_to_goal = max(1, int(data.get("years", 3) or 3) * 12)
    required_monthly = target_gap / months_to_goal
    runway = None if total_monthly_outflow <= 0 else liquid / total_monthly_outflow
    return {
        "assets": assets, "debts": debts, "net": assets - debts,
        "liquid": liquid, "income": income, "core_expenses": core_expenses,
        "debt_payment": debt_payment, "irregular_monthly": irregular_monthly,
        "outflow": total_monthly_outflow, "surplus": surplus, "runway": runway,
        "debt_ratio": ratio(debts, assets),
        "repayment_ratio": ratio(debt_payment, income),
        "savings_rate": ratio(surplus, income),
        "target_gap": target_gap, "required_monthly": required_monthly,
        "months_to_goal": months_to_goal,
        "leverage_ratio": ratio(float(data.get("leverage", 0) or 0), float(data.get("stocks", 0) or 0)),
        "liquid_to_assets": ratio(liquid, assets),
    }


def hero(kicker: str, title: str, subtitle: str):
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str | None = None):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def money_metric(label: str, value: float, help_text: str | None = None):
    st.metric(label, won(value), help=help_text)


def make_csv(data: dict, calc: dict) -> bytes:
    rows = []
    for key, label in ASSET_FIELDS.items():
        rows.append(("재무상태표", "자산", label, data.get(key, 0)))
    for key, label in DEBT_FIELDS.items():
        rows.append(("재무상태표", "부채", label, data.get(key, 0)))
    rows.extend([
        ("재무상태표", "합계", "총자산", calc["assets"]),
        ("재무상태표", "합계", "총부채", calc["debts"]),
        ("재무상태표", "합계", "순자산(자동 계산)", calc["net"]),
        ("현금흐름표", "수입", "월 세후 소득", calc["income"]),
        ("현금흐름표", "지출", "월 생활비·고정지출", calc["core_expenses"]),
        ("현금흐름표", "지출", "월 대출 상환액", calc["debt_payment"]),
        ("현금흐름표", "지출", "비정기 지출 월 환산액", calc["irregular_monthly"]),
        ("현금흐름표", "합계", "월 총지출", calc["outflow"]),
        ("현금흐름표", "합계", "월 잉여자금(자동 계산)", calc["surplus"]),
        ("진단", "지표", "현금·예금으로 버틸 수 있는 기간(개월)", calc["runway"]),
        ("진단", "지표", "부채/총자산(%)", calc["debt_ratio"]),
        ("진단", "지표", "월 상환액/월 소득(참고용 %)", calc["repayment_ratio"]),
        ("목표", "정보", "목표", data.get("goal", "")),
        ("목표", "정보", "목표 기간(년)", data.get("years", 0)),
        ("목표", "금액", "목표 금액", data.get("target", 0)),
        ("목표", "금액", "이미 모은 금액", data.get("already_saved", 0)),
        ("목표", "계산", "필요 월 저축액(수익률 미반영)", calc["required_monthly"]),
    ])
    frame = pd.DataFrame(rows, columns=["표", "구분", "항목", "값(금액은 만원 단위)"])
    return frame.to_csv(index=False).encode("utf-8-sig")


def validate_data(data: dict) -> tuple[list[str], list[str]]:
    """오류는 저장 차단, 경고는 저장 허용하되 확인하도록 안내."""
    errors, warnings = [], []
    numeric_keys = list(ASSET_FIELDS) + list(DEBT_FIELDS) + [
        "income", "other_income", "living_cost", "debt_payment",
        "irregular_monthly", "target", "already_saved", "extra_monthly",
        "leverage", "planned_expense",
    ]
    for key in numeric_keys:
        value = data.get(key, 0)
        if value is None or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            errors.append(f"{key} 항목이 올바른 숫자가 아닙니다.")
        elif value < 0:
            errors.append(f"{key} 항목은 음수일 수 없습니다.")
        elif value > 10_000_000:
            warnings.append(f"{key} 금액이 매우 큽니다. 입력 단위가 만원인지 확인해 주세요.")
    total_assets = sum(float(data.get(k, 0) or 0) for k in ASSET_FIELDS)
    total_debts = sum(float(data.get(k, 0) or 0) for k in DEBT_FIELDS)
    monthly_income = float(data.get("income", 0) or 0) + float(data.get("other_income", 0) or 0)
    monthly_outflow = sum(float(data.get(k, 0) or 0) for k in ["living_cost", "debt_payment", "irregular_monthly"])
    if data.get("already_saved", 0) > data.get("target", 0) and data.get("target", 0) > 0:
        warnings.append("이미 모은 금액이 목표 금액보다 큽니다. 목표 금액 또는 이미 모은 금액을 확인해 주세요.")
    if data.get("target", 0) == 0 and data.get("already_saved", 0) > 0:
        warnings.append("목표 금액이 0인데 이미 모은 금액이 입력되어 있습니다.")
    if monthly_income == 0 and monthly_outflow > 0:
        warnings.append("월 소득이 0이고 지출이 있습니다. 소득 공백 상황인지, 소득 입력을 빠뜨렸는지 확인해 주세요.")
    if monthly_income > 0 and monthly_outflow > monthly_income * 3:
        warnings.append("월 지출이 소득의 3배를 넘습니다. 단위와 지출 입력을 다시 확인해 주세요. 실제 상황일 수도 있습니다.")
    if total_debts > total_assets:
        warnings.append("총부채가 총자산보다 큽니다. 실제 상황일 수 있으므로 입력값을 확인한 뒤 계속할 수 있습니다.")
    if data.get("leverage", 0) > data.get("stocks", 0):
        errors.append("레버리지 ETF 금액은 주식·ETF 전체 금액보다 클 수 없습니다. 레버리지 ETF는 주식·ETF 금액의 일부로 입력해 주세요.")
    if data.get("planned_expense", 0) > 0 and data.get("planned_expense_months", 0) <= 0:
        errors.append("예정된 큰 지출이 있다면 지출까지 남은 기간을 1개월 이상으로 입력해 주세요.")
    if data.get("income", 0) + data.get("other_income", 0) < 0:
        errors.append("월 소득을 다시 확인해 주세요.")
    if data.get("living_cost", 0) + data.get("debt_payment", 0) + data.get("irregular_monthly", 0) < 0:
        errors.append("월 지출을 다시 확인해 주세요.")
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def make_diagnosis(data: dict, c: dict) -> list[dict]:
    """각 진단에는 관찰 결과, 근거, 다음 행동을 함께 제공한다."""
    items = []
    if c["surplus"] < 0:
        items.append({
            "level": "우선 점검", "title": "매달 현금흐름이 부족해요",
            "finding": f"입력값 기준으로 매달 {won(abs(c['surplus']))}이 부족합니다.",
            "evidence": f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])} = {won(c['surplus'])}",
            "action": "생활비를 필수 지출과 조정 가능한 지출로 나누고, 대출 상환액과 예정된 큰 지출을 함께 점검해 보세요.",
            "why": "매달 적자가 지속되면 비상자금이 줄거나 추가 차입이 필요해질 수 있습니다.",
        })
    elif c["surplus"] == 0:
        items.append({
            "level": "우선 점검", "title": "매달 남는 돈이 거의 없어요",
            "finding": "현재 입력값에서는 월 소득과 월 지출이 같습니다.",
            "evidence": f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])} = 0원",
            "action": "비정기 지출이 빠지지 않았는지 확인하고, 조정 가능한 지출을 찾아보세요.",
            "why": "예상하지 못한 지출이 생기면 곧바로 적자로 전환될 수 있습니다.",
        })
    else:
        items.append({
            "level": "유지·관리", "title": "월 잉여자금이 발생하고 있어요",
            "finding": f"입력값 기준으로 매달 {won(c['surplus'])}이 남습니다.",
            "evidence": f"월 소득 {won(c['income'])} − 월 지출 {won(c['outflow'])} = {won(c['surplus'])}",
            "action": "이 금액이 실제 저축액과 비슷한지 확인하고, 비정기 지출을 빠뜨렸다면 지출 항목에 추가하세요.",
            "why": "계산상 남는 돈과 실제로 통장에 남는 돈은 다를 수 있습니다.",
        })
    if c["runway"] is not None:
        if c["runway"] < 1:
            items.append({
                "level": "우선 점검", "title": "현금·예금 여력이 매우 짧아요",
                "finding": f"현금과 예금은 현재 월 지출의 약 {c['runway']:.1f}개월분입니다.",
                "evidence": f"현금·예금 {won(c['liquid'])} ÷ 월 지출 {won(c['outflow'])}",
                "action": "가까운 시기에 필요한 지출과 대출 상환 일정을 확인하고, 투자자산을 즉시 현금화할 수 있다고 가정하지 마세요.",
                "why": "주식이나 부동산 등은 원하는 시점에 손실 없이 현금화하기 어려울 수 있습니다.",
            })
        elif c["runway"] < 3:
            items.append({
                "level": "확인 권장", "title": "비상자금 목표를 점검해 보세요",
                "finding": f"현금과 예금은 현재 월 지출의 약 {c['runway']:.1f}개월분입니다.",
                "evidence": f"현금·예금 {won(c['liquid'])} ÷ 월 지출 {won(c['outflow'])}",
                "action": "고용 안정성, 가족 부양 여부, 예정된 큰 지출을 고려해 비상자금 목표를 정하세요. 3~6개월은 참고 범위이지 모든 사람에게 적용되는 정답은 아닙니다.",
                "why": "비상자금 필요 수준은 소득 안정성과 지출 구조에 따라 달라집니다.",
            })
        else:
            items.append({
                "level": "유지·관리", "title": "현금·예금 완충 여력을 확인했어요",
                "finding": f"현금과 예금은 현재 월 지출의 약 {c['runway']:.1f}개월분입니다.",
                "evidence": f"현금·예금 {won(c['liquid'])} ÷ 월 지출 {won(c['outflow'])}",
                "action": "이 금액에서 가까운 시기에 사용할 예정인 돈을 빼고도 여유가 있는지 확인하세요.",
                "why": "비상자금은 예정된 주거비·교육비 등 큰 지출과 별도로 생각하는 편이 좋습니다.",
            })
    if c["debt_ratio"] is not None and c["debt_ratio"] >= 60:
        items.append({
            "level": "확인 권장", "title": "자산에서 부채가 차지하는 비중이 높아요",
            "finding": f"총부채는 총자산의 {c['debt_ratio']:.1f}%입니다.",
            "evidence": f"총부채 {won(c['debts'])} ÷ 총자산 {won(c['assets'])}",
            "action": "대출별 금리, 만기, 상환 방식과 중도상환수수료를 정리해 상환 우선순위를 검토하세요.",
            "why": "부채 비율만으로 위험을 단정할 수 없고, 금리와 소득 대비 상환 부담을 함께 봐야 합니다.",
        })
    if c["repayment_ratio"] is not None and c["repayment_ratio"] >= 30:
        items.append({
            "level": "확인 권장", "title": "월 소득 중 대출 상환액을 살펴보세요",
            "finding": f"월 대출 상환액은 월 소득의 {c['repayment_ratio']:.1f}%입니다.",
            "evidence": f"월 대출 상환액 {won(c['debt_payment'])} ÷ 월 소득 {won(c['income'])}",
            "action": "모든 대출의 원금·이자 상환액을 빠짐없이 포함했는지 확인하고, 만기 일시상환 대출도 별도로 점검하세요.",
            "why": "이 지표는 간단한 참고 비율이며 금융기관의 공식 DSR 산정 결과가 아닙니다.",
        })
    if c["savings_rate"] is not None and c["savings_rate"] >= 20:
        items.append({
            "level": "기회", "title": "목표를 위한 저축 여력을 확인해 보세요",
            "finding": f"계산상 월 잉여자금은 월 소득의 {c['savings_rate']:.1f}%입니다.",
            "evidence": f"월 잉여자금 {won(c['surplus'])} ÷ 월 소득 {won(c['income'])}",
            "action": "비상자금과 단기 예정 지출을 먼저 고려한 뒤, 남는 금액 중 지속 가능한 저축액을 정하세요.",
            "why": "잉여자금 전부를 저축할 수 있다고 가정하면 비정기 지출 때문에 계획이 흔들릴 수 있습니다.",
        })
    if data.get("planned_expense", 0) > 0:
        planned = float(data["planned_expense"])
        liquid_after = c["liquid"] - planned
        items.append({
            "level": "예정 지출", "title": "앞으로 예정된 큰 지출이 있어요",
            "finding": f"{data.get('planned_expense_months', 6)}개월 안에 {won(planned)}을 사용할 계획입니다.",
            "evidence": f"현재 현금·예금 {won(c['liquid'])} − 예정 지출 {won(planned)} = {won(liquid_after)}",
            "action": "이 지출을 위해 이미 따로 확보한 돈이 있는지 확인하고, 없다면 월별로 준비할 금액을 계산해 보세요.",
            "why": "예정된 지출을 반영하지 않으면 비상자금이 실제보다 충분해 보일 수 있습니다.",
        })
    if data.get("leverage", 0) > 0:
        items.append({
            "level": "위험 이해", "title": "레버리지 ETF의 변동성을 별도로 확인하세요",
            "finding": f"주식·ETF 중 레버리지 ETF로 입력한 금액은 {won(data['leverage'])}입니다.",
            "evidence": f"주식·ETF 중 비중 {pct(c['leverage_ratio'])}",
            "action": "보유 목적, 투자 기간, 일일 수익률 배수 구조와 큰 폭의 하락을 감당할 수 있는지를 확인하세요.",
            "why": "레버리지 ETF는 장기 누적 수익률이 기초지수 수익률의 단순 배수와 달라질 수 있습니다.",
        })
    if not items:
        items.append({
            "level": "정보 확인", "title": "현재 입력값으로는 추가 진단이 제한적이에요",
            "finding": "소득, 지출, 자산 등 입력된 정보가 충분한지 확인해 주세요.",
            "evidence": "입력 항목이 비어 있거나 0이면 관련 지표를 계산할 수 없습니다.",
            "action": "정확한 계좌번호 같은 개인정보가 아니라 합계 금액을 입력하고 다시 계산해 보세요.",
            "why": "정보가 부족한 상태에서 단정적인 진단을 제공하지 않도록 했습니다.",
        })
    return items[:6]


def build_scenarios(data: dict, base: dict, income_change_pct: float,
                    expense_change: float, one_off_cost: float,
                    debt_payment_change: float) -> dict:
    """시나리오는 원본 데이터를 수정하지 않는 별도 계산."""
    new_income = base["income"] * (1 + income_change_pct / 100)
    new_outflow = max(0, base["outflow"] + expense_change + debt_payment_change)
    new_surplus = new_income - new_outflow
    new_liquid = base["liquid"] - one_off_cost
    months = None if new_outflow <= 0 else new_liquid / new_outflow
    new_net = base["net"] - one_off_cost
    return {
        "income": new_income, "outflow": new_outflow, "surplus": new_surplus,
        "liquid": new_liquid, "runway": months, "net": new_net,
        "income_change": new_income-base["income"],
        "surplus_change": new_surplus-base["surplus"],
    }


# ---------------------------- 사이드바 ----------------------------
st.sidebar.markdown('<div class="brand">💚 머니체크</div>', unsafe_allow_html=True)
st.sidebar.caption("내 돈을 이해하는 가장 쉬운 첫걸음")
page = st.sidebar.radio(
    "메뉴",
    ["홈", "내 재무현황", "목표와 실행계획"],
    label_visibility="visible",
)
st.sidebar.divider()
st.sidebar.caption("처음 사용하나요?")
st.sidebar.markdown("1. 홈에서 금액 입력\n2. 재무현황 확인\n3. 목표와 행동 정하기")
if st.sidebar.button("입력 정보 지우기", use_container_width=True):
    st.session_state.pop("moneycheck_data", None)
    st.session_state.pop("action_done", None)
    st.rerun()
st.sidebar.caption("개인정보 보호를 위해 계좌번호·주민등록번호·비밀번호는 입력하지 마세요.")

data = st.session_state.get("moneycheck_data")
has_data = isinstance(data, dict)
calc = calculate(data) if has_data else None

# ============================================================
# HOME: 입력 / 요약
# ============================================================
if page == "홈":
    hero("MONEY CHECK", "내 돈의 상태, 쉽게 확인해요.", "복잡한 금융 용어 대신 꼭 필요한 숫자와 다음 행동을 알려드릴게요.")
    st.markdown(
        '<div class="callout"><b>입력 안내</b><br>금액은 모두 <b>만원</b> 단위예요. '
        '예를 들어 500은 500만 원, 10000은 1억 원입니다. 모르는 항목은 0으로 두고, '
        '같은 자산을 두 번 입력하지 마세요.</div>',
        unsafe_allow_html=True,
    )
    if has_data:
        st.write("")
        st.markdown("#### 현재 저장된 요약")
        a, b, c = st.columns(3)
        a.metric("내 순자산", won(calc["net"]))
        b.metric("매달 남는 돈", won(calc["surplus"]))
        c.metric("현금·예금 여력", fmt_months(calc["runway"]))
        st.caption("아래 양식에 새 값을 입력하고 저장하면 기존 진단을 업데이트합니다.")
    else:
        st.write("")
        cols = st.columns(3)
        cards = [
            ("01 · 내 상황 입력", "자산·부채·월 소득과 지출을 입력해요."),
            ("02 · 한눈에 확인", "순자산과 현금흐름을 자동 계산해요."),
            ("03 · 다음 행동 찾기", "목표와 재무 변화 시나리오를 살펴봐요."),
        ]
        for col, (title, desc) in zip(cols, cards):
            with col:
                st.markdown(f'<div class="soft-card"><h4>{title}</h4><p>{desc}</p></div>', unsafe_allow_html=True)
    st.write("")
    section("내 재무정보", "순자산은 직접 입력하지 않아요. 자산과 부채를 바탕으로 자동 계산합니다.")
    with st.form("finance_input_form"):
        st.markdown("**먼저, 나의 상황**")
        p1, p2, p3 = st.columns(3)
        with p1:
            household = st.selectbox("가구 형태", ["1인 가구", "부부·2인 가구", "자녀가 있는 가구", "기타"], index=0 if not has_data else ["1인 가구","부부·2인 가구","자녀가 있는 가구","기타"].index(data.get("household","1인 가구")))
        with p2:
            life_stage = st.selectbox("현재 생활 단계", ["사회초년기", "가족 형성기", "자녀 양육기", "중장년기", "은퇴 전후", "기타"], index=0 if not has_data else ["사회초년기","가족 형성기","자녀 양육기","중장년기","은퇴 전후","기타"].index(data.get("life_stage","사회초년기")))
        with p3:
            goal = st.selectbox("가장 중요한 목표", GOALS, index=0 if not has_data else GOALS.index(data.get("goal", GOALS[0])))

        st.markdown("---")
        st.markdown("**1. 가지고 있는 돈과 자산**")
        st.caption("현재 기준의 대략적인 평가액을 입력하세요. 부동산은 대출을 빼기 전 금액입니다.")
        a1, a2 = st.columns(2)
        with a1:
            cash = st.number_input("현금·입출금 계좌 (만원)", min_value=0, value=int(data.get("cash",0)) if has_data else 0, step=10, key="in_cash")
            deposits = st.number_input("예금·적금 (만원)", min_value=0, value=int(data.get("deposits",0)) if has_data else 0, step=10, key="in_deposits")
            stocks = st.number_input("주식·ETF (만원)", min_value=0, value=int(data.get("stocks",0)) if has_data else 0, step=10, key="in_stocks")
        with a2:
            pension = st.number_input("연금계좌 (만원)", min_value=0, value=int(data.get("pension",0)) if has_data else 0, step=10, key="in_pension")
            property_value = st.number_input("부동산 현재 평가액 (만원)", min_value=0, value=int(data.get("property",0)) if has_data else 0, step=100, key="in_property")
            other_assets = st.number_input("기타 자산 (만원)", min_value=0, value=int(data.get("other_assets",0)) if has_data else 0, step=10, key="in_other_assets")
        with st.expander("자산을 어떻게 입력해야 하나요?"):
            st.markdown(
                "- **현금·입출금:** 바로 사용할 수 있는 현금과 입출금 계좌 잔액\n"
                "- **예금·적금:** 정기예금과 적금 잔액\n"
                "- **주식·ETF:** 일반 증권계좌에 보유한 주식·ETF 평가액\n"
                "- **연금계좌:** 연금저축·IRP 등 계좌의 평가액. 연금계좌 안의 ETF를 주식·ETF에도 중복 입력하지 마세요.\n"
                "- **부동산:** 대출을 차감하기 전 현재 평가액\n"
                "- **기타 자산:** 위 항목에 포함되지 않은 자산. 같은 자산을 두 번 더하지 마세요."
            )
        st.markdown("---")
        st.markdown("**2. 갚아야 할 돈**")
        st.caption("부채는 현재 남아 있는 잔액을 입력하세요. 월 상환액은 아래에서 따로 입력합니다.")
        d1, d2, d3 = st.columns(3)
        with d1:
            mortgage = st.number_input("주택담보대출 등 (만원)", min_value=0, value=int(data.get("mortgage",0)) if has_data else 0, step=100, key="in_mortgage")
        with d2:
            credit = st.number_input("신용대출·마이너스통장 (만원)", min_value=0, value=int(data.get("credit",0)) if has_data else 0, step=10, key="in_credit")
        with d3:
            other_debt = st.number_input("기타 부채 (만원)", min_value=0, value=int(data.get("other_debt",0)) if has_data else 0, step=10, key="in_other_debt")
        st.markdown("---")
        st.markdown("**3. 한 달에 들어오고 나가는 돈**")
        st.caption("월평균 금액을 입력하세요. 생활비에는 대출 상환액을 포함하지 마세요.")
        f1, f2, f3 = st.columns(3)
        with f1:
            income = st.number_input("월 세후 소득 (만원)", min_value=0, value=int(data.get("income",0)) if has_data else 0, step=10, key="in_income")
            other_income = st.number_input("기타 월 소득 (만원)", min_value=0, value=int(data.get("other_income",0)) if has_data else 0, step=10, key="in_other_income")
        with f2:
            living_cost = st.number_input("월 생활비·고정지출 (만원)", min_value=0, value=int(data.get("living_cost",0)) if has_data else 0, step=10, key="in_living")
            irregular_monthly = st.number_input("비정기 지출의 월 환산액 (만원)", min_value=0, value=int(data.get("irregular_monthly",0)) if has_data else 0, step=10, key="in_irregular")
        with f3:
            debt_payment = st.number_input("월 대출 상환액 (만원)", min_value=0, value=int(data.get("debt_payment",0)) if has_data else 0, step=10, key="in_debt_payment")
            leverage = st.number_input("주식·ETF 중 레버리지 ETF 금액 (만원)", min_value=0, value=int(data.get("leverage",0)) if has_data else 0, step=10, key="in_leverage")
        with st.expander("비정기 지출은 무엇인가요?"):
            st.write("매달 발생하지 않지만 연간으로 보면 반복되는 자동차 보험료, 명절 비용, 경조사비, 정기 건강검진, 가전 교체 등입니다. 연간 예상액을 12로 나눈 월평균 금액을 입력하면 월 현금흐름이 과대평가되는 것을 줄일 수 있어요.")
        st.markdown("---")
        st.markdown("**4. 앞으로 예정된 큰 지출과 목표**")
        q1, q2, q3 = st.columns(3)
        with q1:
            planned_expense = st.number_input("예정된 큰 지출 (만원)", min_value=0, value=int(data.get("planned_expense",0)) if has_data else 0, step=50, key="in_planned")
            planned_expense_months = st.number_input("지출까지 남은 개월", min_value=1, max_value=600, value=int(data.get("planned_expense_months",6)) if has_data else 6, step=1, key="in_planned_months")
        with q2:
            years = st.selectbox("목표까지 남은 기간", [1,2,3,5,7,10,15,20,30], index=2 if not has_data else ([1,2,3,5,7,10,15,20,30].index(data.get("years",3)) if data.get("years",3) in [1,2,3,5,7,10,15,20,30] else 2), format_func=lambda v:f"{v}년")
            target = st.number_input("목표에 필요한 총금액 (만원)", min_value=0, value=int(data.get("target",0)) if has_data else 0, step=100, key="in_target")
        with q3:
            already_saved = st.number_input("목표를 위해 이미 모은 금액 (만원)", min_value=0, value=int(data.get("already_saved",0)) if has_data else 0, step=10, key="in_saved")
            extra_monthly = st.number_input("현재 계획 중인 추가 월 저축액 (만원)", min_value=0, value=int(data.get("extra_monthly",0)) if has_data else 0, step=10, key="in_extra")
        st.caption("목표 금액은 선택 항목입니다. 입력하지 않으면 목표 달성 계산은 생략합니다.")
        submitted = st.form_submit_button("내 재무상태 진단하기", type="primary", use_container_width=True)
    if submitted:
        candidate = {
            "cash":cash, "deposits":deposits, "stocks":stocks, "pension":pension,
            "property":property_value, "other_assets":other_assets,
            "mortgage":mortgage, "credit":credit, "other_debt":other_debt,
            "income":income, "other_income":other_income, "living_cost":living_cost,
            "irregular_monthly":irregular_monthly, "debt_payment":debt_payment,
            "leverage":leverage, "planned_expense":planned_expense,
            "planned_expense_months":planned_expense_months, "goal":goal, "years":years,
            "target":target, "already_saved":already_saved, "extra_monthly":extra_monthly,
            "household":household, "life_stage":life_stage,
        }
        errors, warnings = validate_data(candidate)
        if errors:
            st.error("입력값을 저장하기 전에 아래 내용을 수정해 주세요.")
            for item in errors:
                st.error(item)
        else:
            st.session_state["moneycheck_data"] = candidate
            st.session_state["last_warnings"] = warnings
            st.success("재무정보를 저장하고 계산했어요.")
            for item in warnings:
                st.warning(item)
            result = calculate(candidate)
            st.markdown("#### 먼저 핵심 결과를 확인하세요")
            m1, m2, m3 = st.columns(3)
            m1.metric("총자산", won(result["assets"]))
            m2.metric("총부채", won(result["debts"]))
            m3.metric("내 순자산", won(result["net"]))
            st.caption(f"순자산 자동 계산: {won(result['assets'])} − {won(result['debts'])} = {won(result['net'])}")
            st.info("상세한 재무상태표와 현금흐름표는 왼쪽 ‘내 재무현황’ 메뉴에서, 시나리오 분석은 ‘목표와 실행계획’에서 확인할 수 있어요.")

# ============================================================
# FINANCIAL SNAPSHOT: balance sheet / cash flow / report
# ============================================================
if page == "내 재무현황":
    if not has_data:
        hero("MY SNAPSHOT", "먼저 내 상황을 알려주세요.", "자산과 부채를 입력하면 순자산과 월 현금흐름을 자동 계산합니다.")
        st.info("왼쪽 메뉴의 ‘홈’에서 재무정보를 입력해 주세요.")
    else:
        hero("MY SNAPSHOT", "내 재무현황", "먼저 핵심 숫자를 확인하고, 아래에서 계산 근거와 상세 구성을 볼 수 있어요.")
        m1, m2, m3 = st.columns(3)
        m1.metric("총자산", won(calc["assets"]))
        m2.metric("총부채", won(calc["debts"]))
        m3.metric("내 순자산", won(calc["net"]), help="순자산 = 총자산 − 총부채. 직접 입력하지 않습니다.")
        st.markdown(
            f'<div class="callout"><b>내 순자산 계산</b><br>{won(calc["assets"])} − {won(calc["debts"])} = <b>{won(calc["net"])}</b><br>'
            '<span class="tiny-note">순자산은 현재 입력한 자산 평가액에서 남은 부채를 뺀 값입니다. 자산의 실제 매각가격이나 세금·수수료를 반영한 금액은 아닙니다.</span></div>',
            unsafe_allow_html=True,
        )
        if calc["net"] < 0:
            st.warning("순자산이 음수입니다. 실제 상황일 수 있습니다. 우선 월 현금흐름과 대출 상환 조건을 함께 확인해 보세요.")
        st.write("")
        section("재무상태표", "현재 가진 자산과 갚아야 할 부채를 정리한 표입니다.")
        asset_rows = [{"구분":"자산","항목":label,"금액":data.get(key,0)} for key,label in ASSET_FIELDS.items()]
        debt_rows = [{"구분":"부채","항목":label,"금액":data.get(key,0)} for key,label in DEBT_FIELDS.items()]
        balance_rows = asset_rows + debt_rows + [
            {"구분":"합계","항목":"총자산","금액":calc["assets"]},
            {"구분":"합계","항목":"총부채","금액":calc["debts"]},
            {"구분":"합계","항목":"순자산(자동 계산)","금액":calc["net"]},
        ]
        balance_df = pd.DataFrame(balance_rows)
        balance_df["금액"] = balance_df["금액"].apply(won)
        st.dataframe(balance_df, use_container_width=True, hide_index=True)
        with st.expander("자산과 부채의 구성 보기"):
            x, y = st.columns(2)
            with x:
                st.markdown("**자산 구성**")
                asset_chart = pd.DataFrame({
                    "자산": [ASSET_FIELDS[k] for k in ASSET_FIELDS],
                    "금액(만원)": [data.get(k,0) for k in ASSET_FIELDS],
                })
                asset_chart = asset_chart[asset_chart["금액(만원)"] > 0].set_index("자산")
                if not asset_chart.empty:
                    st.bar_chart(asset_chart)
                else:
                    st.caption("입력된 자산이 없습니다.")
            with y:
                st.markdown("**부채 구성**")
                debt_chart = pd.DataFrame({
                    "부채": [DEBT_FIELDS[k] for k in DEBT_FIELDS],
                    "금액(만원)": [data.get(k,0) for k in DEBT_FIELDS],
                })
                debt_chart = debt_chart[debt_chart["금액(만원)"] > 0].set_index("부채")
                if not debt_chart.empty:
                    st.bar_chart(debt_chart)
                else:
                    st.caption("입력된 부채가 없습니다.")
        st.caption("재무상태표는 사용자가 입력한 현재 평가액 기준의 참고용 요약이며, 공인 회계보고서나 금융기관 제출용 자료가 아닙니다.")
        st.divider()
        section("현금흐름표", "매달 들어오는 돈과 나가는 돈을 비교해 실제로 남는 금액을 확인합니다.")
        f1, f2, f3 = st.columns(3)
        f1.metric("월 총소득", won(calc["income"]))
        f2.metric("월 총지출", won(calc["outflow"]))
        f3.metric("월 잉여자금", won(calc["surplus"]))
        flow_df = pd.DataFrame([
            {"구분":"수입","항목":"월 세후 소득 + 기타 월 소득","금액(만원)":calc["income"]},
            {"구분":"지출","항목":"생활비·고정지출","금액(만원)":calc["core_expenses"]},
            {"구분":"지출","항목":"대출 상환액","금액(만원)":calc["debt_payment"]},
            {"구분":"지출","항목":"비정기 지출 월 환산액","금액(만원)":calc["irregular_monthly"]},
            {"구분":"결과","항목":"월 잉여자금(자동 계산)","금액(만원)":calc["surplus"]},
        ])
        flow_view = flow_df.copy()
        flow_view["금액"] = flow_view["금액(만원)"].apply(won)
        st.dataframe(flow_view[["구분","항목","금액"]], use_container_width=True, hide_index=True)
        if calc["surplus"] < 0:
            st.error(f"입력값 기준으로 매달 {won(abs(calc['surplus']))}이 부족합니다. 생활비와 대출 상환액의 중복 여부, 비정기 지출, 소득 누락을 확인해 보세요.")
        elif calc["surplus"] == 0:
            st.warning("월 소득과 지출이 같아 계산상 남는 돈이 없습니다. 실제 저축액과 비정기 지출을 확인해 보세요.")
        else:
            st.success(f"입력값 기준으로 매달 {won(calc['surplus'])}이 남습니다. 실제 통장에 남는 금액과 비교해 보세요.")
        with st.expander("현금흐름을 그림으로 보기"):
            chart = pd.DataFrame({
                "항목":["월 총소득","월 총지출","월 잉여자금"],
                "금액(만원)":[calc["income"],calc["outflow"],calc["surplus"]],
            }).set_index("항목")
            st.bar_chart(chart)
        st.divider()
        section("쉬운 재무진단", "각 진단은 입력값에서 계산한 근거와 다음 행동을 함께 보여줍니다.")
        diagnosis = make_diagnosis(data, calc)
        st.markdown(f"**현재 확인할 항목: {len(diagnosis)}개**")
        for i, item in enumerate(diagnosis, start=1):
            with st.expander(f"{i}. {item['level']} · {item['title']}", expanded=(i == 1)):
                st.markdown(f"**무슨 뜻인가요?**  \n{item['finding']}")
                st.markdown(f"**계산 근거**  \n{item['evidence']}")
                st.markdown(f"**왜 확인해야 하나요?**  \n{item['why']}")
                st.markdown(f"**다음 행동**  \n{item['action']}")
        st.divider()
        section("파일로 저장", "아래 CSV에는 재무상태표, 현금흐름표, 주요 지표와 목표 계산값이 포함됩니다.")
        st.download_button(
            "재무 리포트 CSV 다운로드",
            data=make_csv(data, calc),
            file_name=f"머니체크_재무리포트_{date.today().isoformat()}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )
        st.caption("CSV의 금액은 만원 단위입니다. 순자산과 월 잉여자금은 앱에서 자동 계산한 값입니다.")

# ============================================================
# GOALS: goal planner / stress test / action checklist
# ============================================================
if page == "목표와 실행계획":
    if not has_data:
        hero("YOUR NEXT STEP", "목표를 세우기 전에", "먼저 내 재무정보를 입력하면 현재 상황에 맞는 계획을 비교할 수 있어요.")
        st.info("왼쪽 메뉴의 ‘홈’에서 재무정보를 입력해 주세요.")
    else:
        hero("YOUR NEXT STEP", "내 상황에 맞는 다음 행동", "목표 계산과 가상 상황을 비교해 보고, 이번 달에 할 행동을 정해 보세요.")
        section("1. 목표 역산 플래너", "목표 금액을 정한 뒤 필요한 월 저축액을 계산합니다. 투자수익률은 가정하지 않습니다.")
        if data["target"] > 0:
            goal_gap = max(0, data["target"] - data["already_saved"])
            required = goal_gap / calc["months_to_goal"]
            g1, g2, g3 = st.columns(3)
            g1.metric("목표 금액", won(data["target"]))
            g2.metric("이미 모은 금액", won(data["already_saved"]))
            g3.metric("앞으로 필요한 금액", won(goal_gap))
            st.markdown(f'<div class="callout">목표까지 {data["years"]}년이 남았다면, 수익률을 반영하지 않은 단순 계산상 매달 <b>{won(required)}</b>을 모아야 합니다.</div>', unsafe_allow_html=True)
            st.write("")
            max_slider = max(100, min(5000, int(max(calc["income"], data["target"] / max(1, calc["months_to_goal"]), 100))))
            initial_extra = min(max_slider, max(0, int(data.get("extra_monthly",0))))
            assumed_extra = st.slider("현재 월 잉여자금 외에 추가로 저축할 금액 (만원)", 0, max_slider, initial_extra, step=10, help="이 값은 가정일 뿐이며 실제 저축 가능 금액을 보장하지 않습니다.")
            available_monthly = calc["surplus"] + assumed_extra
            x, y = st.columns(2)
            x.metric("현재 계산상 월 잉여자금", won(calc["surplus"]))
            y.metric("가정 적용 후 월 저축 여력", won(available_monthly))
            if available_monthly <= 0:
                st.warning("현재 가정에서는 매달 저축할 수 있는 금액이 0 이하입니다. 저축 목표를 늘리기 전에 현금흐름을 먼저 점검하세요.")
            elif available_monthly >= required:
                st.success("단순 계산상 목표 기간에 필요한 금액을 충족할 수 있습니다. 비정기 지출과 비상자금은 별도로 고려하세요.")
            else:
                st.warning(f"목표 기간 내 달성하려면 월 저축액이 약 {won(required-available_monthly)} 더 필요합니다. 목표 금액이나 기간을 조정하는 선택지도 비교해 보세요.")
            if available_monthly > 0:
                months_needed = math.ceil(goal_gap / available_monthly)
                st.write(f"이 저축액을 유지한다면 목표 잔액까지 약 **{months_needed}개월**이 필요합니다.")
                st.progress(min(1.0, (available_monthly * calc["months_to_goal"]) / max(1, goal_gap)))
                st.caption("진행 막대는 목표 기간 동안 저축할 수 있는 금액과 남은 목표 금액을 비교한 값입니다. 투자수익률·세금·물가·수수료는 반영하지 않았습니다.")
        else:
            st.info("홈 화면에서 목표 금액을 입력하면 필요한 월 저축액과 목표 기간을 계산할 수 있어요.")
        st.divider()

        section("2. 재무 스트레스 테스트", "실제 재무정보는 바꾸지 않고, 가정한 변화가 결과에 미치는 영향만 계산합니다.")
        st.markdown("**어떤 상황을 시험해 볼까요?**")
        s1, s2 = st.columns(2)
        with s1:
            income_change_pct = st.slider("월 소득 변화", min_value=-80, max_value=50, value=0, step=5, format="%d%%", help="예: -20%는 월 소득이 현재보다 20% 줄어드는 가정입니다.")
            expense_change = st.slider("월 생활비 변화 (만원)", min_value=-100, max_value=200, value=0, step=10, help="음수는 지출 감소, 양수는 지출 증가입니다. 기존 월 지출에 더합니다.")
        with s2:
            debt_payment_change = st.slider("월 대출 상환액 변화 (만원)", min_value=-100, max_value=200, value=0, step=10, help="음수는 상환액 감소, 양수는 상환액 증가입니다. 실제 대출 조건 변경을 의미하지 않습니다.")
            one_off_cost = st.slider("한 번 발생하는 큰 지출 (만원)", min_value=0, max_value=5000, value=0, step=100, help="현금·예금과 순자산에서 차감하는 가정입니다. 새 부채로 충당한다고 가정하지 않습니다.")
        scenario = build_scenarios(data, calc, income_change_pct, expense_change, one_off_cost, debt_payment_change)
        st.markdown("#### 현재와 시나리오 비교")
        comp = pd.DataFrame([
            {"지표":"월 소득","현재":won(calc["income"]),"가정 후":won(scenario["income"])},
            {"지표":"월 지출","현재":won(calc["outflow"]),"가정 후":won(scenario["outflow"])},
            {"지표":"월 잉여자금","현재":won(calc["surplus"]),"가정 후":won(scenario["surplus"])},
            {"지표":"현금·예금","현재":won(calc["liquid"]),"가정 후":won(scenario["liquid"])},
            {"지표":"순자산","현재":won(calc["net"]),"가정 후":won(scenario["net"])},
            {"지표":"현금·예금 여력","현재":fmt_months(calc["runway"]),"가정 후":fmt_months(scenario["runway"])},
        ])
        st.dataframe(comp, use_container_width=True, hide_index=True)
        if scenario["surplus"] < 0:
            st.error(f"이 가정에서는 매달 {won(abs(scenario['surplus']))}이 부족합니다. 가정값을 바꾸며 적자 전환 지점을 확인해 보세요.")
        elif scenario["surplus"] < calc["surplus"]:
            st.warning(f"월 잉여자금이 {won(calc['surplus']-scenario['surplus'])} 줄어듭니다. 예정 지출과 비상자금에 미치는 영향을 확인하세요.")
        else:
            st.success("이 가정에서는 월 현금흐름이 현재보다 나빠지지 않습니다. 다른 상황도 시험해 볼 수 있어요.")
        if scenario["liquid"] < 0:
            st.warning("한 번 발생하는 큰 지출이 현재 현금·예금보다 큽니다. 실제로는 다른 자산 매각이나 차입 등 자금 조달 방법이 필요할 수 있습니다.")
        chart_df = pd.DataFrame({
            "항목":["현재 월 소득","가정 후 월 소득","현재 월 지출","가정 후 월 지출"],
            "금액(만원)":[calc["income"],scenario["income"],calc["outflow"],scenario["outflow"]],
        }).set_index("항목")
        with st.expander("비교 그래프 보기"):
            st.bar_chart(chart_df)
        st.caption("스트레스 테스트는 사용자가 설정한 가정의 산술적 결과입니다. 실제 미래를 예측하거나 발생 가능성을 추정하지 않습니다. 일회성 지출은 현금·예금 및 순자산에서 차감하고 새 부채는 가정하지 않습니다.")
        st.divider()

        section("3. 이번 달 행동 추천", "현재 계산에서 확인된 항목을 실제 행동으로 바꿔 보세요.")
        tasks = []
        if calc["surplus"] < 0:
            tasks.append(("먼저", "월 적자의 원인 구분하기", f"월 {won(abs(calc['surplus']))}이 부족합니다. 필수 생활비, 선택 지출, 대출 상환액, 비정기 지출을 나누어 확인하세요.", "cashflow"))
        elif calc["surplus"] == 0:
            tasks.append(("먼저", "비정기 지출과 누락된 지출 확인하기", "계산상 남는 돈이 없습니다. 연간 보험료·경조사비·수리비 등을 월평균으로 나누어 포함했는지 확인하세요.", "irregular"))
        else:
            tasks.append(("이번 달", "실제 저축액과 계산상 잉여자금 비교하기", f"계산상 월 {won(calc['surplus'])}이 남습니다. 지난 2~3개월의 실제 통장 잔액 변화와 비교해 보세요.", "saving"))
        if calc["runway"] is not None and calc["runway"] < 3:
            tasks.append(("우선", "비상자금 목표 정하기", "현재 현금·예금이 월 지출의 3개월분보다 적습니다. 3개월은 참고 기준이며 소득 안정성·가족 상황에 맞게 목표를 정하세요.", "emergency"))
        if calc["debts"] > 0:
            tasks.append(("점검", "대출 조건 한 장으로 정리하기", "대출별 잔액, 금리, 만기, 월 상환액, 중도상환수수료를 한곳에 정리하세요. 상환 순서는 금리뿐 아니라 계약 조건도 고려해야 합니다.", "debt"))
        if data["planned_expense"] > 0:
            tasks.append(("예정 지출", "큰 지출에 필요한 돈 따로 확보하기", f"{data['planned_expense_months']}개월 안에 {won(data['planned_expense'])}이 필요합니다. 이미 마련한 금액과 매달 추가로 준비할 금액을 확인하세요.", "planned"))
        if data["target"] > 0:
            tasks.append(("목표", "목표 저축액을 월 예산에 반영하기", f"현재 목표 기간에 필요한 월 저축액은 약 {won(calc['required_monthly'])}입니다. 지속 가능한 금액인지 확인하고 월 예산에 반영하세요.", "goal"))
        if not tasks:
            tasks.append(("매월", "재무정보를 월 1회 업데이트하기", "소득·지출·대출 잔액이 바뀌면 다시 계산하고, 이전 결과와 비교할 수 있도록 기록을 남기세요.", "update"))
        for i, (tag, title, description, key) in enumerate(tasks):
            task_key = f"action_{key}"
            with st.expander(f"{tag} · {title}", expanded=(i == 0)):
                st.write(description)
                done = st.checkbox("완료했어요", value=st.session_state.get(task_key, False), key=task_key)
                if done:
                    st.caption("완료로 표시했어요. 실제 재무정보를 바꿨다면 홈에서 최신 금액으로 다시 진단하세요.")
        st.divider()
        st.download_button(
            "목표·시나리오 결과 CSV 다운로드",
            data=pd.DataFrame([
                {"항목":"월 소득 변화 가정(%)","현재":0,"시나리오":income_change_pct},
                {"항목":"월 생활비 변화(만원)","현재":0,"시나리오":expense_change},
                {"항목":"월 대출 상환액 변화(만원)","현재":0,"시나리오":debt_payment_change},
                {"항목":"일회성 큰 지출(만원)","현재":0,"시나리오":one_off_cost},
                {"항목":"월 소득(만원)","현재":calc["income"],"시나리오":scenario["income"]},
                {"항목":"월 지출(만원)","현재":calc["outflow"],"시나리오":scenario["outflow"]},
                {"항목":"월 잉여자금(만원)","현재":calc["surplus"],"시나리오":scenario["surplus"]},
                {"항목":"현금·예금(만원)","현재":calc["liquid"],"시나리오":scenario["liquid"]},
                {"항목":"순자산(만원)","현재":calc["net"],"시나리오":scenario["net"]},
            ]).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"머니체크_시나리오_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ---------------------------- 공통 하단 안내 ----------------------------
st.divider()
with st.expander("계산 기준과 한계 확인하기"):
    st.markdown(
        """
        **계산 기준**
        - 총자산 = 현금·입출금 + 예금·적금 + 주식·ETF + 연금계좌 + 부동산 + 기타 자산
        - 총부채 = 주택담보대출 등 + 신용대출·마이너스통장 + 기타 부채
        - 순자산 = 총자산 − 총부채
        - 월 총소득 = 월 세후 소득 + 기타 월 소득
        - 월 총지출 = 월 생활비·고정지출 + 월 대출 상환액 + 비정기 지출 월 환산액
        - 월 잉여자금 = 월 총소득 − 월 총지출
        - 현금·예금 여력 = 현금·예금 ÷ 월 총지출

        **중요한 한계**
        - 이 앱은 입력값에 기반한 무료 규칙 기반 참고 도구이며, 외부 생성형 AI나 금융기관 계좌에 연결하지 않습니다.
        - 입력값이 틀리거나 자산이 중복 입력되면 결과도 달라집니다. 중복 여부를 완벽하게 자동 판별할 수는 없습니다.
        - 현금·예금 여력은 참고 지표입니다. 실제 비상자금 적정성은 고용 안정성, 부양가족, 보험, 예정 지출 등에 따라 달라집니다.
        - 월 대출 상환액/월 소득은 참고 비율이며, 금융기관의 공식 DSR 산정 방식과 다릅니다.
        - 투자 수익률, 세금, 보험 보장 분석, 연금 수령액, 부동산 거래비용, 물가 상승률은 반영하지 않습니다.
        - 목표 플래너와 스트레스 테스트는 가정값에 대한 단순 계산으로 목표 달성이나 미래 상황을 보장하지 않습니다.
        - 중요한 투자·대출·세금 결정 전에는 상품 약관과 최신 공식 정보를 확인하고 필요한 경우 전문가와 상담하세요.
        """
    )
st.caption("머니체크 · 사용자의 이해와 선택을 돕는 재무 점검 프로토타입")
