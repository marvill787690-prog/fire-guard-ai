import streamlit as st
import pandas as pd
from datetime import date

# =========================================================
# 머니체크 | 무료 가계 재무진단
# 외부 AI API 없이 작동하는 규칙 기반 재무설계 도구
# =========================================================

st.set_page_config(
    page_title="머니체크 | 가계 재무진단",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# 디자인
# -------------------------
st.markdown(
    """
    <style>
    .block-container {max-width: 1220px; padding-top: 1.5rem; padding-bottom: 3rem;}
    .hero {
        padding: 1.7rem 1.8rem; border-radius: 18px;
        background: linear-gradient(120deg, #10243b, #236779);
        color: white; margin-bottom: 1.2rem;
    }
    .hero h1 {color: white; margin: 0 0 .45rem 0; font-size: 2.2rem;}
    .hero p {color: #e7f1f5; margin: 0; font-size: 1.03rem;}
    .section-note {color: #64748b; font-size: .92rem;}
    div[data-testid="stMetric"] {
        background: rgba(120, 140, 160, .08);
        border: 1px solid rgba(120, 140, 160, .22);
        padding: 13px 15px; border-radius: 13px;
    }
    .tiny-note {font-size: .82rem; color: #64748b;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# 공통 함수
# -------------------------
def money(value):
    """입력 단위인 만 원을 읽기 쉬운 원화로 표시."""
    value = int(round(value or 0))
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 10000:
        eok = amount // 10000
        remainder = amount % 10000
        if remainder == 0:
            return f"{sign}{eok:,}억 원"
        return f"{sign}{eok:,}억 {remainder:,}만 원"
    return f"{sign}{amount:,}만 원"


def ratio(numerator, denominator):
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def pct(value):
    return "계산 불가" if value is None else f"{value * 100:.1f}%"


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def build_csv_bytes(data, totals):
    rows = [
        ("구분", "항목", "금액(만원)"),
        ("자산", "현금·입출금", data["cash"]),
        ("자산", "예금·적금", data["deposits"]),
        ("자산", "주식·ETF", data["stocks"]),
        ("자산", "연금계좌", data["pension_assets"]),
        ("자산", "부동산", data["real_estate"]),
        ("자산", "기타 자산", data["other_assets"]),
        ("부채", "주택담보대출 등", data["housing_debt"]),
        ("부채", "신용대출·마이너스통장", data["credit_debt"]),
        ("부채", "기타 부채", data["other_debt"]),
        ("합계", "총자산", totals["total_assets"]),
        ("합계", "총부채", totals["total_debt"]),
        ("합계", "순자산(자동 계산)", totals["net_worth"]),
        ("월 현금흐름", "월 세후 소득", data["monthly_income"]),
        ("월 현금흐름", "월 생활비·고정지출", data["monthly_expenses"]),
        ("월 현금흐름", "월 대출 상환액", data["monthly_debt_payment"]),
        ("월 현금흐름", "월 잉여자금(자동 계산)", totals["monthly_surplus"]),
    ]
    return pd.DataFrame(rows[1:], columns=rows[0]).to_csv(index=False).encode("utf-8-sig")


# -------------------------
# 사이드바 / 헤더
# -------------------------
st.sidebar.title("💰 머니체크")
st.sidebar.caption("내 돈의 현재 상태부터 다음 행동까지")
page = st.sidebar.radio(
    "메뉴",
    [
        "시작하기",
        "재무정보 입력",
        "한눈에 보는 재무상태",
        "현금흐름 분석",
        "목표 시뮬레이터",
        "실행 계획",
        "계산 기준·안내",
    ],
)
st.sidebar.divider()
st.sidebar.info(
    "무료 규칙 기반 도구\n\n"
    "외부 생성형 AI API를 호출하지 않습니다. 입력값은 현재 세션에서 분석하며, "
    "정확한 재무설계나 금융상품 추천을 대체하지 않습니다."
)

st.markdown(
    """
    <div class="hero">
      <h1>머니체크</h1>
      <p>복잡한 재무정보를 쉽게 정리하고, 지금 할 수 있는 다음 행동을 찾아보세요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("금액은 모두 만 원 단위로 입력합니다. 예: 500 = 500만 원 · 10000 = 1억 원")

# -------------------------
# 입력 폼
# -------------------------
if page == "시작하기":
    st.subheader("돈 관리, 어디서부터 시작할지 모르겠다면")
    st.write(
        "머니체크는 자산과 부채를 정리하고, 매월 돈이 얼마나 남는지 확인한 뒤, "
        "목표에 맞는 실행 계획을 세우도록 돕는 무료 재무진단 도구입니다."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 1. 내 상황 입력")
        st.write("자산·부채·월 소득과 지출을 입력합니다. 순자산은 직접 입력하지 않습니다.")
    with c2:
        st.markdown("### 2. 구조 파악")
        st.write("재무상태표와 현금흐름을 보고 돈이 어디에 묶여 있는지 확인합니다.")
    with c3:
        st.markdown("### 3. 행동 계획")
        st.write("비상자금, 부채 상환, 주택·결혼·은퇴 등 목표별 계획을 비교합니다.")
    st.warning(
        "개인 식별정보, 계좌번호, 주민등록번호, 로그인 정보는 입력하지 마세요. "
        "정확한 잔액을 모르면 추정치를 입력해도 됩니다."
    )
    st.info("시작하려면 왼쪽 메뉴에서 ‘재무정보 입력’을 선택하세요.")

if page == "재무정보 입력":
    st.header("1. 재무정보 입력")
    st.write("모르는 항목은 0으로 둘 수 있습니다. 0은 해당 항목이 없거나 이번 분석에서 제외한다는 의미입니다.")
    with st.form("finance_form", clear_on_submit=False):
        st.subheader("① 기본 상황")
        c1, c2 = st.columns(2)
        with c1:
            household = st.selectbox("가구 유형", ["1인 가구", "부부", "자녀가 있는 가구", "기타"])
            life_stage = st.selectbox(
                "현재 상황",
                ["사회초년생", "직장 생활 중", "결혼·주택 마련 준비", "자녀 양육 중", "은퇴 준비", "은퇴 후", "기타"],
            )
        with c2:
            goal = st.selectbox(
                "가장 중요한 재무 목표",
                ["비상자금 마련", "부채 상환", "결혼 자금 마련", "주택 마련", "자녀 교육비 마련",
                 "은퇴 준비", "경제적 독립(FIRE)", "자산 증식", "전반적인 재무 상태 점검"],
            )
            analysis_years = st.selectbox("목표 계획 기간", [1, 3, 5, 10, 20], index=2, format_func=lambda x: f"{x}년")

        st.divider()
        st.subheader("② 자산")
        st.caption("현재 평가액 기준으로 입력하세요. 같은 자산을 두 항목에 중복해서 넣지 마세요.")
        c1, c2, c3 = st.columns(3)
        with c1:
            cash = st.number_input("현금·입출금 계좌 (만원)", min_value=0, value=0, step=10)
            deposits = st.number_input("예금·적금 (만원)", min_value=0, value=0, step=10)
        with c2:
            stocks = st.number_input("주식·ETF 전체 (만원)", min_value=0, value=0, step=10)
            pension_assets = st.number_input("연금계좌 자산 (만원)", min_value=0, value=0, step=10)
        with c3:
            real_estate = st.number_input("부동산 현재 평가액 (만원)", min_value=0, value=0, step=100)
            other_assets = st.number_input("기타 자산 (만원)", min_value=0, value=0, step=10)
        st.info("연금계좌 금액을 주식·ETF 전체 금액에도 포함했다면 한쪽에서만 입력하세요. 부동산은 대출을 빼기 전의 현재 평가액으로 입력합니다.")

        st.divider()
        st.subheader("③ 부채")
        c1, c2, c3 = st.columns(3)
        with c1:
            housing_debt = st.number_input("주택담보대출 등 (만원)", min_value=0, value=0, step=100)
        with c2:
            credit_debt = st.number_input("신용대출·마이너스통장 (만원)", min_value=0, value=0, step=10)
        with c3:
            other_debt = st.number_input("기타 부채 (만원)", min_value=0, value=0, step=10)
        st.caption("부동산 대출은 자산에서 차감하지 말고, 부채 항목에 별도로 입력합니다.")

        st.divider()
        st.subheader("④ 월 소득과 지출")
        st.caption("월 소득은 세후 금액입니다. 생활비·고정지출에는 월 대출 상환액을 포함하지 마세요.")
        c1, c2, c3 = st.columns(3)
        with c1:
            monthly_income = st.number_input("월 세후 소득 (만원)", min_value=0, value=0, step=10)
        with c2:
            monthly_expenses = st.number_input("월 생활비·고정지출 (만원)", min_value=0, value=0, step=10)
        with c3:
            monthly_debt_payment = st.number_input("월 대출 상환액 (만원)", min_value=0, value=0, step=10)

        st.divider()
        st.subheader("⑤ 투자 위험·예정 지출")
        c1, c2 = st.columns(2)
        with c1:
            leveraged_etf = st.number_input(
                "레버리지 ETF 보유액 (만원)", min_value=0, value=0, step=10,
                help="주식·ETF 전체 금액에 포함된 금액입니다. 총자산에 따로 더하지 않습니다.",
            )
            upcoming_expense = st.number_input(
                "향후 12개월 내 큰 예정 지출 (만원)", min_value=0, value=0, step=10,
                help="예: 이사비, 등록금, 보증금 반환, 결혼비용 등",
            )
        with c2:
            goal_target = st.number_input("목표 달성에 필요한 총금액 (만원)", min_value=0, value=0, step=100)
            goal_current = st.number_input("해당 목표를 위해 이미 모은 금액 (만원)", min_value=0, value=0, step=10)

        extra_saving = st.number_input(
            "추가로 확보할 수 있는 월 저축액 (만원)", min_value=0, value=0, step=10,
            help="현재 계산된 월 잉여자금과 별개로 추가 절약·소득으로 확보할 수 있다고 가정하는 금액입니다.",
        )
        st.caption("추가 저축액은 가정입니다. 현재 월 잉여자금에 이미 포함된 돈을 다시 입력하지 마세요.")

        submitted = st.form_submit_button("입력값 검토 후 재무진단", type="primary", use_container_width=True)

    if submitted:
        errors = []
        warnings = []
        if leveraged_etf > stocks:
            errors.append("레버리지 ETF 보유액이 주식·ETF 전체 금액보다 큽니다. 중복 입력 여부를 확인하세요.")
        if goal_target == 0 and goal_current > 0:
            warnings.append("목표 총금액이 0인데 이미 모은 금액이 입력되어 있습니다. 목표 금액을 입력하거나 현재 모은 금액을 수정하세요.")
        if goal_target > 0 and goal_current > goal_target:
            errors.append("이미 모은 금액이 목표 총금액보다 큽니다. 두 금액을 확인하세요.")
        if monthly_income == 0 and (monthly_expenses > 0 or monthly_debt_payment > 0):
            warnings.append("월 소득이 0이고 지출이 입력되어 있습니다. 현재 소득 공백 기간인지 입력값이 맞는지 확인하세요.")
        if monthly_income > 0 and monthly_expenses + monthly_debt_payment > monthly_income * 3:
            warnings.append("월 지출과 상환액이 소득의 3배를 초과합니다. 입력 단위와 금액이 맞는지 확인하세요.")
        if total_assets_check := (cash + deposits + stocks + pension_assets + real_estate + other_assets):
            if housing_debt + credit_debt + other_debt > total_assets_check:
                warnings.append("총부채가 총자산보다 큽니다. 실제 상황일 수 있지만 자산·부채 입력값을 한 번 더 확인하세요.")
        if errors:
            st.error("입력값을 저장하기 전에 다음 항목을 수정해 주세요.")
            for item in errors:
                st.write(f"- {item}")
        else:
            st.session_state["finance_data"] = {
                "household": household, "life_stage": life_stage, "goal": goal, "analysis_years": analysis_years,
                "cash": cash, "deposits": deposits, "stocks": stocks, "pension_assets": pension_assets,
                "real_estate": real_estate, "other_assets": other_assets,
                "housing_debt": housing_debt, "credit_debt": credit_debt, "other_debt": other_debt,
                "monthly_income": monthly_income, "monthly_expenses": monthly_expenses,
                "monthly_debt_payment": monthly_debt_payment, "leveraged_etf": leveraged_etf,
                "upcoming_expense": upcoming_expense, "goal_target": goal_target, "goal_current": goal_current,
                "extra_saving": extra_saving,
            }
            st.session_state["diagnosis_ready"] = True
            st.success("입력값을 저장했습니다. 왼쪽 메뉴에서 ‘한눈에 보는 재무상태’를 확인하세요.")
            for item in warnings:
                st.warning(item)

# -------------------------
# 계산 공통부
# -------------------------
data = st.session_state.get("finance_data")
ready = bool(st.session_state.get("diagnosis_ready", False) and data)

if page not in ["시작하기", "재무정보 입력", "계산 기준·안내"] and not ready:
    st.warning("먼저 ‘재무정보 입력’ 메뉴에서 정보를 입력하고 재무진단을 시작해 주세요.")
    st.stop()

if ready:
    total_assets = sum(data[k] for k in ["cash", "deposits", "stocks", "pension_assets", "real_estate", "other_assets"])
    total_debt = sum(data[k] for k in ["housing_debt", "credit_debt", "other_debt"])
    net_worth = total_assets - total_debt  # 순자산은 항상 자동 계산
    liquid_assets = data["cash"] + data["deposits"]
    monthly_outflow = data["monthly_expenses"] + data["monthly_debt_payment"]
    monthly_surplus = data["monthly_income"] - monthly_outflow
    emergency_months = ratio(liquid_assets, monthly_outflow)
    debt_asset_ratio = ratio(total_debt, total_assets)
    repayment_income_ratio = ratio(data["monthly_debt_payment"], data["monthly_income"])
    leveraged_ratio = ratio(data["leveraged_etf"], total_assets)
    stock_ratio = ratio(data["stocks"], total_assets)
    goal_gap = max(0, data["goal_target"] - data["goal_current"])
    months = data["analysis_years"] * 12
    required_monthly_saving = goal_gap / months if months > 0 else 0
    planned_expense_gap = max(0, data["upcoming_expense"] - liquid_assets)
    totals = {
        "total_assets": total_assets, "total_debt": total_debt,
        "net_worth": net_worth, "monthly_surplus": monthly_surplus,
    }

# -------------------------
# 한눈에 보는 재무상태
# -------------------------
if page == "한눈에 보는 재무상태" and ready:
    st.header("한눈에 보는 재무상태")
    st.caption(f"{data['household']} · {data['life_stage']} · 주요 목표: {data['goal']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총자산", money(total_assets))
    c2.metric("총부채", money(total_debt))
    c3.metric("순자산", money(net_worth), help="순자산은 총자산에서 총부채를 뺀 값으로 자동 계산됩니다.")
    c4.metric("월 잉여자금", money(monthly_surplus))
    st.caption(f"계산 확인: {money(total_assets)} − {money(total_debt)} = {money(net_worth)}")
    st.divider()

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("재무상태표")
        balance_rows = [
            ("자산", "현금·입출금", data["cash"]),
            ("자산", "예금·적금", data["deposits"]),
            ("자산", "주식·ETF", data["stocks"]),
            ("자산", "연금계좌", data["pension_assets"]),
            ("자산", "부동산", data["real_estate"]),
            ("자산", "기타 자산", data["other_assets"]),
            ("부채", "주택담보대출 등", data["housing_debt"]),
            ("부채", "신용대출·마이너스통장", data["credit_debt"]),
            ("부채", "기타 부채", data["other_debt"]),
            ("합계", "총자산", total_assets),
            ("합계", "총부채", total_debt),
            ("합계", "순자산", net_worth),
        ]
        df_balance = pd.DataFrame(balance_rows, columns=["구분", "항목", "금액(만원)"])
        df_balance["표시 금액"] = df_balance["금액(만원)"].apply(money)
        st.dataframe(df_balance[["구분", "항목", "표시 금액"]], use_container_width=True, hide_index=True)
    with right:
        st.subheader("자산 구성")
        asset_values = {
            "현금·입출금": data["cash"], "예금·적금": data["deposits"],
            "주식·ETF": data["stocks"], "연금계좌": data["pension_assets"],
            "부동산": data["real_estate"], "기타 자산": data["other_assets"],
        }
        asset_df = pd.DataFrame({"항목": list(asset_values.keys()), "금액(만원)": list(asset_values.values())})
        asset_df = asset_df[asset_df["금액(만원)"] > 0].set_index("항목")
        if not asset_df.empty:
            st.bar_chart(asset_df, use_container_width=True)
        else:
            st.info("자산 금액을 입력하면 자산 구성 그래프가 표시됩니다.")
        st.subheader("부채 구성")
        debt_values = {
            "주택담보대출 등": data["housing_debt"],
            "신용대출·마이너스통장": data["credit_debt"],
            "기타 부채": data["other_debt"],
        }
        debt_df = pd.DataFrame({"항목": list(debt_values.keys()), "금액(만원)": list(debt_values.values())})
        debt_df = debt_df[debt_df["금액(만원)"] > 0].set_index("항목")
        if not debt_df.empty:
            st.bar_chart(debt_df, use_container_width=True)
        else:
            st.info("입력된 부채가 없습니다.")

    st.divider()
    st.subheader("핵심 지표 해석")
    c1, c2, c3 = st.columns(3)
    c1.metric("부채 / 총자산", pct(debt_asset_ratio))
    c2.metric("현금·예금", money(liquid_assets))
    c3.metric("월 지출 대비 유동자금", f"{emergency_months:.1f}개월" if emergency_months is not None else "계산 불가")
    if total_assets == 0:
        st.warning("총자산이 0으로 입력되어 자산 대비 부채 비율을 계산할 수 없습니다.")
    if net_worth < 0:
        st.error("순자산이 음수입니다. 실제 상황일 수 있으므로 부채 금리·만기·상환 여력을 우선 점검하세요.")
    if emergency_months is not None and emergency_months < 3:
        st.warning("현금·예금이 현재 월 지출의 3개월분보다 적습니다. 예정 지출과 소득 안정성을 함께 고려해 유동자금 목표를 검토하세요.")
    elif emergency_months is not None and emergency_months >= 6:
        st.success("현금·예금이 현재 월 지출의 6개월분 이상입니다. 다만 예정 지출이나 사용 제한이 있는 자금은 따로 고려하세요.")
    if data["leveraged_etf"] > 0:
        st.warning("레버리지 ETF는 손익 변동이 확대될 수 있습니다. 보유 기간의 누적 수익률이 기초지수 누적 수익률과 달라질 수 있으므로 상품 구조를 확인하세요.")

    st.download_button(
        "재무상태표 CSV 다운로드",
        data=build_csv_bytes(data, totals),
        file_name=f"머니체크_재무요약_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# -------------------------
# 현금흐름 분석
# -------------------------
if page == "현금흐름 분석" and ready:
    st.header("현금흐름 분석")
    st.write("한 달 동안 들어오는 돈과 나가는 돈을 비교합니다. 월 잉여자금은 입력한 소득과 지출로 자동 계산됩니다.")
    c1, c2, c3 = st.columns(3)
    c1.metric("월 세후 소득", money(data["monthly_income"]))
    c2.metric("월 총지출·상환", money(monthly_outflow))
    c3.metric("월 잉여자금", money(monthly_surplus))
    flow_df = pd.DataFrame(
        {
            "항목": ["월 세후 소득", "생활비·고정지출", "대출 상환액", "월 잉여자금"],
            "금액(만원)": [data["monthly_income"], data["monthly_expenses"], data["monthly_debt_payment"], monthly_surplus],
        }
    )
    st.subheader("월 현금흐름표")
    st.dataframe(
        pd.DataFrame({
            "항목": flow_df["항목"],
            "금액": flow_df["금액(만원)"].apply(money),
            "소득 대비 비중": [
                "100.0%" if data["monthly_income"] > 0 else "계산 불가",
                pct(ratio(data["monthly_expenses"], data["monthly_income"])),
                pct(ratio(data["monthly_debt_payment"], data["monthly_income"])),
                pct(ratio(monthly_surplus, data["monthly_income"])),
            ],
        }),
        use_container_width=True,
        hide_index=True,
    )
    chart_df = pd.DataFrame({
        "항목": ["생활비·고정지출", "대출 상환액", "월 잉여자금"],
        "금액(만원)": [data["monthly_expenses"], data["monthly_debt_payment"], max(0, monthly_surplus)],
    }).set_index("항목")
    st.subheader("월 지출과 잉여자금")
    st.bar_chart(chart_df, use_container_width=True)
    if data["monthly_income"] == 0:
        st.warning("월 소득이 0이므로 소득 대비 지출 비중을 계산할 수 없습니다. 소득 공백 기간이라면 향후 생활비를 마련할 자금 계획도 확인하세요.")
    elif monthly_surplus < 0:
        st.error(f"매월 {money(abs(monthly_surplus))}의 적자가 발생하는 구조입니다. 먼저 필수 지출·선택 지출·대출 상환 일정을 나누어 적자 원인을 확인하세요.")
    elif monthly_surplus == 0:
        st.warning("월 잉여자금이 없습니다. 비정기 지출이 생기면 보유 현금이 줄어들 수 있습니다.")
    else:
        st.success(f"현재 계산상 월 잉여자금은 {money(monthly_surplus)}입니다. 이 금액이 실제로 저축 가능한 금액인지 확인하세요.")
    if repayment_income_ratio is not None:
        st.write(f"**월 대출 상환액 / 월 세후 소득:** {pct(repayment_income_ratio)}")
        st.caption("이 지표는 현금흐름 참고용이며 금융기관의 공식 DSR 산식이나 대출 심사 결과가 아닙니다.")
    st.info("이 버전은 월평균 입력값을 사용합니다. 상여금, 계절성 지출, 카드 결제 시차, 세금 환급 등 비정기 현금흐름은 자동 반영하지 않습니다.")

# -------------------------
# 목표 시뮬레이터
# -------------------------
if page == "목표 시뮬레이터" and ready:
    st.header("목표 시뮬레이터")
    st.write(f"선택한 주요 목표: **{data['goal']}**")
    st.caption("수익률을 가정하지 않는 단순 저축 시뮬레이션입니다. 실제 목표 달성 여부를 보장하지 않습니다.")
    if data["goal_target"] <= 0:
        st.info("목표 총금액이 입력되지 않았습니다. ‘재무정보 입력’에서 목표 금액을 입력하면 계산할 수 있습니다.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("목표 금액", money(data["goal_target"]))
        c2.metric("이미 모은 금액", money(data["goal_current"]))
        c3.metric("남은 금액", money(goal_gap))
        st.write(f"설정 기간: **{data['analysis_years']}년 ({months}개월)**")
        st.write(f"목표를 위해 필요한 월평균 저축액: **{money(required_monthly_saving)}**")
        scenario_extra = st.slider(
            "추가로 줄일 지출 또는 늘릴 소득 (월, 만원)",
            min_value=0, max_value= max(100, min(500, int(max(0, data['monthly_income']) or 100))),
            value=min(int(data["extra_saving"]), max(100, min(500, int(max(0, data['monthly_income']) or 100)))),
            step=10,
        )
        scenario_monthly = monthly_surplus + scenario_extra
        if scenario_monthly > 0:
            months_needed = int((goal_gap + scenario_monthly - 1) // scenario_monthly)
        else:
            months_needed = None
        c1, c2 = st.columns(2)
        c1.metric("현재 월 잉여자금", money(monthly_surplus))
        c2.metric("시나리오 적용 후 월 잉여자금", money(scenario_monthly), delta=money(scenario_extra))
        if scenario_monthly >= required_monthly_saving and scenario_monthly >= 0:
            st.success("단순 계산상 설정 기간에 필요한 저축액을 충족합니다. 실제로 매월 유지 가능한지, 예정 지출을 반영했는지 확인하세요.")
        else:
            st.warning("현재 가정으로는 목표 기간 내 필요한 저축액을 충족하기 어렵습니다. 기간 연장, 목표 조정, 지출 재검토를 비교해 보세요.")
        if months_needed is not None:
            st.write(f"목표 잔액을 모으는 데 필요한 예상 기간: **약 {months_needed}개월** (수익률·물가·세금 미반영)")
        else:
            st.write("월 잉여자금이 0 이하이므로 현재 가정에서는 목표 달성 기간을 계산할 수 없습니다.")
        st.subheader("기간별 단순 저축 경로")
        if scenario_monthly > 0:
            timeline = []
            for m in range(0, months + 1, max(1, months // 12)):
                saved = min(data["goal_target"], data["goal_current"] + scenario_monthly * m)
                timeline.append({"개월": m, "누적 목표자금(만원)": saved})
            if timeline[-1]["개월"] != months:
                timeline.append({"개월": months, "누적 목표자금(만원)": min(data["goal_target"], data["goal_current"] + scenario_monthly * months)})
            st.line_chart(pd.DataFrame(timeline).set_index("개월"), use_container_width=True)
        else:
            st.info("월 잉여자금이 0 이하이므로 저축 경로 그래프를 표시하지 않습니다.")

# -------------------------
# 실행 계획
# -------------------------
if page == "실행 계획" and ready:
    st.header("실행 계획")
    st.write("아래 제안은 입력값을 바탕으로 한 점검 순서입니다. 모든 가구에 똑같이 적용되는 정답은 아닙니다.")
    priorities = []
    if monthly_surplus < 0:
        priorities.append(("높음", "월 현금흐름 적자 원인 파악", f"월 {money(abs(monthly_surplus))}의 적자가 계산됩니다. 필수 지출, 선택 지출, 대출 상환을 구분하고 단위가 맞는지 먼저 확인하세요."))
    if emergency_months is not None and emergency_months < 3:
        priorities.append(("높음", "유동자금 확보 검토", "현금·예금이 현재 월 지출의 3개월분보다 적습니다. 소득 안정성, 예정 지출, 사용 가능한 예금을 고려해 목표를 정하세요."))
    if planned_expense_gap > 0:
        priorities.append(("높음", "예정 지출 자금 마련", f"향후 12개월 내 큰 예정 지출이 현금·예금보다 {money(planned_expense_gap)} 많습니다. 지출 시점과 필요한 자금 조달 방법을 미리 정리하세요."))
    if data["leveraged_etf"] > 0:
        priorities.append(("점검", "레버리지 투자 위험 확인", "보유 목적, 손실 감내 수준, 상품의 일일 수익률 추종 구조와 보유 기간 위험을 확인하세요."))
    if total_debt > 0:
        priorities.append(("점검", "대출 조건 한곳에 정리", "대출별 잔액, 금리, 만기, 중도상환수수료, 월 상환액을 표로 정리하면 상환 우선순위를 검토하기 쉽습니다."))
    if not priorities:
        priorities.append(("기본", "정기 점검 루틴 만들기", "월 1회 실제 지출과 계획을 비교하고, 소득·가족 구성·주거 계획이 바뀌면 재진단하세요."))
    for i, (level, title, description) in enumerate(priorities, start=1):
        with st.expander(f"{i}. [{level}] {title}", expanded=(i == 1)):
            st.write(description)
            st.checkbox("이 항목을 확인했어요", key=f"task_done_{i}_{title}")
    st.divider()
    st.subheader("이번 달에 해볼 일")
    st.markdown(
        """
        - [ ] 자산·부채 잔액을 최근 기준으로 다시 확인하기
        - [ ] 지난달 실제 지출과 월평균 지출 비교하기
        - [ ] 향후 12개월의 큰 지출과 예정 시기 적어두기
        - [ ] 주요 목표의 진행 상황과 저축 가능액 점검하기
        """
    )
    st.caption("체크박스 상태는 현재 세션에서만 유지될 수 있습니다. 영구 저장 기능은 포함되어 있지 않습니다.")

# -------------------------
# 계산 기준·안내
# -------------------------
if page == "계산 기준·안내":
    st.header("계산 기준과 한계")
    st.subheader("자동 계산하는 항목")
    st.markdown(
        """
        - **총자산** = 현금 + 예금·적금 + 주식·ETF + 연금계좌 + 부동산 + 기타 자산
        - **총부채** = 주택담보대출 등 + 신용대출 등 + 기타 부채
        - **순자산** = 총자산 − 총부채 (직접 입력하지 않음)
        - **월 잉여자금** = 월 세후 소득 − 월 생활비·고정지출 − 월 대출 상환액
        - **유동자금 충당 개월 수** = (현금 + 예금·적금) ÷ (월 생활비·고정지출 + 월 대출 상환액)
        - **목표 필요 월 저축액** = max(0, 목표 총금액 − 이미 모은 금액) ÷ 목표까지 남은 개월 수
        - **부채 / 총자산** = 총부채 ÷ 총자산
        """
    )
    st.subheader("입력 오류를 줄이는 방법")
    st.markdown(
        """
        1. 모든 금액 입력 단위는 만 원입니다.
        2. 순자산은 입력란이 없으며 총자산과 총부채에서 자동 계산합니다.
        3. 부동산은 대출을 빼기 전의 평가액을 자산에 입력하고, 대출 잔액은 부채에 따로 입력합니다.
        4. 레버리지 ETF는 주식·ETF에 포함되는 금액이므로 자산에 중복 합산하지 않습니다.
        5. 연금계좌 자산을 주식·ETF 전체 금액에 포함했다면 중복 입력하지 않습니다.
        6. 월 생활비에는 월 대출 상환액을 포함하지 않습니다. 상환액은 별도 항목으로 입력합니다.
        7. 목표 금액과 이미 모은 금액의 관계가 맞지 않으면 저장 전에 오류를 표시합니다.
        """
    )
    st.subheader("현재 버전의 한계")
    st.markdown(
        """
        - 외부 생성형 AI를 호출하지 않는 **규칙 기반 프로토타입**입니다.
        - 공식 DSR, 신용평가, 세금, 보험 보장 분석, 연금 수령액, 투자수익률을 자동 산출하지 않습니다.
        - 목표 시뮬레이션은 수익률·물가·세금·수수료를 반영하지 않은 단순 저축 계산입니다.
        - 입력값이 부정확하면 결과도 부정확할 수 있습니다.
        - 이 앱은 특정 금융상품의 매수·매도를 권유하지 않습니다.
        """
    )
    st.info("개인 식별정보나 금융계정 로그인 정보는 입력하지 마세요. 실제 의사결정 전에는 계약서, 금융상품 설명서, 관련 세법과 전문가 안내를 확인하세요.")

# -------------------------
# 하단 안내
# -------------------------
st.divider()
st.caption(
    "머니체크 · 무료 규칙 기반 가계 재무진단 | "
    "입력값에 기반한 참고용 도구이며 전문 재무설계·세무·투자 자문을 대체하지 않습니다."
)
