"""
Club Budget Tracker
활용
Arc Operation team 의 회계 부분에서 매 학기 회비·지원금 수입과
행사·식비 지출을 추적하고, 임원진이 예산 집행 현황을
한눈에 볼 수 있도록 만들었습니다.
"""

import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt


#  1. 데이터 불러오기 
def load_transactions(csv_path):
    """CSV를 읽어서 날짜 파싱하고 정렬합니다."""
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    # 'type'은 income / expense
    df["type"] = df["type"].str.lower()
    return df


#  2. 잔액 계산 
def calculate_balance(df):
    """총 수입, 총 지출, 현재 잔액을 계산합니다."""
    income = df.loc[df["type"] == "income", "amount"].sum()
    expense = df.loc[df["type"] == "expense", "amount"].sum()
    balance = income - expense
    return income, expense, balance


#  3. 카테고리별 집계 
def summarize_by_category(df):
    """지출을 카테고리별로 묶어서 큰 순서대로 정렬합니다."""
    expenses = df[df["type"] == "expense"]
    by_cat = (
        expenses.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )
    return by_cat


#  4. 월별 집계 
def monthly_summary(df):
    """월별 수입/지출/순현금흐름 표를 만듭니다."""
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    pivot = df.pivot_table(
        index="month", columns="type", values="amount",
        aggfunc="sum", fill_value=0
    )
    for col in ["income", "expense"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["net"] = pivot["income"] - pivot["expense"]
    return pivot[["income", "expense", "net"]]


#  5. 예산 대비 실적 
def budget_vs_actual(df, budgets):
    """카테고리별 예산과 실제 지출을 비교합니다."""
    actual = summarize_by_category(df)
    rows = []
    for cat, planned in budgets.items():
        spent = float(actual.get(cat, 0))
        rows.append({
            "category": cat,
            "budget": planned,
            "actual": spent,
            "remaining": planned - spent,
            "used_%": round(spent / planned * 100, 1) if planned else 0,
        })
    return pd.DataFrame(rows)


#  6. 차트 생성 
def generate_charts(df, by_cat, monthly):
    """지출 구성 파이차트 + 월별 현금흐름 막대차트를 저장합니다."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # 작은 카테고리(전체 3% 미만)는 'Other'로 묶어서 라벨 겹침을 방지합니다
    total = by_cat.sum()
    big = by_cat[by_cat / total >= 0.03]
    small = by_cat[by_cat / total < 0.03]
    if not small.empty:
        big = pd.concat([big, pd.Series({"Other": small.sum()})])

    # 카테고리별 지출 파이차트
    axes[0].pie(big.values, labels=big.index, autopct="%1.0f%%",
                startangle=90, pctdistance=0.8)
    axes[0].set_title("Expenses by Category")

    # 월별 수입 vs 지출 막대차트
    x = range(len(monthly))
    width = 0.35
    axes[1].bar([i - width/2 for i in x], monthly["income"],
                width, label="Income", color="#4C9F70")
    axes[1].bar([i + width/2 for i in x], monthly["expense"],
                width, label="Expense", color="#D1495B")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(monthly.index, rotation=45, ha="right")
    axes[1].set_title("Monthly Income vs Expense")
    axes[1].set_ylabel("Amount")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig("budget_report.png", dpi=130, bbox_inches="tight")
    plt.close()


#  7. 텍스트 보고서 
def generate_report(df, budgets=None):
    """콘솔에 재무 요약 보고서를 출력합니다."""
    income, expense, balance = calculate_balance(df)
    by_cat = summarize_by_category(df)
    monthly = monthly_summary(df)

    print("=" * 48)
    print("        CLUB FINANCIAL REPORT")
    print("=" * 48)
    print(f"Period: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"Transactions: {len(df)}")
    print("-" * 48)
    print(f"Total Income : {income:>10,.0f}")
    print(f"Total Expense: {expense:>10,.0f}")
    print(f"Balance      : {balance:>10,.0f}")
    print("-" * 48)
    print("Expenses by Category:")
    for cat, amt in by_cat.items():
        share = amt / expense * 100
        print(f"  {cat:<16} {amt:>8,.0f}  ({share:4.1f}%)")
    print("-" * 48)
    print("Monthly Summary:")
    print(monthly.to_string())

    if budgets:
        print("-" * 48)
        print("Budget vs Actual:")
        print(budget_vs_actual(df, budgets).to_string(index=False))

    print("=" * 48)

    generate_charts(df, by_cat, monthly)
    print("Chart saved -> budget_report.png")


#  8. PDF 보고서 생성 
def generate_pdf(df, budgets=None, filename="budget_report.pdf"):
    """재무 요약 + 예산표 + 차트를 PDF 한 장으로 저장합니다."""
    income, expense, balance = calculate_balance(df)
    by_cat = summarize_by_category(df)
    monthly = monthly_summary(df)

    fig = plt.figure(figsize=(8.27, 11.69))  # A4 세로 크기
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 0.9, 1.3],
                          hspace=0.45, wspace=0.3)

    # --- 상단: 제목 + 요약 수치 ---
    ax_top = fig.add_subplot(gs[0, :])
    ax_top.axis("off")
    period = f"{df['date'].min().date()} ~ {df['date'].max().date()}"
    ax_top.text(0.5, 1.0, "CLUB FINANCIAL REPORT", ha="center", va="top",
                fontsize=18, fontweight="bold")
    ax_top.text(0.5, 0.75, f"Period: {period}   |   Transactions: {len(df)}",
                ha="center", va="top", fontsize=10, color="#555555")
    summary = (f"Total Income :  {income:>10,.0f}\n"
               f"Total Expense:  {expense:>10,.0f}\n"
               f"Balance      :  {balance:>10,.0f}")
    ax_top.text(0.5, 0.5, summary, ha="center", va="top",
                fontsize=12, family="monospace")

    # --- 중간: 예산 대비 실적 표 ---
    ax_tbl = fig.add_subplot(gs[1, :])
    ax_tbl.axis("off")
    if budgets:
        bva = budget_vs_actual(df, budgets)
        cell_text = [
            [r["category"], f"{r['budget']:,.0f}", f"{r['actual']:,.0f}",
             f"{r['remaining']:,.0f}", f"{r['used_%']:.1f}%"]
            for _, r in bva.iterrows()
        ]
        tbl = ax_tbl.table(
            cellText=cell_text,
            colLabels=["Category", "Budget", "Actual", "Remaining", "Used %"],
            loc="center", cellLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.scale(1, 1.6)
        ax_tbl.set_title("Budget vs Actual", fontsize=11, fontweight="bold")

    # --- 하단: 파이차트 + 막대차트 ---
    total = by_cat.sum()
    big = by_cat[by_cat / total >= 0.03]
    small = by_cat[by_cat / total < 0.03]
    if not small.empty:
        big = pd.concat([big, pd.Series({"Other": small.sum()})])

    ax_pie = fig.add_subplot(gs[2, 0])
    ax_pie.pie(big.values, labels=big.index, autopct="%1.0f%%",
               startangle=90, pctdistance=0.8, textprops={"fontsize": 8})
    ax_pie.set_title("Expenses by Category", fontsize=10)

    ax_bar = fig.add_subplot(gs[2, 1])
    x = range(len(monthly))
    width = 0.4
    ax_bar.bar([i - width/2 for i in x], monthly["income"], width,
               label="Income", color="#4C9F70")
    ax_bar.bar([i + width/2 for i in x], monthly["expense"], width,
               label="Expense", color="#D1495B")
    ax_bar.set_xticks(list(x))
    ax_bar.set_xticklabels(monthly.index, rotation=45, ha="right", fontsize=7)
    ax_bar.set_title("Monthly Income vs Expense", fontsize=10)
    ax_bar.legend(fontsize=8)

    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)
    print(f"PDF saved -> {filename}")


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "sample_transactions.csv"
    df = load_transactions(csv_path)

    # 카테고리별 예산 (직접 수정해서 쓰면 됩니다.)
    budgets = {
        "event": 6500,
        "food": 3000,
        "marketing": 1200,
        "supplies": 1000,
        "equipment": 500,
    }

    generate_report(df, budgets)
    generate_pdf(df, budgets)


if __name__ == "__main__":
    main()