import pandas as pd
import openai
from openai import OpenAI
from tqdm import tqdm  # 用於進度條
import re
import string
import time

# 設定你的 API 金鑰
api_key = "?????"


# 讀取 CSV 文件
year = "111"
option = "單選"
# option = "複選"

file_path = f"{year}準備({option}).xlsx"  # 替換為您的 CSV 文件路徑

# MODLE='o1-preview'
# MODLE=['gpt-4o']
# MODLE=['gpt-4']
# MODLE=['gpt-3.5-turbo']
modle_list = ['gpt-4.5-preview']
# 讀取 Excel 文件
df = pd.read_excel(file_path, engine="openpyxl")
次數 = 1


# GPT API 函式
def ask_gpt(question):
    try:
        response = client.chat.completions.create(
            model= MODLE,  # 替換為您需要的模型，例如 "gpt-4" 或 "gpt-3.5-turbo"
            # model="gpt-4",  # 替換為您需要的模型，例如 "gpt-4" 或 "gpt-3.5-turbo"
            messages=[
                {"role": "user", "content": question}
            ]
        )
        # 提取 GPT 的回應
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error while communicating with GPT: {e}")
        return "Error"


# 動態生成選項字典
def generate_options(question_text):
    # 分割問題文本為行
    lines = question_text.strip().splitlines()

    # 提取問題和選項
    question = lines[0]  # 第一行是問題
    options = lines[1:]  # 後面的行是選項

    # 過濾掉空行，並生成選項字典
    option_dict = {}
    valid_options = [opt.strip() for opt in options if opt.strip()]  # 過濾掉空行
    for i, option in enumerate(valid_options):
        key = string.ascii_uppercase[i]  # 生成 A, B, C, ...
        option_dict[key] = option

    return question, option_dict


# 動態提取問題中的選項和對應的編號
def extract_options(question_text):
    matches = re.findall(r"([A-Z])\.\s*(.*)", question_text)  # 提取 "A. 選項內容" 格式
    return {option.strip(): content.strip() for option, content in matches}

# 提取 GPT 答案的函式
def parse_gpt_answer(gpt_raw_answer,option="單選"):
    """
    校正 GPT 回答，只提取選項字母。
    """
    matches = re.findall(r"[A-Z]", gpt_raw_answer.upper())  # 只提取獨立的選項字母
    
    if option== "單選":
        try:
            return matches[0]  # 單選題只返回第一個字母
        except:
            return "無解"
    else:
        return "".join(matches)


def is_correct(correct_option, gpt_answer, options,option="單選"):
    # 格式化正確答案（移除空格和多餘字符）
    correct_set = set(correct_option.upper())  # 正確答案集合
    gpt_set = set(parse_gpt_answer(gpt_answer,option))  # GPT 答案集合
    
    # 比較兩個集合是否一致
    return correct_set == gpt_set
    
# def is_correct(correct_option, gpt_answer, options,option="單選"):
#     # 將 GPT 回答格式化並嘗試提取選項編號
#     gpt_answer = gpt_answer.strip()
#     gpt_option = ""

#     # 檢查是否包含選項編號 (A, B, C, etc.)
#     if gpt_answer[0].upper() in options:
#         gpt_option = gpt_answer[0].upper()

#     # 比較 GPT 的選項編號與正確選項
#     return gpt_option == correct_option

def evaluate_multiple_choice(correct_option, gpt_answer, option="複選"):
    # 正確答案集合
    correct_set = set(correct_option.upper())

    # GPT 回答集合，過濾非合法選項
    all_options = {"A", "B", "C", "D", "E"}
    gpt_set = {char.upper() for char in gpt_answer if char.upper() in all_options}

    # 如果回答完全正確，直接返回滿分
    if correct_set == gpt_set:
        return {
            "Precision": 1,
            "Negative Precision": 1,
            "F1 Score": 1
        }

    # Precision (正確選項的命中率)
    precision = len(gpt_set.intersection(correct_set)) / len(correct_set) if correct_set else 0

    # Negative Precision (正確排除錯誤選項的比率)
    incorrect_set = all_options.difference(correct_set)
    negative_precision = len(incorrect_set.difference(gpt_set)) / len(incorrect_set) if incorrect_set else 1

    # F1 分數
    f1_score = 2 * (precision * negative_precision) / (precision + negative_precision) if (precision + negative_precision) > 0 else 0

    return {
        "Precision": precision,
        "Negative Precision": negative_precision,
        "F1 Score": f1_score
    }

for MODLE in modle_list:
    for i in range(次數):
        # 記錄開始時間
        start_time = time.time()
        count +=1
        client = OpenAI(api_key=api_key)
        all_options = {"A", "B", "C", "D", "E"}
        # 初始化結果
        results = {
            "Question": [],
            "Correct Answer": [],
            "GPT Answer": [],
            "Is Correct": [],
            "Precision": [],
            "Negative Precision": [],
            "F1 Score": []
        }
           
        # 遍歷問題並顯示進度條
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing Questions"):
            # 為問題生成選項
            question_text, options = generate_options(row["Question"])
    
            # 生成新的帶編號問題文本
            numbered_question = f"{question_text}\n"
            for key, value in options.items():
                numbered_question += f"{key}. {value}\n"
        
            # 正確答案的選項（如 B）
            correct_option = row["Answer"]
            
            # GPT 回答
            if option == "單選":
                gpt_answer = ask_gpt(f"這都是{option}，請只給我答案的選項字母，例如 A，不要多餘內容。\n{numbered_question}")
            else:
                gpt_answer = ask_gpt(f"這是多選題，請只給我答案的選項字母，例如 AB，不要多餘內容。\n{numbered_question}\n")

            # print(gpt_answer)
#             gpt_answer= {char.upper() for char in gpt_answer if char.upper() in all_options} 單選會有問題
            # gpt_answer_result = ''.join(sorted(gpt_answer))
            
            
            # 判斷正確性和詳細評估
            if option == "單選":
                is_correct_result = is_correct(correct_option, gpt_answer, options,option)
                results["Precision"].append(None)  # 單選不計算 Precision
                results["Negative Precision"].append(None)  # 單選不計算 Negative Precision
                results["F1 Score"].append(None)  # 單選不計算 F1 Score
            else:
                evaluation = evaluate_multiple_choice(correct_option, gpt_answer, options)
                is_correct_result = evaluation["Precision"] == 1.0 and evaluation["Negative Precision"] == 1.0  # 全部正確才記為 True
                # 記錄詳細評估結果
                results["Precision"].append(evaluation["Precision"])
                results["Negative Precision"].append(evaluation["Negative Precision"])
                results["F1 Score"].append(evaluation["F1 Score"])

            # 記錄結果
            results["Question"].append(numbered_question)
            results["Correct Answer"].append(correct_option)
            results["GPT Answer"].append(gpt_answer)
            results["Is Correct"].append(is_correct_result)
        
        
        # 將結果轉換為 DataFrame
        results_df = pd.DataFrame(results)
        
        # 計算正確率
        accuracy = results_df["Is Correct"].mean()
        mean_precision = results_df["Precision"].mean()
        mean_negative_precision = results_df["Negative Precision"].mean()
        mean_f1_score = results_df["F1 Score"].mean()
        print(f"GPT 測試正確率: {accuracy:.2%}")
        print(f"平均精確率: {mean_precision:.2%}, 平均排錯率: {mean_negative_precision:.2%}, 平均F1分數: {mean_f1_score:.2%}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 保存結果到 Excel 文件
        if option == "複選":
            output_path = f"./結果/GPT_{MODLE}第{count}次測試{year}準備({option})__正確率{accuracy:.2%}_耗時{elapsed_time:.2f}秒__精確率{mean_precision:.2%}__排錯率{mean_negative_precision:.2%}__F1分數{mean_f1_score:.2%}.xlsx"
        else:    
            output_path = f"./結果/GPT_{MODLE}第{count}次測試{year}準備({option})__正確率{accuracy:.2%}_耗時{elapsed_time:.2f}秒.xlsx"
        results_df.to_excel(output_path, index=False)
        print(f"測試結果已保存至 {output_path}")

