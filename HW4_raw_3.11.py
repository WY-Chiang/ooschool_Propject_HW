import yfinance as yf
import pandas as pd
import numpy as np
import datetime

QUARTERS_WINDOW = 2*4  # 最近5年 = 20季
TARGET_HORIZON_Q = 1  # 下一季回報

def normalize_symbol(symbol: str) -> str:
    return symbol.replace(".", "-").strip().upper()

def ensure_datetime_index(s: pd.Series) -> pd.Series:
    s = s.copy()
    try:
        s.index = pd.to_datetime(s.index)
    except Exception:
        pass
    return s

def fetch_price_quarterly(symbol: str, years_back: int = 1) -> pd.Series:
    ticker_hist = yf.Ticker(symbol)
    start_date = datetime.datetime.now() - datetime.timedelta(days=years_back*365)
    hist = ticker_hist.history(start=start_date)
    if hist.empty:
        return pd.Series(dtype=float)
    hist.index = pd.to_datetime(hist.index)
    quarter_ends = hist['Close'].resample('Q').last()
    quarter_ends.index = quarter_ends.index.to_period('Q').to_timestamp('Q')
    return quarter_ends

def build_quarterly_dataset(symbol: str, save_csv: bool = True) -> pd.DataFrame:
    symbol = normalize_symbol(symbol)
    ticker = yf.Ticker(symbol)

    # 財報抓取
    try:
        qfin, qbs, qcf = ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow
        for df in (qfin, qbs, qcf):
            if df is not None and not df.empty:
                df.columns = pd.to_datetime(df.columns)
    except Exception as e:
        raise RuntimeError(f"{symbol} 季報抓取錯誤: {e}")

    def safe_row(df, row_names):
        if df is None or df.empty:
            return pd.Series(dtype=float)
        for name in row_names:
            if name in df.index:
                s = df.loc[name].dropna()
                s.index = pd.to_datetime(s.index)
                return s
        return pd.Series(dtype=float)

    # 取各類財報資料
    eps_q = safe_row(qfin, ["Diluted EPS", "Basic EPS", "Earnings Per Share"])
    revenue_q = safe_row(qfin, ["Total Revenue", "Revenue"])
    net_income_q = safe_row(qfin, ["Net Income", "NetIncome", "NetIncomeLoss"])
    ebit_q = safe_row(qfin, ["EBIT", "Ebit", "Operating Income"])
    interest_exp_q = safe_row(qfin, ["Interest Expense", "InterestExpense"])
    equity_q = safe_row(qbs, ["Stockholders Equity", "Total Stockholder Equity", "Total Equity"])
    op_cf_q = safe_row(qcf, ["Cash Flow From Continuing Operating Activities", "Net Cash Provided by Operating Activities"])
    capex_q = safe_row(qcf, ["Capital Expenditure", "Capital Expenditures"])

    # 季末股價
    price_q = fetch_price_quarterly(symbol).tail(QUARTERS_WINDOW)

    # 合併季度 index
    idx = sorted(set(
        eps_q.index.tolist() + revenue_q.index.tolist() + net_income_q.index.tolist() +
        ebit_q.index.tolist() + interest_exp_q.index.tolist() + equity_q.index.tolist() +
        op_cf_q.index.tolist() + capex_q.index.tolist() + price_q.index.tolist()
    ))
    if not idx: raise RuntimeError(f"{symbol} 沒有可用季度資料")
    df = pd.DataFrame(index=pd.to_datetime(idx))
    df['price_q'] = price_q.reindex(df.index)
    df['eps_q'] = eps_q.reindex(df.index)
    df['revenue_q'] = revenue_q.reindex(df.index)
    df['net_income_q'] = net_income_q.reindex(df.index)
    df['ebit_q'] = ebit_q.reindex(df.index)
    df['interest_exp_q'] = interest_exp_q.reindex(df.index)
    df['equity_q'] = equity_q.reindex(df.index)
    df['op_cf_q'] = op_cf_q.reindex(df.index)
    df['capex_q'] = capex_q.reindex(df.index)

    # dividend quarterly
    div_series = ticker.dividends if hasattr(ticker,'dividends') else pd.Series(dtype=float)
    if not div_series.empty:
        div_series = ensure_datetime_index(div_series)
        div_q = div_series.groupby(div_series.index.to_period('Q')).sum()
        div_q.index = div_q.index.to_timestamp('Q')
        df['dividend_q'] = div_q.reindex(df.index).fillna(0)
    else:
        df['dividend_q'] = 0.0

    # 時序特徵
    df['eps_q_diff'] = df['eps_q'].diff()
    df['eps_q_pct'] = df['eps_q'].pct_change(fill_method=None)
    df['revenue_q_pct'] = df['revenue_q'].pct_change(fill_method=None)
    df['net_income_q_pct'] = df['net_income_q'].pct_change(fill_method=None)
    df['net_margin_q'] = df['net_income_q'] / df['revenue_q']
    df['roe_q'] = (df['net_income_q']*4) / df['equity_q']
    df['ic_q'] = df['ebit_q'] / df['interest_exp_q']
    df['fcf_q'] = df['op_cf_q'] + df['capex_q']

    # target: next quarter return
    df['next_q_price'] = df['price_q'].shift(-TARGET_HORIZON_Q)
    df['next_q_return'] = (df['next_q_price'] / df['price_q']) - 1
    df['target_up'] = (df['next_q_return']>0).astype(float)

    df = df.sort_index()
    if save_csv:
        filename = f"ML_Quarterly_Dataset_{symbol}.csv"
        df.to_csv(filename, float_format='%.6f', index_label='quarter_end')
        print(f"{symbol} CSV 已儲存：{filename}")

    return df

# ======= 批次處理 =======
symbols = ["AMGN", "AAPL", "T", "XOM", "CVX", "MO", "KO", "VICI", "PEP","JNJ", "PFE" ,"VZ"]
datasets = {}
for s in symbols:
    try:
        df = build_quarterly_dataset(s)
        datasets[s] = df
    except Exception as e:
        print(f"{s} 發生錯誤: {e}")

# 示範印出最後 5 列
# for sym, df in datasets.items():
#     print("="*60)
#     print(sym)
#     print(df.tail(5)[['price_q','next_q_price','next_q_return','target_up']])
