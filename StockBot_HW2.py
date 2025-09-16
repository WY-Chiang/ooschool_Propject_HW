import yfinance as yf
import pandas as pd

def score_stock(symbol: str):
    ticker = yf.Ticker(symbol)

    # 財報資料
    try:
        fin = ticker.financials  # 包含 Diluted EPS, Net Income, Revenue, EBIT, Interest Expense
        bs = ticker.balance_sheet  # Stockholders Equity
        cf = ticker.cashflow  # Operating Cash Flow, Capital Expenditure
        div = ticker.dividends  # 股息
        fin.to_csv(f"{ticker}financial.csv")
    except Exception as e:
        print(f"抓取資料錯誤: {e}")
        return None

    # 取得可用年份 (以 EPS 為主)
    try:
        eps = fin.loc["Diluted EPS"].dropna()
        years_available = len(eps)
        window = 10 if years_available >= 10 else min(5, years_available)
        years = eps.index.year[-window:]
    except Exception:
        print("EPS 資料不足")
        return None

    # 建立結果 DataFrame (以年份為 index)
    score = {}

    # --- 1. EPS 穩定成長 ---
    eps_sub = eps[eps.index.year.isin(years)]
    eps_sub.index = eps_sub.index.year
    score["EPS Score"] = 1 if all(eps_sub.diff().dropna() > 0) else 0

    # --- 2. Dividends 穩定成長 ---
    if not div.empty:
        annual_div = div.groupby(div.index.year).sum()
        div_sub = annual_div[annual_div.index.isin(years)]
        div_sub.index.name = "Year"  # 設定 index 名稱

        score["Dividends Score"] = 1 if len(div_sub) >= 2 and all(div_sub.diff().dropna() > 0) else 0
    else:
        div_sub = pd.Series(dtype=float)
        score["Dividends Score"] = 0

    # --- 3. ROE > 20% ---
    try:
        net_income = fin.loc["Net Income"]
        equity = bs.loc["Stockholders Equity"]
        net_sub = net_income[net_income.index.year.isin(years)]
        equity_sub = equity[equity.index.year.isin(years)]
        net_sub.index = net_sub.index.year
        equity_sub.index = equity_sub.index.year
        roe = net_sub / equity_sub
        score["ROE Score"] = 1 if all(roe > 0.2) else 0
    except Exception:
        roe = pd.Series(dtype=float)
        score["ROE Score"] = 0

    # --- 4. Net Margin >20%(+1) or 10%(+0.5) ---
    try:
        revenue = fin.loc["Total Revenue"]
        net_sub = fin.loc["Net Income"]
        revenue_sub = revenue[revenue.index.year.isin(years)]
        net_sub = net_sub[net_sub.index.year.isin(years)]
        revenue_sub.index = revenue_sub.index.year
        net_sub.index = net_sub.index.year
        nm = net_sub / revenue_sub
        print(nm)
        if all(nm > 0.2):
            score["Net Margin Score"] = 1
        elif all(nm > 0.1):
            score["Net Margin Score"] = 0.5
        else:
            score["Net Margin Score"] = 0
    except Exception:
        nm = pd.Series(dtype=float)
        score["Net Margin Score"] = 0

    # --- 5. Interest Coverage (>10(+1), >4(+0.5) )---
    try:
        ebit = fin.loc["EBIT"]
        interest = fin.loc["Interest Expense"].abs()
        ebit_sub = ebit[ebit.index.year.isin(years)]
        interest_sub = interest[interest.index.year.isin(years)]
        ic = (ebit_sub / interest_sub).dropna()
        ic.index = ic.index.year
        print(ebit)
        print(interest_sub)
        print(ic)
        if all(ic > 10):
            score["IC Score"] = 1
        elif all(ic > 4):
            score["IC Score"] = 0.5
        else:
            score["IC Score"] = 0
    except Exception:
        ic = pd.Series(dtype=float)
        score["IC Score"] = 0

    # --- 6. FCF > 0 (continuously)---
    try:
        op_cf = cf.loc["Cash Flow From Continuing Operating Activities"]
        capex = cf.loc["Capital Expenditure"]
        op_sub = op_cf[op_cf.index.year.isin(years)]
        cap_sub = capex[capex.index.year.isin(years)]
        # op_sub.index = op_sub.index.year
        # cap_sub.index = cap_sub.index.year
        fcf = op_sub + cap_sub
        fcf.index = fcf.index.year
        score["FCF Score"] = 1 if all(fcf > 0) else 0
    except Exception:
        fcf = pd.Series(dtype=float)
        score["FCF Score"] = 0

    # 總分
    score["Total Score"] = sum(score.values())
    score_df = pd.DataFrame({f"{window}Y Window": score}).T

    #raw data
    raw_df = pd.DataFrame({
        "EPS":eps_sub,
        "Dividen" : div_sub,
        "ROE": roe,
        "Net Margin": nm,
        "Free Cash flow": fcf,
        "Interest Coverage": ic,
    })
    raw_df.index.name = "Year"

    return score_df, raw_df

# =================== 主程式 ===================
if __name__ == "__main__":
    stock_symbol = input("Please input stock Symbol: ").strip().upper()
    score_df, raw_df = score_stock(stock_symbol)
    print("分數")
    print(score_df)
    print("原始資料")
    print(raw_df)

    score_df.to_csv(f"Report_{stock_symbol}_score.csv")
    raw_df.to_csv(f"Report_{stock_symbol}_raw.csv")

