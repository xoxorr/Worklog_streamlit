import sqlite3
import os
import pandas as pd
from datetime import datetime
import json
from typing import List

# DB 파일 경로
DB_PATH = 'worklog.db'

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 일일업무 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_work (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        content TEXT NOT NULL
    )
    ''')
    # 사건 테이블 (case는 SQLite 예약어이므로 cases로 변경)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        manager TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        status TEXT NOT NULL,
        logs TEXT -- JSON 배열(진행내역)
    )
    ''')
    # 업무 분류 테이블 추가
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS work_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        main_category TEXT NOT NULL,
        sub_category TEXT NOT NULL,
        content TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL,
        writer TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()
    print("데이터베이스가 초기화되었습니다.")

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

# 사건 관련 함수

def add_case(title, manager, status="진행 중"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    start_date = datetime.now().strftime("%Y-%m-%d")
    logs = json.dumps([])
    cursor.execute('''
    INSERT INTO cases (title, manager, start_date, status, logs) VALUES (?, ?, ?, ?, ?)
    ''', (title, manager, start_date, status, logs))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_cases(status=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM cases"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY start_date DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_case(case_id):
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

def update_case_status(case_id, status, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if status == "완료" and end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('UPDATE cases SET status=?, end_date=? WHERE id=?', (status, end_date, case_id))
    conn.commit()
    conn.close()
    return True

def get_case_logs(case_id) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT logs FROM cases WHERE id=?', (case_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []

# 업무 분류 관련 함수
def add_work_category(main_category, sub_category, content, start_date, end_date, status, writer):
    """업무 분류 데이터 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO work_categories 
    (main_category, sub_category, content, start_date, end_date, status, writer, created_at) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (main_category, sub_category, content, start_date, end_date, status, writer, created_at))
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

def update_work_category(category_id, main_category=None, sub_category=None, content=None, 
                         start_date=None, end_date=None, status=None):
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
    
    if main_category is not None:
        updates.append("main_category = ?")
        params.append(main_category)
    
    if sub_category is not None:
        updates.append("sub_category = ?")
        params.append(sub_category)
    
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    
    if start_date is not None:
        updates.append("start_date = ?")
        params.append(start_date)
    
    if end_date is not None:
        updates.append("end_date = ?")
        params.append(end_date)
    
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    
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