import sqlite3
import os
import pandas as pd
from datetime import datetime
import json
from typing import List, Dict, Any, Optional, Union

# DB 파일 경로
DB_PATH = 'worklog.db'

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 일일업무 테이블 (기존)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_work (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        content TEXT NOT NULL
    )
    ''')
    
    # A 테이블: 사건 테이블 (Case DB)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,                -- 사건명
        manager TEXT NOT NULL,              -- 담당자
        client TEXT,                        -- 의뢰인
        case_type TEXT,                     -- 사건 종류 (예: 아전범, 명예훼손)
        status TEXT NOT NULL,               -- 진행상태
        priority TEXT,                      -- 우선순위
        description TEXT,                   -- 사건 설명
        start_date TEXT NOT NULL,           -- 시작일
        end_date TEXT,                      -- 종료일
        logs TEXT,                          -- JSON 배열(진행내역)
        created_at TEXT NOT NULL            -- 생성일시
    )
    ''')
    
    # 업무 진행 경과 테이블 (기존 case_logs를 독립 테이블로 분리)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS case_progresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,           -- 연결된 사건 ID
        date TEXT NOT NULL,                 -- 날짜
        writer TEXT NOT NULL,               -- 작성자
        content TEXT NOT NULL,              -- 진행 내용
        created_at TEXT NOT NULL,           -- 생성일시
        FOREIGN KEY(case_id) REFERENCES cases(id)
    )
    ''')
    
    # 업무 기록 테이블 (Work Log DB)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS work_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,                 -- 날짜
        main_category TEXT NOT NULL,        -- 대분류
        sub_category TEXT NOT NULL,         -- 소분류
        content TEXT NOT NULL,              -- 업무 상세 설명 
        start_date TEXT NOT NULL,           -- 시작일
        end_date TEXT NOT NULL,             -- 종료일
        status TEXT NOT NULL,               -- 상태
        writer TEXT NOT NULL,               -- 작성자
        hours REAL,                         -- 소요 시간(시간)
        case_id INTEGER,                    -- 사건 관련 DB와 연결
        created_at TEXT NOT NULL,           -- 생성일시
        memo TEXT,                          -- 추가 메모용
        FOREIGN KEY(case_id) REFERENCES cases(id)
    )
    ''')
    
    # 기기 관리 테이블 (Device DB)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS digital_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,           -- 연결된 사건 ID
        device_type TEXT NOT NULL,          -- 기기 종류 (휴대폰/PC/블랙박스 등)
        name TEXT NOT NULL,                 -- 기기명
        model TEXT,                         -- 모델명 (예: "아이폰 14pro", "갤럭시 S21")
        acquisition_date TEXT,              -- 수집일자
        examination_start_date TEXT,        -- 검토 시작일
        examination_end_date TEXT,          -- 검토 완료일
        status TEXT NOT NULL,               -- 상태 (수집완료/검토중/검토완료 등)
        serial_number TEXT,                 -- 시리얼번호
        manufacturer TEXT,                  -- 제조사
        storage_size TEXT,                  -- 저장용량
        acquisition_method TEXT,            -- 수집방법
        hash_value TEXT,                    -- 해시값
        description TEXT,                   -- 설명
        created_at TEXT NOT NULL,           -- 생성일시
        FOREIGN KEY(case_id) REFERENCES cases(id)
    )
    ''')
    
    # 사건 세부 작업 테이블 (A-1 테이블, case_tasks)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS case_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,           -- 연결된 사건 ID
        main_category TEXT NOT NULL,        -- 대분류
        sub_category TEXT NOT NULL,         -- 소분류
        content TEXT NOT NULL,              -- 작업 내용
        start_date TEXT NOT NULL,           -- 시작일
        end_date TEXT NOT NULL,             -- 종료일
        status TEXT NOT NULL,               -- 상태 (진행 중/완료/미완료)
        writer TEXT NOT NULL,               -- 작성자
        hours REAL,                         -- 소요 시간
        created_at TEXT NOT NULL,           -- 생성일시
        FOREIGN KEY(case_id) REFERENCES cases(id)
    )
    ''')
    
    # 테이블 업그레이드 검사 실행
    upgrade_tables(conn, cursor)
    
    conn.commit()
    conn.close()
    print("데이터베이스가 초기화되었습니다.")

def upgrade_tables(conn, cursor):
    """기존 테이블에 누락된 컬럼이 있는지 확인하고 필요한 경우 업그레이드"""
    
    # 기존 테이블 구조 확인 함수
    def table_has_column(table_name, column_name):
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return any(column[1] == column_name for column in columns)
    
    # 기존 테이블이 존재하는지 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cases'")
    if cursor.fetchone():
        # 1. cases 테이블 업그레이드
        required_columns = {
            'client': 'TEXT',
            'case_type': 'TEXT',
            'description': 'TEXT',
            'created_at': 'TEXT'
        }
        
        for column_name, column_type in required_columns.items():
            if not table_has_column('cases', column_name):
                try:
                    print(f"테이블 cases에 컬럼 {column_name} 추가 중...")
                    cursor.execute(f"ALTER TABLE cases ADD COLUMN {column_name} {column_type}")
                except sqlite3.OperationalError as e:
                    print(f"오류 발생: {e}")
    
    # 2. work_categories 테이블 업그레이드
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='work_categories'")
    if cursor.fetchone():
        required_columns = {
            'date': 'TEXT',
            'hours': 'REAL',
            'case_id': 'INTEGER',
            'memo': 'TEXT'
        }
        
        for column_name, column_type in required_columns.items():
            if not table_has_column('work_categories', column_name):
                try:
                    print(f"테이블 work_categories에 컬럼 {column_name} 추가 중...")
                    cursor.execute(f"ALTER TABLE work_categories ADD COLUMN {column_name} {column_type}")
                except sqlite3.OperationalError as e:
                    print(f"오류 발생: {e}")
    
    # 3. digital_devices 테이블 업그레이드
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='digital_devices'")
    if cursor.fetchone():
        required_columns = {
            'examination_start_date': 'TEXT',
            'examination_end_date': 'TEXT'
        }
        
        for column_name, column_type in required_columns.items():
            if not table_has_column('digital_devices', column_name):
                try:
                    print(f"테이블 digital_devices에 컬럼 {column_name} 추가 중...")
                    cursor.execute(f"ALTER TABLE digital_devices ADD COLUMN {column_name} {column_type}")
                except sqlite3.OperationalError as e:
                    print(f"오류 발생: {e}")
    
    conn.commit()

# 일일업무 관련 함수

def add_daily_work(name, date, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO daily_work (name, date, content) VALUES (?, ?, ?)
    ''', (name, date, content))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_daily_works(date=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM daily_work"
    params = []
    if date:
        query += " WHERE date = ?"
        params.append(date)
    query += " ORDER BY name, id"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def delete_daily_work(work_id):
    """일일 업무 삭제"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM daily_work WHERE id=?', (work_id,))
    conn.commit()
    conn.close()
    return True

# 사건(A 테이블) 관련 함수 (기존 함수 확장)
def add_case(title, manager, client, case_type, status, description, start_date=None, end_date=None):
    """
    사건 정보를 데이터베이스에 추가
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_date = start_date or now.split()[0]
        
        cursor.execute(
            """
            INSERT INTO cases (title, manager, client, case_type, status, description, start_date, end_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, manager, client, case_type, status, description, start_date, end_date, now)
        )
        
        case_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return case_id
    except Exception as e:
        print(f"사건 추가 중 오류 발생: {e}")
        return None

def get_cases(filter_dict=None):
    """사건 목록 조회 (필터링 지원)"""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT * FROM cases"
    params = []
    
    if filter_dict:
        conditions = []
        for key, value in filter_dict.items():
            if value:
                conditions.append(f"{key} = ?")
                params.append(value)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY start_date DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_case(case_id, **kwargs):
    """
    사건 정보 업데이트
    
    Args:
        case_id: 업데이트할 사건 ID
        **kwargs: 업데이트할 필드 (title, manager, client, case_type, status, description, start_date, end_date)
    
    Returns:
        bool: 업데이트 성공 여부
    """
    try:
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['title', 'manager', 'client', 'case_type', 'status', 'description', 'start_date', 'end_date']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = f"UPDATE cases SET {', '.join(fields)} WHERE id = ?"
        values.append(case_id)
        
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"사건 업데이트 중 오류 발생: {e}")
        return False

# 업무 진행 경과(B 테이블) 관련 함수
def add_case_progress(case_id, writer, content):
    """업무 진행 경과 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
    INSERT INTO case_progresses
    (case_id, date, writer, content, created_at)
    VALUES (?, ?, ?, ?, ?)
    ''', (case_id, date, writer, content, created_at))
    
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    
    # 기존 case_logs와의 호환성을 위해 json 업데이트도 함께 수행
    add_case_log(case_id, content)
    
    return last_id

def get_case_progresses(case_id=None, start_date=None, end_date=None):
    """업무 진행 경과 조회"""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT * FROM case_progresses"
    params = []
    conditions = []
    
    if case_id:
        conditions.append("case_id = ?")
        params.append(case_id)
    
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY date DESC, created_at DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# 사건 세부 작업(A-1 테이블) 관련 함수
def add_case_task(case_id, main_category, sub_category, content, 
                  start_date, end_date, status, writer, hours=None):
    """사건 세부 작업 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
    INSERT INTO case_tasks
    (case_id, main_category, sub_category, content, start_date, end_date, 
     status, writer, hours, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (case_id, main_category, sub_category, content, start_date, 
          end_date, status, writer, hours, created_at))
    
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_case_tasks(case_id=None, filter_dict=None):
    """사건 세부 작업 조회"""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT * FROM case_tasks"
    params = []
    conditions = []
    
    if case_id:
        conditions.append("case_id = ?")
        params.append(case_id)
    
    if filter_dict:
        for key, value in filter_dict.items():
            if value and key in ['main_category', 'sub_category', 'status', 'writer']:
                conditions.append(f"{key} = ?")
                params.append(value)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY start_date DESC, created_at DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_case_tasks_by_date_range(start_date, end_date, case_id=None):
    """날짜 범위로 사건 세부 작업 조회"""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT * FROM case_tasks WHERE (start_date BETWEEN ? AND ?) OR (end_date BETWEEN ? AND ?)"
    params = [start_date, end_date, start_date, end_date]
    
    if case_id:
        query += " AND case_id = ?"
        params.append(case_id)
    
    query += " ORDER BY start_date"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# 디지털 장비 정보 관련 함수
def add_digital_device(case_id, device_type, name, model=None, **kwargs):
    """디지털 장비 정보 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 기본 필드 및 추가 정보
    serial_number = kwargs.get('serial_number', '')
    manufacturer = kwargs.get('manufacturer', '')
    storage_size = kwargs.get('storage_size', '')
    acquisition_date = kwargs.get('acquisition_date', datetime.now().strftime("%Y-%m-%d"))
    examination_start_date = kwargs.get('examination_start_date', '')
    examination_end_date = kwargs.get('examination_end_date', '')
    acquisition_method = kwargs.get('acquisition_method', '')
    hash_value = kwargs.get('hash_value', '')
    description = kwargs.get('description', '')
    status = kwargs.get('status', '수집완료')
    
    cursor.execute('''
    INSERT INTO digital_devices
    (case_id, device_type, name, model, serial_number, manufacturer,
     storage_size, acquisition_date, examination_start_date, examination_end_date, 
     acquisition_method, hash_value, description, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (case_id, device_type, name, model, serial_number, manufacturer,
          storage_size, acquisition_date, examination_start_date, examination_end_date,
          acquisition_method, hash_value, description, status, created_at))
    
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_digital_devices(case_id=None, filter_dict=None):
    """디지털 장비 정보 조회"""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT * FROM digital_devices"
    params = []
    conditions = []
    
    if case_id:
        conditions.append("case_id = ?")
        params.append(case_id)
    
    if filter_dict:
        for key, value in filter_dict.items():
            if value and key in ['device_type', 'name', 'model', 'status']:
                conditions.append(f"{key} = ?")
                params.append(value)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY acquisition_date DESC, created_at DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_digital_device(device_id, **kwargs):
    """디지털 장비 정보 업데이트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 현재 데이터 조회
    cursor.execute('SELECT * FROM digital_devices WHERE id=?', (device_id,))
    current_data = cursor.fetchone()
    
    if not current_data:
        conn.close()
        return False
    
    # 업데이트할 필드와 값 목록 생성
    updates = []
    params = []
    
    valid_fields = ['name', 'device_type', 'model', 'serial_number', 'manufacturer', 
                    'storage_size', 'acquisition_date', 'examination_start_date',
                    'examination_end_date', 'acquisition_method', 
                    'hash_value', 'description', 'status']
    
    for key, value in kwargs.items():
        if value is not None and key in valid_fields:
            updates.append(f"{key} = ?")
            params.append(value)
    
    # 업데이트할 내용이 있을 경우만 실행
    if updates:
        query = f"UPDATE digital_devices SET {', '.join(updates)} WHERE id = ?"
        params.append(device_id)
        cursor.execute(query, params)
        conn.commit()
        
    conn.close()
    return True

# 기존 호환성 함수들 유지
def get_case(case_id):
    """단일 사건 조회 (호환성 유지)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cases WHERE id=?', (case_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def add_case_log(case_id, log_text):
    """기존 사건 로그 추가 함수 (호환성 유지)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT logs FROM cases WHERE id=?', (case_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    logs = json.loads(row[0]) if row[0] else []
    logs.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "text": log_text
    })
    cursor.execute('UPDATE cases SET logs=? WHERE id=?', (json.dumps(logs, ensure_ascii=False), case_id))
    conn.commit()
    conn.close()
    return True

def get_case_logs(case_id) -> List[dict]:
    """기존 사건 로그 조회 함수 (호환성 유지)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT logs FROM cases WHERE id=?', (case_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []

def update_case_status(case_id, status, end_date=None):
    """기존 사건 상태 업데이트 함수 (호환성 유지)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if status == "완료" and end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('UPDATE cases SET status=?, end_date=? WHERE id=?', (status, end_date, case_id))
    conn.commit()
    conn.close()
    return True

# 업무 분류 관련 함수
def add_work_category(main_category, sub_category, content, start_date, end_date, status, writer, hours=None, case_id=None, memo=None):
    """업무 분류 데이터 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO work_categories 
    (date, main_category, sub_category, content, start_date, end_date, status, writer, hours, case_id, created_at, memo) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date, main_category, sub_category, content, start_date, end_date, status, writer, hours, case_id, created_at, memo))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_work_categories(filter_dict=None):
    """업무 분류 데이터 조회"""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM work_categories"
    params = []
    
    if filter_dict:
        conditions = []
        for key, value in filter_dict.items():
            if value:
                conditions.append(f"{key} = ?")
                params.append(value)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_work_category(category_id, **kwargs):
    """업무 분류 데이터 수정"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 현재 데이터 조회
    cursor.execute('SELECT * FROM work_categories WHERE id=?', (category_id,))
    current_data = cursor.fetchone()
    
    if not current_data:
        conn.close()
        return False
    
    # 업데이트할 필드와 값 목록 생성
    updates = []
    params = []
    
    valid_fields = ['date', 'main_category', 'sub_category', 'content', 
                   'start_date', 'end_date', 'status', 'writer', 
                   'hours', 'case_id', 'memo']
    
    for key, value in kwargs.items():
        if value is not None and key in valid_fields:
            updates.append(f"{key} = ?")
            params.append(value)
    
    # 업데이트할 내용이 있을 경우만 실행
    if updates:
        query = f"UPDATE work_categories SET {', '.join(updates)} WHERE id = ?"
        params.append(category_id)
        cursor.execute(query, params)
        conn.commit()
        
    conn.close()
    return True

def delete_work_category(category_id):
    """업무 분류 데이터 삭제"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM work_categories WHERE id=?', (category_id,))
    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return affected_rows > 0

# 데이터베이스 초기화 (앱 시작 시 항상 실행)
init_db() 