import os
import pandas as pd
import re
import numpy as np
from scipy.stats import chi2_contingency, fisher_exact


# 假設資料夾路徑
folder_path = "./"
# 取得所有檔案名稱
file_names = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

df = pd.read_excel(file_name)
df = df[[ 'Is Correct','Bloom’s Taxonomy', 'Vol']]
df["Bloom’s Taxonomy"] = df["Bloom’s Taxonomy"] == "知識記憶題"


correct_rate = df.groupby("Bloom’s Taxonomy")["Is Correct"].mean()
print(correct_rate)
summary = df.groupby("Bloom’s Taxonomy")["Is Correct"].agg(['count', 'sum'])
summary['correct'] = summary['sum']
summary['correct_rate'] = summary['correct'] / summary['count']
summary['wrong']= summary['count']-summary['correct']

summary = summary[['count', 'correct','wrong','correct_rate']]
contingency_table = summary[['correct','wrong']]
chi2, p, dof, expected = chi2_contingency(contingency_table)
print("Chi-square Test:")
print("Chi-square:", chi2)
print("p-value:", p)
print("Degrees of freedom:", dof)
print("Expected frequencies:\n", expected)
summary
