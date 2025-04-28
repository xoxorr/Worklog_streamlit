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
    
    # 사건 종류 목록
    case_types = ["아전범", "명예훼손", "저작권 침해", "개인정보 유출", "사기", "기타"]
    
    # 저장 성공 알림
    if st.session_state.get("case_saved", False):
        st.success("✅ 사건이 등록되었습니다.")
        st.session_state.case_saved = False
        # 리디렉션용 플래그
        if st.session_state.get("should_rerun", False):
            st.session_state.should_rerun = False
            st.rerun()
    
    # 폼 리셋 처리
    if st.session_state.get("reset_form", False):
        st.session_state.reset_form = False
        # 폼을 리셋하기 위해 아무것도 하지 않음 (재실행될 때 기본값이 적용됨)
    
    with st.form("case_input_form"):
        st.subheader("💼 사건 정보 입력")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("사건명 *")
            manager = st.text_input("담당자 *")
            client = st.text_input("의뢰인")
            case_type = st.selectbox("사건 유형", ["디지털 포렌식", "모바일 포렌식", "네트워크 포렌식", "기타"])
            
        with col2:
            status = st.selectbox("상태", ["접수", "진행중", "완료", "보류"])
            description = st.text_area("설명")
            start_date = st.date_input("시작일", datetime.now())
            end_date = st.date_input("종료일", None, disabled=True if status != "완료" else False)
            
        submit_button = st.form_submit_button("저장")
        
        if submit_button:
            if not title or not manager:
                st.error("사건명과 담당자는 필수 입력 항목입니다.")
            else:
                # 사건 정보 저장
                result = db.add_case(title, manager, client, case_type, status, description, start_date.strftime("%Y-%m-%d"), 
                                     end_date.strftime("%Y-%m-%d") if end_date and status == "완료" else None)
                
                if result:
                    st.success("사건 정보가 저장되었습니다.")
                else:
                    st.error("사건 정보 저장 중 오류가 발생했습니다.")

def show_case_manage():
    """사건 관리 화면 표시"""
    st.header("🗂️ 사건 관리")
    
    # 사건 목록 가져오기
    df = db.get_cases()
    
    if df.empty:
        st.info("등록된 사건이 없습니다.")
        return
    
    # 필터링 옵션들
    with st.expander("필터 옵션", expanded=False):
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            filter_status = st.selectbox("상태 필터", ["전체", "진행 중", "완료", "미완료"])
        
        with filter_col2:
            filter_manager = st.text_input("담당자 검색")
        
        filter_title = st.text_input("사건명 검색")
    
    # 필터링 적용
    filtered_df = df.copy()
    
    if filter_status != "전체":
        filtered_df = filtered_df[filtered_df["status"] == filter_status]
    
    if filter_manager:
        filtered_df = filtered_df[filtered_df["manager"].str.contains(filter_manager, na=False)]
    
    if filter_title:
        filtered_df = filtered_df[filtered_df["title"].str.contains(filter_title, na=False)]
    
    # 필터링된 사건이 없는 경우
    if filtered_df.empty:
        st.warning("조건에 맞는 사건이 없습니다.")
        return
    
    # 사건별 확장 패널 표시
    for i, row in filtered_df.iterrows():
        case_id = row['id']
        
        # 우선순위에 따른 아이콘 추가
        priority_icon = "🔴" if row.get('priority') == "높음" else "🟡" if row.get('priority') == "보통" else "🟢"
        expander_title = f"{priority_icon} {row['title']} (담당: {row['manager']}, 상태: {row['status']})"
        
        with st.expander(expander_title, expanded=False):
            # 탭 인터페이스 사용
            tab1, tab2, tab3, tab4 = st.tabs(["기본 정보", "진행 내역", "세부 작업", "디지털 장비"])
            
            # 탭 1: 기본 정보
            with tab1:
                st.subheader("사건 정보")
                
                # 기본 정보 표시
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.write(f"**사건명**: {row['title']}")
                    st.write(f"**담당자**: {row['manager']}")
                    st.write(f"**의뢰인**: {row.get('client', '-')}")
                    st.write(f"**우선순위**: {row.get('priority', '보통')}")
                
                with info_col2:
                    st.write(f"**시작일**: {row['start_date']}")
                    st.write(f"**종료일**: {row['end_date'] if row['end_date'] else '-'}")
                    st.write(f"**상태**: {row['status']}")
                    st.write(f"**생성일**: {row.get('created_at', '-')}")
                
                # 사건 설명
                if "description" in row and row["description"]:
                    st.subheader("사건 설명")
                    st.write(row["description"])
                
                # 상태/종료일 변경
                st.subheader("상태 변경")
                status_col1, status_col2, status_col3 = st.columns(3)
                
                with status_col1:
                    new_status = st.selectbox(
                        "상태", 
                        ["진행 중", "완료", "미완료"], 
                        index=["진행 중", "완료", "미완료"].index(row['status']), 
                        key=f"status_{case_id}"
                    )
                
                with status_col2:
                    end_date = None
                    if new_status == "완료":
                        end_date = st.date_input(
                            "종료일", 
                            value=datetime.now() if not row['end_date'] else datetime.strptime(row['end_date'], "%Y-%m-%d"),
                            key=f"end_date_{case_id}"
                        )
                
                with status_col3:
                    new_priority = st.selectbox(
                        "우선순위", 
                        ["높음", "보통", "낮음"],
                        index=["높음", "보통", "낮음"].index(row.get('priority', '보통')),
                        key=f"priority_{case_id}"
                    )
                
                if st.button("상태 변경", key=f"update_status_{case_id}"):
                    update_data = {
                        "status": new_status,
                        "priority": new_priority
                    }
                    
                    if new_status == "완료" and end_date:
                        update_data["end_date"] = end_date.strftime("%Y-%m-%d")
                    elif new_status != "완료":
                        update_data["end_date"] = None
                    
                    if db.update_case(case_id, **update_data):
                        st.success("상태가 변경되었습니다.")
                        st.session_state.update_case = True
                        st.rerun()
                    else:
                        st.error("상태 변경 중 오류가 발생했습니다.")
            
            # 탭 2: 진행 내역
            with tab2:
                st.subheader("진행 내역")
                
                # 진행 내역 테이블로 표시
                progresses_df = db.get_case_progresses(case_id=case_id)
                
                if not progresses_df.empty:
                    progress_view = progresses_df[["date", "writer", "content"]]
                    progress_view.columns = ["날짜", "작성자", "내용"]
                    st.dataframe(progress_view, use_container_width=True)
                else:
                    # 기존 case_logs 호환성 처리
                    logs = db.get_case_logs(case_id)
                    if logs:
                        for log in logs:
                            st.markdown(f"- {log['date']}: {log['text']}")
                    else:
                        st.info("진행 내역이 없습니다.")
                
                # 진행 내역 추가 폼
                with st.form(f"add_progress_{case_id}"):
                    progress_col1, progress_col2 = st.columns([3, 1])
                    
                    with progress_col1:
                        new_progress = st.text_area("진행 내역", key=f"progress_{case_id}")
                    
                    with progress_col2:
                        progress_writer = st.text_input("작성자", key=f"progress_writer_{case_id}")
                    
                    progress_submit = st.form_submit_button("추가")
                    
                    if progress_submit and new_progress:
                        if not progress_writer:
                            st.error("작성자를 입력해주세요.")
                        else:
                            # 새 진행 내역 추가
                            db.add_case_progress(case_id, progress_writer, new_progress)
                            st.success("진행 내역이 추가되었습니다. 새로고침 해주세요.")
                            st.rerun()
            
            # 탭 3: 세부 작업 목록
            with tab3:
                st.subheader("세부 작업 목록")
                
                # 세부 작업 목록 표시
                tasks_df = db.get_case_tasks(case_id=case_id)
                
                if not tasks_df.empty:
                    # 세부 작업 테이블로 표시
                    task_view = tasks_df[["main_category", "sub_category", "content", "start_date", "end_date", "status", "writer"]]
                    task_view.columns = ["대분류", "소분류", "내용", "시작일", "종료일", "상태", "작성자"]
                    st.dataframe(task_view, use_container_width=True)
                else:
                    st.info("등록된 세부 작업이 없습니다.")
                
                # 세부 작업 추가 버튼
                if st.button("새 세부 작업 추가", key=f"add_task_btn_{case_id}"):
                    st.session_state.add_task_case_id = case_id
                    st.session_state.show_add_task_form = True
                
                # 세부 작업 추가 폼 (session_state로 표시 제어)
                if st.session_state.get("show_add_task_form", False) and st.session_state.get("add_task_case_id") == case_id:
                    st.subheader("새 세부 작업 추가")
                    
                    with st.form(f"add_task_form_{case_id}"):
                        # 폼 외부에서는 session_state 변수만 초기화
                        if "selected_main_category" not in st.session_state:
                            st.session_state.selected_main_category = list(CATEGORY_MAPPING.keys())[0]
                        
                        # 작성자 입력
                        task_writer = st.text_input("작성자")
                        
                        # 대분류 선택
                        main_category = st.selectbox(
                            "대분류 선택", 
                            list(CATEGORY_MAPPING.keys()),
                            key=f"task_main_category_{case_id}",
                            index=list(CATEGORY_MAPPING.keys()).index(st.session_state.selected_main_category)
                        )
                        
                        # 소분류 선택
                        sub_category = st.selectbox(
                            "소분류 선택",
                            CATEGORY_MAPPING[main_category],
                            key=f"task_sub_category_{case_id}"
                        )
                        
                        # 업무 내용 입력
                        task_content = st.text_area("업무 내용", height=100)
                        
                        # 날짜 및 상태 입력
                        task_col1, task_col2, task_col3 = st.columns(3)
                        
                        with task_col1:
                            task_start_date = st.date_input("시작일", value=datetime.now())
                        
                        with task_col2:
                            task_end_date = st.date_input("종료일", value=datetime.now())
                        
                        with task_col3:
                            task_hours = st.number_input(
                                "소요 시간", 
                                min_value=0.0,
                                value=0.0, 
                                step=0.5,
                                format="%.1f",
                                help="0.5 = 30분, 1.0 = 1시간, 1.5 = 1시간 30분 ..."
                            )
                        
                        task_status = st.selectbox("진행 상태", ["진행 중", "완료", "미완료"])
                        
                        task_submit = st.form_submit_button("저장")
                        
                        if task_submit:
                            if not task_writer or not task_content:
                                st.error("작성자와 업무 내용은 필수입니다.")
                            else:
                                # DB에 저장
                                db.add_case_task(
                                    case_id=case_id,
                                    main_category=main_category,
                                    sub_category=sub_category,
                                    content=task_content,
                                    start_date=task_start_date.strftime("%Y-%m-%d"),
                                    end_date=task_end_date.strftime("%Y-%m-%d"),
                                    status=task_status,
                                    writer=task_writer,
                                    hours=task_hours
                                )
                                
                                # 폼 숨기기
                                st.session_state.show_add_task_form = False
                                st.success("세부 작업이 저장되었습니다.")
                                st.rerun()
            
            # 탭 4: 디지털 장비
            with tab4:
                st.subheader("디지털 장비 목록")
                
                # 디지털 장비 목록 표시
                devices_df = db.get_digital_devices(case_id=case_id)
                
                if not devices_df.empty:
                    # 장비 목록 테이블로 표시
                    device_view = devices_df[["name", "device_type", "model", "acquisition_date", "status"]]
                    device_view.columns = ["장비명", "유형", "모델명", "수집일자", "상태"]
                    st.dataframe(device_view, use_container_width=True)
                
                    # 장비 세부 정보 선택 드롭다운
                    selected_device_id = st.selectbox(
                        "장비 세부 정보 보기", 
                        devices_df["id"].tolist(),
                        format_func=lambda x: devices_df[devices_df["id"] == x]["name"].iloc[0],
                        key=f"device_select_{case_id}"
                    )
                    
                    if selected_device_id:
                        selected_device = devices_df[devices_df["id"] == selected_device_id].iloc[0]
                        
                        # 세부 정보 표시
                        st.write("### 장비 세부 정보")
                        detail_col1, detail_col2 = st.columns(2)
                        
                        with detail_col1:
                            st.write(f"**장비명**: {selected_device['name']}")
                            st.write(f"**장비 유형**: {selected_device['device_type']}")
                            st.write(f"**제조사**: {selected_device['manufacturer'] or '-'}")
                            st.write(f"**모델명**: {selected_device['model'] or '-'}")
                            st.write(f"**시리얼번호**: {selected_device['serial_number'] or '-'}")
                        
                        with detail_col2:
                            st.write(f"**저장용량**: {selected_device['storage_size'] or '-'}")
                            st.write(f"**수집일자**: {selected_device['acquisition_date'] or '-'}")
                            st.write(f"**수집방법**: {selected_device['acquisition_method'] or '-'}")
                            st.write(f"**해시값**: {selected_device['hash_value'] or '-'}")
                            st.write(f"**상태**: {selected_device['status']}")
                        
                        if selected_device['description']:
                            st.write("**설명**:")
                            st.write(selected_device['description'])
                else:
                    st.info("등록된 디지털 장비가 없습니다.")
                
                # 장비 추가 버튼
                if st.button("새 장비 추가", key=f"add_device_btn_{case_id}"):
                    st.session_state.add_device_case_id = case_id
                    st.session_state.show_add_device_form = True
                
                # 장비 추가 폼 (session_state로 표시 제어)
                if st.session_state.get("show_add_device_form", False) and st.session_state.get("add_device_case_id") == case_id:
                    st.subheader("새 장비 추가")
                    
                    with st.form(f"add_device_form_{case_id}"):
                        device_col1, device_col2 = st.columns(2)
                        
                        with device_col1:
                            device_type = st.selectbox(
                                "기기 종류",
                                ["휴대폰", "PC", "블랙박스", "저장장치", "CCTV", "기타"]
                            )
                            device_name = st.text_input("기기명")
                            model = st.text_input("모델명 (예: 아이폰 14pro, 갤럭시 S21)")
                            manufacturer = st.text_input("제조사")
                            serial_number = st.text_input("시리얼 번호")
                        
                        with device_col2:
                            storage_size = st.text_input("저장용량")
                            acquisition_date = st.date_input("수집일자", value=datetime.now())
                            acquisition_method = st.text_input("수집방법")
                            status = st.selectbox("상태", ["수집완료", "검토중", "검토완료", "반환"])
                            hash_value = st.text_input("해시값")
                        
                        # 검토 일정 섹션
                        st.subheader("검토 일정")
                        date_col1, date_col2 = st.columns(2)
                        
                        with date_col1:
                            examination_start_date = st.date_input("검토 시작일", value=datetime.now())
                        
                        with date_col2:
                            examination_end_date = st.date_input("검토 완료일", value=datetime.now() + timedelta(days=3))
                        
                        description = st.text_area("설명", height=100)
                        
                        device_submit = st.form_submit_button("저장")
                        
                        if device_submit:
                            if not device_name or not device_type:
                                st.error("기기명과 기기 종류는 필수입니다.")
                            else:
                                # DB에 저장
                                db.add_digital_device(
                                    case_id=case_id,
                                    device_type=device_type,
                                    name=device_name,
                                    model=model,
                                    serial_number=serial_number,
                                    manufacturer=manufacturer,
                                    storage_size=storage_size,
                                    acquisition_date=acquisition_date.strftime("%Y-%m-%d"),
                                    examination_start_date=examination_start_date.strftime("%Y-%m-%d"),
                                    examination_end_date=examination_end_date.strftime("%Y-%m-%d"),
                                    acquisition_method=acquisition_method,
                                    hash_value=hash_value,
                                    description=description,
                                    status=status
                                )
                                
                                # 폼 숨기기
                                st.session_state.show_add_device_form = False
                                st.success("장비가 저장되었습니다.")
                                st.rerun()

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
    
    # 사건 연결 여부 선택
    link_to_case = st.checkbox("사건에 연결하기", value=False, key="link_to_case")
    
    # 사건 목록 가져오기 (연결 옵션 선택 시)
    selected_case_id = None
    if link_to_case:
        cases_df = db.get_cases(filter_dict={"status": "진행 중"})
        if not cases_df.empty:
            # 사건 선택 드롭다운
            case_options = cases_df["id"].tolist()
            selected_case_id = st.selectbox(
                "연결할 사건 선택",
                case_options,
                format_func=lambda x: f"{cases_df[cases_df['id'] == x]['title'].iloc[0]} (담당: {cases_df[cases_df['id'] == x]['manager'].iloc[0]})",
                key="selected_case"
            )
        else:
            st.warning("진행 중인 사건이 없습니다.")
            link_to_case = False
    
    with st.form("work_category_form"):
        # 작성자 입력
        writer = st.selectbox("작성자", name_options)
        
        # 대분류 선택 (session_state 값으로 초기 인덱스 설정)
        main_category = st.selectbox(
            "대분류 선택", 
            list(CATEGORY_MAPPING.keys()),
            key="main_category",
            index=list(CATEGORY_MAPPING.keys()).index(st.session_state.selected_main_category)
        )
        
        # 폼이 제출되면 session_state.selected_main_category 값이 업데이트됨
        st.session_state.selected_main_category = main_category
        
        # 소분류 선택 (대분류에 따라 동적으로 변경)
        sub_category = st.selectbox(
            "소분류 선택",
            CATEGORY_MAPPING[main_category]
        )
        
        # 업무 내용 입력
        content = st.text_area("업무 내용", height=150)
        
        # 시작일/종료일 입력
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("시작일", value=datetime.now())
        with col2:
            end_date = st.date_input("종료일", value=datetime.now())
        with col3:
            hours = st.number_input(
                "소요 시간", 
                min_value=0.0,
                value=0.0, 
                step=0.5,
                format="%.1f",
                help="0.5 = 30분, 1.0 = 1시간, 1.5 = 1시간 30분 ..."
            )
        
        # 진행 상태 선택
        status = st.selectbox("진행 상태", ["진행 중", "완료", "미완료"])
        
        # 제출 버튼
        submitted = st.form_submit_button("저장")
        
        if submitted:
            if not writer or not content:
                st.error("작성자와 업무 내용은 필수입니다.")
            else:
                # 사건 연결 여부에 따라 저장 위치 결정
                if link_to_case and selected_case_id:
                    # 사건 세부 작업으로 저장 (case_tasks 테이블)
                    db.add_case_task(
                        case_id=selected_case_id,
                        main_category=main_category,
                        sub_category=sub_category,
                        content=content,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        status=status,
                        writer=writer,
                        hours=hours
                    )
                else:
                    # 독립된 업무 기록으로 저장 (work_categories 테이블)
                    db.add_work_category(
                        main_category=main_category,
                        sub_category=sub_category,
                        content=content,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        status=status,
                        writer=writer,
                        hours=hours,
                        case_id=None,  # 연결된 사건 없음
                        memo=None      # 메모 없음
                    )
                
                st.session_state.work_category_saved = True
                st.rerun()
    
    # 기록된 데이터 조회 및 표시
    st.subheader("기록된 업무 내역")
    
    # 상태에 따른 스타일링 적용 함수 - 함수를 여기로 옮겨서 모든 탭에서 접근 가능하게 함
    def highlight_status(val):
        if val == "완료":
            return "background-color: lightgreen"
        elif val == "진행 중":
            return "background-color: lightyellow"
        elif val == "미완료":
            return "background-color: lightcoral"
        return ""
    
    # 필터링 옵션 (탭으로 구분)
    tab1, tab2 = st.tabs(["일반 업무 기록", "사건 관련 업무"])
    
    # 탭 1: 일반 업무 기록 (work_categories 테이블)
    with tab1:
        # 필터링 옵션
        with st.expander("필터 옵션", expanded=False):
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            with filter_col1:
                filter_main = st.selectbox("대분류 필터", ["전체"] + list(CATEGORY_MAPPING.keys()), key="filter_main_general")
            
            with filter_col2:
                # 대분류 선택에 따라 소분류 옵션 변경
                if filter_main == "전체":
                    filter_sub_options = ["전체"]
                else:
                    filter_sub_options = ["전체"] + CATEGORY_MAPPING[filter_main]
                
                filter_sub = st.selectbox("소분류 필터", filter_sub_options, key="filter_sub_general")
            
            with filter_col3:
                filter_status = st.selectbox("상태 필터", ["전체", "진행 중", "완료", "미완료"], key="filter_status_general")
            
            filter_writer = st.selectbox("작성자 필터", ["전체"] + name_options, key="filter_writer_general")
        
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
            
            # 스타일 적용
            styled_df = display_df.style.map(highlight_status, subset=["상태"])
            
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
    
    # 탭 2: 사건 관련 업무 (case_tasks 테이블)
    with tab2:
        # 필터링 옵션
        with st.expander("필터 옵션", expanded=False):
            # 사건 선택 필터
            cases_all_df = db.get_cases()
            if not cases_all_df.empty:
                case_filter_options = ["전체"] + cases_all_df["id"].tolist()
                selected_case_filter = st.selectbox(
                    "사건 필터",
                    case_filter_options,
                    format_func=lambda x: "전체" if x == "전체" else f"{cases_all_df[cases_all_df['id'] == x]['title'].iloc[0]}",
                    key="selected_case_filter"
                )
            else:
                selected_case_filter = None
                st.info("등록된 사건이 없습니다.")
            
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                task_filter_main = st.selectbox("대분류 필터", ["전체"] + list(CATEGORY_MAPPING.keys()), key="filter_main_case")
            
            with filter_col2:
                if task_filter_main == "전체":
                    task_filter_sub_options = ["전체"]
                else:
                    task_filter_sub_options = ["전체"] + CATEGORY_MAPPING[task_filter_main]
                
                task_filter_sub = st.selectbox("소분류 필터", task_filter_sub_options, key="filter_sub_case")
            
            task_filter_writer = st.selectbox("작성자 필터", ["전체"] + name_options, key="filter_writer_case")
        
        # 필터 적용하여 데이터 조회
        case_filter_dict = {}
        case_id_filter = None
        
        if selected_case_filter and selected_case_filter != "전체":
            case_id_filter = selected_case_filter
        
        if task_filter_main != "전체":
            case_filter_dict["main_category"] = task_filter_main
        
        if task_filter_sub != "전체":
            case_filter_dict["sub_category"] = task_filter_sub
        
        if task_filter_writer != "전체":
            case_filter_dict["writer"] = task_filter_writer
        
        # 사건 세부 작업 데이터 가져오기
        tasks_df = db.get_case_tasks(case_id=case_id_filter, filter_dict=case_filter_dict)
        
        if tasks_df.empty:
            st.info("등록된 사건 관련 업무가 없습니다.")
        else:
            # 사건 정보 연결
            if not cases_all_df.empty:
                # 사건 ID와 사건명을 매핑
                case_id_to_title = dict(zip(cases_all_df["id"], cases_all_df["title"]))
                # 사건 ID 컬럼에 사건명 매핑
                tasks_df["case_title"] = tasks_df["case_id"].map(case_id_to_title)
            
            # 표시할 컬럼 선택 및 정렬
            display_tasks_df = tasks_df[["id", "case_title", "writer", "main_category", "sub_category", 
                                          "content", "start_date", "end_date", "hours", "status"]]
            display_tasks_df.columns = ["ID", "사건명", "작성자", "대분류", "소분류", "업무내용", 
                                          "시작일", "종료일", "소요시간", "상태"]
            
            # 스타일 적용
            styled_tasks_df = display_tasks_df.style.map(highlight_status, subset=["상태"])
            
            # 테이블 표시
            st.dataframe(styled_tasks_df, use_container_width=True)
            
            # 엑셀 다운로드 버튼
            tasks_excel_data = utils.create_excel_report(tasks_df)
            st.download_button(
                label="Excel로 다운로드",
                data=tasks_excel_data,
                file_name=f"case_tasks_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_tasks_btn"
            )

if __name__ == "__main__":
    main() 