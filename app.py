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

# 대분류-소분류 매핑
CATEGORY_MAPPING = {
    "사건처리": [
        "수집(센터내)", "수집(출장)",
        "분석(PC)", "분석(모바일)", "분석(블랙박스)", "분석(CCTV)", "분석(기타)",
        "검토(메신저)", "검토(사진)", "검토(영상)", "검토(문서)", "검토(로그)",
        "포렌식 회의", "의뢰인 면담",
        "보고서작성(요약)", "보고서작성(최종)"
    ],
    "회의": [
        "내부회의", "변호사협업회의", "고객회의"
    ],
    "신규상담": [
        "전화상담", "내방상담"
    ],
    "리서치/개발": [
        "기술리서치", "문서작성", "도구개발"
    ],
    "관리업무": [
        "기록관리", "사내문서정리", "시스템관리"
    ],
    "교육/세미나": [
        "사내교육", "외부세미나참석"
    ]
}

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
            ["📥 일일 업무 입력", "📋 일일 취합 보고", "🗂️ 사건 입력", "🗂️ 사건 관리", "📊 업무 기록"],
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
    elif menu == "📊 업무 기록":
        show_work_category_form()

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

def show_work_category_form():
    """업무 기록 폼 표시"""
    st.header("📊 업무 기록")
    
    # 작성자 옵션 목록
    name_options = ["신용학", "김경태", "박종찬", "이서영", "유다정", "임기택"]
    
    # 세션 상태 초기화
    if "work_category_saved" not in st.session_state:
        st.session_state.work_category_saved = False
    
    if "selected_main_category" not in st.session_state:
        st.session_state.selected_main_category = list(CATEGORY_MAPPING.keys())[0]
    
    # 저장 성공 알림 (새로고침 후 1회 표시)
    if st.session_state.work_category_saved:
        st.success("✅ 업무 기록이 저장되었습니다.")
        st.session_state.work_category_saved = False
    
    # 폼 외부에서 대분류 선택 (콜백 사용)
    def on_main_category_change():
        st.session_state.selected_main_category = st.session_state.main_category_outside
    
    # 폼 외부에서 대분류 선택 위젯
    st.selectbox(
        "대분류 선택", 
        list(CATEGORY_MAPPING.keys()),
        key="main_category_outside",
        on_change=on_main_category_change
    )
    
    with st.form("work_category_form"):
        # 작성자 입력
        writer = st.selectbox("작성자", name_options)
        
        # 폼 내부에서는 대분류를 session_state에서 가져오기만 하고, 콜백 없이 표시
        main_category = st.selectbox(
            "대분류 선택", 
            list(CATEGORY_MAPPING.keys()),
            key="main_category",
            index=list(CATEGORY_MAPPING.keys()).index(st.session_state.selected_main_category)
        )
        
        # 소분류 선택 (대분류에 따라 동적으로 변경)
        sub_category = st.selectbox(
            "소분류 선택",
            CATEGORY_MAPPING[st.session_state.selected_main_category]
        )
        
        # 업무 내용 입력
        content = st.text_area("업무 내용", height=150)
        
        # 시작일/종료일 입력
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", value=datetime.now())
        with col2:
            end_date = st.date_input("종료일", value=datetime.now())
        
        # 진행 상태 선택
        status = st.selectbox("진행 상태", ["진행 중", "완료", "미완료"])
        
        # 제출 버튼
        submitted = st.form_submit_button("저장")
        
        if submitted:
            if not writer or not content:
                st.error("작성자와 업무 내용은 필수입니다.")
            else:
                # DB에 저장
                db.add_work_category(
                    main_category=main_category,
                    sub_category=sub_category,
                    content=content,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    status=status,
                    writer=writer
                )
                st.session_state.work_category_saved = True
                st.rerun()
    
    # 기록된 데이터 조회 및 표시
    st.subheader("기록된 업무 내역")
    
    # 필터링 옵션
    with st.expander("필터 옵션", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            filter_main = st.selectbox("대분류 필터", ["전체"] + list(CATEGORY_MAPPING.keys()))
        
        with filter_col2:
            # 대분류 선택에 따라 소분류 옵션 변경
            if filter_main == "전체":
                filter_sub_options = ["전체"]
            else:
                filter_sub_options = ["전체"] + CATEGORY_MAPPING[filter_main]
            
            filter_sub = st.selectbox("소분류 필터", filter_sub_options)
        
        with filter_col3:
            filter_status = st.selectbox("상태 필터", ["전체", "진행 중", "완료", "미완료"])
        
        filter_writer = st.selectbox("작성자 필터", ["전체"] + name_options)
    
    # 필터 적용하여 데이터 조회
    filter_dict = {}
    
    if filter_main != "전체":
        filter_dict["main_category"] = filter_main
    
    if filter_sub != "전체":
        filter_dict["sub_category"] = filter_sub
    
    if filter_status != "전체":
        filter_dict["status"] = filter_status
        
    if filter_writer != "전체":
        filter_dict["writer"] = filter_writer
    
    df = db.get_work_categories(filter_dict)
    
    if df.empty:
        st.info("기록된 업무가 없습니다.")
    else:
        # 데이터프레임에서 중요 컬럼만 선택하여 표시
        display_df = df[["id", "writer", "main_category", "sub_category", "content", "start_date", "end_date", "status"]]
        display_df.columns = ["ID", "작성자", "대분류", "소분류", "업무내용", "시작일", "종료일", "상태"]
        
        # 상태에 따른 스타일링 적용
        def highlight_status(val):
            if val == "완료":
                return "background-color: lightgreen"
            elif val == "진행 중":
                return "background-color: lightyellow"
            elif val == "미완료":
                return "background-color: lightcoral"
            return ""
        
        # 스타일 적용
        styled_df = display_df.style.applymap(highlight_status, subset=["상태"])
        
        # 테이블 표시
        st.dataframe(styled_df, use_container_width=True)
        
        # 엑셀 다운로드 버튼
        excel_data = utils.create_excel_report(df)
        st.download_button(
            label="Excel로 다운로드",
            data=excel_data,
            file_name=f"work_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main() 