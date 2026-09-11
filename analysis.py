import pandas as pd

# Excel 데이터 불러오기
df = pd.read_excel("data/production_data.xlsx")

# 날짜 형식 변환
df["plan_date"] = pd.to_datetime(df["plan_date"])
df["actual_date"] = pd.to_datetime(df["actual_date"])

# 주요 지표 계산
df["achievement_rate"] = (df["actual_qty"] / df["plan_qty"]) * 100
df["defect_rate"] = (df["defect_qty"] / df["actual_qty"]) * 100
df["delay_days"] = (df["actual_date"] - df["plan_date"]).dt.days

# 소수점 정리
df["achievement_rate"] = df["achievement_rate"].round(1)
df["defect_rate"] = df["defect_rate"].round(1)


# 생산달성률 평가
def evaluate_achievement(rate):
    if rate >= 95:
        return "정상"
    elif rate >= 90:
        return "주의"
    else:
        return "위험"


# 불량률 평가
def evaluate_defect(rate):
    if rate <= 1:
        return "정상"
    elif rate <= 3:
        return "주의"
    else:
        return "위험"


# 납기 평가
def evaluate_delivery(days):
    if days <= 0:
        return "정상"
    elif days == 1:
        return "주의"
    else:
        return "위험"


df["achievement_status"] = df["achievement_rate"].apply(evaluate_achievement)
df["defect_status"] = df["defect_rate"].apply(evaluate_defect)
df["delivery_status"] = df["delay_days"].apply(evaluate_delivery)


# 최종 위험도 평가
def evaluate_total(row):
    status_list = [
        row["achievement_status"],
        row["defect_status"],
        row["delivery_status"]
    ]

    if "위험" in status_list:
        return "위험"
    elif "주의" in status_list:
        return "주의"
    else:
        return "정상"


df["total_status"] = df.apply(evaluate_total, axis=1)


# 전체 결과 출력
print("\n=== 생산관리 분석 결과 ===")

print(
    df[
        [
            "part_id",
            "part_name",
            "process",
            "achievement_rate",
            "achievement_status",
            "defect_rate",
            "defect_status",
            "delay_days",
            "delivery_status",
            "total_status"
        ]
    ]
)


# 전체 납기준수율 OTD 계산
on_time_count = (df["delay_days"] <= 0).sum()
total_count = len(df)

otd = (on_time_count / total_count) * 100

print("\n=== 전체 KPI ===")
print(f"납기준수율(OTD): {otd:.1f}%")