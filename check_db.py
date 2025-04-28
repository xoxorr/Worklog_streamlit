import sqlite3
import os

print(f"현재 디렉토리: {os.getcwd()}")
print(f"worklog.db 파일 존재 여부: {os.path.exists('worklog.db')}")

# DB 연결
conn = sqlite3.connect('worklog.db')
cursor = conn.cursor()

# 테이블 목록 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\n데이터베이스 테이블 목록:")
for table in tables:
    print(f"- {table[0]}")

# worklog 테이블 구조 확인
cursor.execute("PRAGMA table_info(worklog)")
columns = cursor.fetchall()
print("\nworklog 테이블 구조:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

# 테이블 데이터 샘플 확인 (각 테이블 별)
for table_name in [t[0] for t in tables]:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\n{table_name} 테이블 레코드 수: {count}")
        
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            sample = cursor.fetchone()
            print(f"{table_name} 샘플 데이터: {sample}")
    except Exception as e:
        print(f"{table_name} 테이블 조회 중 오류: {e}")

conn.close() 