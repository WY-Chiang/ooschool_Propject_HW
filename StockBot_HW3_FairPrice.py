import yfinance as yf
import pandas as pd
import numpy as np

# 預設參數 (目標股息率)
TARGET_DIVIDEND_YIELD = 0.05

def score_stock(symbol: str):
    ticker = yf.Ticker(symbol)

    # 嘗試抓取 info，如果失敗則直接return None*3 (score_df, raw_df, Total_Score)
    try:
        info_dict = ticker.info
    except Exception as e:
        print(f"抓取 {symbol} 基礎資訊錯誤: {e}")
        return None, None, None  # 返回三個 None (score_df, raw_df, Total_Score)

    # 財報資料
    try:
        fin = ticker.financials
        bs = ticker.balance_sheet
        cf = ticker.cashflow
        div = ticker.dividends
        # fin.to_csv(f"{ticker}financial.csv") #print financial report
        # bs.to_csv(f"{ticker}balance_sheet.csv") #print balance sheet
        # cf.to_csv(f"{ticker}cash_flow.csv") #pirnt cash flow
    except Exception as e:
        print(f"抓取 {symbol} 財報資料錯誤: {e}")
        return None, None, None

    # --- 0. 取得可用年份 (以 EPS 為主) ---
    try:
        eps = fin.loc["Diluted EPS"].dropna()
        years_available = len(eps)
        window = 5  # 專注於近五年成長率
        if years_available < 2:
            print(f"{symbol} EPS 資料不足，無法評分")
            return None, None, None

        # 取最近 window 年的年份 (從舊到新)
        years = eps.index.year[-window:]

    except Exception:
        print(f"{symbol} EPS 資料不足或格式錯誤")
        return None, None, None

    # 建立結果 DataFrame
    score = {}

    # --- 1. EPS 穩定成長 ---
    eps_sub = eps[eps.index.year.isin(years)]
    eps_sub.index = eps_sub.index.year
    score["EPS: 每年穩定增加"] = 1 if all(eps_sub.diff().dropna() > 0) else 0
    eps_sub_sorted = eps_sub.sort_index(ascending=True) #最新一年在前, 這樣排序 pct_change算法才是對的成長率


    # --- 1.1 EPS平均五年成長率 ---
    eps_growth_rates = eps_sub_sorted.pct_change().dropna()

    # 如果成長率 Series 為空，或平均值為負，則成長率視為 0
    if eps_growth_rates.empty or eps_growth_rates.mean() < 0:
        eps_avg_rate = 0
    else:
        # 取平均，限制在一個合理的上限 (超過15% 則取15%，防止極端值影響) >> 成長型公司另外考慮
        eps_avg_rate = min(eps_growth_rates.mean(), 0.15) # 先取mean(取5年平均)，再跟15%取min(防止極端值)

    # --- 2. Dividends 穩定成長 ---
    latest_dividen = 0.0  # 預設值為 0

    if not div.empty:
        annual_div = div.groupby(div.index.year).sum()
        div_sub = annual_div[annual_div.index.isin(years)]
        # 取得最新一年的股息總和
        if not div_sub.empty:
            latest_dividen = div_sub.iloc[-1]

        score["Dividends: 每年穩定增加"] = 1 if len(div_sub) >= 2 and all(div_sub.diff().dropna() > 0) else 0
    else:
        div_sub = pd.Series(dtype=float)
        score["Dividends: 每年穩定增加"] = 0

    # --- 3. ROE > 20% ---
    try:
        net_income = fin.loc["Net Income"]
        equity = bs.loc["Stockholders Equity"]
        net_sub = net_income[net_income.index.year.isin(years)]
        equity_sub = equity[equity.index.year.isin(years)]
        net_sub.index = net_sub.index.year
        equity_sub.index = equity_sub.index.year
        roe = net_sub / equity_sub
        score["ROE: 每年都>20%"] = 1 if all(roe > 0.2) else 0
    except Exception:
        roe = pd.Series(dtype=float)
        score["ROE: 每年都>20%"] = 0

    # --- 4. Net Margin >20%(+1) or 10%(+0.5) ---
    try:
        revenue = fin.loc["Total Revenue"]
        net_sub = fin.loc["Net Income"]
        revenue_sub = revenue[revenue.index.year.isin(years)]
        net_sub = net_sub[net_sub.index.year.isin(years)]
        revenue_sub.index = revenue_sub.index.year
        net_sub.index = net_sub.index.year
        nm = net_sub / revenue_sub
        if all(nm > 0.2):
            score["Net Margin: 每年>20%(+1), 每年>10%(+0.5)"] = 1
        elif all(nm > 0.1):
            score["Net Margin: 每年>20%(+1), 每年>10%(+0.5)"] = 0.5
        else:
            score["Net Margin: 每年>20%(+1), 每年>10%(+0.5)"] = 0
    except Exception:
        nm = pd.Series(dtype=float)
        score["Net Margin: 每年>20%(+1), 每年>10%(+0.5)"] = 0

    # --- 5. Interest Coverage (>10(+1), >4(+0.5) )---
    try:
        ebit = fin.loc["EBIT"]
        interest = fin.loc["Interest Expense"].abs()
        ebit_sub = ebit[ebit.index.year.isin(years)]
        interest_sub = interest[interest.index.year.isin(years)]
        ic = (ebit_sub / interest_sub).dropna()
        ic.index = ic.index.year
        if all(ic > 10):
            score["IC: >10% (+1), >4 (+0.5)"] = 1
        elif all(ic > 4):
            score["IC: >10% (+1), >4 (+0.5)"] = 0.5
        else:
            score["IC: >10% (+1), >4 (+0.5)"] = 0
    except Exception:
        ic = pd.Series(dtype=float)
        score["IC: >10% (+1), >4 (+0.5)"] = 0

    # --- 6. FCF > 0 (continuously)---
    try:
        op_cf = cf.loc["Cash Flow From Continuing Operating Activities"]
        capex = cf.loc["Capital Expenditure"]
        op_sub = op_cf[op_cf.index.year.isin(years)]
        cap_sub = capex[capex.index.year.isin(years)]
        fcf = op_sub + cap_sub
        fcf.index = fcf.index.year
        score["FCF: 每年>0"] = 1 if all(fcf > 0) else 0
    except Exception:
        fcf = pd.Series(dtype=float)
        score["FCF: 每年>0"] = 0

    # ------------------------------------------------------------------
    # --- 7. 估值計算邏輯 ---
    # ------------------------------------------------------------------

    Total_Score = sum(score.values())

    # 7.1 設定折現率 (Discount Rate / 安全邊際)
    if Total_Score >= 5:
        discount_rate = 0.08  # 8%
    elif Total_Score >= 3:
        discount_rate = 0.10  # 10%
    else:
        discount_rate = 0.12  # <3分，折現率12%

    # 7.2 預期下一年度股息
    # 下一年度的股息預估 = 最新一年的股息 * (1 + EPS 5 年平均成長率)
    # latest_dividen * (1 + eps_avg_rate)
    expected_dividen = latest_dividen * (1 + eps_avg_rate)

    # 7.3 合理價格 (未調整安全邊際) - 基於股息率 5%
    # 合理價格(未調整) = 股息預估 / 目標股息率
    if expected_dividen > 0 and TARGET_DIVIDEND_YIELD > 0:
        fair_price_unadjusted = expected_dividen / TARGET_DIVIDEND_YIELD
    else:
        fair_price_unadjusted = np.nan

    # 7.4 應用安全邊際後的合理價格
    if not np.isnan(fair_price_unadjusted):
        fair_price = fair_price_unadjusted * (1 - discount_rate)
    else:
        fair_price = np.nan

    # 7.5 目前股價
    current_price = info_dict.get('currentPrice')

    # 7.6 是否低於合理價格
    if not np.isnan(fair_price) and current_price is not None:
        is_buy = "Y" if current_price < fair_price else "N"
    else:
        is_buy = "N/A"

    # ------------------------------------------------------------------
    # --- 8. 整合所有數據 ---
    # ------------------------------------------------------------------

    # 評分結果 DataFrame
    score["Total Score"] = Total_Score
    score["Discount Rate"] = f"{discount_rate:.0%}"  # 顯示為百分比
    score["EPS avg Growth Rate"] = f"{eps_avg_rate:.2%}"  # 顯示為百分比
    score["Latest yearly dividen"] = latest_dividen
    score["Estimated dividen"] = expected_dividen
    score["Fair Price(yield 5%))"] = fair_price
    score["Current Price"] = current_price
    score["Current < Fair?"] = is_buy

    score_df = pd.DataFrame(score, index=[symbol])

    # raw data DataFrame
    raw_df = pd.DataFrame({
        "EPS 原始資料": eps_sub,
        "Dividen 原始資料": div_sub,
        "ROE 原始資料": roe,
        "Net Margin 原始資料": nm,
        "Free Cash flow 原始資料": fcf,
        "Interest Coverage 原始資料": ic,
    })
    raw_df.index.name = "Year"
    raw_df["Symbol"] = symbol
    raw_df = raw_df.sort_index(ascending=True)  # raw data排序(最新一年在前)

    return score_df, raw_df, Total_Score

# =================== 有符號的股票代碼處理(ex:yfinance是 BRK-B ) ===================
def normalize_symbol(symbol:str) -> str:
    return symbol.replace(".", "-") #BRK.B -> BRK-B

# =================== 主程式 ===================
if __name__ == "__main__":
    stock_symbol = input("Please input stock Symbol(用逗號 ',' 分隔): ").strip().upper().split(",")

    all_scores = []
    all_raws = []
    A_company = []
    B_company = []
    C_company = []

    for symbol in stock_symbol:
        symbol = symbol.strip()
        symbol = normalize_symbol(symbol)
        # 呼叫函數並接收三個返回值 (score_df, raw_df, Total_Score)
        score_df, raw_df, Total_Score = score_stock(symbol)

        if score_df is not None:
            all_scores.append(score_df)

            # 將 raw_df 處理並加入 all_raws (空行分隔)
            empty_row = pd.DataFrame([[""] * len(raw_df.columns)], columns=raw_df.columns, index=[""])
            raw_with_blank = pd.concat([raw_df, empty_row])
            all_raws.append(raw_with_blank)

            # 判斷公司等級
            if Total_Score >= 5:
                A_company.append(symbol)
            elif Total_Score >= 3:
                B_company.append(symbol)
            else:
                C_company.append(symbol)



    if all_scores:
        final_scores = pd.concat(all_scores)
        final_raws = pd.concat(all_raws)

        # ---合理價格公司清單--- 用布林遮罩for dataframe較簡潔
        is_undervalued = final_scores["Current < Fair?"] == "Y"
        undervalued_stock = final_scores.loc[is_undervalued].index
        undervalued_stock_list = undervalued_stock.tolist()

        print("-" * 50)
        print(f"5分以上 A 級好公司: {A_company}, 折現率8%")
        print(f"3分以上 B 級好公司: {B_company}, 折現率10%")
        print(f"3分以下 C 級公司: {C_company}, 折現率12%")
        print(f"目前是合理價格公司:{undervalued_stock_list}")
        print("-" * 50)

        # 輸出到 CSV 檔案
        file_symbol_name = "_".join([s.strip() for s in stock_symbol if s.strip()])

        # ----評分和估值(score)放在一個檔案，原始數據(raw)放在另一個檔案。----
        final_scores.to_csv(f"Report_Summary_{file_symbol_name}.csv", float_format='%.2f')
        final_raws.to_csv(f"Report_RawData_{file_symbol_name}.csv")

        print(f"評分與估值結果已儲存至: Report_Summary_{file_symbol_name}.csv")
        print(f"原始數據已儲存至: Report_RawData_{file_symbol_name}.csv")

    else:
        print("沒有取得任何股票資料")

        #VZ,JNJ,PFE,AMGN,T,XOM,CVX,MO,KO,VICI,PEP
        #BRKB算不出fair price -> check