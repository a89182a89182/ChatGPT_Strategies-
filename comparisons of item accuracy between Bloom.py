import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
import statsmodels.api as sm
import statsmodels.formula.api as smf

df = pd.read_excel("./不同token結果.xlsx", engine="openpyxl")
conditions = ['no_train', '4k', '6k', '10k', '20k', 'Whole']
correct_rates = round(df.groupby('Classification')[conditions].mean() * 100,2)  # 轉換為百分比
correct_rates_percent = correct_rates.astype(str) + '%'
counts = df.groupby('Classification')[conditions].count()
counts = counts.reset_index()
correct_rates_percent = correct_rates_percent.reset_index()
counts.rename(columns={'no_train': 'counts'}, inplace=True)
# 將正確率和題目個數合併
combined = pd.concat([correct_rates_percent, counts['counts']], axis=1)

combined = combined[['Classification','counts', 'no_train', '4k', '6k', '10k', '20k', 'Whole']]
combined_statics = combined[['Classification','counts', 'no_train', '4k', '6k', '10k', '20k', 'Whole']]

# 訓練集大小列表
train_sizes = ['no_train', '4k', '6k', '10k', '20k', 'Whole']

# 移除百分比符號並轉換為浮點數
for size in train_sizes:
    # 檢查是否為字串類型
    if combined_statics[size].dtype == object:
        combined_statics[size] = combined_statics[size].str.rstrip('%').astype(float)

# 構建長格式數據框
long_df = pd.melt(combined_statics, id_vars=['Classification', 'counts'], value_vars=train_sizes,
                  var_name='Train_Size', value_name='Accuracy_Percentage')

# 計算正確和不正確次數
long_df['Correct'] = (long_df['counts'] * long_df['Accuracy_Percentage'] / 100).round().astype(int)
long_df['Incorrect'] = long_df['counts'] - long_df['Correct']
long_df['Accuracy_Percentage'] = long_df['Accuracy_Percentage']/100

# 例：改成 6000-token 的資料
df = long_df[long_df['Train_Size'] == "6k"].reset_index(drop=True)

rows = []
for i in range(len(df)):
    for j in range(i + 1, len(df)):
        table = np.array([
            [df.loc[i, "Correct"], df.loc[i, "Incorrect"]],
            [df.loc[j, "Correct"], df.loc[j, "Incorrect"]],
        ])
        # 先算 χ²（含連續性校正），並取得期望值
        chi2, p_chi, dof, expected = stats.chi2_contingency(table, correction=True)
        if (expected < 5).any():
            # 任何期望格 <5 就改用 Fisher's exact
            _, p = stats.fisher_exact(table, alternative="two-sided")
            test = "Fisher exact"
        else:
            p = p_chi
            test = "Chi-square (Yates)"
        rows.append({
            "Group1": df.loc[i, "Classification"],
            "Group2": df.loc[j, "Classification"],
            "n1": int(table[0].sum()), "acc1": df.loc[i, "Accuracy_Percentage"],
            "n2": int(table[1].sum()), "acc2": df.loc[j, "Accuracy_Percentage"],
            "test": test,
            "p_raw": p,
        })

results_df = pd.DataFrame(rows).sort_values("p_raw").reset_index(drop=True)

# Holm–Bonferroni 校正
rej, p_adj, _, _ = multipletests(results_df["p_raw"], method="holm")
results_df["p_adj"] = p_adj
results_df["adj_sig_alpha0.05"] = np.where(rej, "Yes", "No")
results_df
