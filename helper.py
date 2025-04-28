"""
helper.py - 디지털포렌식 업무 기록 시스템을 위한 유틸리티 함수 모음
"""

import os
import io
import base64
import pandas as pd
from datetime import datetime
import textwrap
import re

def get_formatted_date():
    """현재 날짜를 YYYY-MM-DD 형식으로 반환"""
    return datetime.now().strftime("%Y-%m-%d")

def format_report(daily_works):
    """일일 보고서 텍스트 형식으로 변환"""
    report_text = ""
    for name, group in daily_works.groupby("name"):
        report_text += f"■ {name}\n"
        for _, row in group.iterrows():
            wrapped_content = textwrap.fill(row["content"], width=80)
            report_text += f"{wrapped_content}\n\n"
        report_text += "="*80 + "\n"
    return report_text

def create_excel_download_link(df, filename, text="엑셀 다운로드"):
    """DataFrame을 엑셀 파일로 변환하여 다운로드 링크 생성"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">- {text}</a>'
    return href

def clean_text(text):
    """텍스트 정제 (특수문자 제거 등)"""
    if not text:
        return ""
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 특수문자 정제
    text = re.sub(r'[^\w\s\.\,\:\;\-\_\(\)\[\]\{\}\?\!]', '', text)
    return text.strip()

def validate_date_format(date_string):
    """날짜 형식이 YYYY-MM-DD인지 검증"""
    try:
        if date_string:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        return False
    except ValueError:
        return False

def get_file_path(directory, filename):
    """파일 경로 생성 및 디렉토리 확인"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    return os.path.join(directory, filename)

def truncate_text(text, max_length=100):
    """텍스트가 너무 길 경우 잘라서 표시"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def format_date_range(start_date, end_date):
    """날짜 범위 표시"""
    if not start_date:
        return "날짜 미정"
    if not end_date:
        return f"{start_date}부터"
    return f"{start_date} ~ {end_date}"

def get_status_color(status):
    """상태에 따른 색상 반환"""
    if status == "완료":
        return "green"
    elif status == "진행 중":
        return "blue"
    else:
        return "red"

def parse_category_text(text, default_category="기타"):
    """텍스트에서 카테고리 정보 추출 (예: #분류:내부업무)"""
    category = default_category
    match = re.search(r'#분류:([^\s]+)', text)
    if match:
        category = match.group(1)
    return category

def format_work_content(content):
    """업무 내용 포맷팅 (줄바꿈, 강조 등)"""
    if not content:
        return ""
    # 줄바꿈 처리
    content = content.replace("\n", "<br>")
    # 강조 처리 (*강조* -> <b>강조</b>)
    content = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', content)
    return content 