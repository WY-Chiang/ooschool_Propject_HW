import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
import matplotlib.pyplot as plt
# import lightgbm as lgb
# import xgboost as xgb
import glob

# ===================== 1. 讀取所有 CSV =====================
csv_files = glob.glob("ML_Quarterly_Dataset_*.csv")  # 確認路徑正確
all_dfs = []
for f in csv_files:
    df = pd.read_csv(f, index_col='quarter_end', parse_dates=True)
    all_dfs.append(df)

data = pd.concat(all_dfs, axis=0).sort_index()
print(f"資料總行數: {data.shape[0]}, 欄位數: {data.shape[1]}")

# ===================== 2. 特徵與目標 =====================
# 移除不必要欄位
features_to_drop = ['next_q_price','next_q_return','target_up']  # target 與 forward price
X = data.drop(columns=features_to_drop)
y = data['target_up']

# 處理缺值 (簡單用中位數填補)
X = X.fillna(X.median())

# ===================== 3. 分訓練/測試集 (時間序列) =====================
split_idx = int(len(X)*0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

# ===================== 4. 訓練模型 =====================
models = {
    'RandomForest': RandomForestClassifier(n_estimators=200, random_state=42),
    'LogisticRegression': LogisticRegression(max_iter=1000),
    # 'LightGBM': lgb.LGBMClassifier(n_estimators=200),
    # 'XGBoost': xgb.XGBClassifier(n_estimators=200, use_label_encoder=False, eval_metric='logloss')
}

results = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:,1]
    acc = accuracy_score(y_test, y_pred)
    roc = roc_auc_score(y_test, y_prob)
    results[name] = {'Accuracy': acc, 'ROC_AUC': roc}
    print(f"{name}: Accuracy={acc:.3f}, ROC AUC={roc:.3f}")

# ===================== 5. 畫圖比較 =====================
metrics_df = pd.DataFrame(results).T
metrics_df.plot(kind='bar', figsize=(10,6))
plt.title("模型比較: Accuracy 與 ROC AUC")
plt.ylabel("分數")
plt.ylim(0,1)
plt.xticks(rotation=0)
plt.grid(axis='y')
plt.show()
