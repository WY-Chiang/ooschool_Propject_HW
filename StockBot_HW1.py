import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from PIL.ImageMath import lambda_eval
from matplotlib.lines import lineStyles
from matplotlib.pyplot import figure

#### testtesetestestste


#General
AAPL = yf.Ticker("AAPL")
AAPL_bs =AAPL.balancesheet
AAPL_fin = AAPL.financials # print(AAPL_fin.info)#yfinance裡面的內容
AAPL_cf = AAPL.cashflow
AAPL_net_income = AAPL_fin.loc["Net Income"]
AAPL_revenue = AAPL_fin.loc["Total Revenue"]
AAPL_fin.to_csv("AAPL_Financials.csv")
AAPL_bs.to_csv("AAPL_Balancesheet.csv")
AAPL_cf.to_csv("AAPL_CashFlow.csv")
#General

# EPS, 10yrs stable growth
Diluted_EPS = AAPL.financials.loc["Diluted EPS"] # 5年DPS
# for year, eps in Diluted_EPS.items(): #印出5年EPS, 好看模式
#     if pd.notna(eps):
#         print(f"{year.year}, EPS: {eps}")
# EPS

#Dividens, 10yrs stable growth
dividen = AAPL.dividends
annual_dividen = dividen.groupby(dividen.index.year).sum() # 每年dividen sum
annual_dividens = annual_dividen.loc[2015:2025] # 2015~2025 dividen

#Dividens

#Free Cashflow, 10yrs are positive
AAPL_op_cf = AAPL_cf.loc["Operating Cash Flow"]
AAPL_capitalEx = AAPL_cf.loc["Capital Expenditure"]
AAPL_FCF = AAPL_op_cf + AAPL_capitalEx
#Free Cashflow

#ROE, >15%
AAPL_equity = AAPL_bs.loc["Stockholders Equity"]
AAPL_ROE = AAPL_net_income / AAPL_equity *100
#ROE

#Interest coverage, >10, at least >4
AAPL_EBIT = AAPL_fin.loc["EBIT"]
AAPL_InterEX = AAPL_fin.loc["Interest Expense"]
AAPL_InterCover = AAPL_EBIT/AAPL_InterEX
#Interest coverage


#Net Margin, >20%, or >10% and keep growing up

net_margin = (AAPL_net_income / AAPL_revenue) *100
#Net Margin

'''
# Print Value
print(f"EPS: \n{Diluted_EPS}")
print(f"Dividens: \n {annual_dividens}") # 印出10年Dividen
print(f"FCF: \n {AAPL_FCF}")
print(f"ROE: \n {AAPL_ROE.map(lambda x : f"{x:.2f}%")}")
print(f"Interest Coverage: \n {AAPL_InterCover}")
print(f"Net Margin: \n {net_margin.map(lambda x: f"{x:.2f}%")}")
# Print Value
#根據圖表與數據撰寫簡易分析報告，說明資料趨勢和簡單投資判斷要點
'''

print("5-year data:\n"
      "EPS keeps growing: 1 pt\n"
      "dividends keep growing: 1 pt\n"
      "FCF is sufficient: 1 point\n"
      "ROE over 15%: 1 pt; ROE over 100%, need to look into the reasons.\n"
      "IC ratio > 10%: 1 pt\n"
      "Net margin > 20%: 1 pt\n")
print("AAPL Ｂasic financial score: 6 points")
#DashBoard

#General, figure
plt.rcParams.update({'font.size': 9})  # 全域字體大小
fig, ax = plt.subplots(2,3,figsize = (14,8)) #width: 14 inch, height: 8 inch

fig.suptitle("AAPL Financial Dashboard", fontsize = 14, fontweight = "bold")

#ax
ax[0,0].plot(Diluted_EPS, marker ="o")
ax[0,0].set_title("EPS")
ax[0,0].set_xlabel("year")
ax[0,0].set_ylabel("%")

ax[0,1].bar(annual_dividens.index, annual_dividens)
ax[0,1].set_title("Annual Dividens")
ax[0,1].set_xlabel("year")
ax[0,1].set_ylabel("USD")

ax[0,2].plot(AAPL_FCF, marker ="o")
ax[0,2].set_title("Free Cash Flow")
ax[0,2].set_xlabel("year")
ax[0,2].set_ylabel("USD")

ax[1,0].plot(AAPL_ROE, marker ="o")
ax[1,0].set_title("ROE")
ax[1,0].set_xlabel("year")
ax[1,0].set_ylabel("%")

ax[1,1].plot(AAPL_InterCover, marker ="o")
ax[1,1].set_title("Interest Coverage")
ax[1,1].set_xlabel("year")
ax[1,1].set_ylabel("USD")

ax[1,2].plot(net_margin, marker ="o")
ax[1,2].set_title("Net Margin")
ax[1,2].set_xlabel("year")
ax[1,2].set_ylabel("%")


plt.tight_layout(rect=[0, 0, 1, 0.96]) #自動調整間距
plt.show()
