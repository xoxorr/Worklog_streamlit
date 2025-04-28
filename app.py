import streamlit as st
st.set_page_config(
    page_title="디지털포렌식 업무 기록 시스템",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import os
from datetime import datetime, timedelta
import json
from PIL import Image
import io
import uuid
import matplotlib.pyplot as plt
import plotly.express as px
from pathlib import Path
import db
import utils

# 상수 설정
CONFIG_FILE = Path("config.json")

"""
업무기록 관리 시스템
"""

# 설정 파일 관리
def load_config():
    """설정 파일 로드"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "직원목록": ["홍길동", "김철수", "이영희"],
        "업무유형": ["디지털포렌식", "보고서작성", "현장조사", "증거분석", "기타"]
    }

def save_config(config):
    """설정 파일 저장"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# 앱 상태 초기화
if "config" not in st.session_state:
    st.session_state.config = load_config()

# 전역 상수
CATEGORIES = ["A", "B", "C"]
CATEGORY_LABELS = {"A": "매출 관련 업무", "B": "내부업무", "C": "사건처리"}
STATUS_OPTIONS = ["진행 중", "완료", "미완료"]

def main():
    """메인 함수"""
    with st.sidebar:
        st.title("📝 디지털포렌식 업무 기록")
        menu = st.radio(
            "메뉴",
            ["📥 일일 업무 입력", "📋 일일 취합 보고", "🗂️ 사건 입력", "🗂️ 사건 관리"],
            key="menu_radio"
        )

    # 라디오 버튼 값(menu)으로 바로 분기
    if menu == "📥 일일 업무 입력":
        show_daily_work_input()
    elif menu == "📋 일일 취합 보고":
        show_daily_report()
    elif menu == "🗂️ 사건 입력":
        show_case_input()
    elif menu == "🗂️ 사건 관리":
        show_case_manage()

def show_daily_work_input():
    """일일 업무 입력 폼 표시"""
    st.header("📥 일일 업무 입력")
    name_options = ["신용학", "김경태", "박종찬", "이서영", "유다정", "임기택"]

    업무_템플릿 = "A. 매출 관련 업무\n\nB. 내부업무\n\nC. 사건처리\n"

    if "input_name" not in st.session_state:
        st.session_state.input_name = name_options[0]
    if "input_date" not in st.session_state:
        st.session_state.input_date = datetime.now()
    if "input_content" not in st.session_state or not st.session_state.input_content.strip():
        st.session_state.input_content = 업무_템플릿

    # 저장 성공 알림 (새로고침 후 1회 표시)
    if st.session_state.get("daily_work_saved"):
        st.success("일일 업무가 저장되었습니다.")
        st.session_state.daily_work_saved = False

    with st.form("daily_work_form"):
        name = st.selectbox("작성자", name_options, key="input_name")
        date = st.date_input("작성일", value=st.session_state.input_date, key="input_date")
        content = st.text_area("업무 내용", height=350, key="input_content")
        submitted = st.form_submit_button("저장")
        if submitted:
            if not name or not content:
                st.error("작성자와 업무 내용은 필수입니다.")
            else:
                db.add_daily_work(name, date.strftime("%Y-%m-%d"), content)
                st.session_state.daily_work_saved = True
                st.rerun()

def show_daily_report():
    """일일 취합 보고 화면"""
    st.header("📋 일일 취합 보고")
    report_date = st.date_input("보고 날짜", datetime.now(), key="report_date")
    report_date_str = report_date.strftime("%Y-%m-%d")
    df = db.get_daily_works(date=report_date_str)
    name_options = ["신용학", "김경태", "박종찬", "이서영", "유다정", "임기택"]
    if df.empty:
        st.info("해당 날짜에 입력된 업무가 없습니다.")
        return
    df = df.sort_values(["name", "id"])
    입력자_집합 = set(df["name"])
    # 상단에 입력 완료자 + 복사 버튼
    입력완료_리스트 = [f"✅ {이름}" for 이름 in name_options if 이름 in 입력자_집합]
    col1, col2 = st.columns([8, 1])
    with col1:
        if 입력완료_리스트:
            st.markdown("**입력 완료:** " + ", ".join(입력완료_리스트))
        else:
            st.markdown(":gray[입력 완료자가 없습니다.]")
    with col2:
        if st.button("복사", key="copy_all_daily"):
            st.session_state.show_copy_text = not st.session_state.get("show_copy_text", False)
    # 복사 버튼 클릭 시 전체 텍스트 토글 표시
    if st.session_state.get("show_copy_text"):
        # 이름별로 고정 순서로 txt 생성 (절취선 없이 한 줄 띄우기)
        txt_lines = []
        for 이름 in name_options:
            txt_lines.append(f"[{이름}]")
            if 이름 in 입력자_집합:
                for row in df[df["name"] == 이름].itertuples():
                    txt_lines.append(f"{row.content}")
            else:
                txt_lines.append("❌ 미입력")
            txt_lines.append("")  # 한 줄 띄우기
        st.text_area("전체 복사용 텍스트", value="\n".join(txt_lines), height=400)
    # 아래에는 이름별로 고정 순서로 업무/미입력 표시
    for 이름 in name_options:
        st.write(f"[{이름}]")
        if 이름 in 입력자_집합:
            for row in df[df["name"] == 이름].itertuples():
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.text(f"{row.content}")
                with col2:
                    if st.button("삭제", key=f"delete_{row.id}"):
                        db.delete_daily_work(row.id)
                        st.rerun()
        else:
            st.markdown(":gray[❌ 미입력]")
        st.write("--------------------")
    st.subheader("보고서 다운로드")
    # BytesIO 버퍼에 엑셀 저장
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    st.download_button(
        label="Excel로 다운로드",
        data=output,
        file_name=f"daily_report_{report_date_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_report_btn"
    )

def show_case_input():
    """사건 입력 폼 표시"""
    st.header("🗂️ 사건 입력")
    with st.form("case_input_form"):
        title = st.text_input("사건명", key="case_title")
        manager = st.text_input("담당자", key="case_manager")
        submitted = st.form_submit_button("사건 등록")
        if submitted:
            if not title or not manager:
                st.error("사건명과 담당자는 필수입니다.")
            else:
                db.add_case(title, manager)
                st.success("사건이 등록되었습니다.")

def show_case_manage():
    """사건 관리 화면 표시"""
    st.header("🗂️ 사건 관리")
    df = db.get_cases()
    if df.empty:
        st.info("등록된 사건이 없습니다.")
        return
    for i, row in df.iterrows():
        with st.expander(f"{row['title']} (담당: {row['manager']}, 상태: {row['status']})", expanded=False):
            st.write(f"시작일: {row['start_date']}")
            st.write(f"종료일: {row['end_date'] if row['end_date'] else '-'}")
            st.write(f"상태: {row['status']}")
            # 진행내역 표시
            logs = db.get_case_logs(row['id'])
            st.subheader("진행 내역")
            if logs:
                for log in logs:
                    st.markdown(f"- {log['date']}: {log['text']}")
            else:
                st.info("진행 내역이 없습니다.")
            # 진행내역 추가
            with st.form(f"add_log_{row['id']}"):
                new_log = st.text_area("진행 내역 추가", key=f"log_{row['id']}")
                log_submit = st.form_submit_button("추가")
                if log_submit and new_log:
                    db.add_case_log(row['id'], new_log)
                    st.success("진행 내역이 추가되었습니다. 새로고침 해주세요.")
            # 상태/종료일 변경
            st.subheader("상태 변경")
            new_status = st.selectbox("상태", ["진행 중", "완료", "미완료"], index=["진행 중", "완료", "미완료"].index(row['status']), key=f"status_{row['id']}")
            end_date = st.date_input("종료일", value=datetime.now() if not row['end_date'] else pd.to_datetime(row['end_date']), key=f"end_{row['id']}") if new_status == "완료" else None
            if st.button("상태/종료일 저장", key=f"save_status_{row['id']}"):
                db.update_case_status(row['id'], new_status, end_date.strftime("%Y-%m-%d") if end_date else None)
                st.success("상태/종료일이 저장되었습니다. 새로고침 해주세요.")

if __name__ == "__main__":
    main() 