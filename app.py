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
import helper
import base64
import textwrap
import re

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

# 업무 분류 체계
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

def main():
    """메인 함수"""
    # 설정 로드
    config = load_config()
    
    # Streamlit 기본 설정
    st.set_page_config(
        page_title="디지털포렌식 업무 기록",
        page_icon="📋",
        layout="wide"
    )
    
    # 세션 상태 초기화
    if "users" not in st.session_state:
        st.session_state.users = config.get("users", [])
    if "categories" not in st.session_state:
        st.session_state.categories = config.get("categories", [])
    if "notification" not in st.session_state:
        st.session_state.notification = None
    
    # 데이터베이스 초기화
    db.init_db()
    
    # 사이드바 메뉴
    menu = st.sidebar.selectbox(
        "메뉴", 
        ["일일 업무 입력", "일일 보고서", "업무 기록", "사건 입력", "사건 관리", "설정"]
    )
    
    # 메뉴에 따른 화면 표시
    if menu == "일일 업무 입력":
        show_daily_work_input()
    elif menu == "일일 보고서":
        show_daily_report()
    elif menu == "업무 기록":
        show_work_log()
    elif menu == "사건 입력":
        show_case_input()
    elif menu == "사건 관리":
        show_case_management()
    elif menu == "설정":
        show_settings()
    
    # 알림 표시
    if st.session_state.notification:
        st.success(st.session_state.notification)
        st.session_state.notification = None

def show_daily_work_input():
    """일일 업무 입력 화면"""
    st.title("일일 업무 입력")
    
    # 사용자 선택 또는 입력
    if not st.session_state.users:
        user_name = st.text_input("이름")
    else:
        user_name = st.selectbox("이름", st.session_state.users)
    
    # 날짜 선택
    work_date = st.date_input("날짜", datetime.now()).strftime("%Y-%m-%d")
    
    # 업무 내용 입력
    work_content = st.text_area("업무 내용", height=200)
    
    # 제출 버튼
    if st.button("입력", key="input_daily_work_button"):
        if not user_name:
            st.error("이름을 입력해주세요.")
        elif not work_content:
            st.error("업무 내용을 입력해주세요.")
        else:
            # 새 사용자 추가
            if user_name not in st.session_state.users:
                st.session_state.users.append(user_name)
                config = load_config()
                config["users"] = st.session_state.users
                save_config(config)
            
            # 업무 추가
            db.add_daily_work(user_name, work_date, work_content)
            st.session_state.notification = "일일 업무가 추가되었습니다."
            st.rerun()

def show_daily_report():
    """일일 보고서 화면"""
    st.title("일일 보고서")
    
    # 날짜 선택
    report_date = st.date_input("날짜", datetime.now()).strftime("%Y-%m-%d")
    
    # 보고서 생성 버튼
    if st.button("보고서 생성"):
        # 해당 날짜의 업무 가져오기
        daily_works = db.get_daily_works(date=report_date)
        
        if daily_works.empty:
            st.warning(f"{report_date}에 기록된 업무가 없습니다.")
        else:
            st.subheader(f"{report_date} 일일 업무")
            
            # 사용자별 업무 그룹화
            for name, group in daily_works.groupby("name"):
                st.write(f"**{name}**")
                for _, row in group.iterrows():
                    st.text(row["content"])
                st.markdown("---")
            
            # 보고서 다운로드 버튼
            report_text = ""
            for name, group in daily_works.groupby("name"):
                report_text += f"■ {name}\n"
                for _, row in group.iterrows():
                    wrapped_content = textwrap.fill(row["content"], width=80)
                    report_text += f"{wrapped_content}\n\n"
                report_text += "="*80 + "\n"
            
            st.download_button(
                label="보고서 다운로드", 
                data=report_text, 
                file_name=f"보고서_{report_date}.txt", 
                mime="text/plain", 
                key="download_report"
            )

def show_work_log():
    """업무 기록 검색 및 표시"""
    st.title("업무 기록")
    
    # 필터링 옵션
    col1, col2, col3 = st.columns(3)
    with col1:
        if not st.session_state.users:
            filter_user = st.text_input("작성자")
        else:
            filter_user = st.selectbox("작성자", [""] + st.session_state.users)
    
    with col2:
        filter_date = st.date_input("날짜", None)
        filter_date = filter_date.strftime("%Y-%m-%d") if filter_date else None
    
    with col3:
        filter_status = st.selectbox("상태", ["", "진행 중", "완료"])
    
    # 필터 적용 버튼
    if st.button("검색", key="search_worklog"):
        filters = {}
        if filter_user:
            filters["name"] = filter_user
        if filter_date:
            filters["date"] = filter_date
        if filter_status:
            filters["status"] = filter_status
        
        logs = db.get_worklogs(**filters)
        
        if logs.empty:
            st.warning("검색 결과가 없습니다.")
        else:
            st.subheader(f"검색 결과: {len(logs)}건")
            logs["작업"] = None  # 작업 컬럼 추가
            
            # 컬럼 이름 매핑
            column_mapping = {
                "id": "ID",
                "name": "작성자",
                "date": "등록일자",
                "main_category": "대분류",
                "sub_category": "소분류",
                "content": "내용",
                "start_date": "시작일",
                "end_date": "종료일",
                "status": "상태"
            }
            
            # 컬럼 이름 변경
            logs = logs.rename(columns=column_mapping)
            
            # 데이터 표시
            edited_df = st.data_editor(
                logs[["ID", "작성자", "등록일자", "대분류", "소분류", "내용", "시작일", "종료일", "상태", "작업"]], 
                column_config={
                    "작업": st.column_config.ButtonColumn("작업", label="삭제")
                },
                hide_index=True
            )
            
            # 삭제 버튼 처리
            for idx, row in edited_df.iterrows():
                if row["작업"] == "삭제":
                    if st.button(f"정말 삭제하시겠습니까? - {row['ID']}", key=f"confirm_delete_{row['ID']}"):
                        db.delete_worklog(row["ID"])
                        st.session_state.notification = f"업무 기록 ID {row['ID']}이(가) 삭제되었습니다."
                        st.rerun()

def show_case_input():
    """사건 입력 화면"""
    st.title("사건 입력")
    
    # 업무 카테고리
    if not st.session_state.categories:
        st.warning("설정에서 업무 카테고리를 추가해주세요.")
    
    # 입력 폼
    with st.form("case_input_form"):
        # 기본 정보
        user_name = st.selectbox("담당자", st.session_state.users) if st.session_state.users else st.text_input("담당자")
        case_date = st.date_input("등록일", datetime.now()).strftime("%Y-%m-%d")
        
        # 카테고리 선택
        if st.session_state.categories:
            main_category = st.selectbox("대분류", [cat["name"] for cat in st.session_state.categories])
            selected_category = next((cat for cat in st.session_state.categories if cat["name"] == main_category), None)
            if selected_category and "sub_categories" in selected_category:
                sub_category = st.selectbox("소분류", selected_category["sub_categories"])
            else:
                sub_category = st.text_input("소분류")
        else:
            main_category = st.text_input("대분류")
            sub_category = st.text_input("소분류")
        
        # 사건 정보
        case_title = st.text_input("사건명")
        case_content = st.text_area("내용", height=150)
        
        # 기간 정보
        start_date = st.date_input("시작일", datetime.now()).strftime("%Y-%m-%d")
        end_date = st.date_input("종료일(예정)", datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # 상태
        status = st.selectbox("상태", ["진행 중", "완료"])
        
        # 제출 버튼
        submit_button = st.form_submit_button("등록")
        
        if submit_button:
            if not user_name:
                st.error("담당자를 입력해주세요.")
            elif not case_title:
                st.error("사건명을 입력해주세요.")
            else:
                # 새 사용자 추가
                if user_name not in st.session_state.users:
                    st.session_state.users.append(user_name)
                    config = load_config()
                    config["users"] = st.session_state.users
                    save_config(config)
                
                # 사건 DB 추가
                case_id = db.add_case(case_title, user_name)
                
                # 워크로그 추가
                db.add_worklog(
                    name=user_name, 
                    date=case_date, 
                    main_category=main_category, 
                    sub_category=sub_category, 
                    content=case_content, 
                    start_date=start_date, 
                    end_date=end_date, 
                    status=status
                )
                
                # 사건 상태 업데이트
                if status == "완료":
                    db.update_case_status(case_id, status, end_date)
                
                st.session_state.notification = "사건 정보가 추가되었습니다."
                st.rerun()

def show_case_management():
    """사건 관리 화면"""
    st.title("사건 관리")
    
    # 모든 사건 가져오기
    cases = db.get_cases()
    
    # 사건 필터링
    filter_status = st.selectbox("상태 필터", ["모두", "진행 중", "완료"], index=0)
    
    # 필터링된 사건 표시
    filtered_cases = cases if filter_status == "모두" else cases[cases["status"] == filter_status]
    
    if filtered_cases.empty:
        st.warning("사건이 없습니다.")
    else:
        # 컬럼 이름 변경
        display_columns = {
            "id": "ID",
            "title": "사건명",
            "manager": "담당자",
            "start_date": "시작일",
            "end_date": "종료일",
            "status": "상태"
        }
        
        filtered_cases = filtered_cases.rename(columns=display_columns)
        
        # 사건 목록 표시
        st.dataframe(filtered_cases[["ID", "사건명", "담당자", "시작일", "종료일", "상태"]], hide_index=True)
        
        # 사건 선택
        selected_case_id = st.number_input("관리할 사건 ID", min_value=1, step=1)
        
        if st.button("사건 조회"):
            case = db.get_case(selected_case_id)
            
            if case:
                st.subheader(f"사건: {case['title']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**담당자:** {case['manager']}")
                with col2:
                    st.write(f"**시작일:** {case['start_date']}")
                with col3:
                    st.write(f"**상태:** {case['status']}")
                    if case['end_date']:
                        st.write(f"**종료일:** {case['end_date']}")
                
                # 로그 표시
                st.subheader("진행 내역")
                logs = db.get_case_logs(selected_case_id)
                
                if logs:
                    for log in logs:
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.write(f"**{log['date']}**")
                        with col2:
                            st.write(log['text'])
                else:
                    st.info("진행 내역이 없습니다.")
                
                # 로그 추가
                with st.form(key=f"log_form_{selected_case_id}"):
                    log_text = st.text_area("새 진행 내역", key=f"new_log_{selected_case_id}")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        add_log = st.form_submit_button("진행 내역 추가")
                    
                    with col2:
                        status_options = ["진행 중", "완료"]
                        new_status = st.selectbox("상태 변경", status_options, index=status_options.index(case['status']) if case['status'] in status_options else 0)
                    
                if add_log and log_text:
                    db.add_case_log(selected_case_id, log_text)
                    
                    # 상태 변경이 있는 경우
                    if new_status != case['status']:
                        end_date = datetime.now().strftime("%Y-%m-%d") if new_status == "완료" and not case['end_date'] else case['end_date']
                        db.update_case_status(selected_case_id, new_status, end_date)
                    
                    st.session_state.notification = "진행 내역이 추가되었습니다."
                    st.rerun()
            else:
                st.error(f"ID가 {selected_case_id}인 사건을 찾을 수 없습니다.")

def show_settings():
    """설정 화면"""
    st.title("설정")
    
    # 탭 설정
    tab1, tab2 = st.tabs(["사용자 관리", "업무 카테고리 관리"])
    
    with tab1:
        st.subheader("사용자 관리")
        
        # 현재 사용자 목록
        if st.session_state.users:
            st.write("현재 사용자:")
            for i, user in enumerate(st.session_state.users):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text(user)
                with col2:
                    if st.button("삭제", key=f"delete_user_{i}"):
                        st.session_state.users.remove(user)
                        config = load_config()
                        config["users"] = st.session_state.users
                        save_config(config)
                        st.session_state.notification = f"사용자 '{user}'가 삭제되었습니다."
                        st.rerun()
        else:
            st.info("등록된 사용자가 없습니다.")
        
        # 새 사용자 추가
        new_user = st.text_input("새 사용자 이름")
        if st.button("사용자 추가"):
            if new_user:
                if new_user not in st.session_state.users:
                    st.session_state.users.append(new_user)
                    config = load_config()
                    config["users"] = st.session_state.users
                    save_config(config)
                    st.session_state.notification = f"사용자 '{new_user}'가 추가되었습니다."
                    st.rerun()
                else:
                    st.error("이미 존재하는 사용자입니다.")
            else:
                st.error("사용자 이름을 입력해주세요.")
    
    with tab2:
        st.subheader("업무 카테고리 관리")
        
        # 현재 카테고리 목록
        if st.session_state.categories:
            for i, category in enumerate(st.session_state.categories):
                with st.expander(f"{category['name']}"):
                    st.write("소분류:")
                    if "sub_categories" in category and category["sub_categories"]:
                        for j, sub_cat in enumerate(category["sub_categories"]):
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.text(sub_cat)
                            with col2:
                                if st.button("삭제", key=f"delete_subcat_{i}_{j}"):
                                    category["sub_categories"].remove(sub_cat)
                                    config = load_config()
                                    config["categories"] = st.session_state.categories
                                    save_config(config)
                                    st.session_state.notification = f"소분류 '{sub_cat}'가 삭제되었습니다."
                                    st.rerun()
                    else:
                        st.info("소분류가 없습니다.")
                    
                    # 소분류 추가
                    new_subcat = st.text_input("새 소분류", key=f"new_subcat_{i}")
                    if st.button("소분류 추가", key=f"add_subcat_{i}"):
                        if new_subcat:
                            if "sub_categories" not in category:
                                category["sub_categories"] = []
                            
                            if new_subcat not in category["sub_categories"]:
                                category["sub_categories"].append(new_subcat)
                                config = load_config()
                                config["categories"] = st.session_state.categories
                                save_config(config)
                                st.session_state.notification = f"소분류 '{new_subcat}'가 추가되었습니다."
                                st.rerun()
                            else:
                                st.error("이미 존재하는 소분류입니다.")
                        else:
                            st.error("소분류 이름을 입력해주세요.")
                    
                    # 대분류 삭제
                    if st.button("대분류 삭제", key=f"delete_category_{i}"):
                        st.session_state.categories.remove(category)
                        config = load_config()
                        config["categories"] = st.session_state.categories
                        save_config(config)
                        st.session_state.notification = f"대분류 '{category['name']}'가 삭제되었습니다."
                        st.rerun()
        else:
            st.info("등록된 카테고리가 없습니다.")
        
        # 새 대분류 추가
        new_category = st.text_input("새 대분류 이름")
        if st.button("대분류 추가"):
            if new_category:
                category_exists = False
                for category in st.session_state.categories:
                    if category["name"] == new_category:
                        category_exists = True
                        break
                
                if not category_exists:
                    st.session_state.categories.append({"name": new_category, "sub_categories": []})
                    config = load_config()
                    config["categories"] = st.session_state.categories
                    save_config(config)
                    st.session_state.notification = f"대분류 '{new_category}'가 추가되었습니다."
                    st.rerun()
                else:
                    st.error("이미 존재하는 대분류입니다.")
            else:
                st.error("대분류 이름을 입력해주세요.")

if __name__ == "__main__":
    main() 