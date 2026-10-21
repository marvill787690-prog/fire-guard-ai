import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="머니체크 | 쉬운 재무관리", page_icon="💰", layout="wide")

# ---------- Design system ----------
st.markdown("""
<style>
.block-container{max-width:1080px;padding-top:1.5rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:#f6f8fb}
.hero{padding:28px 30px;border-radius:22px;background:linear-gradient(120deg,#17324d,#216b70);color:#fff;margin-bottom:18px}
.hero h1{color:#fff;font-size:2.15rem;line-height:1.2;margin:0 0 8px 0}
.hero p{color:#e8f4f4;font-size:1.02rem;margin:0}
.eyebrow{font-size:.8rem;letter-spacing:.04em;font-weight:700;color:#b9e5e1;margin-bottom:8px}
.small-muted{font-size:.88rem;color:#68778a}
div[data-testid="stMetric"]{background:#f7f9fc;border:1px solid #e7edf4;padding:15px 16px;border-radius:15px}
div[data-testid="stForm"]{border:1px solid #e6ebf2;border-radius:16px;padding:18px}
div.stButton>button{border-radius:12px;min-height:2.8rem;font-weight:600}
div[data-testid="stDownloadButton"] button{border-radius:12px}
hr{margin:1.2rem 0}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def won(value):
    value = int(round(float(value or 0)))
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 10000:
        eok, rest = divmod(value, 10000)
        return f"{sign}{eok:,}억 원" if rest == 0 else f"{sign}{eok:,}억 {rest:,}만 원"
    return f"{sign}{value:,}만 원"

def percent(n, d):
    return None if d <= 0 else n / d * 100

def pct_text(value):
    return "계산할 수 없음" if value is None else f"{value:.1f}%"

def calculate(d):
    assets = sum(d[k] for k in ("cash","deposits","stocks","pension","property","other_assets"))
    debts = sum(d[k] for k in ("mortgage","credit","other_debt"))
    outflow = d["living_cost"] + d["debt_payment"]
    liquid = d["cash"] + d["deposits"]
    return {
        "assets": assets, "debts": debts, "net": assets-debts,
        "liquid": liquid, "outflow": outflow,
        "surplus": d["income"]-outflow,
        "runway": None if outflow <= 0 else liquid/outflow,
        "debt_ratio": percent(debts, assets),
        "repayment_ratio": percent(d["debt_payment"], d["income"]),
    }

def csv_export(d, c):
    rows = [
        ("자산","현금·입출금",d["cash"]),("자산","예금·적금",d["deposits"]),
        ("자산","주식·ETF",d["stocks"]),("자산","연금계좌",d["pension"]),
        ("자산","부동산",d["property"]),("자산","기타 자산",d["other_assets"]),
        ("부채","주택담보대출 등",d["mortgage"]),("부채","신용대출·마이너스통장",d["credit"]),
        ("부채","기타 부채",d["other_debt"]),("합계","총자산",c["assets"]),
        ("합계","총부채",c["debts"]),("합계","순자산(자동 계산)",c["net"]),
        ("월 현금흐름","월 세후 소득",d["income"]),("월 현금흐름","생활비·고정지출",d["living_cost"]),
        ("월 현금흐름","대출 상환액",d["debt_payment"]),("월 현금흐름","월 잉여자금(자동 계산)",c["surplus"]),
    ]
    return pd.DataFrame(rows, columns=["구분","항목","금액(만원)"]).to_csv(index=False).encode("utf-8-sig")

def hero(kicker, title, subtitle):
    st.markdown(f'<div class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

# ---------- Navigation: 3 main destinations ----------
st.sidebar.markdown("## 💰 머니체크")
st.sidebar.caption("내 돈을 이해하는 가장 쉬운 첫걸음")
page = st.sidebar.radio(
    "메인 메뉴",
    ["홈", "내 재무현황", "목표와 실행계획"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption("필요한 순간에만 세부 정보를 확인할 수 있도록 메뉴를 줄였어요.")
if st.sidebar.button("입력 정보 다시 수정하기", use_container_width=True):
    st.session_state["open_input"] = True
    st.session_state["active_page"] = "홈"
    st.rerun()
st.sidebar.caption("🔒 계좌번호·주민등록번호 등 개인정보는 입력하지 마세요.")

d = st.session_state.get("moneycheck_data")
saved = d is not None
c = calculate(d) if saved else None

# ---------- Home / simple intake ----------
if page == "홈":
    hero("MONEY CHECK · YOUR FINANCIAL SNAPSHOT", "내 돈의 상태, 쉽게 확인해요.", "복잡한 금융 용어 대신 꼭 필요한 숫자와 다음 행동만 보여드릴게요.")
    if saved and not st.session_state.get("open_input", False):
        st.success("입력한 재무정보가 있어요. 현재 상태를 이어서 확인할 수 있습니다.")
        a,b,c3 = st.columns(3)
        a.metric("내 순자산", won(c["net"]), help="총자산에서 총부채를 뺀 금액입니다.")
        b.metric("매달 남는 돈", won(c["surplus"]))
        c3.metric("비상자금", f"{c['runway']:.1f}개월" if c["runway"] is not None else "지출 입력 필요")
        st.write("")
        left,right = st.columns([1,1])
        with left:
            st.markdown("### 지금 할 수 있는 일")
            st.write("**내 재무현황**에서 자산·부채와 월 현금흐름을 확인하세요.")
            st.write("**목표와 실행계획**에서 목표에 필요한 저축액과 우선 행동을 확인하세요.")
        with right:
            st.markdown("### 입력 정보가 바뀌었나요?")
            st.write("월급, 대출, 예금 잔액이 바뀌었다면 최신 금액으로 다시 계산해 보세요.")
            if st.button("정보 수정하기", type="primary", use_container_width=True):
                st.session_state["open_input"] = True
                st.rerun()
    else:
        st.markdown("### 3단계로 끝나는 간단한 재무 점검")
        cols = st.columns(3)
        for col, n, title, desc in [
            (cols[0],"01","내 상황 입력","자산·부채·월 소득과 지출"),
            (cols[1],"02","한눈에 확인","순자산과 월 현금흐름 자동 계산"),
            (cols[2],"03","다음 행동 찾기","비상자금과 목표 저축 계획"),
        ]:
            with col:
                st.markdown(f"#### {n} · {title}")
                st.write(desc)
        st.info("금액은 **만원 단위**로 입력해요. 예: 500은 500만 원, 10000은 1억 원입니다. 정확하지 않다면 합리적인 추정치를 입력해도 됩니다.")
        open_input = st.session_state.get("open_input", False)
        with st.form("simple_finance_form"):
            st.markdown("### 내 재무정보")
            st.caption("모르는 항목은 0으로 두고, 같은 자산을 두 번 입력하지 마세요.")
            st.markdown("**1. 자산**")
            x1,x2 = st.columns(2)
            with x1:
                cash = st.number_input("현금·입출금 계좌 (만원)", min_value=0, value=int(d["cash"]) if saved else 0, step=10)
                deposits = st.number_input("예금·적금 (만원)", min_value=0, value=int(d["deposits"]) if saved else 0, step=10)
                stocks = st.number_input("주식·ETF (만원)", min_value=0, value=int(d["stocks"]) if saved else 0, step=10)
            with x2:
                pension = st.number_input("연금계좌 (만원)", min_value=0, value=int(d["pension"]) if saved else 0, step=10)
                property_value = st.number_input("부동산 현재 평가액 (만원)", min_value=0, value=int(d["property"]) if saved else 0, step=100)
                other_assets = st.number_input("기타 자산 (만원)", min_value=0, value=int(d["other_assets"]) if saved else 0, step=10)
            with st.expander("자산 입력이 헷갈리나요?"):
                st.write("부동산은 대출을 빼기 전의 현재 평가액을 입력하세요. 연금계좌 안의 ETF를 주식·ETF에도 넣었다면 중복 입력하지 마세요.")
            st.markdown("**2. 부채**")
            x1,x2,x3 = st.columns(3)
            with x1:
                mortgage = st.number_input("주택담보대출 등 (만원)", min_value=0, value=int(d["mortgage"]) if saved else 0, step=100)
            with x2:
                credit = st.number_input("신용대출·마이너스통장 (만원)", min_value=0, value=int(d["credit"]) if saved else 0, step=10)
            with x3:
                other_debt = st.number_input("기타 부채 (만원)", min_value=0, value=int(d["other_debt"]) if saved else 0, step=10)
            st.markdown("**3. 한 달 수입과 지출**")
            x1,x2,x3 = st.columns(3)
            with x1:
                income = st.number_input("월 세후 소득 (만원)", min_value=0, value=int(d["income"]) if saved else 0, step=10)
            with x2:
                living_cost = st.number_input("월 생활비·고정지출 (만원)", min_value=0, value=int(d["living_cost"]) if saved else 0, step=10)
            with x3:
                debt_payment = st.number_input("월 대출 상환액 (만원)", min_value=0, value=int(d["debt_payment"]) if saved else 0, step=10)
            st.caption("생활비·고정지출에는 대출 상환액을 포함하지 마세요. 대출 상환액은 별도로 입력합니다.")
            st.markdown("**4. 나의 목표**")
            g1,g2 = st.columns(2)
            with g1:
                goal = st.selectbox("가장 중요한 목표", ["전반적인 재무 점검","비상자금 마련","부채 상환","결혼 자금","주택 마련","자녀 교육비","은퇴 준비","경제적 독립(FIRE)","자산 증식"], index=(["전반적인 재무 점검","비상자금 마련","부채 상환","결혼 자금","주택 마련","자녀 교육비","은퇴 준비","경제적 독립(FIRE)","자산 증식"].index(d["goal"]) if saved and d["goal"] in ["전반적인 재무 점검","비상자금 마련","부채 상환","결혼 자금","주택 마련","자녀 교육비","은퇴 준비","경제적 독립(FIRE)","자산 증식"] else 0))
                years = st.selectbox("목표까지 남은 기간", [1,3,5,10,20], index=2, format_func=lambda v:f"{v}년")
            with g2:
                target = st.number_input("목표에 필요한 총금액 (만원)", min_value=0, value=int(d["target"]) if saved else 0, step=100)
                already_saved = st.number_input("목표를 위해 이미 모은 금액 (만원)", min_value=0, value=int(d["already_saved"]) if saved else 0, step=10)
            submitted = st.form_submit_button("내 재무상태 확인하기", type="primary", use_container_width=True)
        if submitted:
            errors=[]
            warnings=[]
            total_assets=sum([cash,deposits,stocks,pension,property_value,other_assets])
            if target == 0 and already_saved > 0:
                warnings.append("목표 금액이 0인데 이미 모은 금액이 입력되어 있습니다. 목표 금액을 확인해 주세요.")
            if target > 0 and already_saved > target:
                errors.append("이미 모은 금액이 목표 총금액보다 큽니다. 두 금액을 확인해 주세요.")
            if income == 0 and living_cost+debt_payment > 0:
                warnings.append("월 소득이 0이고 지출이 입력되어 있습니다. 소득 공백 기간인지 확인해 주세요.")
            if income > 0 and living_cost+debt_payment > income*3:
                warnings.append("월 지출이 소득의 3배를 넘습니다. 단위나 입력 금액을 다시 확인해 주세요.")
            if mortgage+credit+other_debt > total_assets:
                warnings.append("총부채가 총자산보다 큽니다. 실제 상황일 수 있지만 입력값을 한 번 더 확인해 주세요.")
            if errors:
                for e in errors: st.error(e)
            else:
                st.session_state["moneycheck_data"]={
                    "cash":cash,"deposits":deposits,"stocks":stocks,"pension":pension,
                    "property":property_value,"other_assets":other_assets,"mortgage":mortgage,
                    "credit":credit,"other_debt":other_debt,"income":income,
                    "living_cost":living_cost,"debt_payment":debt_payment,"goal":goal,
                    "years":years,"target":target,"already_saved":already_saved,
                }
                st.session_state["open_input"]=False
                st.session_state["active_page"]="내 재무현황"
                st.success("계산이 완료됐어요. 아래 요약부터 확인해 보세요.")
                fresh=calculate(st.session_state["moneycheck_data"])
                m1,m2,m3=st.columns(3)
                m1.metric("총자산",won(fresh["assets"]))
                m2.metric("총부채",won(fresh["debts"]))
                m3.metric("내 순자산",won(fresh["net"]))
                st.caption(f"순자산은 자동 계산됩니다: {won(fresh['assets'])} − {won(fresh['debts'])} = {won(fresh['net'])}")
                for w in warnings: st.warning(w)
                st.button("재무현황 자세히 보기", type="primary", on_click=lambda: st.session_state.update({"active_page":"내 재무현황"}))

# Handle page selection from buttons (sidebar remains 3 items)
if st.session_state.get("active_page") and st.session_state["active_page"] != page:
    # State hint only; sidebar navigation remains controlled by user.
    if page == "홈" and st.session_state["active_page"] == "내 재무현황":
        st.info("왼쪽 메뉴에서 ‘내 재무현황’을 선택하면 상세 결과를 볼 수 있어요.")

# ---------- Financial snapshot ----------
if page == "내 재무현황":
    if not saved:
        hero("MY SNAPSHOT","먼저 내 상황을 알려주세요","자산과 부채를 입력하면 순자산과 현금흐름을 자동으로 계산합니다.")
        st.info("왼쪽 메뉴에서 ‘홈’을 선택한 뒤 재무정보를 입력해 주세요.")
    else:
        hero("MY SNAPSHOT","내 재무현황","여러 숫자를 한 번에 보기 쉽게 정리했어요.")
        a,b,c3 = st.columns(3)
        a.metric("총자산",won(c["assets"]))
        b.metric("총부채",won(c["debts"]))
        c3.metric("내 순자산",won(c["net"]),help="순자산은 총자산에서 총부채를 뺀 값입니다. 직접 입력하지 않습니다.")
        st.caption(f"자동 계산 확인: {won(c['assets'])} − {won(c['debts'])} = {won(c['net'])}")
        if c["net"] < 0:
            st.warning("순자산이 음수예요. 실제 상황일 수 있습니다. 대출 조건과 월 상환 여력을 먼저 확인해 보세요.")
        st.divider()
        st.markdown("### 재무상태표")
        st.caption("현재 보유한 자산과 갚아야 할 부채를 정리한 표예요.")
        balance_rows=[
            ("자산","현금·입출금",d["cash"]),("자산","예금·적금",d["deposits"]),
            ("자산","주식·ETF",d["stocks"]),("자산","연금계좌",d["pension"]),
            ("자산","부동산",d["property"]),("자산","기타 자산",d["other_assets"]),
            ("부채","주택담보대출 등",d["mortgage"]),("부채","신용대출·마이너스통장",d["credit"]),
            ("부채","기타 부채",d["other_debt"]),("합계","총자산",c["assets"]),
            ("합계","총부채",c["debts"]),("합계","순자산",c["net"]),
        ]
        bdf=pd.DataFrame(balance_rows,columns=["구분","항목","금액(만원)"])
        bdf["금액"]=bdf["금액(만원)"].apply(won)
        st.dataframe(bdf[["구분","항목","금액"]],use_container_width=True,hide_index=True)
        with st.expander("자산과 부채의 구성 보기"):
            left,right=st.columns(2)
            with left:
                st.markdown("**자산 구성**")
                adf=pd.DataFrame({"자산":["현금·입출금","예금·적금","주식·ETF","연금계좌","부동산","기타 자산"],
                                  "금액(만원)":[d["cash"],d["deposits"],d["stocks"],d["pension"],d["property"],d["other_assets"]]})
                adf=adf[adf["금액(만원)"]>0].set_index("자산")
                if not adf.empty: st.bar_chart(adf)
                else: st.caption("입력된 자산이 없습니다.")
            with right:
                st.markdown("**부채 구성**")
                ddf=pd.DataFrame({"부채":["주택담보대출 등","신용대출·마이너스통장","기타 부채"],
                                  "금액(만원)":[d["mortgage"],d["credit"],d["other_debt"]]})
                ddf=ddf[ddf["금액(만원)"]>0].set_index("부채")
                if not ddf.empty: st.bar_chart(ddf)
                else: st.caption("입력된 부채가 없습니다.")
        st.divider()
        st.markdown("### 현금흐름표")
        st.caption("매달 들어오는 돈과 나가는 돈을 비교해 실제로 얼마가 남는지 보여줘요.")
        f1,f2,f3=st.columns(3)
        f1.metric("월 세후 소득",won(d["income"]))
        f2.metric("월 지출·대출 상환",won(c["outflow"]))
        f3.metric("매달 남는 돈",won(c["surplus"]))
        flow=pd.DataFrame({
            "항목":["생활비·고정지출","대출 상환액","월 잉여자금"],
            "금액(만원)":[d["living_cost"],d["debt_payment"],max(0,c["surplus"])]
        }).set_index("항목")
        st.bar_chart(flow)
        if c["surplus"]<0:
            st.error(f"현재 입력값 기준으로 매달 {won(abs(c['surplus']))}이 부족해요. 필수 지출과 선택 지출을 구분해 적자 원인을 확인해 보세요.")
        elif c["surplus"]==0:
            st.warning("현재 입력값 기준으로 매달 남는 돈이 없어요. 비정기 지출까지 고려해 보세요.")
        else:
            st.success(f"현재 입력값 기준으로 매달 {won(c['surplus'])}이 남아요. 실제로 저축할 수 있는 금액인지 확인해 보세요.")
        r1,r2=st.columns(2)
        r1.metric("현금·예금으로 버틸 수 있는 기간",f"{c['runway']:.1f}개월" if c["runway"] is not None else "지출 입력 필요")
        r2.metric("부채 / 총자산",pct_text(c["debt_ratio"]))
        st.caption("버틸 수 있는 기간은 현금과 예금을 월 지출·대출 상환액으로 나눈 참고 지표입니다. 공식 DSR이나 대출 심사 결과가 아닙니다.")
        st.download_button("재무상태표·현금흐름표 CSV 다운로드",data=csv_export(d,c),
                           file_name=f"머니체크_재무요약_{date.today().isoformat()}.csv",
                           mime="text/csv",type="primary",use_container_width=True)

# ---------- Goals & action ----------
if page == "목표와 실행계획":
    if not saved:
        hero("YOUR NEXT STEP","목표를 세우기 전에","먼저 내 재무정보를 입력하면 상황에 맞는 실행 계획을 확인할 수 있어요.")
        st.info("왼쪽 메뉴에서 ‘홈’을 선택한 뒤 정보를 입력해 주세요.")
    else:
        hero("YOUR NEXT STEP","다음 행동을 정해요","현재 숫자에서 출발해 이번 달에 할 수 있는 일부터 확인해 보세요.")
        gap=max(0,d["target"]-d["already_saved"])
        months=int(d["years"]*12)
        needed=gap/months if months else 0
        st.markdown("### 나의 목표")
        st.write(f"**{d['goal']}** · 목표 기간 **{d['years']}년**")
        g1,g2,g3=st.columns(3)
        g1.metric("목표 금액",won(d["target"]))
        g2.metric("이미 모은 금액",won(d["already_saved"]))
        g3.metric("앞으로 필요한 금액",won(gap))
        if d["target"]>0:
            st.write(f"목표까지 매달 필요한 저축액은 약 **{won(needed)}**입니다. (수익률·물가·세금 미반영)")
            max_extra=max(100,min(1000,int(max(d["income"],1000))))
            extra=st.slider("매달 추가로 저축할 금액을 가정해 보세요 (만원)",0,max_extra,min(100,max_extra),step=10)
            monthly=c["surplus"]+extra
            q1,q2=st.columns(2)
            q1.metric("현재 매달 남는 돈",won(c["surplus"]))
            q2.metric("가정 적용 후 매달 남는 돈",won(monthly))
            if monthly>=needed and monthly>=0:
                st.success("단순 계산상 목표 기간에 필요한 저축액을 충족해요. 실제로 유지 가능한 금액인지 확인해 보세요.")
            else:
                st.warning("현재 가정으로는 목표 기간에 필요한 저축액이 부족해요. 목표 기간이나 목표 금액을 조정하거나 지출을 점검해 보세요.")
            if monthly>0:
                needed_months=max(0,int((gap+monthly-1)//monthly))
                st.write(f"가정한 저축액을 유지하면 목표 잔액까지 약 **{needed_months}개월**이 필요해요.")
            else:
                st.write("월 잉여자금이 0 이하라면 저축액을 늘리기 전에 현금흐름부터 점검하는 것이 우선이에요.")
        else:
            st.info("목표 금액을 입력하지 않았어요. 홈 화면에서 목표 금액을 입력하면 필요한 월 저축액을 계산할 수 있습니다.")
        st.divider()
        st.markdown("### 우선 확인할 것")
        tasks=[]
        if c["surplus"]<0:
            tasks.append(("먼저","매달 적자가 나는 이유 찾기",f"월 {won(abs(c['surplus']))}이 부족해요. 필수 생활비, 선택 지출, 대출 상환액을 나누어 살펴보세요."))
        if c["runway"] is not None and c["runway"]<3:
            tasks.append(("우선","비상자금 계획 세우기","현금·예금이 현재 월 지출의 3개월분보다 적어요. 소득 안정성과 예정 지출을 고려해 비상자금 목표를 정해 보세요."))
        if d["mortgage"]+d["credit"]+d["other_debt"]>0:
            tasks.append(("점검","대출 조건 한곳에 모으기","대출별 잔액·금리·만기·월 상환액을 정리하면 상환 계획을 세우기 쉬워요."))
        if not tasks:
            tasks.append(("매월","월 1회 재무정보 업데이트","실제 지출과 계획을 비교하고, 소득·주거·가족 상황이 바뀌면 다시 진단해 보세요."))
        for i,(level,title,desc) in enumerate(tasks):
            with st.expander(f"{level} · {title}",expanded=(i==0)):
                st.write(desc)
                st.checkbox("확인했어요",key=f"goal_task_{i}_{title}")
        st.caption("이 결과는 입력값을 바탕으로 한 단순 계산이며, 목표 달성이나 투자 성과를 보장하지 않습니다.")

# ---------- Footer / privacy ----------
st.divider()
st.caption("머니체크는 무료 규칙 기반 재무 점검 도구입니다. 공식 DSR·세금·보험·연금 분석이나 개인별 투자 자문을 제공하지 않습니다. 입력값이 정확하지 않으면 결과도 달라질 수 있습니다.")
