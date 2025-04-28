import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import plotly.figure_factory as ff
from fpdf import FPDF
import xlsxwriter
import io

def create_excel_report(df, filename=None):
    """검색 결과를 Excel 파일로 출력"""
    if filename is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"worklog_report_{now}.xlsx"
    
    # 메모리에 Excel 파일 생성
    output = io.BytesIO()
    
    # ExcelWriter 생성
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 데이터프레임을 Excel에 쓰기
        df.to_excel(writer, sheet_name='업무 기록', index=False)
        
        # 워크시트 및 워크북 가져오기
        workbook = writer.book
        worksheet = writer.sheets['업무 기록']
        
        # 열 너비 설정
        worksheet.set_column('A:A', 8)  # id
        worksheet.set_column('B:B', 15)  # name
        worksheet.set_column('C:C', 12)  # date
        worksheet.set_column('D:D', 10)  # category
        worksheet.set_column('E:E', 50)  # content
        worksheet.set_column('F:F', 12)  # start_date
        worksheet.set_column('G:G', 12)  # end_date
        worksheet.set_column('H:H', 12)  # status
        
        # 헤더 형식 설정
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # 헤더에 형식 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    
    # 파일 내용 가져오기
    output.seek(0)
    
    return output.getvalue()

def create_pdf_report(df, filename=None):
    """검색 결과를 PDF 파일로 출력"""
    if filename is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"worklog_report_{now}.pdf"
    
    # PDF 생성
    pdf = FPDF()
    pdf.add_page()
    
    # 한글 폰트 설정 - 폰트 파일이 있다고 가정
    # pdf.add_font('NanumGothic', '', 'NanumGothic.ttf', uni=True)
    # pdf.set_font('NanumGothic', '', 12)
    
    # 기본 내장 폰트 사용 (한글 지원이 필요하면 위 주석 해제 및 폰트 파일 추가 필요)
    pdf.set_font('Arial', 'B', 16)
    
    # 타이틀
    pdf.cell(0, 10, '업무 기록 보고서', 0, 1, 'C')
    pdf.cell(0, 10, f'생성일: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
    pdf.ln(10)
    
    # 테이블 헤더
    pdf.set_font('Arial', 'B', 12)
    headers = ['ID', '이름', '날짜', '카테고리', '내용', '시작일', '종료일', '상태']
    
    # 컬럼 너비 설정
    col_widths = [12, 25, 25, 20, 80, 25, 25, 25]
    
    # 페이지 너비에 맞게 조정
    page_width = pdf.w - 2 * pdf.l_margin
    total_width = sum(col_widths)
    scale = page_width / total_width
    col_widths = [w * scale for w in col_widths]
    
    # 헤더 그리기
    for i in range(len(headers)):
        pdf.cell(col_widths[i], 10, headers[i], 1, 0, 'C')
    pdf.ln()
    
    # 데이터 쓰기
    pdf.set_font('Arial', '', 10)
    for index, row in df.iterrows():
        # 내용 제한 (너무 길면 잘라내기)
        content = str(row['content'])
        if len(content) > 50:
            content = content[:47] + '...'
        
        pdf.cell(col_widths[0], 10, str(row['id']), 1)
        pdf.cell(col_widths[1], 10, str(row['name']), 1)
        pdf.cell(col_widths[2], 10, str(row['date']), 1)
        pdf.cell(col_widths[3], 10, str(row['category']), 1)
        pdf.cell(col_widths[4], 10, content, 1)
        pdf.cell(col_widths[5], 10, str(row['start_date']), 1)
        pdf.cell(col_widths[6], 10, str(row['end_date']), 1)
        pdf.cell(col_widths[7], 10, str(row['status']), 1)
        pdf.ln()
    
    # 메모리에 PDF 저장
    return pdf.output(dest='S').encode('latin1')

def create_gantt_chart(df):
    """업무 기록으로 간트 차트 생성"""
    # 빈 데이터프레임 처리
    if df.empty:
        return None
    
    # 데이터 준비
    gantt_data = []
    
    for _, row in df.iterrows():
        # 시작일과 종료일이 있는 항목만 처리
        if pd.notna(row['start_date']) and pd.notna(row['end_date']):
            # 상태에 따른 색상 설정
            if row['status'] == '완료':
                color = 'green'
            elif row['status'] == '진행 중':
                color = 'blue'
            else:  # 미완료
                color = 'red'
            
            # 간트 차트 데이터 추가
            gantt_data.append(dict(
                Task=f"{row['id']} - {row['name']}",
                Start=row['start_date'],
                Finish=row['end_date'],
                Resource=row['category'],
                Description=row['content'][:30] + ('...' if len(row['content']) > 30 else ''),
                Status=row['status'],
                Color=color
            ))
    
    if not gantt_data:
        return None
    
    # 간트 차트 생성
    fig = ff.create_gantt(
        gantt_data,
        colors={task['Resource']: task['Color'] for task in gantt_data},
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True,
        title='업무 일정 간트 차트'
    )
    
    # 레이아웃 설정
    fig.update_layout(
        autosize=True,
        height=600,
        margin=dict(l=50, r=50, b=100, t=100, pad=4)
    )
    
    return fig

def create_category_chart(df):
    """카테고리별 통계 차트 생성"""
    if df.empty:
        return None
    
    # 카테고리별 카운트
    category_counts = df['category'].value_counts().reset_index()
    category_counts.columns = ['카테고리', '건수']
    
    # 차트 생성
    fig = px.pie(
        category_counts, 
        values='건수', 
        names='카테고리',
        title='카테고리별 업무 비율'
    )
    
    return fig

def create_status_chart(df):
    """상태별 통계 차트 생성"""
    if df.empty:
        return None
    
    # 상태별 카운트
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['상태', '건수']
    
    # 차트 생성
    fig = px.bar(
        status_counts, 
        x='상태', 
        y='건수',
        title='상태별 업무 건수',
        color='상태',
        color_discrete_map={
            '완료': 'green',
            '진행 중': 'blue',
            '미완료': 'red'
        }
    )
    
    return fig

def create_monthly_chart(df):
    """월별 업무 건수 차트 생성"""
    if df.empty:
        return None
    
    # 날짜 형식 변환
    df['date'] = pd.to_datetime(df['date'])
    
    # 월별 집계
    monthly_counts = df.groupby(df['date'].dt.strftime('%Y-%m')).size().reset_index()
    monthly_counts.columns = ['월', '건수']
    
    # 시간순 정렬
    monthly_counts = monthly_counts.sort_values('월')
    
    # 차트 생성
    fig = px.line(
        monthly_counts, 
        x='월', 
        y='건수',
        title='월별 업무 건수 추이',
        markers=True
    )
    
    return fig

def get_date_ymd(date_text):
    """날짜 문자열을 년-월-일 형식으로 반환"""
    try:
        date_obj = datetime.strptime(date_text, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None 