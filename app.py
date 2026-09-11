import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


# ==========
# 환경 설정
# ==========
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "production_data.xlsx"

st.set_page_config(
    page_title="항공기 부품 생산관리 대시보드",
    layout="wide"
)

# ====
#  UI
# =====
st.markdown(
    """
    <style>
    :root {
        --theme-deep-navy: #091A3B;
        --theme-navy: #103074;
        --theme-royal-blue: #1C3C85;
        --theme-accent-blue: #3658B9;
        --theme-sky-blue: #3C88B3;
        --theme-light-bg: #F7F9FC;
        --theme-light-border: #DDE4F0;
        --theme-alert-red: #D9534F;
    }

    .stApp {
        background-color: var(--theme-light-bg);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1 {
        color: var(--theme-navy) !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }

    h2, h3 {
        color: var(--theme-royal-blue) !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid var(--theme-light-border);
        border-left: 5px solid var(--theme-accent-blue);
        padding: 16px;
        border-radius: 10px;
        min-height: 112px;
        height: 112px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    [data-testid="stMetricLabel"] {
        color: var(--theme-royal-blue);
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--theme-deep-navy);
        font-weight: 700;
    }

    .stButton > button {
        background-color: var(--theme-navy);
        color: #FFFFFF;
        border: none;
        border-radius: 7px;
        font-weight: 600;
        padding: 0.45rem 1rem;
    }

    .stButton > button:hover {
        background-color: var(--theme-accent-blue);
        color: #FFFFFF;
        border: none;
    }

    div[data-baseweb="select"] > div {
        border-color: var(--theme-accent-blue);
    }

    hr {
        border-color: var(--theme-light-border);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--theme-light-border);
        border-radius: 8px;
        overflow: hidden;
    }

    [data-testid="stAlert"] {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ====
# 제목
# ====
st.title("항공기 부품 생산관리 분석 대시보드")
st.caption(
    "가상의 항공기 부품 생산 데이터를 기반으로 생산실적, 부하, 공수, 일정 및 생산현안을 분석합니다."
)


COLUMN_KR = {
    "part_id": "부품 ID",
    "part_name": "부품명",
    "process": "공정",
    "plan_qty": "계획수량",
    "actual_qty": "실제수량",
    "achievement_rate": "생산달성률(%)",
    "defect_qty": "불량수량",
    "defect_rate": "불량률(%)",
    "plan_date": "계획완료일",
    "actual_date": "실제완료일",
    "delay_days": "지연일수",
    "work_hours": "실제작업공수(h)",
    "standard_hours": "단위표준공수(h/개)",
    "planned_load_hours": "계획소요공수(h)",
    "actual_load_hours": "실제소요공수(h)",
    "available_hours": "가용공수(h)",
    "load_rate": "계획부하율(%)",
    "capacity_gap_hours": "공수차이(h)",
    "shortage_hours": "부족공수(h)",
    "load_status": "부하상태",
    "production_status": "생산상태",
    "quality_status": "품질상태",
    "delivery_status": "일정상태",
    "review_status": "검토구분",
    "next_process": "다음공정",
    "next_plan_date": "다음공정 계획일",
    "downstream_impact_days": "후속일정 침범일수",
    "downstream_status": "후속일정 상태"
}


# 데이터 불러오기
df = pd.read_excel(DATA_PATH)

# 날짜 형식 변환
df["plan_date"] = pd.to_datetime(df["plan_date"])
df["actual_date"] = pd.to_datetime(df["actual_date"])


# ===============
# 기본 KPI 계산
# ===============
df["achievement_rate"] = (
    df["actual_qty"] / df["plan_qty"] * 100
).round(1)

df["defect_rate"] = (
    df["defect_qty"] / df["actual_qty"] * 100
).round(1)

df["delay_days"] = (
    df["actual_date"] - df["plan_date"]
).dt.days


# =====================
# 생산 부하 / 공수 분석
# =====================

# 계획 소요공수 = 계획수량 × 단위 표준공수
df["planned_load_hours"] = (
    df["plan_qty"] * df["standard_hours"]
).round(1)

# 실제 소요공수
df["actual_load_hours"] = (
    df["work_hours"]
).round(1)

# 계획 부하율 = 계획 소요공수 ÷ 가용공수 × 100
df["load_rate"] = (
    df["planned_load_hours"] / df["available_hours"] * 100
).round(1)

# 공수 차이 = 계획 소요공수 - 가용공수
df["capacity_gap_hours"] = (
    df["planned_load_hours"] - df["available_hours"]
).round(1)

# 부족공수: 계획 소요공수가 가용공수를 초과한 경우만 표시
df["shortage_hours"] = (
    df["capacity_gap_hours"]
).clip(lower=0).round(1)


def evaluate_load(row):
    """
    임의의 90%, 95% 구간을 두지 않고
    계획 소요공수가 가용공수를 실제로 초과하는지만 판정한다.
    """
    if row["planned_load_hours"] > row["available_hours"]:
        return "과부하"
    return "가용범위"


df["load_status"] = df.apply(
    evaluate_load,
    axis=1
)


# =========================
# 생산실적 / 품질 / 일정 현황
# =========================

# 별도의 임의 정상/주의/위험 임계값은 사용하지 않음

# 계획 생산량 충족 여부
df["production_status"] = df.apply(
    lambda row: "계획 미달"
    if row["actual_qty"] < row["plan_qty"]
    else "계획 충족",
    axis=1
)

# 불량 발생 여부
df["quality_status"] = df["defect_qty"].apply(
    lambda x: "불량 발생" if x > 0 else "불량 없음"
)

# 일정 준수 여부
df["delivery_status"] = df["delay_days"].apply(
    lambda x: "지연" if x > 0 else "일정 준수"
)


# =========================
# Bottleneck 검토 대상 식별
# =========================

# 개별 관리 이슈
df["issue_overload"] = (
    df["planned_load_hours"] > df["available_hours"]
)

df["issue_plan_shortfall"] = (
    df["actual_qty"] < df["plan_qty"]
)

df["issue_defect"] = (
    df["defect_qty"] > 0
)

df["issue_delay"] = (
    df["delay_days"] > 0
)


# Bottleneck 검토 대상

# 계획 단계에서 실제 가용공수를 초과했고
# 실제 생산에서도 계획 미달 또는 일정 지연이 나타난 경우

# Bottleneck '확정'이 아닌
# 생산관리자가 우선 확인해야 할 검토 대상임

df["bottleneck_review"] = (
    df["issue_overload"]
    &
    (
        df["issue_plan_shortfall"]
        | df["issue_delay"]
    )
)


def evaluate_review_status(row):

    if row["bottleneck_review"]:
        return "Bottleneck 검토"

    elif row["issue_overload"]:
        return "부하 검토"

    elif row["issue_delay"]:
        return "일정 검토"

    elif row["issue_defect"]:
        return "품질 검토"

    elif row["issue_plan_shortfall"]:
        return "실적 모니터링"

    return "이상 없음"


df["review_status"] = df.apply(
    evaluate_review_status,
    axis=1
)

# =========================
# 납기 / 후속 공정 영향 분석
# =========================

process_order = {
    "가공": 1,
    "표면처리": 2,
    "조립": 3,
    "도장": 4,
    "검사": 5,
    "출하": 6
}

df["process_order"] = df["process"].map(process_order)

# 부품별 공정 순서대로 정렬
df = df.sort_values(
    ["part_name", "process_order"]
).reset_index(drop=True)


# 다음 공정 정보
df["next_process"] = (
    df.groupby("part_name")["process"]
    .shift(-1)
)

df["next_plan_date"] = (
    df.groupby("part_name")["plan_date"]
    .shift(-1)
)


# 현재 공정의 실제 완료일이
# 다음 공정의 계획일보다 얼마나 늦었는지 계산
df["downstream_impact_days"] = (
    df["actual_date"] - df["next_plan_date"]
).dt.days


# 음수는 후속 일정 침범이 아니므로 0 처리
df["downstream_impact_days"] = (
    df["downstream_impact_days"]
    .clip(lower=0)
)


def evaluate_downstream_impact(row):

    # 출하는 다음 공정이 없음
    if pd.isna(row["next_process"]):
        return "최종 공정"

    # 현재 공정 완료가 다음 공정 계획일을 넘긴 경우
    if row["actual_date"] > row["next_plan_date"]:
        return "후속 일정 영향 검토"

    return "영향 없음"


df["downstream_status"] = df.apply(
    evaluate_downstream_impact,
    axis=1
)

# ========
# 전체 KPI
# ========
overall_achievement = (
    df["actual_qty"].sum() / df["plan_qty"].sum() * 100
)

overall_defect = (
    df["defect_qty"].sum() / df["actual_qty"].sum() * 100
)

otd = (
    (df["delay_days"] <= 0).sum() / len(df) * 100
)

delayed_count = int((df["delay_days"] > 0).sum())


# ===================
# 최종 출하 납기 현황
# ===================
shipping_df = df[
    df["process"] == "출하"
].copy()

shipping_total = len(shipping_df)

shipping_on_time_count = int(
    (shipping_df["delay_days"] <= 0).sum()
)

shipping_delayed_count = int(
    (shipping_df["delay_days"] > 0).sum()
)

shipping_compliance_rate = (
    shipping_on_time_count / shipping_total * 100
    if shipping_total > 0
    else 0.0
)


# =========
# KPI 카드
# =========
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "전체 생산달성률",
    f"{overall_achievement:.1f}%"
)

col2.metric(
    "전체 불량률",
    f"{overall_defect:.1f}%"
)

col3.metric(
    "계획일정 준수율",
    f"{otd:.1f}%"
)

col4.metric(
    "일정 지연 항목",
    f"{delayed_count}건"
)


st.divider()

# ===================
# 최종 출하 납기 현황
# ===================
st.subheader("최종 출하 납기 현황")

ship_col1, ship_col2, ship_col3, _ = st.columns(4)

ship_col1.metric(
    "최종 출하 준수율",
    f"{shipping_compliance_rate:.1f}%"
)

ship_col2.metric(
    "출하 일정 준수",
    f"{shipping_on_time_count}건"
)

ship_col3.metric(
    "출하 일정 지연",
    f"{shipping_delayed_count}건"
)

shipping_display = shipping_df[
    [
        "part_id",
        "part_name",
        "plan_date",
        "actual_date",
        "delay_days",
        "achievement_rate",
        "delivery_status"
    ]
].copy().rename(
    columns={
        "part_id": "부품 ID",
        "part_name": "부품명",
        "plan_date": "출하 계획일",
        "actual_date": "실제 출하일",
        "delay_days": "출하 지연일수",
        "achievement_rate": "출하 생산달성률(%)",
        "delivery_status": "출하 일정상태"
    }
)


def highlight_shipping_cells(data):

    styles = pd.DataFrame(
        "",
        index=data.index,
        columns=data.columns
    )

    styles.loc[
        data["출하 지연일수"] > 0,
        "출하 지연일수"
    ] = "background-color: #FFF3CD; font-weight: bold;"

    styles.loc[
        data["출하 일정상태"] == "지연",
        "출하 일정상태"
    ] = "background-color: #F8D7DA; font-weight: bold;"

    return styles


styled_shipping_df = (
    shipping_display.style
    .apply(
        highlight_shipping_cells,
        axis=None
    )
    .format(
        {
            "출하 계획일": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "",
            "실제 출하일": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "",
            "출하 지연일수": "{:.0f}",
            "출하 생산달성률(%)": "{:.1f}%"
        }
    )
)

st.dataframe(
    styled_shipping_df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "※ 최종 출하 준수율은 '출하' 공정만 대상으로, 실제 출하일이 "
    "출하 계획일 이내인 항목의 비율로 계산합니다. "
    "공정 전체를 대상으로 한 '계획일정 준수율'과 구분하여 표시합니다."
)

st.divider()

# =========================
# 부품별 생산 공정 흐름 분석
# =========================

st.subheader("부품별 생산 공정 흐름 분석")

process_sequence = [
    "가공",
    "표면처리",
    "조립",
    "도장",
    "검사",
    "출하"
]

# 분석할 부품 선택
selected_part_name = st.selectbox(
    "분석할 부품을 선택하세요",
    sorted(df["part_name"].unique()),
    key="process_flow_part"
)

part_flow_df = df[
    df["part_name"] == selected_part_name
].copy()

# 공정 순서 지정
part_flow_df["process_sequence"] = pd.Categorical(
    part_flow_df["process"],
    categories=process_sequence,
    ordered=True
)

part_flow_df = part_flow_df.sort_values(
    "process_sequence"
)

# ======================
# AI 공정 흐름 종합 분석
# ======================

st.write("#### AI 공정 흐름 종합 분석")

if st.button(
    "선택 부품 전체 공정 AI 분석",
    key="ai_flow_analysis"
):

    # -------------------------
    # 전체 공정 데이터 문자열 생성
    # -------------------------
    flow_text = ""

    for _, row in part_flow_df.iterrows():

        flow_text += f"""
공정: {row['process']}
계획 생산량: {int(row['plan_qty'])}개
실제 생산량: {int(row['actual_qty'])}개
생산달성률: {row['achievement_rate']:.1f}%
계획 소요공수: {row['planned_load_hours']:.2f}시간
가용공수: {row['available_hours']:.2f}시간
계획 부하율: {row['load_rate']:.1f}%
부족공수: {row['shortage_hours']:.2f}시간
불량수량: {int(row['defect_qty'])}개
불량률: {row['defect_rate']:.1f}%
일정 지연: {int(row['delay_days'])}일
후속 일정 상태: {row['downstream_status']}
---
"""

    # ---------------------
    # 최종 출하 데이터 확인
    # ---------------------
    shipping_data = part_flow_df[
        part_flow_df["process"] == "출하"
    ]

    if not shipping_data.empty:

        final_shipping_delay = int(
            shipping_data.iloc[0]["delay_days"]
        )

        final_shipping_achievement = float(
            shipping_data.iloc[0]["achievement_rate"]
        )

    else:

        final_shipping_delay = 0
        final_shipping_achievement = 0.0


    # ---------
    # AI Prompt
    # ---------
    prompt = f"""
당신은 항공기 부품 생산관리 담당자의 의사결정을 지원하는 AI입니다.

아래 데이터는 실제 기업 내부 데이터가 아니라
항공기 부품 생산환경을 가정한 가상의 생산 데이터입니다.

분석 부품:
{selected_part_name}

공정 순서:
가공 → 표면처리 → 조립 → 도장 → 검사 → 출하

[공정별 데이터]

{flow_text}

[최종 출하 현황]

최종 출하 생산달성률:
{final_shipping_achievement:.1f}%

최종 출하 지연:
{final_shipping_delay}일


분석 원칙:

1. 입력 데이터에 없는 설비 고장, 자재 부족, 재작업, 작업자 문제 등의 원인은 발생했다고 제시하지 말고, 필요하면 "추가 확인 항목"으로만 표현하세요.

2. 특정 공정의 높은 계획 부하율과
실적 저하 또는 일정 지연이 함께 나타나더라도
직접적인 인과관계로 확정하지 마세요.

3. 계획 소요공수가 가용공수를 초과한 경우에는
'계획상 과부하가 확인됨'이라고 표현할 수 있습니다.

4. Bottleneck이라고 확정하지 말고
필요하면 'Bottleneck 검토 대상'이라고 표현하세요.

5. 앞 공정의 실제 완료일이 다음 공정 계획일을 초과한 경우
후속 일정 영향 가능성을 설명할 수 있지만
실제 지연 원인이라고 확정하지 마세요.

6. 최종 의사결정은 생산관리자가 수행한다는 전제로 분석하세요.


다음 형식으로 작성하세요.

1. 전체 공정 현황
- 이 부품의 생산 흐름을 핵심 수치와 함께 3문장 이내로 요약

2. 우선 검토 공정
- 가장 우선적으로 확인할 공정을 최대 2개 선정
- 선정 근거를 수치로 제시

3. 후속 일정 및 납기 영향
- 앞 공정의 일정 침범 여부
- 최종 출하 일정 상태
- 인과관계는 단정하지 말 것

4. 생산관리 검토안
- 생산계획 조정
- 가용공수 확보
- 공정 우선순위 조정
- 후속 일정 재검토
등에서 실제 데이터에 적합한 방안을 최대 3개 제시


수치 표현 규칙:

- 모든 비율은 반드시 소수점 첫째 자리까지 표시하세요.
- 공수(시간) 값은 소수점 둘째 자리까지 표시하세요.
- 예: 127%가 아니라 127.0%
- 입력된 수치를 임의로 변경하거나 새로운 수치를 생성하지 마세요.
- 계획량, 실제량, 불량수량, 지연일수 등 정수 데이터는 원래 값 그대로 표시하세요.

전체 답변은 약 700자 내외로 작성하세요.
"""


    # ----------------
    # OpenAI API 실행
    # ----------------
    try:

        if client is None:
            raise RuntimeError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
            )

        with st.spinner(
            "AI가 전체 생산 공정을 분석하고 있습니다..."
        ):

            response = client.responses.create(
                model="gpt-5-mini",
                input=prompt
            )

        st.success(
            "전체 공정 분석이 완료되었습니다."
        )

        st.markdown(
            response.output_text
        )

    except Exception as e:

        st.error(
            f"AI 분석 중 오류가 발생했습니다: {e}"
        )


# ==============
# 최종 출하 현황
# ==============

shipping_row = part_flow_df[
    part_flow_df["process"] == "출하"
]

if len(shipping_row) > 0:

    shipping_row = shipping_row.iloc[0]

    col1, col2, col3, _ = st.columns(4)

    col1.metric(
        "최종 출하 생산달성률",
        f"{shipping_row['achievement_rate']:.1f}%"
    )

    col2.metric(
        "최종 출하 지연",
        f"{int(shipping_row['delay_days'])}일"
    )

    col3.metric(
        "최종 출하 상태",
        "일정 지연"
        if shipping_row["delay_days"] > 0
        else "일정 준수"
    )


# ===================
# 공정별 부하율 그래프
# ===================

st.write("#### 공정별 계획 부하율")

flow_chart = alt.Chart(
    part_flow_df
).mark_bar(
    size=45
).encode(

    x=alt.X(
        "process:N",
        title="공정",
        sort=process_sequence,
        axis=alt.Axis(labelAngle=0)
    ),

    y=alt.Y(
        "load_rate:Q",
        title="계획 부하율 (%)"
    ),

    color=alt.condition(
        alt.datum.load_rate > 100,
        alt.value("#D9534F"),
        alt.value("#3658B9")
    ),

    tooltip=[
        alt.Tooltip(
            "process:N",
            title="공정"
        ),
        alt.Tooltip(
            "planned_load_hours:Q",
            title="계획 소요공수",
            format=".1f"
        ),
        alt.Tooltip(
            "available_hours:Q",
            title="가용공수",
            format=".1f"
        ),
        alt.Tooltip(
            "load_rate:Q",
            title="계획 부하율",
            format=".1f"
        ),
        alt.Tooltip(
            "achievement_rate:Q",
            title="생산달성률",
            format=".1f"
        ),
        alt.Tooltip(
            "delay_days:Q",
            title="일정 지연"
        )
    ]
)


# 가용공수 100% 기준선
capacity_line = alt.Chart(
    pd.DataFrame(
        {"capacity": [100]}
    )
).mark_rule(
    color="#103074",
    strokeDash=[6, 4],
    size=2
).encode(
    y="capacity:Q"
)


final_flow_chart = (
    flow_chart
    + capacity_line
).properties(
    height=350
)

st.altair_chart(
    final_flow_chart,
    use_container_width=True
)


st.caption(
    "※ 빨간색 막대는 계획 소요공수가 가용공수를 초과한 공정입니다. "
    "100.0% 기준선은 계획 소요공수와 가용공수가 동일한 지점을 의미합니다."
)


# =====================
# 공정 흐름 상세 데이터
# =====================

st.write("#### 공정 흐름 상세")

flow_display = part_flow_df[
    [
        "process",
        "planned_load_hours",
        "available_hours",
        "load_rate",
        "achievement_rate",
        "defect_qty",
        "defect_rate",
        "delay_days",
        "downstream_status"
    ]
].copy().rename(columns=COLUMN_KR)


def highlight_flow_cells(data):

    styles = pd.DataFrame(
        "",
        index=data.index,
        columns=data.columns
    )

    # 가용공수 초과
    styles.loc[
        data["계획부하율(%)"] > 100,
        "계획부하율(%)"
    ] = (
        "background-color: #F8D7DA; "
        "font-weight: bold;"
    )

    # 실제 일정 지연
    styles.loc[
        data["지연일수"] > 0,
        "지연일수"
    ] = (
        "background-color: #FFF3CD; "
        "font-weight: bold;"
    )

    # 후속 일정 영향 가능성
    styles.loc[
        data["후속일정 상태"]
        == "후속 일정 영향 검토",
        "후속일정 상태"
    ] = (
        "background-color: #F8D7DA; "
        "font-weight: bold;"
    )

    return styles


styled_flow_df = (
    flow_display.style
    .apply(
        highlight_flow_cells,
        axis=None
    )
    .format(
        {
            "계획소요공수(h)": "{:.2f}",
            "가용공수(h)": "{:.2f}",
            "계획부하율(%)": "{:.1f}%",
            "생산달성률(%)": "{:.1f}%",
            "불량률(%)": "{:.1f}%"
        }
    )
)


st.dataframe(
    styled_flow_df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "※ 공정별 계획 부하, 생산실적, 품질 및 일정 데이터를 함께 표시합니다. "
    "앞 공정의 실제 완료일이 다음 공정의 계획일을 초과한 경우 "
    "'후속 일정 영향 검토'로 표시하며, 실제 지연 원인을 확정하는 것은 아닙니다."
)

st.divider()

# ========================
# 후속 공정 납기 영향 분석
# ========================

st.subheader("후속 공정 납기 영향 분석")

schedule_impact_df = df[
    df["downstream_status"] == "후속 일정 영향 검토"
].copy()

schedule_impact_df = schedule_impact_df.sort_values(
    "downstream_impact_days",
    ascending=False
)


st.write("#### 다음 공정 계획 일정과 충돌한 항목")

schedule_display = schedule_impact_df[
    [
        "part_id",
        "part_name",
        "process",
        "actual_date",
        "next_process",
        "next_plan_date",
        "downstream_impact_days",
        "downstream_status"
    ]
].copy().rename(columns=COLUMN_KR)

schedule_display["후속일정 침범일수"] = (
    schedule_display["후속일정 침범일수"]
    .astype(int)
)

def highlight_schedule_cells(data):

    styles = pd.DataFrame(
        "",
        index=data.index,
        columns=data.columns
    )

    styles.loc[
        data["후속일정 침범일수"] > 0,
        "후속일정 침범일수"
    ] = "background-color: #FFF3CD; font-weight: bold;"

    styles.loc[
        data["후속일정 상태"] == "후속 일정 영향 검토",
        "후속일정 상태"
    ] = "background-color: #F8D7DA; font-weight: bold;"

    return styles


styled_schedule_df = (
    schedule_display.style
    .apply(
        highlight_schedule_cells,
        axis=None
    )
    .format(
        {
            "실제완료일": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "",
            "다음공정 계획일": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "",
            "후속일정 침범일수": "{:.0f}"
        }
    )
)


st.dataframe(
    styled_schedule_df,
    use_container_width=True,
    hide_index=True
)


st.caption(
    "※ 현재 공정의 실제 완료일이 다음 공정의 계획일보다 늦은 경우 "
    "'후속 일정 영향 검토'로 표시합니다. "
    "이는 일정상 영향 가능성을 나타내며 실제 지연 원인을 확정하는 것은 아닙니다."
)

st.divider()

# ==============
# 생산현황 요약
# ==============
st.subheader("생산현황 요약")

on_schedule_count = int((df["delay_days"] <= 0).sum())
defect_item_count = int((df["defect_qty"] > 0).sum())
plan_shortfall_count = int((df["actual_qty"] < df["plan_qty"]).sum())

col1, col2, col3, _ = st.columns(4)

col1.metric(
    "계획 미달 항목",
    f"{plan_shortfall_count}건"
)

col2.metric(
    "일정 지연 항목",
    f"{delayed_count}건"
)

col3.metric(
    "불량 발생 항목",
    f"{defect_item_count}건"
)

st.divider()


# ================
# 생산 현황 시각화
# ================
st.subheader("생산실적 시각화")


# 1. 부품별 계획수량 / 실제수량
part_summary = (
    df.groupby("part_name")[["plan_qty", "actual_qty"]]
    .sum()
    .reset_index()
)

part_chart_data = part_summary.melt(
    id_vars="part_name",
    value_vars=["plan_qty", "actual_qty"],
    var_name="구분",
    value_name="수량"
)

st.write("#### 부품별 계획 대비 생산실적")

part_chart = alt.Chart(part_chart_data).mark_bar().encode(
    x=alt.X(
        "part_name:N",
        title="부품",
        axis=alt.Axis(labelAngle=0)
    ),
    y=alt.Y(
        "수량:Q",
        title="수량"
    ),
    xOffset="구분:N",
    color=alt.Color(
        "구분:N",
        title="구분",
        scale=alt.Scale(
            domain=["plan_qty", "actual_qty"],
            range=["#3C88B3", "#103074"]
        )
    ),
    tooltip=[
        alt.Tooltip("part_name:N", title="부품"),
        alt.Tooltip("구분:N", title="구분"),
        alt.Tooltip("수량:Q", title="수량")
    ]
)

st.altair_chart(
    part_chart,
    use_container_width=True
)


# 2. 공정별 평균 생산달성률
process_summary = (
    df.groupby("process")["achievement_rate"]
    .mean()
    .round(1)
    .reset_index()
)

st.write("#### 공정별 평균 생산달성률")

process_chart = alt.Chart(process_summary).mark_bar(color="#3658B9").encode(
    x=alt.X(
        "process:N",
        title="공정",
        axis=alt.Axis(labelAngle=0)
    ),
    y=alt.Y(
        "achievement_rate:Q",
        title="평균 생산달성률 (%)",
        scale=alt.Scale(domain=[0, 100])
    ),
    tooltip=[
        alt.Tooltip("process:N", title="공정"),
        alt.Tooltip(
            "achievement_rate:Q",
            title="평균 생산달성률",
            format=".1f"
        )
    ]
)

st.altair_chart(
    process_chart,
    use_container_width=True
)

st.divider()


# ======================
# 생산 부하 및 공수 분석
# ======================
st.subheader("생산 부하 및 공수 분석")

overload_df = (
    df[df["load_status"] == "과부하"]
    .sort_values("load_rate", ascending=False)
)

overload_count = len(overload_df)
max_load_rate = df["load_rate"].max()
total_shortage_hours = df["shortage_hours"].sum()

col1, col2, col3, _ = st.columns(4)

col1.metric(
    "과부하 항목 수",
    f"{overload_count}건"
)

col2.metric(
    "최대 계획 부하율",
    f"{max_load_rate:.1f}%"
)

col3.metric(
    "총 부족공수",
    f"{total_shortage_hours:.1f}시간"
)

st.write("#### 계획 부하가 가용공수를 초과한 항목")

overload_display = overload_df[
    [
        "part_id",
        "part_name",
        "process",
        "planned_load_hours",
        "available_hours",
        "load_rate",
        "shortage_hours",
        "load_status"
    ]
].copy().rename(columns=COLUMN_KR)

styled_overload_df = (
    overload_display.style
    .format(
        {
            "계획소요공수(h)": "{:.2f}",
            "가용공수(h)": "{:.2f}",
            "계획부하율(%)": "{:.1f}%",
            "부족공수(h)": "{:.2f}"
        }
    )
)

st.dataframe(
    styled_overload_df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "※ 계획 소요공수 = 계획수량 × 단위 표준공수 / "
    "계획 부하율 = 계획 소요공수 ÷ 가용공수 × 100. "
    "계획 소요공수가 가용공수를 초과하는 경우 과부하로 표시합니다."
)

# =======================
# 부품별 공정 부하 시각화
# =======================

st.write("#### 부품별 공정 부하 현황")

process_order = [
    "가공",
    "표면처리",
    "조립",
    "도장",
    "검사",
    "출하"
]

heatmap_data = df.copy()

heatmap_data["load_rate_label"] = (
    heatmap_data["load_rate"].map(lambda x: f"{x:.1f}%")
)

heatmap = alt.Chart(heatmap_data).mark_rect().encode(

    x=alt.X(
        "process:N",
        title="공정",
        sort=process_order,
        axis=alt.Axis(labelAngle=0)
    ),

    y=alt.Y(
        "part_name:N",
        title=None,
        axis=alt.Axis(labelAngle=0)
    ),

    color=alt.condition(
        alt.datum.load_rate > 100,
        alt.value("#E9A3A3"),
        alt.value("#DDE4F0")
    ),

    tooltip=[
        alt.Tooltip(
            "part_id:N",
            title="부품 ID"
        ),
        alt.Tooltip(
            "part_name:N",
            title="부품명"
        ),
        alt.Tooltip(
            "process:N",
            title="공정"
        ),
        alt.Tooltip(
            "planned_load_hours:Q",
            title="계획 소요공수",
            format=".1f"
        ),
        alt.Tooltip(
            "available_hours:Q",
            title="가용공수",
            format=".1f"
        ),
        alt.Tooltip(
            "load_rate:Q",
            title="계획 부하율",
            format=".1f"
        )
    ]
)

# 셀 안에 부하율 숫자 표시
heatmap_text = alt.Chart(heatmap_data).mark_text(
    fontSize=12,
    color="#091A3B"
).encode(

    x=alt.X(
        "process:N",
        sort=process_order,
        axis=alt.Axis(labelAngle=0)
    ),

    y=alt.Y(
        "part_name:N",
        title=None,
        axis=alt.Axis(labelAngle=0)
    ),

    text="load_rate_label:N"
)


final_heatmap = (
    heatmap
    + heatmap_text
).properties(
    height=300
)

st.altair_chart(
    final_heatmap,
    use_container_width=True
)

st.caption(
    "※ 빨간색은 계획 소요공수가 가용공수를 초과한 항목입니다. "
    "색상은 시각적 강조를 위한 것이며 기업의 공식 위험등급을 의미하지 않습니다."
)

st.divider()


# ==============
# 우선 검토 대상
# ==============
st.subheader("Bottleneck 및 생산현안 검토")

review_df = (
    df[
        df["review_status"].isin(
            [
                "Bottleneck 검토",
                "부하 검토",
                "일정 검토",
                "품질 검토"
            ]
        )
    ]
    .sort_values(
        ["bottleneck_review", "load_rate", "delay_days"],
        ascending=[False, False, False]
    )
)

review_display = review_df[
    [
        "part_id",
        "part_name",
        "process",
        "planned_load_hours",
        "available_hours",
        "load_rate",
        "achievement_rate",
        "defect_qty",
        "defect_rate",
        "delay_days",
        "review_status"
    ]
].copy().rename(columns=COLUMN_KR)


def highlight_important_cells(data):

    styles = pd.DataFrame(
        "",
        index=data.index,
        columns=data.columns
    )

    # 계획 부하율 100% 초과
    styles.loc[
        data["계획부하율(%)"] > 100,
        "계획부하율(%)"
    ] = "background-color: #F8D7DA; font-weight: bold;"

    # 일정 지연 발생
    styles.loc[
        data["지연일수"] > 0,
        "지연일수"
    ] = "background-color: #FFF3CD; font-weight: bold;"

    # Bottleneck 검토 대상
    styles.loc[
        data["검토구분"] == "Bottleneck 검토",
        "검토구분"
    ] = "background-color: #F8D7DA; font-weight: bold;"

    return styles


styled_review_df = (
    review_display.style
    .apply(
        highlight_important_cells,
        axis=None
    )
    .format(
        {
            "계획소요공수(h)": "{:.2f}",
            "가용공수(h)": "{:.2f}",
            "계획부하율(%)": "{:.1f}%",
            "생산달성률(%)": "{:.1f}%",
            "불량률(%)": "{:.1f}%"
        }
    )
)

st.dataframe(
    styled_review_df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "※ 검토 구분은 별도의 위험 점수를 적용한 결과가 아닙니다. "
    "계획 부하 초과, 일정 지연, 불량 발생, 계획 미달 여부를 바탕으로 "
    "생산관리자가 확인할 항목을 구분해 표시합니다."
)

st.divider()


# ========================
# 우선 검토 대상 상세 분석
# ========================
st.subheader("생산현안 상세 분석")

review_parts = review_df["part_id"].tolist()

if len(review_parts) > 0:

    selected_part = st.selectbox(
        "분석할 항목을 선택하세요",
        review_parts
    )

    selected_row = review_df[
        review_df["part_id"] == selected_part
    ].iloc[0]

    st.write(
        f"### {selected_row['part_id']} / "
        f"{selected_row['part_name']} / "
        f"{selected_row['process']}"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "생산달성률",
        f"{selected_row['achievement_rate']:.1f}%"
    )

    col2.metric(
        "계획 부하율",
        f"{selected_row['load_rate']:.1f}%"
    )

    col3.metric(
        "불량률",
        f"{selected_row['defect_rate']:.1f}%"
    )

    col4.metric(
        "일정 지연",
        f"{selected_row['delay_days']}일"
    )

    st.write("#### 데이터 기반 자동 확인 결과")

    issues = []

    if selected_row["planned_load_hours"] > selected_row["available_hours"]:
        issues.append(
            f"계획 소요공수 {selected_row['planned_load_hours']:.2f}시간이 "
            f"가용공수 {selected_row['available_hours']:.2f}시간을 초과했습니다. "
            f"계획 부하율은 {selected_row['load_rate']:.1f}%이며 "
            f"부족공수는 {selected_row['shortage_hours']:.2f}시간입니다."
        )

    if selected_row["actual_qty"] < selected_row["plan_qty"]:
        production_gap = int(
            selected_row["plan_qty"] - selected_row["actual_qty"]
        )
        issues.append(
            f"계획 생산량 {int(selected_row['plan_qty'])}개 대비 "
            f"실제 생산량은 {int(selected_row['actual_qty'])}개로 "
            f"{production_gap}개 미달했습니다. "
            f"생산달성률은 {selected_row['achievement_rate']:.1f}%입니다."
        )

    if selected_row["defect_qty"] > 0:
        issues.append(
            f"불량 {int(selected_row['defect_qty'])}개가 발생했으며 "
            f"불량률은 {selected_row['defect_rate']:.1f}%입니다."
        )

    if selected_row["delay_days"] > 0:
        issues.append(
            f"계획 완료일보다 {int(selected_row['delay_days'])}일 지연되었습니다."
        )

    for issue in issues:
        st.warning(issue)


    # ================
    # AI 생산현안 분석
    # ================
    st.write("#### AI 생산현안 분석")

    if st.button("AI 분석 실행"):

        prompt = f"""
당신은 항공기 부품 생산관리 담당자의 의사결정을 지원하는 AI입니다.

아래 데이터는 실제 기업의 내부 데이터가 아니라
항공기 부품 생산환경을 가정하여 만든 가상의 생산 데이터입니다.
실제 KAI, Boeing 또는 다른 항공우주 기업의 내부 생산 기준이라고 표현하지 마세요.

[생산 공정 정보]
부품 ID: {selected_row['part_id']}
부품명: {selected_row['part_name']}
공정: {selected_row['process']}

[생산 계획 및 실적]
계획 생산량: {int(selected_row['plan_qty'])}개
실제 생산량: {int(selected_row['actual_qty'])}개
생산달성률: {selected_row['achievement_rate']:.1f}%

[부하 및 공수]
단위 표준공수: {selected_row['standard_hours']}시간/개
계획 소요공수: {selected_row['planned_load_hours']:.2f}시간
가용공수: {selected_row['available_hours']:.2f}시간
계획 부하율: {selected_row['load_rate']:.1f}%
부족공수: {selected_row['shortage_hours']:.2f}시간
실제 작업공수: {selected_row['actual_load_hours']:.2f}시간

[품질]
불량 수량: {int(selected_row['defect_qty'])}개
불량률: {selected_row['defect_rate']:.1f}%

[일정]
계획 완료일: {selected_row['plan_date'].date()}
실제 완료일: {selected_row['actual_date'].date()}
일정 지연: {int(selected_row['delay_days'])}일

분석 원칙:
- 주어진 데이터만으로 실제 원인을 단정하지 마세요.
- 계획 부하 초과와 실제 실적 저하가 함께 나타나더라도 인과관계로 확정하지 마세요.
- 생산관리자가 추가 확인해야 할 가능성으로만 제시하세요.
- Bottleneck이라고 확정하지 말고 필요하면 "Bottleneck 검토 대상"이라고 표현하세요.
- 설비 고장, 자재 부족, 재작업, 작업자 문제 등 입력에 없는 원인은 발생했다고 제시하지 말고, 필요하면 "추가 확인 항목"으로만 표현하세요.
- 최종 의사결정은 생산관리자가 한다는 전제로 작성하세요.

다음 형식으로 간결하게 분석하세요.

1. 현안 요약
- 핵심 수치를 포함해 2~3문장

2. 가능한 원인 후보
- 최대 3개
- 반드시 "가능성", "확인 필요" 등의 표현 사용

3. 우선 확인사항
- 생산관리자가 확인할 항목을 우선순위 순으로 최대 3개

4. 대응 검토안
- 생산계획 조정, 가용공수 확보, 우선순위 조정,
  후속 일정 영향 검토 등 생산관리 관점의 대안을 최대 3개
- 조정안을 확정적으로 지시하지 말고 검토안으로 제시

수치 표현 규칙:
- 생산달성률, 불량률, 부하율 등 모든 비율은 반드시 소수점 첫째 자리까지 표시하세요.
- 공수(시간) 값은 소수점 둘째 자리까지 표시하세요.
- 입력된 수치를 임의로 정수화하거나 다른 값으로 변경하지 마세요.
- 계획량, 실제량, 불량수량, 지연일수 등 정수 단위 데이터는 원래 값 그대로 표시하세요.

전체 답변은 약 500~700자 내외로 작성하세요.
"""

        try:
            if client is None:
                raise RuntimeError(
                    "OPENAI_API_KEY가 설정되지 않았습니다. "
                    ".env.example을 참고해 프로젝트 루트에 .env 파일을 생성하세요."
                )

            with st.spinner(
                "AI가 생산현안을 분석하고 있습니다..."
            ):

                response = client.responses.create(
                    model="gpt-5-mini",
                    input=prompt
                )

            st.success("AI 분석이 완료되었습니다.")
            st.markdown(response.output_text)

        except Exception as e:
            st.error(
                f"AI 분석 중 오류가 발생했습니다: {e}"
            )

else:
    st.success("현재 우선 검토 대상이 없습니다.")


st.divider()


# ===========
# 전체 데이터
# ===========
st.subheader("전체 생산 데이터 (가상)")

full_display = df[
    [
        "part_id",
        "part_name",
        "process",
        "plan_qty",
        "actual_qty",
        "achievement_rate",
        "standard_hours",
        "planned_load_hours",
        "available_hours",
        "load_rate",
        "shortage_hours",
        "defect_qty",
        "defect_rate",
        "delay_days",
        "load_status",
        "review_status"
    ]
].copy().rename(columns=COLUMN_KR)

styled_full_df = (
    full_display.style
    .format(
        {
            "생산달성률(%)": "{:.1f}%",
            "단위표준공수(h/개)": "{:.3f}",
            "계획소요공수(h)": "{:.2f}",
            "가용공수(h)": "{:.2f}",
            "계획부하율(%)": "{:.1f}%",
            "부족공수(h)": "{:.2f}",
            "불량률(%)": "{:.1f}%"
        }
    )
)

st.dataframe(
    styled_full_df,
    use_container_width=True,
    hide_index=True
)
