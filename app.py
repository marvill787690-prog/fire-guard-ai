import streamlit as st

# =========================================================
# FIRE GUARD AI
# AFPK 영 플래너 챌린지 2026
# 공모전용 재무진단 프로토타입
# =========================================================

st.set_page_config(
    page_title="FIRE GUARD AI",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# CSS
# ---------------------------------------------------------
st.markdown("""
<style>
    .main {
        background-color: #f7f8fa;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    .hero {
        padding: 30px;
        border-radius: 18px;
        background: linear-gradient(135deg, #111827 0%, #374151 100%);
        color: white;
        margin-bottom: 25px;
    }

    .hero h1 {
        font-size: 42px;
        margin-bottom: 8px;
    }

    .hero p {
        font-size: 18px;
        color: #e5e7eb;
    }

    .risk-card {
        padding: 20px;
        border-radius: 15px;
        background: white;
        border: 1px solid #e5e7eb;
        margin-bottom: 12px;
    }

    .section-title {
        font-size: 27px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .small-text {
        color: #6b7280;
        font-size: 14px;
    }

    .recommendation {
        padding: 18px;
        border-left: 5px solid #111827;
        background: white;
        border-radius: 10px;
        margin-bottom: 12px;
    }

    .footer {
        text-align: center;
        color: #6b7280;
        font-size: 13px;
        padding-top: 30px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Hero
# ---------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>🔥 FIRE GUARD AI</h1>
    <p>영끌 FIRE 가계를 위한 통합 재무진단 · 리밸런싱 · 실행관리</p>
    <p>자산이 많다고 재무적으로 안전한 것은 아닙니다.</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
st.sidebar.title("🔥 FIRE GUARD AI")
st.sidebar.caption("AFPK 영 플래너 챌린지 2026")

st.sidebar.divider()

mode = st.sidebar.radio(
    "재무정보 입력 방식",
    ["공모전 사례", "직접 입력"]
)

st.sidebar.divider()

st.sidebar.info(
    "본 서비스는 공모전용 재무설계 프로토타입입니다. "
    "계산 및 진단 결과는 입력값과 사전 정의된 규칙에 기반합니다."
)


# =========================================================
# INPUT
# =========================================================

if mode == "공모전 사례":

    total_assets = 42.2
    real_estate = 34.0
    financial_assets = 8.2

    total_debt = 16.5
    financial_debt = 6.0
    rental_deposit_debt = 10.5

    monthly_income = 840
    monthly_expense = 750

    cash_like = 0.5
    leveraged_etf = 4.5
    high_risk_other = 3.2

    temporary_child = 1200
    temporary_repair = 1000
    deposit_return = 45000

    insurance_gap = True
    gift_tax_risk = True

    report_case = True

else:

    st.sidebar.subheader("직접 입력")

    total_assets = st.sidebar.number_input(
        "총자산 (억원)", 0.0, 1000.0, 10.0, 0.1
    )

    real_estate = st.sidebar.number_input(
        "부동산 자산 (억원)", 0.0, 1000.0, 5.0, 0.1
    )

    financial_assets = max(total_assets - real_estate, 0)

    total_debt = st.sidebar.number_input(
        "총부채 (억원)", 0.0, 1000.0, 3.0, 0.1
    )

    financial_debt = st.sidebar.number_input(
        "금융부채 (억원)", 0.0, 1000.0, 2.0, 0.1
    )

    rental_deposit_debt = max(total_debt - financial_debt, 0)

    monthly_income = st.sidebar.number_input(
        "월소득 (만원)", 0, 100000, 500, 10
    )

    monthly_expense = st.sidebar.number_input(
        "월 정기지출 (만원)", 0, 100000, 400, 10
    )

    cash_like = st.sidebar.number_input(
        "현금성 자산 (억원)", 0.0, 1000.0, 1.0, 0.1
    )

    leveraged_etf = st.sidebar.number_input(
        "레버리지 투자자산 (억원)", 0.0, 1000.0, 0.0, 0.1
    )

    high_risk_other = st.sidebar.number_input(
        "기타 고위험 금융자산 (억원)", 0.0, 1000.0, 0.0, 0.1
    )

    temporary_child = st.sidebar.number_input(
        "자녀 관련 연간 한시적 지출 (만원)",
        0, 100000, 0, 100
    )

    temporary_repair = st.sidebar.number_input(
        "주거 관련 연간 한시적 지출 (만원)",
        0, 100000, 0, 100
    )

    deposit_return = st.sidebar.number_input(
        "향후 반환 필요 보증금 (만원)",
        0, 1000000, 0, 1000
    )

    insurance_gap = st.sidebar.checkbox(
        "보장성 보험 공백이 있음",
        False
    )

    gift_tax_risk = st.sidebar.checkbox(
        "증여·세무 검토 필요",
        False
    )

    report_case = False


# =========================================================
# CALCULATION
# =========================================================

net_assets = total_assets - total_debt

if total_assets > 0:
    debt_ratio = total_debt / total_assets * 100
    real_estate_ratio = real_estate / total_assets * 100
else:
    debt_ratio = 0
    real_estate_ratio = 0

monthly_surplus = monthly_income - monthly_expense
annual_surplus = monthly_surplus * 12

temporary_year1_2 = temporary_child + temporary_repair
temporary_year3_4 = temporary_child

if monthly_expense > 0:
    emergency_months = cash_like * 10000 / monthly_expense
else:
    emergency_months = 0

if total_assets > 0:
    leverage_ratio = leveraged_etf / total_assets * 100
    high_risk_ratio = (
        leveraged_etf + high_risk_other
    ) / total_assets * 100
else:
    leverage_ratio = 0
    high_risk_ratio = 0


# =========================================================
# RISK SCORE
# =========================================================

risk_score = 0
risk_reasons = []

# 유동성
if emergency_months < 6:
    risk_score += 25
    risk_reasons.append("현금성 자산 부족")
elif emergency_months < 12:
    risk_score += 15
    risk_reasons.append("유동성 보완 필요")
else:
    risk_score += 5

# 부채
if debt_ratio >= 40:
    risk_score += 20
    risk_reasons.append("높은 부채/자산 비율")
elif debt_ratio >= 30:
    risk_score += 12
    risk_reasons.append("부채 부담 모니터링 필요")
else:
    risk_score += 5

# 부동산 집중
if real_estate_ratio >= 75:
    risk_score += 20
    risk_reasons.append("부동산 자산 집중")
elif real_estate_ratio >= 60:
    risk_score += 12
    risk_reasons.append("부동산 집중도 관리 필요")
else:
    risk_score += 5

# 레버리지
if leverage_ratio >= 10:
    risk_score += 20
    risk_reasons.append("레버리지 투자 비중 높음")
elif leverage_ratio > 0:
    risk_score += 10
    risk_reasons.append("레버리지 투자 모니터링 필요")
else:
    risk_score += 3

# 보험
if insurance_gap:
    risk_score += 10
    risk_reasons.append("보장성 보험 공백")

risk_score = min(risk_score, 100)


if risk_score >= 70:
    risk_grade = "위험"
    risk_message = "유동성·투자·부채·보장 영역의 동시 관리가 필요합니다."
elif risk_score >= 50:
    risk_grade = "주의"
    risk_message = "일부 핵심 위험요인을 우선적으로 개선해야 합니다."
elif risk_score >= 30:
    risk_grade = "관찰"
    risk_message = "재무구조는 관리 가능하나 정기적인 점검이 필요합니다."
else:
    risk_grade = "안정"
    risk_message = "현재 지표 기준으로 상대적으로 안정적인 구조입니다."


# =========================================================
# TOP DASHBOARD
# =========================================================

st.markdown(
    '<div class="section-title">📊 종합 재무건강 대시보드</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "총자산",
        f"{total_assets:.1f}억"
    )

with c2:
    st.metric(
        "순자산",
        f"{net_assets:.1f}억"
    )

with c3:
    st.metric(
        "월 잉여자금",
        f"{monthly_surplus:,.0f}만원"
    )

with c4:
    st.metric(
        "재무위험 점수",
        f"{risk_score}/100",
        risk_grade
    )


# =========================================================
# SUMMARY
# =========================================================

st.divider()

c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("💧 유동성")
    st.metric(
        "비상자금",
        f"{emergency_months:.1f}개월"
    )

    if emergency_months < 6:
        st.error("위험")
    elif emergency_months < 12:
        st.warning("보완 필요")
    else:
        st.success("양호")


with c2:
    st.subheader("🏠 부동산 집중")
    st.metric(
        "부동산 비중",
        f"{real_estate_ratio:.1f}%"
    )

    if real_estate_ratio >= 75:
        st.error("집중도 높음")
    elif real_estate_ratio >= 60:
        st.warning("관리 필요")
    else:
        st.success("분산 양호")


with c3:
    st.subheader("📈 레버리지")
    st.metric(
        "레버리지 비중",
        f"{leverage_ratio:.1f}%"
    )

    if leverage_ratio >= 10:
        st.error("위험")
    elif leverage_ratio > 0:
        st.warning("모니터링")
    else:
        st.success("해당 없음")


# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 자산·부채",
    "💰 현금흐름",
    "📈 투자위험",
    "🔄 리밸런싱",
    "🎯 실행계획"
])


# =========================================================
# TAB 1
# =========================================================

with tab1:

    st.header("자산·부채 구조")

    c1, c2 = st.columns(2)

    with c1:

        st.subheader("자산 구성")

        asset_data = {
            "부동산": real_estate,
            "금융자산": financial_assets
        }

        st.bar_chart(asset_data)

        st.write(
            f"부동산 비중: **{real_estate_ratio:.1f}%**"
        )

    with c2:

        st.subheader("부채 구성")

        debt_data = {
            "금융부채": financial_debt,
            "임대보증금 등": rental_deposit_debt
        }

        st.bar_chart(debt_data)

        st.write(
            f"부채/자산 비율: **{debt_ratio:.1f}%**"
        )

    st.divider()

    st.subheader("재무구조 해석")

    if real_estate_ratio >= 75:
        st.warning(
            "총자산 중 부동산 비중이 높습니다. "
            "자산 규모 자체보다 실제 현금화 가능성과 부채 상환 구조를 함께 관리해야 합니다."
        )

    if debt_ratio >= 40:
        st.warning(
            "부채/자산 비율이 높습니다. "
            "조기은퇴 과정에서 현금흐름이 감소할 경우 부채상환 부담이 확대될 수 있습니다."
        )

    if real_estate_ratio < 75 and debt_ratio < 40:
        st.success(
            "현재 입력값 기준 자산과 부채 구조는 상대적으로 균형적입니다."
        )


# =========================================================
# TAB 2
# =========================================================

with tab2:

    st.header("📅 기간별 현금흐름 시뮬레이션")

    st.write(
        "한시적 지출은 영구적인 생활비 증가와 구분하여 "
        "기간별로 분석합니다."
    )

    year1 = annual_surplus - temporary_year1_2
    year2 = annual_surplus - temporary_year1_2
    year3 = annual_surplus - temporary_year3_4
    year4 = annual_surplus - temporary_year3_4
    year5 = annual_surplus

    cashflow_data = {
        "1년차": year1,
        "2년차": year2,
        "3년차": year3,
        "4년차": year4,
        "5년차": year5
    }

    st.bar_chart(cashflow_data)

    st.subheader("연도별 해석")

    years = [
        ("1년차", year1),
        ("2년차", year2),
        ("3년차", year3),
        ("4년차", year4),
        ("5년차 이후", year5)
    ]

    for year, value in years:

        if value >= 0:
            st.success(
                f"{year}: 연간 현금흐름 **+{value:,.0f}만원**"
            )
        else:
            st.error(
                f"{year}: 연간 현금흐름 **{value:,.0f}만원**"
            )

    st.divider()

    st.subheader("⚠️ 대규모 유동성 이벤트")

    if deposit_return > 0:

        st.error(
            f"최대 **{deposit_return:,.0f}만원**의 "
            "보증금 반환 등 우발적 자본지출 가능성이 있습니다."
        )

        st.write(
            "장기 투자자산과 별도로 유동성 확보 계획을 마련해야 합니다."
        )

    else:

        st.info("입력된 대규모 보증금 반환 수요가 없습니다.")


# =========================================================
# TAB 3
# =========================================================

with tab3:

    st.header("📈 투자위험 분석")

    c1, c2 = st.columns(2)

    with c1:

        st.subheader("금융자산 구성")

        investment_data = {
            "레버리지 ETF": leveraged_etf,
            "기타 고위험 자산": high_risk_other,
            "기타 금융자산": max(
                financial_assets -
                leveraged_etf -
                high_risk_other,
                0
            )
        }

        st.bar_chart(investment_data)

    with c2:

        st.subheader("위험자산 비중")

        st.metric(
            "레버리지 비중",
            f"{leverage_ratio:.1f}%"
        )

        st.metric(
            "고위험 금융자산 비중",
            f"{high_risk_ratio:.1f}%"
        )

        if leverage_ratio >= 10:
            st.error(
                "레버리지 투자 비중이 높습니다."
            )
        else:
            st.success(
                "레버리지 투자 비중이 상대적으로 낮습니다."
            )

    st.divider()

    st.subheader("🛡️ 위험관리 공백")

    if insurance_gap:
        st.error(
            "보장성 보험 공백이 발견되었습니다."
        )

        st.write(
            "조기은퇴 자산을 유지하는 것뿐 아니라 "
            "질병·사고 등 예상하지 못한 위험에 대한 보장자산을 함께 점검해야 합니다."
        )

    else:
        st.success(
            "입력값 기준 보장성 보험 공백이 없습니다."
        )

    if gift_tax_risk:
        st.warning(
            "증여·세무 검토가 필요한 항목이 있습니다."
        )

        st.write(
            "자녀 명의 자산 이전 등은 금융투자 판단과 별도로 "
            "세무 전문가 또는 관련 제도를 통한 확인이 필요합니다."
        )


# =========================================================
# TAB 4
# =========================================================

with tab4:

    st.header("🔄 포트폴리오 리밸런싱")

    if report_case:

        st.info(
            "공모전 사례의 재무상황을 기준으로 작성된 "
            "리밸런싱 시나리오입니다."
        )

        st.subheader("현재")

        current = {
            "레버리지 ETF": 4.5,
            "기타 위험자산": 3.2,
            "현금성 자산": 0.5
        }

        st.bar_chart(current)

        st.divider()

        st.subheader("제안 시나리오")

        st.markdown("""
        <div class="recommendation">
        <b>① 레버리지 ETF 2억원 축소</b><br>
        고위험 레버리지 자산의 일부를 축소하여
        포트폴리오 변동성을 낮춥니다.
        </div>

        <div class="recommendation">
        <b>② 1억원 → CMA·단기채권 등 유동성 자산</b><br>
        향후 교육비·주거비 및 예상하지 못한 현금수요에 대비합니다.
        </div>

        <div class="recommendation">
        <b>③ 1억원 → 배당성장형 ETF·채권 등</b><br>
        장기 투자자산을 분산하여 수익성과 위험의 균형을 추구합니다.
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.subheader("Before → After")

        c1, c2 = st.columns(2)

        with c1:

            st.markdown("### Before")

            st.write("레버리지 ETF: **4.5억원**")
            st.write("현금성 자산: **0.5억원**")
            st.write("레버리지 집중도가 높음")

        with c2:

            st.markdown("### After")

            st.write("레버리지 ETF: **2.5억원**")
            st.write("현금성 자산: **1.5억원**")
            st.write("위험자산 일부 축소 + 유동성 확대")

        st.caption(
            "※ After 값은 기존 현금성 자산 0.5억원에 "
            "리밸런싱으로 확보하는 1억원을 더한 단순 시나리오입니다."
        )

    else:

        if leveraged_etf > 0:

            recommended = leveraged_etf * 0.4

            st.warning(
                f"현재 레버리지 투자자산의 약 **{recommended:.1f}억원** "
                "축소를 검토할 수 있습니다."
            )

        else:

            st.success(
                "현재 입력값 기준 레버리지 투자자산이 없습니다."
            )

        st.write(
            "리밸런싱은 투자기간, 위험성향, 현금흐름, "
            "세금 및 목표를 함께 고려해야 합니다."
        )


# =========================================================
# TAB 5
# =========================================================

with tab5:

    st.header("🎯 FIRE 실행계획")

    st.subheader("재무위험 우선순위")

    if risk_reasons:

        for i, reason in enumerate(risk_reasons, 1):

            st.write(
                f"**{i}. {reason}**"
            )

    else:

        st.success(
            "현재 입력값에서 주요 위험요인이 발견되지 않았습니다."
        )

    st.divider()

    st.subheader("6단계 재무설계 로드맵")

    steps = [
        (
            "STEP 1",
            "관계 정립",
            "조기은퇴 목표와 가계의 우선순위를 확인합니다."
        ),
        (
            "STEP 2",
            "목표·자료 수집",
            "자산·부채·소득·지출·투자 및 위험관리 정보를 수집합니다."
        ),
        (
            "STEP 3",
            "재무상태 분석",
            "유동성·부채·투자위험·보장 및 세무 위험을 분석합니다."
        ),
        (
            "STEP 4",
            "재무계획 수립",
            "현금흐름과 포트폴리오를 목표에 맞게 조정합니다."
        ),
        (
            "STEP 5",
            "실행",
            "리밸런싱·유동성 확보·보장 보완 등을 실행합니다."
        ),
        (
            "STEP 6",
            "모니터링",
            "목표와 실제 재무상태를 정기적으로 재점검합니다."
        )
    ]

    for step, title, description in steps:

        st.markdown(f"### {step} · {title}")
        st.write(description)


# =========================================================
# FIRE READINESS
# =========================================================

st.divider()

st.header("🔥 FIRE 준비도")

if monthly_income > 0:

    savings_rate = monthly_surplus / monthly_income * 100

else:

    savings_rate = 0


c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "월 잉여율",
        f"{savings_rate:.1f}%"
    )

with c2:
    st.metric(
        "연간 정기 잉여",
        f"{annual_surplus:,.0f}만원"
    )

with c3:
    if emergency_months >= 12 and leverage_ratio < 10:
        fire_status = "준비 양호"
    elif emergency_months >= 6:
        fire_status = "보완 필요"
    else:
        fire_status = "위험"

    st.metric(
        "FIRE 준비상태",
        fire_status
    )


if savings_rate >= 20 and emergency_months >= 12:
    st.success(
        "현재 지표 기준으로 FIRE 준비 기반이 비교적 양호합니다."
    )
elif emergency_months < 6:
    st.error(
        "조기은퇴보다 먼저 유동성 확보를 우선 검토해야 합니다."
    )
else:
    st.warning(
        "조기은퇴 목표를 유지하되 유동성·투자위험을 함께 관리해야 합니다."
    )


# =========================================================
# AI / HUMAN JUDGMENT
# =========================================================

st.divider()

st.header("🧠 AI 활용 및 사람의 판단")

st.write(
    "이 프로토타입은 입력된 재무정보를 사전 정의된 규칙으로 "
    "계산·분류하고, 재무설계 단계에 맞는 개선 방향을 제시합니다."
)

c1, c2 = st.columns(2)

with c1:

    st.subheader("AI·자동화가 지원하는 영역")

    st.write("• 재무지표 자동 계산")
    st.write("• 위험요인 분류")
    st.write("• 기간별 현금흐름 시뮬레이션")
    st.write("• 포트폴리오 리밸런싱 시나리오")
    st.write("• 6단계 재무설계 구조화")

with c2:

    st.subheader("사람의 판단이 필요한 영역")

    st.write("• 고객 목표와 우선순위")
    st.write("• 한시적 지출과 영구적 지출의 구분")
    st.write("• 세무·법률 적용 여부")
    st.write("• 투자 위험의 실제 수용 가능성")
    st.write("• 최종 재무계획의 선택 및 실행")


# =========================================================
# DISCLAIMER
# =========================================================

st.divider()

st.markdown("""
<div class="footer">
본 서비스는 AFPK 영 플래너 챌린지 2026 공모전용
재무설계 프로토타입입니다.<br>
본 결과는 입력값과 사전 정의된 규칙에 따른 교육·분석용 결과이며,
실제 금융상품 가입·투자·세무 의사결정을 대신하지 않습니다.
</div>
""", unsafe_allow_html=True)
