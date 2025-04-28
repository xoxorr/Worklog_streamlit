import sqlite3
import os
import pandas as pd
from datetime import datetime
import json
from typing import List
from pathlib import Path

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
        content TEXT NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # 사건 테이블 (case는 SQLite 예약어이므로 cases로 변경)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        manager TEXT NOT NULL,
        start_date TEXT DEFAULT CURRENT_DATE,
        end_date TEXT,
        status TEXT DEFAULT '진행 중',
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # 사건 로그 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS case_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER,
        text TEXT,
        date TEXT DEFAULT CURRENT_DATE,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases (id)
    )
    ''')
    # 워크로그 테이블 (업무 분류별 기록)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worklog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        main_category TEXT NOT NULL,
        sub_category TEXT NOT NULL,
        content TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        status TEXT DEFAULT '진행 중',
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
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

def get_daily_works(date=None, name=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM daily_work"
    params = []
    
    if date or name:
        query += " WHERE"
        if date:
            query += " date = ?"
            params.append(date)
        if name:
            if date:  # date 파라미터가 이미 있는 경우
                query += " AND"
            query += " name = ?"
            params.append(name)
    
    query += " ORDER BY date DESC, name"
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

def add_case(title, manager):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO cases (title, manager) VALUES (?, ?)
    ''', (title, manager))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_cases():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM cases ORDER BY start_date DESC", conn)
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

def add_case_log(case_id, text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO case_log (case_id, text) VALUES (?, ?)
    ''', (case_id, text))
    conn.commit()
    conn.close()

def update_case_status(case_id, status, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if end_date:
        cursor.execute('UPDATE cases SET status=?, end_date=? WHERE id=?', (status, end_date, case_id))
    else:
        cursor.execute('UPDATE cases SET status=? WHERE id=?', (status, case_id))
    conn.commit()
    conn.close()
    return True

def get_case_logs(case_id) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM case_log WHERE case_id = ? ORDER BY date DESC, id DESC
    ''', (case_id,))
    logs = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
    conn.close()
    return logs

# 워크로그 관련 함수

def add_worklog(name, date, main_category, sub_category, content, start_date=None, end_date=None, status="진행 중"):
    """워크로그 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO worklog (name, date, main_category, sub_category, content, start_date, end_date, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, date, main_category, sub_category, content, start_date, end_date, status))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_worklogs(date=None, name=None, main_category=None, sub_category=None, status=None):
    """워크로그 조회 (필터 가능)"""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM worklog"
    conditions = []
    params = []
    
    if date:
        conditions.append("date = ?")
        params.append(date)
    if name:
        conditions.append("name = ?")
        params.append(name)
    if main_category:
        conditions.append("main_category = ?")
        params.append(main_category)
    if sub_category:
        conditions.append("sub_category = ?")
        params.append(sub_category)
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY date DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def delete_worklog(worklog_id):
    """워크로그 삭제"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM worklog WHERE id=?', (worklog_id,))
    conn.commit()
    conn.close()
    return True

def update_worklog_status(worklog_id, status, end_date=None):
    """워크로그 상태 업데이트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if status == "완료" and end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('UPDATE worklog SET status=?, end_date=? WHERE id=?', (status, end_date, worklog_id))
    conn.commit()
    conn.close()
    return True

# 데이터베이스 초기화 (앱 시작 시 항상 실행)
init_db() 