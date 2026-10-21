
import streamlit as st

# =========================================================
# 머니체크 | 무료 가계 재무진단
# 외부 AI API 없이 작동하는 규칙 기반 프로토타입
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
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .hero {
        padding: 1.6rem;
        border-radius: 18px;
        background: linear-gradient(120deg, #142b4a, #286a83);
        color: white;
        margin-bottom: 1.2rem;
    }
    .hero h1 {
        color: white;
        margin-bottom: 0.4rem;
    }
    .hero p {
        color: #e6f1f7;
        margin-bottom: 0;
    }
    .small-note {
        color: #64748b;
        font-size: 0.88rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# 공통 함수
# -------------------------
def money(value):
    """만원 단위 숫자를 읽기 쉬운 원화 금액으로 표시."""
    value = int(round(value or 0))

    if abs(value) >= 10000:
        eok = abs(value) // 10000
        remainder = abs(value) % 10000
        sign = "-" if value < 0 else ""

        if remainder == 0:
            return f"{sign}{eok:,}억 원"

        return f"{sign}{eok:,}억 {remainder:,}만 원"

    return f"{value:,}만 원"


def safe_ratio(numerator, denominator):
    if denominator <= 0:
        return None
    return numerator / denominator


def ratio_text(value):
    if value is None:
        return "계산 불가"
    return f"{value * 100:.1f}%"


def metric_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)


# -------------------------
# 사이드바
# -------------------------
st.sidebar.title("머니체크")
st.sidebar.caption("나의 재무 상태를 이해하고 계획하기")

page = st.sidebar.radio(
    "메뉴",
    [
        "재무정보 입력",
        "종합 재무진단",
        "개선 실행계획",
        "계산 기준 안내",
    ],
)

st.sidebar.divider()
st.sidebar.info(
    "현재 버전은 외부 AI API를 사용하지 않는 "
    "무료 규칙 기반 재무진단 프로토타입입니다."
)

# -------------------------
# 메인 소개
# -------------------------
st.markdown(
    """
    <div class="hero">
        <h1>머니체크</h1>
        <p>사회초년생부터 다양한 가계까지, 나의 재무 상태를 확인하고
        목표에 맞는 계획을 세워 보세요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "입력 금액은 모두 만 원 단위입니다. "
    "예: 500 = 500만 원 / 10000 = 1억 원"
)

# =========================================================
# 1. 재무정보 입력
# =========================================================
if page == "재무정보 입력":
    st.header("1. 나의 재무정보")
    st.write(
        "정확한 금액을 모르면 가장 가까운 금액을 입력하거나 "
        "0으로 두고 분석에서 제외할 수 있습니다. "
        "0은 실제 금액이 없다는 뜻으로 처리됩니다."
    )

    with st.form("finance_form"):
        st.subheader("① 기본 정보")

        col1, col2 = st.columns(2)

        with col1:
            household = st.selectbox(
                "가구 유형",
                [
                    "1인 가구",
                    "부부",
                    "자녀가 있는 가구",
                    "기타",
                ],
            )

            life_stage = st.selectbox(
                "현재 상황",
                [
                    "사회초년생",
                    "직장 생활 중",
                    "결혼·주택 마련 준비",
                    "자녀 양육 중",
                    "은퇴 준비",
                    "은퇴 후",
                    "기타",
                ],
            )

        with col2:
            goal = st.selectbox(
                "가장 중요한 재무 목표",
                [
                    "비상자금 마련",
                    "부채 상환",
                    "결혼 자금 마련",
                    "주택 마련",
                    "자녀 교육비 마련",
                    "은퇴 준비",
                    "경제적 독립(FIRE)",
                    "자산 증식",
                    "전반적인 재무 상태 점검",
                ],
            )

            analysis_years = st.selectbox(
                "주요 계획 기간",
                [1, 3, 5, 10, 20],
                index=2,
                format_func=lambda x: f"{x}년",
            )

        st.divider()
        st.subheader("② 보유 자산")
        st.caption("각 항목의 현재 평가액을 만 원 단위로 입력하세요.")

        c1, c2, c3 = st.columns(3)

        with c1:
            cash = st.number_input(
                "현금·입출금 계좌 (만원)",
                min_value=0,
                value=0,
                step=100,
            )
            deposits = st.number_input(
                "예금·적금 (만원)",
                min_value=0,
                value=0,
                step=100,
            )

        with c2:
            stocks = st.number_input(
                "주식·ETF 전체 (만원)",
                min_value=0,
                value=0,
                step=100,
            )
            pension_assets = st.number_input(
                "연금계좌 자산 (만원)",
                min_value=0,
                value=0,
                step=100,
            )

        with c3:
            real_estate = st.number_input(
                "부동산 (만원)",
                min_value=0,
                value=0,
                step=1000,
            )
            other_assets = st.number_input(
                "기타 자산 (만원)",
                min_value=0,
                value=0,
                step=100,
            )

        st.caption(
            "주의: 연금계좌를 주식·ETF 전체 금액에 포함했다면 "
            "중복 입력하지 마세요. 부동산은 현재 평가액을 입력하세요."
        )

        st.divider()
        st.subheader("③ 부채")

        c1, c2, c3 = st.columns(3)

        with c1:
            housing_debt = st.number_input(
                "주택담보대출 등 (만원)",
                min_value=0,
                value=0,
                step=1000,
            )

        with c2:
            credit_debt = st.number_input(
                "신용대출·마이너스통장 (만원)",
                min_value=0,
                value=0,
                step=100,
            )

        with c3:
            other_debt = st.number_input(
                "기타 부채 (만원)",
                min_value=0,
                value=0,
                step=100,
            )

        st.divider()
        st.subheader("④ 월 소득과 지출")
        st.caption(
            "월 소득은 세후 기준, 생활비는 대출 상환액을 제외한 "
            "기준으로 입력하세요."
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            monthly_income = st.number_input(
                "월 세후 소득 (만원)",
                min_value=0,
                value=0,
                step=10,
            )

        with c2:
            monthly_expenses = st.number_input(
                "월 생활비·고정지출 (만원)",
                min_value=0,
                value=0,
                step=10,
            )

        with c3:
            monthly_debt_payment = st.number_input(
                "월 대출 상환액 (만원)",
                min_value=0,
                value=0,
                step=10,
            )

        st.divider()
        st.subheader("⑤ 투자 위험과 예정 지출")

        c1, c2 = st.columns(2)

        with c1:
            leveraged_etf = st.number_input(
                "레버리지 ETF 보유액 (만원)",
                min_value=0,
                value=0,
                step=100,
                help="주식·ETF 전체 금액에 포함되는 금액입니다. "
                     "총자산에 별도로 더하지 않습니다.",
            )

            upcoming_expense = st.number_input(
                "향후 12개월 내 큰 예정 지출 (만원)",
                min_value=0,
                value=0,
                step=100,
                help="예: 이사비, 교육비, 보증금 반환, 수술비 등",
            )

        with c2:
            goal_target = st.number_input(
                "목표 달성에 필요한 총금액 (만원)",
                min_value=0,
                value=0,
                step=100,
                help="목표 금액을 모르는 경우 0으로 입력하세요.",
            )

            goal_current = st.number_input(
                "해당 목표를 위해 이미 모은 금액 (만원)",
                min_value=0,
                value=0,
                step=100,
            )

        st.divider()
        st.subheader("⑥ 개선 계획 시뮬레이션")

        extra_saving = st.number_input(
            "추가로 확보할 수 있는 월 저축액 (만원)",
            min_value=0,
            value=0,
            step=10,
            help="현재 월 잉여자금 외에 추가로 확보 가능한 금액입니다.",
        )

        st.caption(
            "이 입력값은 시뮬레이션을 위한 가정입니다. "
            "실제로 저축할 수 있는 금액만 입력하세요."
        )

        submitted = st.form_submit_button(
            "재무진단 시작",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        st.session_state["finance_data"] = {
            "household": household,
            "life_stage": life_stage,
            "goal": goal,
            "analysis_years": analysis_years,
            "cash": cash,
            "deposits": deposits,
            "stocks": stocks,
            "pension_assets": pension_assets,
            "real_estate": real_estate,
            "other_assets": other_assets,
            "housing_debt": housing_debt,
            "credit_debt": credit_debt,
            "other_debt": other_debt,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "monthly_debt_payment": monthly_debt_payment,
            "leveraged_etf": leveraged_etf,
            "upcoming_expense": upcoming_expense,
            "goal_target": goal_target,
            "goal_current": goal_current,
            "extra_saving": extra_saving,
        }
        st.session_state["diagnosis_ready"] = True

        st.success(
            "입력이 완료되었습니다. 왼쪽 메뉴에서 "
            "'종합 재무진단'을 선택하세요."
        )

# =========================================================
# 2. 입력값 확인 및 계산
# =========================================================
data = st.session_state.get("finance_data")
ready = st.session_state.get("diagnosis_ready", False)

if page in ["종합 재무진단", "개선 실행계획"] and not ready:
    st.warning(
        "먼저 '재무정보 입력' 메뉴에서 정보를 입력하고 "
        "'재무진단 시작'을 눌러 주세요."
    )

if ready and data is not None:
    total_assets = (
        data["cash"]
        + data["deposits"]
        + data["stocks"]
        + data["pension_assets"]
        + data["real_estate"]
        + data["other_assets"]
    )

    total_debt = (
        data["housing_debt"]
        + data["credit_debt"]
        + data["other_debt"]
    )

    net_worth = total_assets - total_debt

    liquid_assets = data["cash"] + data["deposits"]

    monthly_surplus = (
        data["monthly_income"]
        - data["monthly_expenses"]
        - data["monthly_debt_payment"]
    )

    monthly_outflow = (
        data["monthly_expenses"]
        + data["monthly_debt_payment"]
    )

    emergency_months = safe_ratio(
        liquid_assets,
        monthly_outflow,
    )

    debt_asset_ratio = safe_ratio(
        total_debt,
        total_assets,
    )

    repayment_income_ratio = safe_ratio(
        data["monthly_debt_payment"],
        data["monthly_income"],
    )

    leveraged_ratio = safe_ratio(
        data["leveraged_etf"],
        total_assets,
    )

    stock_ratio = safe_ratio(
        data["stocks"],
        total_assets,
    )

    planned_expense_gap = max(
        0,
        data["upcoming_expense"] - liquid_assets,
    )

    goal_gap = max(
        0,
        data["goal_target"] - data["goal_current"],
    )

    years = data["analysis_years"]
    months = years * 12

    required_monthly_saving = (
        goal_gap / months if months > 0 else 0
    )

    # =====================================================
    # 3. 종합 재무진단
    # =====================================================
    if page == "종합 재무진단":
        st.header("나의 종합 재무진단")
        st.caption(
            f"{data['household']} · {data['life_stage']} · "
            f"주요 목표: {data['goal']}"
        )

        st.subheader("핵심 재무지표")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card("총자산", money(total_assets))

        with c2:
            metric_card("총부채", money(total_debt))

        with c3:
            metric_card("순자산", money(net_worth))

        with c4:
            metric_card("월 잉여자금", money(monthly_surplus))

        st.divider()
        st.subheader("현금흐름과 유동성")

        c1, c2, c3 = st.columns(3)

        with c1:
            metric_card(
                "현금·예금",
                money(liquid_assets),
            )

        with c2:
            metric_card(
                "월 지출 대비 유동자금",
                (
                    f"{emergency_months:.1f}개월"
                    if emergency_months is not None
                    else "계산 불가"
                ),
                help="현금·예금 ÷ (월 생활비 + 월 대출 상환액)",
            )

        with c3:
            metric_card(
                "부채 / 총자산",
                ratio_text(debt_asset_ratio),
            )

        st.subheader("진단 결과")

        if data["monthly_income"] == 0:
            st.warning(
                "월 소득이 0원으로 입력되어 현금흐름과 "
                "소득 대비 상환 부담을 충분히 분석할 수 없습니다."
            )
        elif monthly_surplus < 0:
            st.error(
                f"월 현금흐름 적자: 매월 "
                f"{money(abs(monthly_surplus))}만큼 지출이 "
                "소득을 초과합니다. 지출과 대출 상환 구조를 "
                "우선 점검하세요."
            )
        elif monthly_surplus == 0:
            st.warning(
                "월 잉여자금이 없습니다. 비정기 지출이 발생하면 "
                "보유 현금이 줄어들 수 있습니다."
            )
        else:
            st.success(
                f"현재 월 잉여자금은 {money(monthly_surplus)}입니다. "
                "이 금액이 실제 저축 가능액과 일치하는지 확인하세요."
            )

        if emergency_months is not None:
            if emergency_months < 3:
                st.warning(
                    "현금·예금이 현재 월 지출의 3개월분보다 적습니다. "
                    "가까운 예정 지출과 소득 중단 가능성을 고려해 "
                    "유동자금 확보 계획을 검토하세요."
                )
            elif emergency_months < 6:
                st.info(
                    "현금·예금이 월 지출의 3~6개월분입니다. "
                    "예정 지출과 소득 안정성을 고려해 적정 수준을 "
                    "검토하세요."
                )
            else:
                st.success(
                    "현금·예금이 월 지출의 6개월분 이상입니다. "
                    "다만 예정 지출이나 자금 사용 제약이 있다면 "
                    "실제로 활용 가능한 금액을 별도로 확인하세요."
                )
        else:
            st.info(
                "월 지출이 0원이므로 유동자금 충당 개월 수를 "
                "계산할 수 없습니다."
            )

        if total_assets > 0 and total_debt > total_assets:
            st.error(
                "총부채가 총자산보다 큽니다. 부채의 만기, 금리, "
                "상환 가능성을 우선 점검하세요."
            )

        if data["monthly_income"] > 0:
            if repayment_income_ratio is not None:
                st.write(
                    "**월 대출 상환액 / 월 세후 소득:** "
                    f"{ratio_text(repayment_income_ratio)}"
                )
                st.caption(
                    "이는 월 현금흐름 참고 지표이며, 금융기관의 "
                    "공식 DSR 산식이나 대출 심사 결과가 아닙니다."
                )

        st.divider()
        st.subheader("투자 위험 점검")

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "주식·ETF 비중",
                ratio_text(stock_ratio),
            )
            st.metric(
                "레버리지 ETF / 총자산",
                ratio_text(leveraged_ratio),
            )

        with c2:
            st.write("**투자 관련 참고 사항**")

            if data["leveraged_etf"] > data["stocks"]:
                st.error(
                    "레버리지 ETF 보유액이 주식·ETF 전체 금액보다 "
                    "큽니다. 입력값의 중복 여부를 확인하세요."
                )
            elif data["leveraged_etf"] > 0:
                st.warning(
                    "레버리지 ETF는 기초자산의 변동을 확대하며, "
                    "일일 수익률을 추종하는 상품은 보유 기간의 "
                    "누적 수익률이 기초지수 누적 수익률과 "
                    "달라질 수 있습니다."
                )
            else:
                st.info(
                    "레버리지 ETF 보유액이 0원으로 입력되었습니다. "
                    "다른 투자자산의 위험은 별도로 점검해야 합니다."
                )

            if (
                leveraged_ratio is not None
                and leveraged_ratio > 0.2
            ):
                st.warning(
                    "레버리지 ETF가 총자산의 20%를 초과합니다. "
                    "이 비율은 참고용 점검 기준이며, 개인별 "
                    "적정 투자 비중을 의미하지 않습니다."
                )

        st.divider()
        st.subheader("목표 달성 가능성 참고")

        if data["goal_target"] > 0:
            st.write(f"**선택 목표:** {data['goal']}")
            st.write(f"**목표 금액:** {money(data['goal_target'])}")
            st.write(f"**이미 마련한 금액:** {money(data['goal_current'])}")
            st.write(f"**남은 목표 금액:** {money(goal_gap)}")
            st.write(
                f"**{years}년 동안 필요한 월평균 저축액:** "
                f"{money(required_monthly_saving)}"
            )

            if monthly_surplus >= required_monthly_saving:
                st.success(
                    "현재 월 잉여자금만으로 계산하면 설정한 기간 내 "
                    "목표 금액을 마련할 수 있는 수준입니다. "
                    "수익률, 물가, 비정기 지출은 반영하지 않았습니다."
                )
            else:
                st.warning(
                    "현재 월 잉여자금만으로는 목표 기간 내 필요한 "
                    "저축액에 미치지 못할 수 있습니다. 목표 금액, "
                    "기간, 지출 구조를 다시 검토하세요."
                )
        else:
            st.info(
                "목표 금액을 입력하지 않아 목표 달성에 필요한 "
                "월 저축액을 계산하지 않았습니다."
            )

        st.caption(
            "본 결과는 입력값에 기초한 참고용 진단입니다. "
            "세금, 투자수익률, 물가, 보험 보장, 대출별 조건 및 "
            "모든 생애주기 변수를 반영한 전문 재무설계 결과는 아닙니다."
        )

    # =====================================================
    # 4. 개선 실행계획
    # =====================================================
    elif page == "개선 실행계획":
        st.header("우선순위별 개선 실행계획")
        st.write(
            "아래 항목은 입력한 수치에 따른 규칙 기반 제안입니다. "
            "실제 실행 전에는 계약 조건과 생활 여건을 확인하세요."
        )

        st.subheader("우선순위 1 · 먼저 확인할 사항")

        urgent_items = []

        if monthly_surplus < 0:
            urgent_items.append(
                (
                    "월 현금흐름 개선",
                    "월 지출과 대출 상환액이 월 소득을 초과합니다. "
                    "필수지출, 선택지출, 대출 상환 일정을 구분해 "
                    "적자 원인을 먼저 확인하세요."
                )
            )

        if (
            emergency_months is not None
            and emergency_months < 3
        ):
            urgent_items.append(
                (
                    "유동자금 확보",
                    "현재 현금·예금은 월 지출 3개월분보다 적습니다. "
                    "가까운 예정 지출과 소득 안정성을 고려해 "
                    "현금 확보 목표를 설정하세요."
                )
            )

        if planned_expense_gap > 0:
            urgent_items.append(
                (
                    "예정 지출 대비 자금 점검",
                    f"향후 12개월 내 예정 지출이 현금·예금보다 "
                    f"{money(planned_expense_gap)} 많습니다. "
                    "지출 시점, 필요한 자금, 조달 방법을 확인하세요."
                )
            )

        if data["leveraged_etf"] > data["stocks"]:
            urgent_items.append(
                (
                    "투자자산 입력 검토",
                    "레버리지 ETF 보유액이 주식·ETF 전체 금액보다 "
                    "큽니다. 중복 입력 또는 금액 오류를 수정하세요."
                )
            )

        if urgent_items:
            for title, description in urgent_items:
                with st.expander(title, expanded=True):
                    st.write(description)
        else:
            st.success(
                "입력값 기준으로 즉시 표시할 우선 경고가 없습니다. "
                "이것이 모든 재무 위험이 없다는 뜻은 아닙니다."
            )

        st.divider()
        st.subheader("우선순위 2 · 목표에 맞는 저축 계획")

        if data["goal_target"] > 0:
            st.write(f"목표: **{data['goal']}**")
            st.write(
                f"남은 목표 금액: **{money(goal_gap)}**"
            )
            st.write(
                f"설정 기간: **{years}년**"
            )
            st.write(
                f"필요 월 저축액: **{money(required_monthly_saving)}**"
            )

            scenario_surplus = monthly_surplus + data["extra_saving"]

            c1, c2 = st.columns(2)

            with c1:
                st.metric(
                    "현재 월 잉여자금",
                    money(monthly_surplus),
                )

            with c2:
                st.metric(
                    "추가 저축 가정 반영 후",
                    money(scenario_surplus),
                    delta=money(data["extra_saving"]),
                )

            if scenario_surplus >= required_monthly_saving:
                st.success(
                    "추가 저축 가정을 반영하면 설정한 기간에 필요한 "
                    "월 저축액을 충족합니다. 실제로 지속 가능한 "
                    "금액인지 확인하세요."
                )
            else:
                st.warning(
                    "추가 저축 가정을 반영해도 필요한 월 저축액에 "
                    "미치지 못합니다. 목표 기간 연장, 목표 금액 조정, "
                    "지출 재검토 등을 고려할 수 있습니다."
                )
        else:
            st.info(
                "목표 금액을 입력하면 필요한 월 저축액과 "
                "추가 저축 시나리오를 확인할 수 있습니다."
            )

        st.divider()
        st.subheader("우선순위 3 · 실행 일정")

        st.markdown(
            """
            **지금**
            - 입력한 자산·부채 잔액과 월 소득·지출 확인
            - 향후 12개월 내 큰 지출의 시기와 금액 정리
            - 월 잉여자금이 실제 저축 가능액과 일치하는지 점검

            **향후 3개월**
            - 비상자금 목표와 매월 저축액 설정
            - 대출 금리·만기·상환 조건 정리
            - 투자자산의 목적, 위험 수준, 집중도 확인

            **향후 1년**
            - 주요 재무 목표의 진행 상황 점검
            - 실제 지출과 계획의 차이 확인
            - 소득·가족 구성·주거 계획이 바뀌면 재진단
            """
        )

        st.caption(
            "위 일정은 일반적인 예시이며, 개인의 상황에 따라 "
            "순서와 기간을 조정해야 합니다."
        )

# =========================================================
# 5. 계산 기준 안내
# =========================================================
if page == "계산 기준 안내":
    st.header("계산 기준과 한계")

    st.subheader("주요 계산식")

    st.markdown(
        """
        - **총자산** = 현금 + 예금·적금 + 주식·ETF + 연금계좌
          자산 + 부동산 + 기타 자산
        - **총부채** = 주택담보대출 등 + 신용대출 등 + 기타 부채
        - **순자산** = 총자산 − 총부채
        - **월 잉여자금** = 월 세후 소득 − 월 생활비·고정지출
          − 월 대출 상환액
        - **유동자금 충당 개월 수** = (현금 + 예금·적금) ÷
          (월 생활비·고정지출 + 월 대출 상환액)
        - **부채 / 총자산** = 총부채 ÷ 총자산
        - **목표 필요 월 저축액** = (목표 금액 − 이미 마련한 금액)
          ÷ 목표까지 남은 개월 수
        """
    )

    st.divider()
    st.subheader("해석할 때 유의할 점")

    st.markdown(
        """
        1. 금액 입력 단위는 만 원이며, 표시할 때 읽기 쉬운 단위로 변환합니다.
        2. 현금·예금 충당 개월 수는 유동성 참고 지표입니다.
           모든 가구에 동일한 적정 개월 수가 적용되는 것은 아닙니다.
        3. 월 대출 상환액 / 월 세후 소득은 현금흐름 참고 지표입니다.
           공식 DSR과 동일하지 않습니다.
        4. 목표 저축액 계산은 투자수익률, 세금, 물가, 수수료를 반영하지 않습니다.
        5. 주식·ETF 보유액에 포함된 레버리지 ETF 금액은
           총자산에 중복 합산하지 않습니다.
        6. 보험 보장 적정성, 증여세, 상속세, 연금 세액공제 등은
           현재 버전에서 자동 판정하지 않습니다.
        7. 이 도구는 외부 생성형 AI를 호출하지 않는 규칙 기반 프로토타입입니다.
           'AI가 모든 상황을 이해해 내린 판단'으로 해석하면 안 됩니다.
        """
    )

    st.info(
        "정확한 재무설계를 위해서는 대출 계약, 세법, 보험 약관, "
        "투자상품 설명서 등 개별 조건을 별도로 확인해야 합니다."
    )

# -------------------------
# 하단 안내
# -------------------------
st.divider()
st.caption(
    "머니체크 · 무료 규칙 기반 재무진단 프로토타입 | "
    "입력값은 개인 재무상황을 이해하기 위한 참고자료이며, "
    "특정 금융상품의 매수·매도를 권유하지 않습니다."
)
