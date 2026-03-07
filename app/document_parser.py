"""
文档解析模块 - 支持 PDF 和 Word 格式
使用 PyMuPDF 和 python-docx
"""
import fitz  # PyMuPDF
from docx import Document
import io
from typing import Optional
import re


class DocumentParser:
    """文档解析器"""
    
    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """解析 PDF 文件，返回纯文本"""
        text_parts = []
        
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc, 1):
                # 提取文本
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"\n--- 第{page_num}页 ---\n{text}")
                
                # 尝试提取表格内容（有些招标文件的表格是图片形式）
                tables = page.find_tables()
                if tables:
                    for table_idx, table in enumerate(tables.tables):
                        text_parts.append(f"\n[表格 {table_idx + 1}]")
                        for row in table.extract():
                            if row:
                                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                                text_parts.append(row_text)
        
        return "\n".join(text_parts)
    
    @staticmethod
    def parse_word(file_path: str) -> str:
        """解析 Word 文件（.docx），返回纯文本"""
        doc = Document(file_path)
        text_parts = []
        
        # 提取段落
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        # 提取表格内容
        for table_idx, table in enumerate(doc.tables):
            text_parts.append(f"\n[表格 {table_idx + 1}]")
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                if row_text:
                    text_parts.append(row_text)
        
        return "\n".join(text_parts)
    
    @staticmethod
    def parse(file_path: str, file_type: Optional[str] = None) -> str:
        """根据文件类型自动选择解析方法"""
        if file_type is None:
            file_type = file_path.lower().split('.')[-1]
        
        if file_type in ['pdf']:
            return DocumentParser.parse_pdf(file_path)
        elif file_type in ['docx', 'doc']:
            return DocumentParser.parse_word(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_type}")


    @staticmethod
    def parse_from_bytes(content: bytes, file_type: str) -> str:
        """从字节流解析文档"""
        if file_type in ['pdf']:
            return DocumentParser._parse_pdf_bytes(content)
        elif file_type in ['docx', 'doc']:
            return DocumentParser._parse_word_bytes(content)
        else:
            raise ValueError(f"不支持的文件格式: {file_type}")
    
    @staticmethod
    def _parse_pdf_bytes(content: bytes) -> str:
        """从字节流解析 PDF"""
        text_parts = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"\n--- 第{page_num}页 ---\n{text}")
        return "\n".join(text_parts)
    
    @staticmethod
    def _parse_word_bytes(content: bytes) -> str:
        """从字节流解析 Word"""
        doc = Document(io.BytesIO(content))
        text_parts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        for table_idx, table in enumerate(doc.tables):
            text_parts.append(f"\n[表格 {table_idx + 1}]")
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                if row_text:
                    text_parts.append(row_text)
        
        return "\n".join(text_parts)


class TextCleaner:
    """文本清洗工具"""
    
    @staticmethod
    def clean(raw_text: str) -> str:
        """清洗提取的文本"""
        # 移除多余空白
        text = re.sub(r'\n{3,}', '\n\n', raw_text)
        # 移除页眉页脚常见的重复内容
        text = re.sub(r'第\s*\d+\s*页\s*共\s*\d+\s*页', '', text)
        # 标准化空格
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()
