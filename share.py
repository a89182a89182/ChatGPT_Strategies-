import pdfplumber
import re
from nltk.tokenize import sent_tokenize
import os


def extract_and_split_text_from_pdf(file_path, max_length=10000):
    sections = []
    current_section = None
    content = []

    # 開啟 PDF 文件
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # 獲取頁面尺寸
            page_width = page.width
            mid_x = page_width / 2  # 假設頁面左右分佈的中線

            # 提取圖片區域
            images = page.images
            image_bboxes = [
                (img["x0"], img["top"], img["x1"], img["bottom"]) for img in images
            ]

            # 提取文字並按區域分類
            left_text = []
            right_text = []

            for char in page.chars:
                char_bbox = (char["x0"], char["top"], char["x1"], char["bottom"])
                # 確認字元不在圖片區域內
                if not any(
                        char_bbox[0] >= img[0]
                        and char_bbox[2] <= img[2]
                        and char_bbox[1] >= img[1]
                        and char_bbox[3] <= img[3]
                        for img in image_bboxes
                ):
                    if char["x0"] < mid_x:  # 判斷是否屬於左區塊
                        left_text.append(char["text"])
                    else:  # 屬於右區塊
                        right_text.append(char["text"])

            # 合併左右區塊文字，分行處理
            cleaned_text = "\n".join(["".join(left_text), "".join(right_text)])
            for line in cleaned_text.split("\n"):
                line = line.strip()
                if re.match(r"^\d+\s+[A-Za-z].*", line):  # 偵測章節標題
                    if current_section:
                        sections.append((current_section, "\n".join(content)))
                        content = []
                    current_section = line
                else:
                    content.append(line)

    if current_section:
        sections.append((current_section, "\n".join(content)))

    # 如果 sections 為空，則直接處理整個 PDF
    if not sections:
        with pdfplumber.open(file_path) as pdf:
            all_text = " ".join(
                [page.extract_text() for page in pdf.pages if page.extract_text()]
            )
            sections = [("Default Section", all_text)]

    # 分段處理
    split_sections = []
    for section_title, section_content in sections:
        sentences = sent_tokenize(section_content)
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > max_length:
                split_sections.append((section_title, " ".join(current_chunk)))
                current_chunk = []
                current_length = 0
            current_chunk.append(sentence)
            current_length += sentence_length

        if current_chunk:
            split_sections.append((section_title, " ".join(current_chunk)))

    return split_sections


length_list = [6000]

file_path = input('please give me the filename:   ')

for length in length_list:
    # 提取和分段處理
    split_sections = extract_and_split_text_from_pdf(file_path, max_length=length)

    for idx, (title, content) in enumerate(split_sections):
        # 構建目標資料夾和檔案路徑
        # folder_path = f"./V{vol}C{ch}/"
        # output_file = f"{folder_path}V{vol}C{ch}_part{idx+1}.txt"
        folder_path = f"./{length}/V{vol}C{ch}/"
        output_file = f"./{length}/V{vol}C{ch}/V{vol}C{ch}_part{idx + 1}.txt"
        # 檢查資料夾是否存在，如果不存在則建立
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    # 將分段保存為檔案
    for idx, (title, content) in enumerate(split_sections):
        # output_file = f"./V{vol}C{ch}/V{vol}C{ch}_part{idx+1}.txt"
        output_file = f"./{length}/V{vol}C{ch}/V{vol}C{ch}_part{idx + 1}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Section: {title}\n\n{content}")
        print(f"Saved: {output_file}")

print(f"Now all you need to do is upload the split files to the LLM model, and the training will be complete!~")
