# 디지털포렌식 업무기록 시스템

디지털포렌식 팀의 업무 기록과 관리를 위한 웹 애플리케이션입니다. Streamlit 프레임워크와 SQLite 데이터베이스를 사용하여 구현되었으며, 다양한 업무 기록, 검색, 시각화 및 보고서 생성 기능을 제공합니다.

## 주요 기능

- **업무 입력**: 작성자, A/B/C 카테고리, 업무 내용, 시작/종료일 등 상세 정보 기록
- **검색 및 조회**: 작성자, 카테고리, 상태, 기간별 필터링 및 키워드 검색
- **통계 및 시각화**: 카테고리별, 상태별, 작성자별 통계 및 간트 차트 시각화
- **데이터 출력**: 검색 결과를 Excel, PDF로 다운로드 기능
- **DB 관리**: 데이터베이스 백업 및 복원 기능

## 프로젝트 구조

```
/worklog_streamlit
 ├── app.py            # Streamlit 메인 파일
 ├── db.py             # DB 연결 및 함수 관리
 ├── utils.py          # 검색, 필터링, 보고서 생성 유틸리티
 ├── templates/        # PDF 양식, 리포트 템플릿
 ├── worklog.db        # SQLite DB 파일
 └── requirements.txt  # 필수 패키지 목록
```

## 설치 방법

### 1. 필수 요구사항

- Python 3.8 이상
- Windows 운영체제

### 2. 가상환경 설정

```
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows)
.\.venv\Scripts\activate
```

### 3. 의존성 패키지 설치

```
# 필요한 패키지 설치
pip install -r requirements.txt
```

## 실행 방법

```
# 애플리케이션 실행
streamlit run app.py
```

실행 후 웹 브라우저에서 자동으로 애플리케이션이 열립니다. (기본 주소: http://localhost:8501)

## 데이터베이스 구조

- **id** (INTEGER, PK): 레코드 고유 식별자
- **name** (TEXT): 작성자 이름
- **date** (TEXT): 작성일 (YYYY-MM-DD)
- **category** (TEXT): 카테고리 (A/B/C)
- **content** (TEXT): 업무 내용
- **start_date** (TEXT): 사건 시작일 (YYYY-MM-DD)
- **end_date** (TEXT): 사건 종료일 (YYYY-MM-DD)
- **status** (TEXT): 상태 (진행 중/완료/미완료)

## 주의사항

- 데이터 손실 방지를 위해 정기적으로 백업 기능을 사용하세요.
- SQLite 데이터베이스는 동시 접근에 제한이 있으므로, 여러 사용자가 동시에 접근할 경우 데이터 충돌이 발생할 수 있습니다. 