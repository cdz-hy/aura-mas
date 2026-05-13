import os
import re
import uuid
from typing import List, Dict, Any, Tuple

def extract_last_sentence(text: str, max_length: int = 150) -> str:
    """提取文本段落的最后一句，用于图片的自动标题生成"""
    sentence_endings = r'[。！？\.!?]'
    sentences = re.split(sentence_endings, text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return text[:max_length]
    for sentence in reversed(sentences):
        if len(sentence) <= max_length:
            return sentence
    return sentences[-1][:max_length]

def _should_split_text(text_lines: list, max_chars: int = 1200) -> bool:
    """判断是否需要切分文本"""
    total_chars = sum(len(line) for line in text_lines)
    return total_chars > max_chars

def split_lines_with_overlap(lines: List[str], max_chars: int = 1200, overlap_chars: int = 200) -> List[str]:
    """
    基于行边界的智能切片算法，确保不从行中间截断：
    - 尽量保持代码块和句子的完整性
    - 仅在行与行之间进行切分
    """
    chunks = []
    current_chunk_lines = []
    current_chars = 0
    
    for line in lines:
        line_len = len(line) + 1 # +1 for newline
        
        # 如果单行已经超过了 max_chars，那只能强行切分（极少见）
        if line_len > max_chars and not current_chunk_lines:
            chunks.append(line)
            continue
            
        if current_chars + line_len > max_chars and current_chunk_lines:
            # 结算当前块
            chunks.append("\n".join(current_chunk_lines))
            
            # 处理重叠：保留末尾若干行，直到达到 overlap_chars
            overlap_lines = []
            overlap_len = 0
            for l in reversed(current_chunk_lines):
                if overlap_len + len(l) + 1 > overlap_chars:
                    break
                overlap_lines.insert(0, l)
                overlap_len += len(l) + 1
            
            current_chunk_lines = overlap_lines + [line]
            current_chars = overlap_len + line_len
        else:
            current_chunk_lines.append(line)
            current_chars += line_len
            
    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines))
        
    return chunks

def parse_markdown(md_content: str, doc_id: int, doc_title: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    解析 Markdown 内容
    返回：
    - data_points: List[Dict] (用于存入向量库的小切块)
    - parent_chunks: Dict[str, str] (ID -> 大切块内容的映射，用于存入 JSON)
    """
    lines = md_content.splitlines()
    data_points = []
    parent_chunks = {}
    
    current_headings = ["根目录"]
    current_text_lines = []
    in_code_block = False
    
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    html_img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*>', re.IGNORECASE)
    heading_pattern = re.compile(r'^(#{1,6})\s+(.*)')

    def process_accumulated_text(force=False):
        nonlocal current_text_lines
        if not current_text_lines:
            return
            
        # 如果在代码块内部，除非 force 且代码块已结束，否则不切分
        if in_code_block and not force:
            return

        full_text = "\n".join(current_text_lines).strip()
        if len(full_text) > 10:
            parent_id = str(uuid.uuid4())
            parent_chunks[parent_id] = full_text
            
            # 使用行感知的切片逻辑，确保小切块也不会截断代码行
            small_chunks = split_lines_with_overlap(current_text_lines, max_chars=500, overlap_chars=100)
            
            for small_chunk in small_chunks:
                data_points.append({
                    "id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "type": "text",
                    "content": small_chunk,
                    "parent_id": parent_id,
                    "image_path": "",
                    "image_caption": "",
                    "heading": list(current_headings),
                    "page_num": 0
                })
        current_text_lines = []

    for line in lines:
        line_raw = line # 保留原始缩进
        line_strip = line.strip()
        
        # 代码块检测
        if line_strip.startswith("```"):
            in_code_block = not in_code_block
            current_text_lines.append(line_raw)
            continue
            
        # 如果在代码块内，直接追加
        if in_code_block:
            current_text_lines.append(line_raw)
            continue

        if not line_strip:
            if current_text_lines:
                current_text_lines.append("")
            continue
            
        # 标题检测
        h_match = heading_pattern.match(line_strip)
        if h_match:
            process_accumulated_text(force=True)
            level = len(h_match.group(1))
            title = h_match.group(2).strip()
            if level <= len(current_headings):
                current_headings = current_headings[:level-1]
            current_headings.append(title)
            continue
            
        # 图片检测
        img_match = img_pattern.search(line_strip)
        html_match = html_img_pattern.search(line_strip)
        if img_match or html_match:
            process_accumulated_text(force=True)
            
            caption_candidate = ""
            if data_points and data_points[-1]["type"] == "text":
                caption_candidate = extract_last_sentence(parent_chunks.get(data_points[-1]["parent_id"], ""))
            
            parent_id = str(uuid.uuid4())
            if img_match:
                alt_text, img_rel_path = img_match.group(1).strip(), img_match.group(2).strip()
            else:
                img_rel_path, alt_text = html_match.group(1).strip(), html_match.group(2).strip() if html_match.group(2) else ""
            
            caption = alt_text if alt_text else (caption_candidate or f"{current_headings[-1]} 插图")
            parent_chunks[parent_id] = f"图片描述：{caption}"

            data_points.append({
                "id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "doc_title": doc_title,
                "type": "image",
                "content": "",
                "parent_id": parent_id,
                "image_path": img_rel_path,
                "image_caption": caption,
                "heading": list(current_headings),
                "page_num": 0
            })
            continue
            
        current_text_lines.append(line_raw)
        if _should_split_text(current_text_lines, max_chars=1200):
            process_accumulated_text()
        
    process_accumulated_text(force=True)
                
    return data_points, parent_chunks



