import yfinance as yf
import pandas as pd
from pyasn1_modules.rfc5280 import anotherNameMap

stock_symbol = input("Please input stock Symbol: ")
ticker = yf.Ticker(stock_symbol)

# 財務資料
BS = ticker.balance_sheet
Fin = ticker.financials
CF = ticker.cashflow

Net_income = Fin.loc["Net Income"].dropna()
Revenue = Fin.loc["Total Revenue"].dropna()
Equity = BS.loc["Stockholders Equity"].dropna()
Op_CF = CF.loc["Operating Cash Flow"].dropna()
CapitalEx = CF.loc["Capital Expenditure"].dropna()
EBIT = Fin.loc["EBIT"].dropna()
InterEX = Fin.loc["Interest Expense"].dropna()

# ======== 整理數據 ========
Diluted_EPS = Fin.loc["Diluted EPS"].dropna()
Diluted_EPS.index = Diluted_EPS.index.year


dividen = ticker.dividends
annual_dividen = dividen.groupby(dividen.index.year).sum()

ROE = (Net_income / Equity * 100).dropna()
Net_margin = (Net_income / Revenue * 100).dropna()
FCF = (Op_CF + CapitalEx).dropna()
InterCover = (EBIT / InterEX).dropna()




# ======== 計算使用年份區間 ========
all_years = sorted(set(
    list(Diluted_EPS.index) +
    list(annual_dividen.index) +
    [i.year for i in ROE.index] +
    [i.year for i in Net_margin.index] +
    [i.year for i in FCF.index] +
    [i.year for i in InterCover.index]
))

if len(all_years) >= 10:
    years = all_years[-10:]
else:
    years = all_years[-5:]

# ======== 打分規則 ========

# EPS 穩定成長
eps_sub = Diluted_EPS[ Diluted_EPS.index.isin(years) ].dropna()
eps_score = 1 if all(eps_sub.iloc[i] > eps_sub.iloc[i-1] for i in range(1, len(eps_sub))) else 0


# Dividends 穩定成長
div_sub = annual_dividen[ annual_dividen.index.isin(years) ].dropna()
div_score = 1 if all(div_sub.iloc[i] > div_sub.iloc[i-1] for i in range(1, len(div_sub))) else 0

# ROE >20%
roe_sub = ROE[ ROE.index.year.isin(years) ].dropna()
roe_score = 1 if len(roe_sub) == len(years) and all(roe_sub > 20) else 0

# Net Margin
nm_sub  = Net_margin[ Net_margin.index.year.isin(years) ].dropna()

if len(nm_sub) == len(years):
    if all(nm_sub > 20):
        net_margin_score = 1
    elif all(nm_sub > 10):
        net_margin_score = 0.5
    else:
        net_margin_score = 0
else:
    net_margin_score = 0

# Interest Coverage
ic_sub  = InterCover[ InterCover.index.year.isin(years) ].dropna()
if len(ic_sub) == len(years):
    if all(ic_sub > 10):
        ic_score = 1
    elif all(ic_sub > 4):
        ic_score = 0.5
    else:
        ic_score = 0
else:
    ic_score = 0

# FCF >0
fcf_sub = FCF[ FCF.index.year.isin(years) ].dropna()
fcf_score = 1 if len(fcf_sub) == len(years) and all(fcf_sub > 0) else 0

# ======== 總分 ========
total_score = eps_score + div_score + roe_score + net_margin_score + ic_score + fcf_score

# ======== 輸出結果 ========
df = pd.DataFrame({
    "EPS": [eps_score],
    "Dividends": [div_score],
    "ROE": [roe_score],
    "Net Margin": [net_margin_score],
    "Interest Coverage": [ic_score],
    "FCF": [fcf_score],
    "Total Score": [total_score]
}, index=[f"{len(years)}Y Window"])

print(df)
