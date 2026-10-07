
import streamlit as st

# =========================================================
# FIRE GUARD AI
# AFPK 영 플래너 챌린지 2026
# Rule-based financial planning prototype
# =========================================================

st.set_page_config(
    page_title="FIRE GUARD AI",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
    .main .block-container {
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }
    .hero {
        background: linear-gradient(135deg, #172033 0%, #26334d 100%);
        padding: 2.4rem 2.6rem;
        border-radius: 24px;
        color: white;
        margin-bottom: 1.6rem;
        box-shadow: 0 10px 35px rgba(20,30,50,.12);
    }
    .hero h1 {font-size: 2.7rem; margin-bottom: .4rem;}
    .hero p {font-size: 1.08rem; opacity: .92; margin: .35rem 0;}
    .section-title {
        font-size: 1.65rem;
        font-weight: 800;
        margin-top: 1.4rem;
        margin-bottom: .8rem;
    }
    .insight {
        padding: 1rem 1.15rem;
        border-radius: 14px;
        background: #f4f7fb;
        border: 1px solid #e5eaf2;
        margin: .45rem 0;
    }
    .good {
        padding: 1rem 1.15rem;
        border-radius: 14px;
        background: #eefaf2;
        border: 1px solid #ccebd7;
        color: #176b35;
        margin: .45rem 0;
    }
    .warn {
        padding: 1rem 1.15rem;
        border-radius: 14px;
        background: #fff8e8;
        border: 1px solid #f3dfaa;
        color: #7a5b00;
        margin: .45rem 0;
    }
    .danger {
        padding: 1rem 1.15rem;
        border-radius: 14px;
        background: #fff0f0;
        border: 1px solid #f0c8c8;
        color: #8a2525;
        margin: .45rem 0;
    }
    .small-note {
        color: #667085;
        font-size: .88rem;
    }
    .stage {
        border-left: 5px solid #364152;
        padding: .75rem 1rem;
        margin: .65rem 0;
        background: #f8fafc;
        border-radius: 0 12px 12px 0;
    }
    .tag {
        display: inline-block;
        padding: .25rem .65rem;
        border-radius: 999px;
        background: #eef2f7;
        margin-right: .3rem;
        font-size: .82rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------
def eok(v):
    return f"{v:,.2f}억"

def manwon(v):
    return f"{v:,.0f}만원"

def pct(v):
    return f"{v:.1f}%"

def score_color(score):
    if score >= 75:
        return "양호"
    if score >= 55:
        return "주의"
    return "개선 필요"

def health_score(debt_ratio, monthly_surplus, emergency_months, real_estate_ratio, leverage_ratio):
    score = 100
    score -= max(0, debt_ratio - 30) * 0.55
    score += min(15, max(0, monthly_surplus) / 20)
    score += min(18, emergency_months * 1.2)
    score -= max(0, real_estate_ratio - 50) * 0.25
    score -= leverage_ratio * 0.45
    return max(0, min(100, score))

def diagnosis_messages(debt_ratio, surplus, emergency_months, real_estate_ratio, leverage_ratio):
    msgs = []
    if emergency_months < 6:
        msgs.append(("danger", "유동성", f"비상자금이 약 {emergency_months:.1f}개월로 단기 충격에 취약할 수 있습니다."))
    elif emergency_months < 12:
        msgs.append(("warn", "유동성", f"비상자금은 약 {emergency_months:.1f}개월입니다. 단기 유동성 여유를 더 확보하는 것을 검토할 수 있습니다."))
    else:
        msgs.append(("good", "유동성", f"비상자금이 약 {emergency_months:.1f}개월로 비교적 충분합니다."))

    if debt_ratio >= 40:
        msgs.append(("danger", "부채", f"부채/자산 비율이 {debt_ratio:.1f}%입니다. 부채상환과 유동성 관리를 함께 살펴볼 필요가 있습니다."))
    elif debt_ratio >= 30:
        msgs.append(("warn", "부채", f"부채/자산 비율이 {debt_ratio:.1f}%입니다. 은퇴 전 부채구조 점검이 필요합니다."))
    else:
        msgs.append(("good", "부채", f"부채/자산 비율이 {debt_ratio:.1f}%로 상대적으로 낮은 편입니다."))

    if surplus <= 0:
        msgs.append(("danger", "현금흐름", "월 현금흐름이 적자이므로 구조적인 지출 조정이 우선입니다."))
    elif surplus < 100:
        msgs.append(("warn", "현금흐름", f"월 잉여자금은 {manwon(surplus)}입니다. 일시적 지출을 별도로 관리해야 합니다."))
    else:
        msgs.append(("good", "현금흐름", f"월 잉여자금은 {manwon(surplus)}로 저축·투자 여력이 있습니다."))

    if leverage_ratio > 10:
        msgs.append(("danger", "투자위험", f"레버리지 자산 비중이 {leverage_ratio:.1f}%입니다. 변동성 확대 가능성을 별도로 관리해야 합니다."))
    elif leverage_ratio > 0:
        msgs.append(("warn", "투자위험", f"레버리지 자산 비중이 {leverage_ratio:.1f}%입니다. 은퇴자금의 손실 가능성을 점검하세요."))
    else:
        msgs.append(("good", "투자위험", "입력된 레버리지 자산이 없습니다."))

    if real_estate_ratio > 70:
        msgs.append(("warn", "자산집중", f"부동산 비중이 {real_estate_ratio:.1f}%로 높습니다. 금융자산과의 균형을 검토할 수 있습니다."))
    else:
        msgs.append(("good", "자산집중", f"부동산 비중은 {real_estate_ratio:.1f}%입니다."))

    return msgs


# ---------- Case defaults from contest report ----------
CASE = {
    "total_assets": 42.2,
    "real_estate": 34.0,
    "financial_assets": 8.2,
    "debt": 16.5,
    "income": 840.0,
    "regular_expense": 750.0,
    "child_temp": 1200.0,       # annual, 4 years
    "repair_temp": 1000.0,      # annual, 2 years
    "deposit_need": 4.5,        # potential liquidity need within 1 year
    "leveraged_etf": 4.5,
    "cash_like": 0.5,
    "insurance": 0.0,
    "pension_annual": 900.0,
}

# ---------- Sidebar ----------
st.sidebar.markdown("## 🔥 FIRE GUARD AI")
st.sidebar.caption("AFPK 영 플래너 챌린지 2026")
st.sidebar.divider()

mode = st.sidebar.radio(
    "재무정보 입력 방식",
    ["공모전 사례", "직접 입력"],
    index=0,
)

st.sidebar.info(
    "본 서비스는 공모전용 재무설계 프로토타입입니다. "
    "계산·진단 결과는 입력값과 사전 정의된 규칙에 기반합니다."
)

if mode == "공모전 사례":
    total_assets = CASE["total_assets"]
    real_estate = CASE["real_estate"]
    financial_assets = CASE["financial_assets"]
    debt = CASE["debt"]
    income = CASE["income"]
    regular_expense = CASE["regular_expense"]
    child_temp = CASE["child_temp"]
    repair_temp = CASE["repair_temp"]
    deposit_need = CASE["deposit_need"]
    leveraged_etf = CASE["leveraged_etf"]
    cash_like = CASE["cash_like"]
else:
    st.sidebar.markdown("### 직접 입력")
    total_assets = st.sidebar.number_input("총자산 (억원)", min_value=0.0, value=10.0, step=0.1)
    real_estate = st.sidebar.number_input("부동산 자산 (억원)", min_value=0.0, value=5.0, step=0.1)
    financial_assets = st.sidebar.number_input(
        "금융자산 (억원)", min_value=0.0, value=max(0.0, total_assets-real_estate), step=0.1
    )
    debt = st.sidebar.number_input("총부채 (억원)", min_value=0.0, value=3.0, step=0.1)
    income = st.sidebar.number_input("월소득 (만원)", min_value=0.0, value=700.0, step=10.0)
    regular_expense = st.sidebar.number_input("월 정기지출 (만원)", min_value=0.0, value=550.0, step=10.0)
    child_temp = st.sidebar.number_input("자녀 한시적 연간지출 (만원)", min_value=0.0, value=600.0, step=100.0)
    repair_temp = st.sidebar.number_input("주택수선 한시적 연간지출 (만원)", min_value=0.0, value=300.0, step=100.0)
    deposit_need = st.sidebar.number_input("1년 내 잠재적 보증금 반환액 (억원)", min_value=0.0, value=0.0, step=0.5)
    leveraged_etf = st.sidebar.number_input("레버리지 ETF (억원)", min_value=0.0, value=0.0, step=0.1)
    cash_like = st.sidebar.number_input("현금·CMA·단기채 등 (억원)", min_value=0.0, value=1.0, step=0.1)

# ---------- Calculations ----------
net_assets = total_assets - debt
financial_assets = max(financial_assets, 0)
monthly_surplus = income - regular_expense
debt_ratio = (debt / total_assets * 100) if total_assets else 0
real_estate_ratio = (real_estate / total_assets * 100) if total_assets else 0
financial_ratio = (financial_assets / total_assets * 100) if total_assets else 0
leverage_ratio = (leveraged_etf / total_assets * 100) if total_assets else 0
emergency_months = (cash_like * 10000 / regular_expense) if regular_expense else 0
annual_surplus = monthly_surplus * 12
score = health_score(debt_ratio, monthly_surplus, emergency_months, real_estate_ratio, leverage_ratio)

# ---------- Hero ----------
st.markdown("""
<div class="hero">
    <h1>🔥 FIRE GUARD AI</h1>
    <p><b>영끌 FIRE 가계를 위한 통합 재무진단 · 리밸런싱 · 실행관리</b></p>
    <p>자산이 많다고 재무적으로 안전한 것은 아닙니다.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Top dashboard ----------
st.markdown('<div class="section-title">📊 종합 재무건강 대시보드</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("총자산", eok(total_assets))
c2.metric("총부채", eok(debt))
c3.metric("순자산", eok(net_assets))
c4.metric("월 잉여자금", manwon(monthly_surplus))
c5.metric("재무건강 점수", f"{score:.0f}/100", score_color(score))

st.caption("※ 건강점수는 공모전 시연을 위한 내부 규칙 기반 지표이며 실제 금융기관의 신용·위험평가 점수가 아닙니다.")

# ---------- Quick risk cards ----------
st.markdown('<div class="section-title">🔎 핵심 위험 신호</div>', unsafe_allow_html=True)
r1, r2, r3 = st.columns(3)

with r1:
    st.metric("비상자금", f"{emergency_months:.1f}개월")
    if emergency_months >= 12:
        st.success("유동성 양호")
    elif emergency_months >= 6:
        st.warning("유동성 보완 검토")
    else:
        st.error("유동성 부족")

with r2:
    st.metric("부동산 비중", pct(real_estate_ratio))
    if real_estate_ratio > 70:
        st.warning("자산집중 주의")
    else:
        st.success("집중도 관리 가능")

with r3:
    st.metric("레버리지 자산 비중", pct(leverage_ratio))
    if leverage_ratio > 10:
        st.error("레버리지 위험 높음")
    elif leverage_ratio > 0:
        st.warning("레버리지 점검 필요")
    else:
        st.success("입력된 레버리지 없음")

# ---------- Tabs ----------
tabs = st.tabs([
    "🏠 자산·부채",
    "💰 현금흐름",
    "📈 투자위험",
    "🔄 리밸런싱",
    "🎯 실행계획",
])

# ---------- Tab 1 ----------
with tabs[0]:
    st.markdown('<div class="section-title">자산·부채 구조</div>', unsafe_allow_html=True)

    a, b = st.columns(2)
    with a:
        st.subheader("자산 구성")
        asset_data = {
            "부동산": real_estate,
            "금융자산": financial_assets,
        }
        st.bar_chart(asset_data)
        st.metric("부동산 비중", pct(real_estate_ratio))
        st.metric("금융자산 비중", pct(financial_ratio))

    with b:
        st.subheader("부채 구조")
        st.bar_chart({"부채": debt, "순자산": max(net_assets, 0)})
        st.metric("부채/자산", pct(debt_ratio))

    st.markdown("### 재무구조 해석")
    for typ, title, msg in diagnosis_messages(
        debt_ratio, monthly_surplus, emergency_months, real_estate_ratio, leverage_ratio
    ):
        box = {"good": "good", "warn": "warn", "danger": "danger"}[typ]
        st.markdown(f'<div class="{box}"><b>{title}</b> · {msg}</div>', unsafe_allow_html=True)

# ---------- Tab 2 ----------
with tabs[1]:
    st.markdown('<div class="section-title">💰 기간별 현금흐름 분석</div>', unsafe_allow_html=True)

    st.write("핵심은 **영구적 지출과 한시적 지출을 구분하는 것**입니다.")

    years = ["현재~2년", "3~4년", "5년 이후"]
    temp_annual = [
        child_temp + repair_temp,
        child_temp,
        0,
    ]
    regular_annual = [regular_expense * 12] * 3
    annual_income = income * 12
    total_out = [regular_annual[i] + temp_annual[i] for i in range(3)]
    annual_net = [annual_income - x for x in total_out]

    rows = []
    for i, y in enumerate(years):
        rows.append({
            "기간": y,
            "연간소득(만원)": round(annual_income),
            "정기지출(만원)": round(regular_annual[i]),
            "한시적지출(만원)": round(temp_annual[i]),
            "총지출(만원)": round(total_out[i]),
            "연간 잉여/부족(만원)": round(annual_net[i]),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("한시적 지출의 소멸 효과")
    st.line_chart({
        "한시적 지출": temp_annual,
        "연간 잉여/부족": annual_net,
    })

    if deposit_need > 0:
        st.markdown(
            f'<div class="warn"><b>⚠ 1년 내 잠재적 유동성 수요:</b> '
            f'{eok(deposit_need)} · 정기지출과 별도로 자금계획을 세워야 하는 항목입니다.</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="insight"><b>해석 포인트</b><br>'
        '한시적 지출을 영구적인 적자로 간주하면 은퇴 가능성을 과도하게 낮게 평가할 수 있습니다. '
        '따라서 기간별 현금흐름을 분리해 보는 것이 중요합니다.</div>',
        unsafe_allow_html=True,
    )

# ---------- Tab 3 ----------
with tabs[2]:
    st.markdown('<div class="section-title">📈 투자위험 분석</div>', unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    p1.metric("금융자산", eok(financial_assets))
    p2.metric("레버리지 ETF", eok(leveraged_etf))
    p3.metric("레버리지 비중", pct(leverage_ratio))

    st.subheader("위험 진단")
    if leverage_ratio >= 10:
        st.error(
            "레버리지 자산 비중이 높습니다. FIRE 단계에서는 수익률뿐 아니라 "
            "급락 시 회복기간과 현금 필요시점의 충돌을 함께 고려해야 합니다."
        )
    elif leverage_ratio > 0:
        st.warning("레버리지 자산이 존재합니다. 은퇴 전후의 변동성 관리가 필요합니다.")
    else:
        st.success("입력된 레버리지 자산이 없습니다.")

    st.subheader("투자 판단 체크리스트")
    checks = [
        ("수익성", "기대수익률만으로 판단하지 않기"),
        ("위험", "레버리지·변동성·손실회복기간 확인"),
        ("유동성", "1년 내 필요한 현금과 투자자산 분리"),
        ("세금", "상품별 세제와 가입요건 확인"),
        ("승계", "가족 이전·증여 등 장기계획과 연결"),
    ]
    st.dataframe(
        [{"항목": a, "확인 내용": b} for a, b in checks],
        use_container_width=True,
        hide_index=True,
    )

# ---------- Tab 4 ----------
with tabs[3]:
    st.markdown('<div class="section-title">🔄 리밸런싱 시뮬레이션</div>', unsafe_allow_html=True)

    if mode == "공모전 사례":
        st.info("공모전 사례의 제안안을 자동으로 불러왔습니다.")
        sell = st.number_input("레버리지 ETF 매도액 (억원)", min_value=0.0, value=2.0, step=0.5)
        safe_add = st.number_input("CMA·단기채 배분액 (억원)", min_value=0.0, value=1.0, step=0.5)
        growth_add = st.number_input("배당성장 ETF·채권 배분액 (억원)", min_value=0.0, value=1.0, step=0.5)
    else:
        sell = st.number_input("레버리지 ETF 매도액 (억원)", min_value=0.0, value=0.0, step=0.5)
        safe_add = st.number_input("CMA·단기채 배분액 (억원)", min_value=0.0, value=0.0, step=0.5)
        growth_add = st.number_input("배당성장 ETF·채권 배분액 (억원)", min_value=0.0, value=0.0, step=0.5)

    after_leverage = max(0, leveraged_etf - sell)
    after_cash = cash_like + safe_add
    after_financial = financial_assets
    after_leverage_ratio = (after_leverage / total_assets * 100) if total_assets else 0
    after_emergency = (after_cash * 10000 / regular_expense) if regular_expense else 0

    before_after = [
        {
            "지표": "레버리지 자산",
            "현재": eok(leveraged_etf),
            "리밸런싱 후": eok(after_leverage),
        },
        {
            "지표": "레버리지 비중",
            "현재": pct(leverage_ratio),
            "리밸런싱 후": pct(after_leverage_ratio),
        },
        {
            "지표": "현금·단기자산",
            "현재": eok(cash_like),
            "리밸런싱 후": eok(after_cash),
        },
        {
            "지표": "비상자금",
            "현재": f"{emergency_months:.1f}개월",
            "리밸런싱 후": f"{after_emergency:.1f}개월",
        },
    ]
    st.dataframe(before_after, use_container_width=True, hide_index=True)

    if sell > 0:
        st.success(
            f"시뮬레이션상 레버리지 ETF {eok(sell)}을 축소하고, "
            f"현금성 자산 {eok(safe_add)}을 늘리는 구조입니다."
        )

    st.subheader("리밸런싱 논리")
    st.markdown(
        '<div class="insight">'
        '① 1년 내 필요한 유동성 확보 → '
        '② 레버리지 위험 축소 → '
        '③ 중장기 성장·현금흐름 자산으로 분산 → '
        '④ 실행 후 정기 모니터링'
        '</div>',
        unsafe_allow_html=True,
    )

    st.caption("※ 실제 상품 매매·세금·적합성 판단은 별도의 전문가 검토가 필요합니다.")

# ---------- Tab 5 ----------
with tabs[4]:
    st.markdown('<div class="section-title">🎯 6단계 재무설계 실행계획</div>', unsafe_allow_html=True)

    stages = [
        ("1단계 관계형성", "가계의 상황과 우선순위를 파악하고 재무설계의 범위를 설정합니다."),
        ("2단계 목표·자료수집", "자산·부채·소득·지출·투자·보험 등 핵심 재무자료를 정리합니다."),
        ("3단계 재무상태 분석", "유동성·부채·현금흐름·투자위험·자산집중을 분석합니다."),
        ("4단계 계획 수립·제시", "한시적 지출과 잠재적 유동성 수요를 반영해 대안을 비교합니다."),
        ("5단계 실행", "우선순위에 따라 자산배분·현금확보·위험관리 과제를 실행합니다."),
        ("6단계 모니터링", "소득·지출·시장상황·목표 변화를 확인하고 필요시 계획을 조정합니다."),
    ]

    for title, desc in stages:
        st.markdown(
            f'<div class="stage"><b>{title}</b><br>{desc}</div>',
            unsafe_allow_html=True,
        )

    st.subheader("우선 실행 과제")
    actions = [
        "1년 내 필요한 보증금 반환 가능성을 고려한 유동성 확보",
        "레버리지 ETF 비중 및 손실회복기간 점검",
        "한시적 교육·주택수선 지출을 별도 현금흐름으로 관리",
        "연금·보험·세제 관련 사항을 실제 요건에 맞춰 검토",
        "리밸런싱 이후 정기적인 자산·현금흐름 모니터링",
    ]
    for i, action in enumerate(actions, 1):
        st.checkbox(action, key=f"action_{i}")

# ---------- FIRE readiness ----------
st.markdown("---")
st.markdown('<div class="section-title">🔥 FIRE 준비도</div>', unsafe_allow_html=True)

f1, f2, f3 = st.columns(3)
saving_rate = (monthly_surplus / income * 100) if income else 0
f1.metric("월 잉여율", pct(saving_rate))
f2.metric("연간 정기 잉여", manwon(annual_surplus))
fire_status = "준비 양호" if score >= 70 and emergency_months >= 6 else "보완 필요"
f3.metric("FIRE 준비상태", fire_status)

st.progress(int(score))
st.caption(f"현재 입력값 기준 종합 준비도: {score:.0f}/100")

# ---------- AI / human judgment ----------
st.markdown("---")
st.markdown('<div class="section-title">🧠 AI 활용과 사람의 판단</div>', unsafe_allow_html=True)
left, right = st.columns(2)

with left:
    st.subheader("자동화·AI가 지원하는 영역")
    for x in [
        "재무지표 자동 계산",
        "위험요인 분류",
        "기간별 현금흐름 시뮬레이션",
        "리밸런싱 시나리오 비교",
        "6단계 재무설계 구조화",
    ]:
        st.write("• " + x)

with right:
    st.subheader("사람의 판단이 필요한 영역")
    for x in [
        "고객 목표와 우선순위",
        "한시적 지출과 영구적 지출의 최종 판단",
        "세무·법률 적용 여부",
        "투자위험의 실제 수용 가능성",
        "최종 재무계획의 선택과 실행",
    ]:
        st.write("• " + x)

st.markdown(
    '<div class="insight"><b>중요:</b> 이 프로토타입은 외부 생성형 AI API를 호출하지 않고, '
    '입력값과 사전 정의된 규칙으로 자동 계산·분류합니다. 따라서 공모전에서는 '
    '“AI를 활용한 재무설계 프로토타입”으로 설명하되, 생성형 AI가 모든 판단을 대신하는 것으로 표현하지 않습니다.</div>',
    unsafe_allow_html=True,
)

# ---------- Footer ----------
st.markdown("---")
st.caption(
    "본 서비스는 AFPK 영 플래너 챌린지 2026 공모전용 재무설계 프로토타입입니다. "
    "계산·분석 결과는 교육·시연 목적이며 실제 금융상품 가입·투자·세무 의사결정을 대신하지 않습니다."
)
