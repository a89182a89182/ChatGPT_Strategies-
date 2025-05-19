import fitz  # PyMuPDF
import re
import tiktoken


def count_tokens(text, model="gpt-4.1"):
    """
    使用 OpenAI 的 tiktoken 套件計算 token 數量。

    參數:
      text: 欲計算 token 的文字字串。
      model: 要使用的模型名稱（預設 "gpt-3.5-turbo"），不同模型的編碼方式可能不同。

    回傳:
      該文字的 token 數量。
    """
    # 根據指定模型取得編碼器
    enc = tiktoken.encoding_for_model(model)
    # 將文字編碼成 token 並回傳長度
    tokens = enc.encode(text)
    return len(tokens)


def process_page(page):
    """
    依照頁面中的文字區塊，將頁面依垂直方向分段，
    並依各區段的平均寬度決定為單欄或雙欄格式，再合併該區段內的文字。
    """
    page_width = page.rect.width
    # 取得所有文字區塊，每個 block 為 (x0, y0, x1, y1, text, block_no)
    blocks = page.get_text("blocks")
    # 依上方座標排序（由上而下）
    blocks = sorted(blocks, key=lambda b: b[1])

    # 將區塊依垂直間距分群：相鄰區塊若間隔超過一定點數，視為不同段落區
    segments = []
    current_segment = []
    gap_threshold = 20  # 單位：點（points），可根據需要調整
    last_bottom = None
    for block in blocks:
        text = block[4].strip()
        if not text:
            continue  # 忽略空白區塊
        if last_bottom is not None and block[1] - last_bottom > gap_threshold:
            segments.append(current_segment)
            current_segment = []
        current_segment.append(block)
        last_bottom = block[3]  # 更新上一區塊的底部座標
    if current_segment:
        segments.append(current_segment)

    segment_texts = []
    # 逐個區段進行處理
    for seg in segments:
        # 取得每個區塊的寬度
        widths = [b[2] - b[0] for b in seg]
        avg_width = sum(widths) / len(widths)
        # 若平均寬度接近頁面寬度（例如 ≥ 80%），視為單欄
        if avg_width >= 0.8 * page_width:
            seg_sorted = sorted(seg, key=lambda b: b[1])
            seg_text = "\n".join(b[4].strip() for b in seg_sorted)
        else:
            # 若平均寬度較窄，則判定為雙欄：依 x 座標分左右兩組
            left_blocks = [b for b in seg if b[0] < page_width / 2]
            right_blocks = [b for b in seg if b[0] >= page_width / 2]
            left_sorted = sorted(left_blocks, key=lambda b: b[1])
            right_sorted = sorted(right_blocks, key=lambda b: b[1])
            left_text = "\n".join(b[4].strip() for b in left_sorted)
            right_text = "\n".join(b[4].strip() for b in right_sorted)
            # 雙欄版面的閱讀順序通常為先左欄再右欄
            seg_text = left_text + "\n" + right_text
        segment_texts.append(seg_text)
    # 以空白行分隔各個區段
    return "\n\n".join(segment_texts)


def extract_pdf_text(pdf_path, txt_output_path):
    """
    解析整個 PDF 檔案，每頁依上述方法處理，
    並將所有頁面合併後進行基本的文字清理，
    最後存成純文字檔案。
    """
    doc = fitz.open(pdf_path)
    all_page_text = []
    for page in doc:
        page_text = process_page(page)
        all_page_text.append(page_text)
    doc.close()

    # 合併所有頁的文字
    raw_text = "\n".join(all_page_text)

    # 進一步處理：處理斷行、連字號與段落連接
    cleaned_lines = []
    for line in raw_text.splitlines():
        if not line.strip():
            cleaned_lines.append("")
        else:
            # 如果前一行存在且沒有以標點符號結尾，則合併至同一段落
            if cleaned_lines and cleaned_lines[-1] != "":
                prev_line = cleaned_lines[-1]
                if prev_line.endswith("-"):
                    # 移除連字號後直接連接
                    cleaned_lines[-1] = prev_line[:-1] + line.strip()
                    continue
                if not re.search(r'[。！？.?]$', prev_line):
                    cleaned_lines[-1] = prev_line + " " + line.strip()
                    continue
            cleaned_lines.append(line.strip())
    cleaned_text = "\n".join(cleaned_lines)

    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)


def split_text_into_files(text, max_tokens=6000, base_filename="output_part"):
    """
    依據 max_tokens 參數，每累積約 6000 tokens（不切斷段落）
    就輸出一個檔案，檔案名稱依序為 output_part1.txt, output_part2.txt, ...。

    參數：
      text: 已經清理過的完整文字（字串）
      max_tokens: 每個檔案的 token 限制（預設 6000）
      base_filename: 檔案基本名稱（預設 "output_part"）
    """
    # 依照空行（兩個或以上換行符）切割為段落
    paragraphs = re.split(r'\n\s*\n', text)

    file_texts = []  # 存放各個分割後的檔案內容（字串）
    current_paragraphs = []  # 目前累積的段落（清單）
    current_token_count = 0  # 目前累積的 token 數

    for paragraph in paragraphs:
        # 去除前後空白
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        tokens_in_paragraph = count_tokens(paragraph)

        # 若累積後超過限制，先把目前累積的段落合併輸出成一個檔案
        if current_token_count + tokens_in_paragraph > max_tokens:
            # 將目前累積的段落以空行分隔組合成一個完整檔案的內容
            file_texts.append("\n\n".join(current_paragraphs))
            # 重新開始累積，將目前這個段落作為第一個
            current_paragraphs = [paragraph]
            current_token_count = tokens_in_paragraph
        else:
            # 累積這個段落
            current_paragraphs.append(paragraph)
            current_token_count += tokens_in_paragraph

    # 處理剩下的段落
    if current_paragraphs:
        file_texts.append("\n\n".join(current_paragraphs))

    # 寫入檔案
    for idx, file_text in enumerate(file_texts, start=1):
        filename = f"{base_filename}{idx}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(file_text)
        print(f"File saved: {filename} (approximately {count_tokens(file_text)} tokens)")


# === 主程式 ===
if __name__ == "__main__":

    name = input('Please enter the PDF file\' name.:        ')
    # If the name contains ".pdf", remove it
    if ".pdf" in name:
        name = name.replace(".pdf", "")

    extract_pdf_text(f"{name}.pdf", f"{name}.txt")

    # 假設您的純文字內容已存入 'extracted_text.txt'
    input_file = f"{name}.txt"
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    # 將文字依每 6000 tokens 分割並輸出至多個檔案
    split_text_into_files(text, max_tokens=6000, base_filename=f'{name}_part')
