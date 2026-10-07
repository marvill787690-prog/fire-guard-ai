import streamlit as st

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="FIRE GUARD AI",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 FIRE GUARD AI")
st.subheader("영끌 FIRE 가계를 위한 재무진단 서비스")
st.write("자산이 많다고 재무적으로 안전한 것은 아닙니다.")

st.divider()

# --------------------------------------------------
# 사례 선택
# --------------------------------------------------
st.header("1. 재무정보 입력")

mode = st.radio(
    "입력 방법을 선택하세요.",
    ["공모전 사례 불러오기", "직접 입력하기"],
    horizontal=True
)

if mode == "공모전 사례 불러오기":

    st.info(
        "공모전 사례의 재무정보를 불러왔습니다. "
        "필요하면 직접 입력 모드에서 수정할 수 있습니다."
    )

    total_assets = 42.2
    total_debt = 16.5
    monthly_income = 840
    monthly_expense = 750

    cash_like = 0.5
    leveraged_etf = 4.5

    child_temporary = 1200
    home_repair = 1000
    deposit_return = 45000

else:

    col1, col2 = st.columns(2)

    with col1:
        total_assets = st.number_input(
            "총자산 (억원)",
            min_value=0.0,
            value=10.0,
            step=0.1
        )

        total_debt = st.number_input(
            "총부채 (억원)",
            min_value=0.0,
            value=3.0,
            step=0.1
        )

        monthly_income = st.number_input(
            "월소득 (만원)",
            min_value=0,
            value=500,
            step=10
        )

    with col2:
        monthly_expense = st.number_input(
            "월 정기지출 (만원)",
            min_value=0,
            value=400,
            step=10
        )

        cash_like = st.number_input(
            "현금성 자산 (억원)",
            min_value=0.0,
            value=1.0,
            step=0.1
        )

        leveraged_etf = st.number_input(
            "레버리지 투자자산 (억원)",
            min_value=0.0,
            value=0.0,
            step=0.1
        )

    child_temporary = st.number_input(
        "자녀 관련 연간 한시적 지출 (만원)",
        min_value=0,
        value=0,
        step=100
    )

    home_repair = st.number_input(
        "주거 관련 연간 한시적 지출 (만원)",
        min_value=0,
        value=0,
        step=100
    )

    deposit_return = st.number_input(
        "향후 반환해야 할 보증금 등 유동성 필요액 (만원)",
        min_value=0,
        value=0,
        step=1000
    )


# --------------------------------------------------
# 재무지표 계산
# --------------------------------------------------

net_assets = total_assets - total_debt

if total_assets > 0:
    debt_ratio = total_debt / total_assets * 100
else:
    debt_ratio = 0

monthly_surplus = monthly_income - monthly_expense

if monthly_expense > 0:
    emergency_months = cash_like * 10000 / monthly_expense
else:
    emergency_months = 0

temporary_expense = child_temporary + home_repair


# --------------------------------------------------
# 재무진단
# --------------------------------------------------

st.divider()
st.header("2. 종합 재무진단")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "총자산",
        f"{total_assets:.1f}억원"
    )

with col2:
    st.metric(
        "총부채",
        f"{total_debt:.1f}억원"
    )

with col3:
    st.metric(
        "순자산",
        f"{net_assets:.1f}억원"
    )

with col4:
    st.metric(
        "부채/자산",
        f"{debt_ratio:.1f}%"
    )


col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "월소득",
        f"{monthly_income:,.0f}만원"
    )

with col2:
    st.metric(
        "월 정기지출",
        f"{monthly_expense:,.0f}만원"
    )

with col3:
    st.metric(
        "월 잉여자금",
        f"{monthly_surplus:,.0f}만원"
    )


# --------------------------------------------------
# 유동성 진단
# --------------------------------------------------

st.divider()
st.header("3. 유동성 및 현금흐름 진단")

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "비상자금 확보기간",
        f"{emergency_months:.1f}개월"
    )

    if emergency_months < 6:
        st.error("⚠️ 비상자금이 부족할 가능성이 있습니다.")
    elif emergency_months < 12:
        st.warning("⚠️ 기본적인 유동성은 있으나 추가 확보를 검토할 필요가 있습니다.")
    else:
        st.success("✅ 비교적 충분한 현금성 자산을 확보하고 있습니다.")

with col2:

    st.metric(
        "연간 한시적 지출",
        f"{temporary_expense:,.0f}만원"
    )

    st.write(
        "한시적 지출은 영구적인 생활비 증가와 구분하여 "
        "기간별로 관리해야 합니다."
    )


# --------------------------------------------------
# 투자위험 진단
# --------------------------------------------------

st.divider()
st.header("4. 투자위험 진단")

if leveraged_etf > 0:

    leverage_ratio = leveraged_etf / total_assets * 100

    st.metric(
        "레버리지 투자자산 비중",
        f"{leverage_ratio:.1f}%"
    )

    if leverage_ratio >= 10:
        st.error(
            "🚨 레버리지 투자 비중이 높은 편입니다. "
            "조기은퇴 목표와 현금흐름을 고려한 위험관리가 필요합니다."
        )
    else:
        st.warning(
            "⚠️ 레버리지 투자 비중을 지속적으로 모니터링하세요."
        )

else:

    st.success("✅ 입력된 레버리지 투자자산이 없습니다.")


# --------------------------------------------------
# 현금흐름 Timeline
# --------------------------------------------------

st.divider()
st.header("5. 기간별 현금흐름 분석")

st.write(
    "공모전 사례에서는 자녀 교육·주거비와 주택수리비가 "
    "일정 기간 발생하는 한시적 지출로 제시되었습니다."
)

years = ["현재", "1~2년", "3~4년", "5년 이후"]

if mode == "공모전 사례 불러오기":

    cashflows = [
        monthly_surplus * 12,
        monthly_surplus * 12 - 2200,
        monthly_surplus * 12 - 1200,
        monthly_surplus * 12
    ]

else:

    cashflows = [
        monthly_surplus * 12,
        monthly_surplus * 12 - temporary_expense,
        monthly_surplus * 12 - child_temporary,
        monthly_surplus * 12
    ]

for year, cashflow in zip(years, cashflows):

    if cashflow >= 0:
        st.success(
            f"**{year}** → 연간 현금흐름 잉여 "
            f"{cashflow:,.0f}만원"
        )
    else:
        st.error(
            f"**{year}** → 연간 현금흐름 부족 "
            f"{abs(cashflow):,.0f}만원"
        )


# --------------------------------------------------
# 보증금 반환 리스크
# --------------------------------------------------

st.divider()
st.header("6. 잠재적 대규모 유동성 수요")

if deposit_return > 0:

    st.warning(
        f"⚠️ 향후 최대 {deposit_return:,.0f}만원의 "
        "보증금 반환 등 대규모 유동성 수요가 발생할 수 있습니다."
    )

    st.write(
        "이 자금은 장기 투자자산과 분리하여 "
        "현금성 자산 또는 단기 금융상품으로 관리하는 방안을 검토해야 합니다."
    )

else:

    st.info("현재 입력된 대규모 유동성 수요가 없습니다.")


# --------------------------------------------------
# 리밸런싱 제안
# --------------------------------------------------

st.divider()
st.header("7. FIRE 포트폴리오 리밸런싱 제안")

if mode == "공모전 사례 불러오기":

    st.success("📌 공모전 사례 기반 제안")

    st.write(
        """
        **① 레버리지 ETF 일부 축소**

        레버리지 ETF 4.5억원 중 2억원을 매도하여
        포트폴리오의 위험을 낮추는 방안을 제안합니다.
        """
    )

    st.write(
        """
        **② 유동성 자산 확보**

        매도금액 중 1억원은 CMA·단기채권 등
        유동성이 높은 자산으로 배분합니다.
        """
    )

    st.write(
        """
        **③ 장기 투자자산 재배분**

        나머지 1억원은 배당성장형 ETF·채권 등으로
        분산하여 수익성과 위험의 균형을 검토합니다.
        """
    )

else:

    if leveraged_etf > 0:

        recommended_sell = leveraged_etf * 0.4

        st.write(
            f"현재 레버리지 투자자산 {leveraged_etf:.1f}억원 중 "
            f"약 {recommended_sell:.1f}억원을 축소하는 방안을 검토할 수 있습니다."
        )

    else:

        st.info(
            "레버리지 투자자산이 없어 별도의 레버리지 축소 제안을 하지 않습니다."
        )


# --------------------------------------------------
# Before / After
# --------------------------------------------------

st.divider()
st.header("8. Before → After")

if mode == "공모전 사례 불러오기":

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Before")

        st.write("• 레버리지 ETF 4.5억원")
        st.write("• 현금성 자산 0.5억원")
        st.write("• 월 잉여자금 90만원")
        st.write("• 투자위험 및 유동성 위험 존재")

    with col2:

        st.subheader("After")

        st.write("• 레버리지 ETF 2억원 축소")
        st.write("• 현금성 자산 확대")
        st.write("• 월 잉여자금 개선")
        st.write("• 포트폴리오 위험 분산")

else:

    st.info(
        "직접 입력 모드에서는 입력한 재무정보를 기준으로 "
        "현재 상태와 개선 방향을 확인할 수 있습니다."
    )


# --------------------------------------------------
# 6단계 재무설계 프로세스
# --------------------------------------------------

st.divider()
st.header("9. 6단계 재무설계 실행 로드맵")

steps = [
    ("STEP 1", "관계 정립", "고객의 목표와 우선순위를 확인"),
    ("STEP 2", "목표·자료 수집", "자산·부채·소득·지출·투자정보 수집"),
    ("STEP 3", "재무상태 분석", "유동성·부채·투자위험 분석"),
    ("STEP 4", "재무계획 수립", "현금흐름과 투자 포트폴리오 개선"),
    ("STEP 5", "실행", "리밸런싱 및 금융상품 실행"),
    ("STEP 6", "모니터링", "정기적으로 목표와 재무상태 재점검")
]

for step, title, description in steps:

    st.markdown(
        f"### {step} · {title}"
    )

    st.write(description)


# --------------------------------------------------
# 마무리
# --------------------------------------------------

st.divider()

st.success(
    "🔥 FIRE GUARD AI 재무진단이 완료되었습니다."
)

st.caption(
    "본 서비스는 교육·공모전용 재무진단 프로토타입이며 "
    "실제 금융상품 가입 및 투자 의사결정 전에는 추가적인 검토가 필요합니다."
)
