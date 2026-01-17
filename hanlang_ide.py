# -*- coding: utf-8 -*-
"""
한랭(HanLang) IDE - VSCode 스타일 GUI 컴파일러
한준후랭귀지를 위한 통합 개발 환경
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import threading
import queue
import re
import os
from typing import Optional, Dict, List

from hanlang_interpreter import HanlangInterpreter, 런타임에러
from hanlang_lexer import HanlangLexer, TokenType


class 구문강조:
    """구문 강조 처리"""

    # 색상 테마 (VSCode Dark+ 스타일)
    COLORS = {
        '키워드': '#569CD6',      # 파란색
        '함수': '#DCDCAA',        # 노란색
        '문자열': '#CE9178',      # 주황색
        '숫자': '#B5CEA8',        # 연두색
        '주석': '#6A9955',        # 초록색
        '연산자': '#D4D4D4',      # 흰색
        '괄호': '#FFD700',        # 금색
        '내장함수': '#4EC9B0',    # 청록색
        '불리언': '#569CD6',      # 파란색
        '클래스': '#4EC9B0',      # 청록색
    }

    키워드 = ['변수', '상수', '함수', '반환', '만약', '아니면', '아니면만약',
              '반복', '동안', '중단', '계속', '클래스', '참', '거짓', '없음',
              '그리고', '또는', '아님', '출력', '입력',
              '시도', '잡기', '마침내', '던지기']

    내장함수 = ['길이', '정수변환', '실수변환', '문자열변환', '타입', '범위',
               '절대값', '최대값', '최소값', '합계', '정렬', '뒤집기', '추가',
               '제거', '포함',
               # 수학 함수
               '제곱근', '거듭제곱', '올림', '내림', '반올림',
               '사인', '코사인', '탄젠트', '아크사인', '아크코사인', '아크탄젠트',
               '로그', '로그10', '파이', '자연상수', '무한대', '랜덤', '랜덤정수',
               # 문자열 함수
               '대문자', '소문자', '분리', '결합', '교체', '공백제거',
               '왼쪽공백제거', '오른쪽공백제거', '찾기', '시작확인', '끝확인',
               '자르기', '반복문자', '채우기', '왼쪽채우기', '오른쪽채우기',
               # 딕셔너리 함수
               '키값들', '값들', '항목들', '딕셔너리',
               # 리스트 함수
               '삽입', '빼기', '인덱스', '개수', '복사', '비우기']


class 줄번호위젯(tk.Canvas):
    """줄 번호 표시 위젯"""

    def __init__(self, parent, text_widget, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_widget = text_widget
        self.font = font.Font(family='D2Coding', size=12)

    def 다시그리기(self):
        self.delete("all")

        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break

            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(35, y, anchor="ne", text=linenum,
                           fill="#858585", font=self.font)

            i = self.text_widget.index(f"{i}+1line")


class 코드편집기(tk.Frame):
    """코드 편집기 위젯"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.configure(bg='#1E1E1E')

        # 접기 마진 캔버스
        self.접기마진 = tk.Canvas(self, width=15, bg='#1E1E1E', highlightthickness=0)
        self.접기마진.pack(side=tk.LEFT, fill=tk.Y)

        # 줄 번호 캔버스
        self.줄번호 = 줄번호위젯(self, None, width=45, bg='#1E1E1E',
                              highlightthickness=0)
        self.줄번호.pack(side=tk.LEFT, fill=tk.Y)

        # 접힌 영역 관리
        self.접힌영역들 = {}  # {시작줄: 끝줄}

        # 스크롤바
        self.스크롤바 = ttk.Scrollbar(self)
        self.스크롤바.pack(side=tk.RIGHT, fill=tk.Y)

        # 텍스트 위젯
        self.텍스트 = tk.Text(
            self,
            wrap=tk.NONE,
            bg='#1E1E1E',
            fg='#D4D4D4',
            insertbackground='#AEAFAD',
            selectbackground='#264F78',
            selectforeground='#D4D4D4',
            font=('D2Coding', 12),
            undo=True,
            padx=5,
            pady=5,
            spacing1=2,
            spacing2=2,
            spacing3=2,
            tabs=('4c',)
        )
        self.텍스트.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 가로 스크롤바
        self.가로스크롤바 = ttk.Scrollbar(self, orient=tk.HORIZONTAL,
                                       command=self.텍스트.xview)
        self.가로스크롤바.pack(side=tk.BOTTOM, fill=tk.X)

        self.텍스트.configure(yscrollcommand=self._on_scroll,
                            xscrollcommand=self.가로스크롤바.set)
        self.스크롤바.configure(command=self._on_scrollbar)

        self.줄번호.text_widget = self.텍스트

        # 구문 강조 태그 설정
        self._setup_tags()

        # 이벤트 바인딩
        self.텍스트.bind('<KeyRelease>', self._on_key_release)
        self.텍스트.bind('<Configure>', self._on_configure)
        self.텍스트.bind('<Tab>', self._on_tab)
        self.텍스트.bind('<Return>', self._on_return)
        self.텍스트.bind('<<Modified>>', self._on_modified)
        self.텍스트.bind('<Control-space>', self._자동완성트리거)

        # 접기 마진 이벤트
        self.접기마진.bind('<Button-1>', self._접기마진클릭)

        self.after_id = None
        self.자동완성팝업 = None
        self.parent_window = None

        # 접기 태그 설정
        self.텍스트.tag_configure('접힘', elide=True)

    def _setup_tags(self):
        """구문 강조 태그 설정"""
        for name, color in 구문강조.COLORS.items():
            self.텍스트.tag_configure(name, foreground=color)

        # 현재 줄 강조
        self.텍스트.tag_configure('현재줄', background='#2D2D2D')

    def _on_scroll(self, *args):
        self.스크롤바.set(*args)
        self.줄번호.다시그리기()
        self._접기마진그리기()

    def _on_scrollbar(self, *args):
        self.텍스트.yview(*args)
        self.줄번호.다시그리기()
        self._접기마진그리기()

    def _on_key_release(self, event=None):
        # 디바운싱: 타이핑 중에는 구문 강조를 지연
        if self.after_id:
            self.after_cancel(self.after_id)
        self.after_id = self.after(100, self._구문강조적용)
        self.줄번호.다시그리기()
        self._접기마진그리기()
        self._현재줄강조()

    def _on_configure(self, event=None):
        self.줄번호.다시그리기()
        self._접기마진그리기()

    def _on_tab(self, event):
        self.텍스트.insert(tk.INSERT, "    ")
        return "break"

    def _on_return(self, event):
        # 자동 들여쓰기
        current_line = self.텍스트.get("insert linestart", "insert")
        indent = ""
        for char in current_line:
            if char in ' \t':
                indent += char
            else:
                break

        # { 뒤에서 엔터치면 추가 들여쓰기
        if current_line.rstrip().endswith('{'):
            indent += "    "

        self.텍스트.insert(tk.INSERT, "\n" + indent)
        self.줄번호.다시그리기()
        return "break"

    def _on_modified(self, event=None):
        if self.텍스트.edit_modified():
            self.event_generate('<<TextModified>>')
            self.텍스트.edit_modified(False)

    def _현재줄강조(self):
        self.텍스트.tag_remove('현재줄', '1.0', 'end')
        self.텍스트.tag_add('현재줄', 'insert linestart', 'insert lineend+1c')

    def _구문강조적용(self):
        """구문 강조 적용"""
        # 모든 태그 제거
        for tag in 구문강조.COLORS.keys():
            self.텍스트.tag_remove(tag, '1.0', 'end')

        content = self.텍스트.get('1.0', 'end-1c')

        # 주석 강조
        for match in re.finditer(r'#[^\n]*', content):
            self._apply_tag(match.start(), match.end(), '주석')

        # 여러 줄 주석
        for match in re.finditer(r'/\*[\s\S]*?\*/', content):
            self._apply_tag(match.start(), match.end(), '주석')

        # 문자열 강조
        for match in re.finditer(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', content):
            self._apply_tag(match.start(), match.end(), '문자열')

        # 숫자 강조
        for match in re.finditer(r'\b\d+\.?\d*\b', content):
            self._apply_tag(match.start(), match.end(), '숫자')

        # 키워드 강조
        for keyword in 구문강조.키워드:
            pattern = rf'\b{keyword}\b'
            for match in re.finditer(pattern, content):
                self._apply_tag(match.start(), match.end(), '키워드')

        # 내장 함수 강조
        for func in 구문강조.내장함수:
            pattern = rf'\b{func}\b'
            for match in re.finditer(pattern, content):
                self._apply_tag(match.start(), match.end(), '내장함수')

        # 함수 정의 강조
        for match in re.finditer(r'함수\s+(\w+)', content):
            self._apply_tag(match.start(1), match.end(1), '함수')

        # 클래스 정의 강조
        for match in re.finditer(r'클래스\s+(\w+)', content):
            self._apply_tag(match.start(1), match.end(1), '클래스')

        # 괄호 강조
        for match in re.finditer(r'[{}()\[\]]', content):
            self._apply_tag(match.start(), match.end(), '괄호')

    def _apply_tag(self, start: int, end: int, tag: str):
        """태그 적용"""
        start_index = f'1.0+{start}c'
        end_index = f'1.0+{end}c'
        self.텍스트.tag_add(tag, start_index, end_index)

    def 코드가져오기(self) -> str:
        return self.텍스트.get('1.0', 'end-1c')

    def 코드설정하기(self, code: str):
        self.텍스트.delete('1.0', 'end')
        self.텍스트.insert('1.0', code)
        self._구문강조적용()
        self.줄번호.다시그리기()

    def _자동완성트리거(self, event=None):
        """자동완성 트리거 (Ctrl+Space)"""
        # 현재 입력 중인 단어 가져오기
        현재단어 = self._현재단어가져오기()

        # 후보 생성
        후보들 = self._자동완성후보(현재단어)

        if not 후보들:
            return 'break'

        # 커서 위치 계산
        bbox = self.텍스트.bbox(tk.INSERT)
        if bbox:
            x = self.winfo_rootx() + bbox[0]
            y = self.winfo_rooty() + bbox[1] + bbox[3] + 5
        else:
            x = self.winfo_rootx() + 100
            y = self.winfo_rooty() + 100

        # 기존 팝업 닫기
        if self.자동완성팝업:
            try:
                self.자동완성팝업.destroy()
            except:
                pass

        # 새 팝업 생성
        if self.parent_window is None:
            self.parent_window = self.winfo_toplevel()

        self.자동완성팝업 = 자동완성팝업(self.parent_window, self, 후보들, (x, y))

        return 'break'

    def _현재단어가져오기(self) -> str:
        """현재 커서 위치의 단어 가져오기"""
        커서위치 = self.텍스트.index(tk.INSERT)
        줄내용 = self.텍스트.get(f"{커서위치} linestart", 커서위치)

        # 마지막 단어 추출
        단어 = ""
        for i in range(len(줄내용) - 1, -1, -1):
            char = 줄내용[i]
            if char.isalnum() or char == '_' or ord(char) > 127:
                단어 = char + 단어
            else:
                break

        return 단어

    def _자동완성후보(self, 접두사: str) -> List[str]:
        """자동완성 후보 생성"""
        후보들 = []

        # 키워드
        for 키워드 in 구문강조.키워드:
            if 키워드.startswith(접두사):
                후보들.append(키워드)

        # 내장 함수
        for 함수 in 구문강조.내장함수:
            if 함수.startswith(접두사):
                후보들.append(함수)

        # 사용자 정의 변수/함수 추출
        코드 = self.텍스트.get('1.0', 'end-1c')

        # 변수 선언 (변수 이름 = ...)
        for match in re.finditer(r'변수\s+([가-힣a-zA-Z_][가-힣a-zA-Z0-9_]*)', 코드):
            이름 = match.group(1)
            if 이름.startswith(접두사) and 이름 not in 후보들:
                후보들.append(이름)

        # 상수 선언
        for match in re.finditer(r'상수\s+([가-힣a-zA-Z_][가-힣a-zA-Z0-9_]*)', 코드):
            이름 = match.group(1)
            if 이름.startswith(접두사) and 이름 not in 후보들:
                후보들.append(이름)

        # 함수 정의
        for match in re.finditer(r'함수\s+([가-힣a-zA-Z_][가-힣a-zA-Z0-9_]*)', 코드):
            이름 = match.group(1)
            if 이름.startswith(접두사) and 이름 not in 후보들:
                후보들.append(이름)

        # 클래스 정의
        for match in re.finditer(r'클래스\s+([가-힣a-zA-Z_][가-힣a-zA-Z0-9_]*)', 코드):
            이름 = match.group(1)
            if 이름.startswith(접두사) and 이름 not in 후보들:
                후보들.append(이름)

        # 정렬
        후보들.sort()

        return 후보들

    def _접기마진그리기(self):
        """접기 마진에 접기 아이콘 그리기"""
        self.접기마진.delete("all")

        # 접기 가능한 줄 찾기 (중괄호로 시작하는 블록)
        content = self.텍스트.get('1.0', 'end-1c')
        lines = content.split('\n')

        i = self.텍스트.index("@0,0")
        while True:
            dline = self.텍스트.dlineinfo(i)
            if dline is None:
                break

            y = dline[1]
            줄번호 = int(str(i).split(".")[0])

            if 줄번호 <= len(lines):
                줄내용 = lines[줄번호 - 1]

                # 접힌 상태 확인
                if 줄번호 in self.접힌영역들:
                    # 접혀 있으면 ▶ 표시 (펼치기 가능)
                    self.접기마진.create_text(
                        8, y + 8, text="▶", fill="#858585",
                        font=('Arial', 8), tags=f"fold_{줄번호}"
                    )
                elif '{' in 줄내용:
                    # 접기 가능한 줄이면 ▼ 표시
                    self.접기마진.create_text(
                        8, y + 8, text="▼", fill="#858585",
                        font=('Arial', 8), tags=f"fold_{줄번호}"
                    )

            i = self.텍스트.index(f"{i}+1line")

    def _접기마진클릭(self, event):
        """접기 마진 클릭 처리"""
        # 클릭한 위치의 줄 찾기
        y = event.y
        i = self.텍스트.index("@0,0")

        while True:
            dline = self.텍스트.dlineinfo(i)
            if dline is None:
                break

            줄y = dline[1]
            줄높이 = dline[3]
            줄번호 = int(str(i).split(".")[0])

            if 줄y <= y < 줄y + 줄높이:
                self._접기토글(줄번호)
                break

            i = self.텍스트.index(f"{i}+1line")

    def _블록끝찾기(self, 시작줄: int) -> int:
        """블록의 끝 줄 찾기 (중괄호 매칭)"""
        content = self.텍스트.get(f'{시작줄}.0', 'end-1c')
        lines = content.split('\n')

        중괄호깊이 = 0
        시작됨 = False

        for i, line in enumerate(lines):
            for char in line:
                if char == '{':
                    중괄호깊이 += 1
                    시작됨 = True
                elif char == '}':
                    중괄호깊이 -= 1
                    if 시작됨 and 중괄호깊이 == 0:
                        return 시작줄 + i

        return 시작줄

    def _접기토글(self, 줄번호: int):
        """줄 접기/펼치기 토글"""
        content = self.텍스트.get(f'{줄번호}.0', f'{줄번호}.end')

        if '{' not in content:
            return

        if 줄번호 in self.접힌영역들:
            # 펼치기
            끝줄 = self.접힌영역들[줄번호]
            태그이름 = f"접힘_{줄번호}"
            self.텍스트.tag_remove(태그이름, '1.0', 'end')
            del self.접힌영역들[줄번호]
        else:
            # 접기
            끝줄 = self._블록끝찾기(줄번호)
            if 끝줄 > 줄번호:
                self.접힌영역들[줄번호] = 끝줄
                태그이름 = f"접힘_{줄번호}"

                # 태그 설정 (숨김 처리)
                self.텍스트.tag_configure(태그이름, elide=True)

                # 첫 줄 끝부터 마지막 줄까지 숨기기
                시작인덱스 = f"{줄번호}.end"
                끝인덱스 = f"{끝줄}.end"
                self.텍스트.tag_add(태그이름, 시작인덱스, 끝인덱스)

        self._접기마진그리기()
        self.줄번호.다시그리기()


class 터미널위젯(tk.Frame):
    """터미널/출력 위젯"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.configure(bg='#1E1E1E')
        self.입력대기중 = False
        self.입력콜백 = None

        # 탭 프레임
        self.탭프레임 = tk.Frame(self, bg='#252526', height=30)
        self.탭프레임.pack(fill=tk.X)

        self.출력탭 = tk.Label(self.탭프레임, text="출력", bg='#1E1E1E',
                             fg='#CCCCCC', padx=15, pady=5, cursor='hand2')
        self.출력탭.pack(side=tk.LEFT)

        # 출력 영역
        self.출력 = tk.Text(
            self,
            wrap=tk.WORD,
            bg='#1E1E1E',
            fg='#CCCCCC',
            font=('D2Coding', 11),
            state=tk.DISABLED,
            padx=10,
            pady=10
        )
        self.출력.pack(fill=tk.BOTH, expand=True)

        # 입력 프레임
        self.입력프레임 = tk.Frame(self, bg='#1E1E1E')
        self.입력프레임.pack(fill=tk.X, pady=(5, 10), padx=10)

        self.입력프롬프트 = tk.Label(self.입력프레임, text="", bg='#1E1E1E',
                                  fg='#569CD6', font=('D2Coding', 11))
        self.입력프롬프트.pack(side=tk.LEFT)

        self.입력필드 = tk.Entry(
            self.입력프레임,
            bg='#3C3C3C',
            fg='#CCCCCC',
            insertbackground='white',
            font=('D2Coding', 11),
            state=tk.DISABLED
        )
        self.입력필드.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.입력필드.bind('<Return>', self._입력확인)

        self.입력버튼 = tk.Button(
            self.입력프레임,
            text="입력",
            command=self._입력확인,
            bg='#0E639C',
            fg='white',
            relief='flat',
            state=tk.DISABLED,
            cursor='hand2'
        )
        self.입력버튼.pack(side=tk.RIGHT)

        # 태그 설정
        self.출력.tag_configure('오류', foreground='#F44747')
        self.출력.tag_configure('성공', foreground='#4EC9B0')
        self.출력.tag_configure('정보', foreground='#569CD6')
        self.출력.tag_configure('경고', foreground='#DCDCAA')
        self.출력.tag_configure('입력값', foreground='#CE9178')

    def 입력요청(self, 프롬프트: str, 콜백):
        """입력 요청"""
        self.입력대기중 = True
        self.입력콜백 = 콜백
        self.입력프롬프트.config(text=프롬프트 if 프롬프트 else "입력: ")
        self.입력필드.config(state=tk.NORMAL)
        self.입력버튼.config(state=tk.NORMAL)
        self.입력필드.focus_set()

    def _입력확인(self, event=None):
        if not self.입력대기중:
            return

        값 = self.입력필드.get()
        self.입력필드.delete(0, tk.END)
        self.입력필드.config(state=tk.DISABLED)
        self.입력버튼.config(state=tk.DISABLED)
        self.입력프롬프트.config(text="")

        # 입력값 출력
        self.쓰기(f">> {값}", '입력값')

        self.입력대기중 = False
        if self.입력콜백:
            self.입력콜백(값)
            self.입력콜백 = None

    def 지우기(self):
        self.출력.configure(state=tk.NORMAL)
        self.출력.delete('1.0', 'end')
        self.출력.configure(state=tk.DISABLED)

    def 쓰기(self, text: str, tag: str = None):
        self.출력.configure(state=tk.NORMAL)
        if tag:
            self.출력.insert('end', text + '\n', tag)
        else:
            self.출력.insert('end', text + '\n')
        self.출력.see('end')
        self.출력.configure(state=tk.DISABLED)


class 찾기바꾸기대화상자(tk.Toplevel):
    """찾기/바꾸기 다이얼로그"""

    def __init__(self, parent, 편집기, 바꾸기모드=False):
        super().__init__(parent)
        self.편집기 = 편집기
        self.바꾸기모드 = 바꾸기모드

        self.title("찾기" if not 바꾸기모드 else "찾기 및 바꾸기")
        self.geometry("450x180" if not 바꾸기모드 else "450x220")
        self.configure(bg='#252526')
        self.resizable(False, False)
        self.transient(parent)

        # 찾기 프레임
        찾기프레임 = tk.Frame(self, bg='#252526')
        찾기프레임.pack(fill=tk.X, padx=15, pady=(15, 5))

        tk.Label(찾기프레임, text="찾기:", bg='#252526', fg='#CCCCCC',
                font=('Segoe UI', 10), width=8, anchor='e').pack(side=tk.LEFT)
        self.찾기입력 = tk.Entry(찾기프레임, bg='#3C3C3C', fg='#CCCCCC',
                               insertbackground='white', font=('D2Coding', 11))
        self.찾기입력.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # 바꾸기 프레임
        if 바꾸기모드:
            바꾸기프레임 = tk.Frame(self, bg='#252526')
            바꾸기프레임.pack(fill=tk.X, padx=15, pady=5)

            tk.Label(바꾸기프레임, text="바꾸기:", bg='#252526', fg='#CCCCCC',
                    font=('Segoe UI', 10), width=8, anchor='e').pack(side=tk.LEFT)
            self.바꾸기입력 = tk.Entry(바꾸기프레임, bg='#3C3C3C', fg='#CCCCCC',
                                   insertbackground='white', font=('D2Coding', 11))
            self.바꾸기입력.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # 옵션 프레임
        옵션프레임 = tk.Frame(self, bg='#252526')
        옵션프레임.pack(fill=tk.X, padx=15, pady=5)

        self.대소문자구분 = tk.BooleanVar()
        tk.Checkbutton(옵션프레임, text="대소문자 구분", variable=self.대소문자구분,
                      bg='#252526', fg='#CCCCCC', selectcolor='#3C3C3C',
                      activebackground='#252526', activeforeground='#CCCCCC').pack(side=tk.LEFT)

        # 버튼 프레임
        버튼프레임 = tk.Frame(self, bg='#252526')
        버튼프레임.pack(fill=tk.X, padx=15, pady=10)

        btn_style = {'bg': '#0E639C', 'fg': 'white', 'relief': 'flat',
                    'padx': 12, 'pady': 5, 'cursor': 'hand2',
                    'activebackground': '#1177BB', 'activeforeground': 'white'}

        tk.Button(버튼프레임, text="다음 찾기", command=self._다음찾기, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(버튼프레임, text="이전 찾기", command=self._이전찾기, **btn_style).pack(side=tk.LEFT, padx=2)

        if 바꾸기모드:
            tk.Button(버튼프레임, text="바꾸기", command=self._바꾸기, **btn_style).pack(side=tk.LEFT, padx=2)
            tk.Button(버튼프레임, text="모두 바꾸기", command=self._모두바꾸기, **btn_style).pack(side=tk.LEFT, padx=2)

        # 결과 레이블
        self.결과레이블 = tk.Label(self, text="", bg='#252526', fg='#CCCCCC',
                                font=('Segoe UI', 9))
        self.결과레이블.pack(pady=5)

        # 키 바인딩
        self.bind('<Return>', lambda e: self._다음찾기())
        self.bind('<Escape>', lambda e: self.destroy())

        self.찾기입력.focus_set()

        # 강조 태그 설정
        self.편집기.텍스트.tag_configure('검색결과', background='#515C6A')
        self.현재위치 = None

    def _다음찾기(self):
        self._강조제거()
        검색어 = self.찾기입력.get()
        if not 검색어:
            return

        시작위치 = self.현재위치 if self.현재위치 else '1.0'
        if self.현재위치:
            시작위치 = f"{self.현재위치}+1c"

        위치 = self.편집기.텍스트.search(
            검색어, 시작위치, tk.END,
            nocase=not self.대소문자구분.get()
        )

        if 위치:
            끝위치 = f"{위치}+{len(검색어)}c"
            self.편집기.텍스트.tag_add('검색결과', 위치, 끝위치)
            self.편집기.텍스트.mark_set(tk.INSERT, 위치)
            self.편집기.텍스트.see(위치)
            self.현재위치 = 위치
            self.결과레이블.config(text=f"찾음: {위치}")
        else:
            # 처음부터 다시 검색
            위치 = self.편집기.텍스트.search(
                검색어, '1.0', tk.END,
                nocase=not self.대소문자구분.get()
            )
            if 위치:
                끝위치 = f"{위치}+{len(검색어)}c"
                self.편집기.텍스트.tag_add('검색결과', 위치, 끝위치)
                self.편집기.텍스트.mark_set(tk.INSERT, 위치)
                self.편집기.텍스트.see(위치)
                self.현재위치 = 위치
                self.결과레이블.config(text=f"처음부터 다시: {위치}")
            else:
                self.결과레이블.config(text="찾을 수 없습니다")
                self.현재위치 = None

    def _이전찾기(self):
        self._강조제거()
        검색어 = self.찾기입력.get()
        if not 검색어:
            return

        끝위치 = self.현재위치 if self.현재위치 else tk.END

        위치 = self.편집기.텍스트.search(
            검색어, '1.0', 끝위치,
            nocase=not self.대소문자구분.get(),
            backwards=True
        )

        if 위치:
            끝 = f"{위치}+{len(검색어)}c"
            self.편집기.텍스트.tag_add('검색결과', 위치, 끝)
            self.편집기.텍스트.mark_set(tk.INSERT, 위치)
            self.편집기.텍스트.see(위치)
            self.현재위치 = 위치
            self.결과레이블.config(text=f"찾음: {위치}")
        else:
            self.결과레이블.config(text="찾을 수 없습니다")

    def _바꾸기(self):
        if self.현재위치:
            검색어 = self.찾기입력.get()
            바꿀텍스트 = self.바꾸기입력.get()
            끝위치 = f"{self.현재위치}+{len(검색어)}c"
            self.편집기.텍스트.delete(self.현재위치, 끝위치)
            self.편집기.텍스트.insert(self.현재위치, 바꿀텍스트)
            self._다음찾기()

    def _모두바꾸기(self):
        검색어 = self.찾기입력.get()
        바꿀텍스트 = self.바꾸기입력.get()
        if not 검색어:
            return

        내용 = self.편집기.코드가져오기()
        if self.대소문자구분.get():
            횟수 = 내용.count(검색어)
            새내용 = 내용.replace(검색어, 바꿀텍스트)
        else:
            횟수 = len(re.findall(re.escape(검색어), 내용, re.IGNORECASE))
            새내용 = re.sub(re.escape(검색어), 바꿀텍스트, 내용, flags=re.IGNORECASE)

        self.편집기.코드설정하기(새내용)
        self.결과레이블.config(text=f"{횟수}개 바꿈")

    def _강조제거(self):
        self.편집기.텍스트.tag_remove('검색결과', '1.0', tk.END)


class 자동완성팝업(tk.Toplevel):
    """자동완성 팝업 윈도우"""

    def __init__(self, parent, 편집기, 후보들, 위치):
        super().__init__(parent)
        self.편집기 = 편집기
        self.후보들 = 후보들

        # 윈도우 설정
        self.withdraw()  # 일단 숨기기
        self.overrideredirect(True)  # 테두리 없음
        self.configure(bg='#252526')

        # 리스트박스
        self.리스트 = tk.Listbox(
            self,
            bg='#252526',
            fg='#CCCCCC',
            selectbackground='#094771',
            selectforeground='white',
            font=('D2Coding', 11),
            borderwidth=1,
            relief='solid',
            highlightthickness=0,
            exportselection=False
        )
        self.리스트.pack(fill=tk.BOTH, expand=True)

        # 후보 추가
        for 후보 in 후보들:
            self.리스트.insert(tk.END, 후보)

        if 후보들:
            self.리스트.selection_set(0)

        # 크기 계산
        높이 = min(len(후보들), 10) * 20 + 4
        너비 = max(len(h) for h in 후보들) * 10 + 20 if 후보들 else 100
        너비 = max(너비, 150)

        self.geometry(f"{너비}x{높이}+{위치[0]}+{위치[1]}")

        # 키 바인딩
        self.리스트.bind('<Return>', self._선택)
        self.리스트.bind('<Tab>', self._선택)
        self.리스트.bind('<Escape>', lambda e: self.destroy())
        self.리스트.bind('<Double-1>', self._선택)
        self.리스트.bind('<Up>', self._위로)
        self.리스트.bind('<Down>', self._아래로)

        # 포커스 이동 시 닫기
        self.리스트.bind('<FocusOut>', lambda e: self.after(100, self._포커스확인))

        self.deiconify()  # 보이기
        self.리스트.focus_set()

    def _포커스확인(self):
        try:
            if self.winfo_exists() and self.focus_get() != self.리스트:
                self.destroy()
        except:
            pass

    def _위로(self, event):
        현재 = self.리스트.curselection()
        if 현재 and 현재[0] > 0:
            self.리스트.selection_clear(0, tk.END)
            self.리스트.selection_set(현재[0] - 1)
            self.리스트.see(현재[0] - 1)
        return 'break'

    def _아래로(self, event):
        현재 = self.리스트.curselection()
        if 현재 and 현재[0] < self.리스트.size() - 1:
            self.리스트.selection_clear(0, tk.END)
            self.리스트.selection_set(현재[0] + 1)
            self.리스트.see(현재[0] + 1)
        return 'break'

    def _선택(self, event=None):
        선택항목 = self.리스트.curselection()
        if 선택항목:
            선택값 = self.리스트.get(선택항목[0])
            self._삽입(선택값)
        self.destroy()
        return 'break'

    def _삽입(self, 텍스트):
        # 현재 입력 중인 단어 찾기
        커서위치 = self.편집기.텍스트.index(tk.INSERT)
        줄내용 = self.편집기.텍스트.get(f"{커서위치} linestart", 커서위치)

        # 마지막 단어 시작 위치 찾기
        단어시작 = len(줄내용)
        for i in range(len(줄내용) - 1, -1, -1):
            char = 줄내용[i]
            if not (char.isalnum() or char == '_' or ord(char) > 127):
                단어시작 = i + 1
                break
            if i == 0:
                단어시작 = 0

        # 기존 부분 삭제 후 새 텍스트 삽입
        삭제시작 = f"{커서위치} linestart+{단어시작}c"
        self.편집기.텍스트.delete(삭제시작, 커서위치)
        self.편집기.텍스트.insert(삭제시작, 텍스트)
        self.편집기.텍스트.focus_set()


class 파일탐색기(tk.Frame):
    """파일 탐색기 패널"""

    def __init__(self, parent, on_file_select, **kwargs):
        super().__init__(parent, **kwargs)

        self.on_file_select = on_file_select
        self.configure(bg='#252526')

        # 제목
        self.제목 = tk.Label(self, text="탐색기", bg='#252526', fg='#BBBBBB',
                           font=('Segoe UI', 11), anchor='w', padx=10)
        self.제목.pack(fill=tk.X, pady=(10, 5))

        # 트리뷰
        style = ttk.Style()
        style.configure("Treeview",
                       background="#252526",
                       foreground="#CCCCCC",
                       fieldbackground="#252526",
                       borderwidth=0)
        style.configure("Treeview.Heading",
                       background="#252526",
                       foreground="#CCCCCC")
        style.map("Treeview", background=[('selected', '#094771')])

        self.트리 = ttk.Treeview(self, show='tree', selectmode='browse')
        self.트리.pack(fill=tk.BOTH, expand=True, padx=5)

        self.트리.bind('<Double-1>', self._on_double_click)
        self.트리.bind('<<TreeviewOpen>>', self._on_expand)

    def 폴더열기(self, path: str):
        """폴더 열기"""
        # 기존 항목 삭제
        for item in self.트리.get_children():
            self.트리.delete(item)

        self._폴더추가('', path)

    def _폴더추가(self, parent: str, path: str):
        """폴더 내용 추가"""
        try:
            items = sorted(os.listdir(path))

            # 폴더 먼저
            folders = [f for f in items if os.path.isdir(os.path.join(path, f)) and not f.startswith('.')]
            files = [f for f in items if os.path.isfile(os.path.join(path, f)) and f.endswith('.hanlang')]

            for folder in folders:
                full_path = os.path.join(path, folder)
                node = self.트리.insert(parent, 'end', text=f"📁 {folder}",
                                       values=(full_path,), open=False)
                # 더미 항목 추가 (확장 가능하게)
                self.트리.insert(node, 'end', text='')

            for file in files:
                full_path = os.path.join(path, file)
                self.트리.insert(parent, 'end', text=f"📄 {file}",
                               values=(full_path,))

        except PermissionError:
            pass

    def _on_expand(self, event):
        """폴더 확장 시"""
        node = self.트리.focus()
        children = self.트리.get_children(node)

        # 더미 항목 제거 후 실제 내용 추가
        if len(children) == 1 and self.트리.item(children[0])['text'] == '':
            self.트리.delete(children[0])
            path = self.트리.item(node)['values'][0]
            self._폴더추가(node, path)

    def _on_double_click(self, event):
        """더블 클릭 시"""
        node = self.트리.focus()
        if not node:
            return

        values = self.트리.item(node)['values']
        if values:
            path = values[0]
            if os.path.isfile(path):
                self.on_file_select(path)


class 상태바(tk.Frame):
    """상태바"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.configure(bg='#007ACC', height=22)
        self.pack_propagate(False)

        self.왼쪽 = tk.Frame(self, bg='#007ACC')
        self.왼쪽.pack(side=tk.LEFT, fill=tk.Y)

        self.오른쪽 = tk.Frame(self, bg='#007ACC')
        self.오른쪽.pack(side=tk.RIGHT, fill=tk.Y)

        # 브랜치/언어 정보
        self.언어 = tk.Label(self.오른쪽, text="한랭", bg='#007ACC',
                           fg='white', padx=10)
        self.언어.pack(side=tk.RIGHT)

        # 줄:열
        self.위치 = tk.Label(self.오른쪽, text="줄 1, 열 1", bg='#007ACC',
                           fg='white', padx=10)
        self.위치.pack(side=tk.RIGHT)

        # 상태 메시지
        self.상태 = tk.Label(self.왼쪽, text="준비됨", bg='#007ACC',
                           fg='white', padx=10)
        self.상태.pack(side=tk.LEFT)

    def 위치업데이트(self, line: int, col: int):
        self.위치.configure(text=f"줄 {line}, 열 {col}")

    def 상태설정(self, text: str):
        self.상태.configure(text=text)


class HanlangIDE(tk.Tk):
    """한랭 IDE 메인 윈도우"""

    def __init__(self):
        super().__init__()

        self.title("한랭 IDE - 한준후랭귀지 통합 개발 환경")
        self.geometry("1400x800")
        self.configure(bg='#1E1E1E')

        # 현재 파일
        self.현재파일: Optional[str] = None
        self.수정됨 = False

        # 인터프리터
        self.출력큐 = queue.Queue()
        self.입력큐 = queue.Queue()

        # UI 구성
        self._create_menu()
        self._create_toolbar()
        self._create_main_area()
        self._create_statusbar()

        # 키보드 단축키
        self.bind('<Control-n>', lambda e: self.새파일())
        self.bind('<Control-o>', lambda e: self.열기())
        self.bind('<Control-s>', lambda e: self.저장())
        self.bind('<Control-Shift-S>', lambda e: self.다른이름으로저장())
        self.bind('<F5>', lambda e: self.실행())
        self.bind('<Control-F5>', lambda e: self.실행())
        self.bind('<Control-f>', lambda e: self._찾기열기())
        self.bind('<Control-h>', lambda e: self._바꾸기열기())

        # 커서 위치 업데이트
        self.편집기.텍스트.bind('<KeyRelease>', self._update_cursor_position)
        self.편집기.텍스트.bind('<ButtonRelease>', self._update_cursor_position)

        # 수정 감지
        self.편집기.bind('<<TextModified>>', self._on_text_modified)

        # 출력 큐 확인
        self.after(100, self._check_output_queue)

        # 예제 코드 로드
        self._load_example()

        # 예제 폴더 자동 열기
        self._open_examples_folder()

    def _create_menu(self):
        """메뉴바 생성"""
        self.menubar = tk.Menu(self, bg='#3C3C3C', fg='#CCCCCC')

        # 파일 메뉴
        self.file_menu = tk.Menu(self.menubar, tearoff=0, bg='#3C3C3C', fg='#CCCCCC')
        self.file_menu.add_command(label="새 파일          Ctrl+N", command=self.새파일)
        self.file_menu.add_command(label="열기              Ctrl+O", command=self.열기)
        self.file_menu.add_command(label="저장              Ctrl+S", command=self.저장)
        self.file_menu.add_command(label="다른 이름으로 저장  Ctrl+Shift+S", command=self.다른이름으로저장)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="폴더 열기", command=self.폴더열기)
        self.file_menu.add_command(label="예제 폴더 열기", command=self._open_examples_folder)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="종료", command=self.quit)
        self.menubar.add_cascade(label="파일", menu=self.file_menu)

        # 편집 메뉴
        self.edit_menu = tk.Menu(self.menubar, tearoff=0, bg='#3C3C3C', fg='#CCCCCC')
        self.edit_menu.add_command(label="실행 취소    Ctrl+Z",
                                   command=lambda: self.편집기.텍스트.edit_undo())
        self.edit_menu.add_command(label="다시 실행    Ctrl+Y",
                                   command=lambda: self.편집기.텍스트.edit_redo())
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="잘라내기      Ctrl+X",
                                   command=lambda: self.편집기.텍스트.event_generate('<<Cut>>'))
        self.edit_menu.add_command(label="복사          Ctrl+C",
                                   command=lambda: self.편집기.텍스트.event_generate('<<Copy>>'))
        self.edit_menu.add_command(label="붙여넣기      Ctrl+V",
                                   command=lambda: self.편집기.텍스트.event_generate('<<Paste>>'))
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="찾기          Ctrl+F", command=self._찾기열기)
        self.edit_menu.add_command(label="찾기 및 바꾸기  Ctrl+H", command=self._바꾸기열기)
        self.menubar.add_cascade(label="편집", menu=self.edit_menu)

        # 실행 메뉴
        self.run_menu = tk.Menu(self.menubar, tearoff=0, bg='#3C3C3C', fg='#CCCCCC')
        self.run_menu.add_command(label="실행    F5", command=self.실행)
        self.menubar.add_cascade(label="실행", menu=self.run_menu)

        # 도움말 메뉴
        self.help_menu = tk.Menu(self.menubar, tearoff=0, bg='#3C3C3C', fg='#CCCCCC')
        self.help_menu.add_command(label="한랭 문법 도움말", command=self.문법도움말)
        self.help_menu.add_command(label="정보", command=self.정보)
        self.menubar.add_cascade(label="도움말", menu=self.help_menu)

        self.config(menu=self.menubar)

    def _create_toolbar(self):
        """툴바 생성"""
        self.toolbar = tk.Frame(self, bg='#3C3C3C', height=40)
        self.toolbar.pack(fill=tk.X)

        btn_style = {'bg': '#3C3C3C', 'fg': '#CCCCCC', 'relief': 'flat',
                    'padx': 15, 'pady': 5, 'cursor': 'hand2',
                    'activebackground': '#505050', 'activeforeground': 'white'}

        self.btn_new = tk.Button(self.toolbar, text="📄 새 파일", command=self.새파일, **btn_style)
        self.btn_new.pack(side=tk.LEFT, padx=2)

        self.btn_open = tk.Button(self.toolbar, text="📂 열기", command=self.열기, **btn_style)
        self.btn_open.pack(side=tk.LEFT, padx=2)

        self.btn_save = tk.Button(self.toolbar, text="💾 저장", command=self.저장, **btn_style)
        self.btn_save.pack(side=tk.LEFT, padx=2)

        tk.Frame(self.toolbar, bg='#505050', width=1).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        self.btn_run = tk.Button(self.toolbar, text="▶ 실행 (F5)", command=self.실행,
                                bg='#0E639C', fg='white', relief='flat',
                                padx=15, pady=5, cursor='hand2',
                                activebackground='#1177BB', activeforeground='white')
        self.btn_run.pack(side=tk.LEFT, padx=2)

    def _create_main_area(self):
        """메인 영역 생성"""
        # 메인 패널드 윈도우
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg='#1E1E1E',
                                        sashwidth=3, sashrelief=tk.FLAT)
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # 파일 탐색기
        self.파일탐색기 = 파일탐색기(self.main_paned, self._on_file_select)
        self.main_paned.add(self.파일탐색기, minsize=200, width=250)

        # 오른쪽 패널 (편집기 + 터미널)
        self.right_paned = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL,
                                         bg='#1E1E1E', sashwidth=3, sashrelief=tk.FLAT)
        self.main_paned.add(self.right_paned, minsize=400)

        # 코드 편집기
        self.편집기 = 코드편집기(self.right_paned)
        self.right_paned.add(self.편집기, minsize=200, height=500)

        # 터미널
        self.터미널 = 터미널위젯(self.right_paned)
        self.right_paned.add(self.터미널, minsize=100, height=200)

    def _create_statusbar(self):
        """상태바 생성"""
        self.상태바 = 상태바(self)
        self.상태바.pack(fill=tk.X, side=tk.BOTTOM)

    def _on_file_select(self, path: str):
        """파일 선택 시"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.편집기.코드설정하기(content)
            self.현재파일 = path
            self.수정됨 = False
            self._update_title()
            self.상태바.상태설정(f"파일 열림: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("오류", f"파일을 열 수 없습니다: {e}")

    def _on_text_modified(self, event=None):
        if not self.수정됨:
            self.수정됨 = True
            self._update_title()

    def _update_title(self):
        title = "한랭 IDE"
        if self.현재파일:
            title = f"{os.path.basename(self.현재파일)} - {title}"
        if self.수정됨:
            title = f"● {title}"
        self.title(title)

    def _update_cursor_position(self, event=None):
        pos = self.편집기.텍스트.index(tk.INSERT)
        line, col = pos.split('.')
        self.상태바.위치업데이트(int(line), int(col) + 1)

    def _check_output_queue(self):
        """출력 큐 확인"""
        try:
            while True:
                msg, tag = self.출력큐.get_nowait()
                self.터미널.쓰기(msg, tag)
        except queue.Empty:
            pass
        self.after(100, self._check_output_queue)

    def _load_example(self):
        """예제 코드 로드"""
        example = '''개발자한준후가 만든언어입니다.

# 한랭 프로그래밍 언어에 오신 것을 환영합니다!
# 한준후랭귀지 (HanLang) - 한글로 코딩하세요!

# 변수 선언
변수 이름 = "한준후"
변수 나이 = 25

# 출력
출력("=== 한랭 언어 데모 ===")
출력("안녕하세요!", 이름, "님!")

# 함수 정의
함수 인사하기(이름) {
    출력("반갑습니다,", 이름, "님!")
    반환 참
}

# 함수 호출
인사하기(이름)

# 조건문
만약 나이 >= 20 {
    출력("성인입니다")
} 아니면만약 나이 >= 14 {
    출력("청소년입니다")
} 아니면 {
    출력("어린이입니다")
}

# 반복문
출력("\\n1부터 5까지 출력:")
반복 i = 1 : 5 {
    출력(i, "번째")
}

# 리스트와 반복
변수 과일들 = ["사과", "바나나", "오렌지"]
출력("\\n과일 목록:")
반복 i = 0 : 2 {
    출력("-", 과일들[i])
}

# 수학 연산
출력("\\n수학 연산:")
출력("3 + 5 =", 3 + 5)
출력("10 - 3 =", 10 - 3)
출력("4 * 7 =", 4 * 7)
출력("15 / 3 =", 15 / 3)
출력("2 ** 10 =", 2 ** 10)

# 클래스
클래스 사람 {
    함수 생성(이름, 나이) {
        나.이름 = 이름
        나.나이 = 나이
    }

    함수 소개() {
        출력("저는", 나.이름, "이고,", 나.나이, "살입니다.")
    }
}

변수 학생 = 사람("김철수", 20)
출력("\\n클래스 사용:")
학생.소개()

출력("\\n=== 프로그램 종료 ===")

감사합니다.
'''
        self.편집기.코드설정하기(example)

    # 파일 메뉴 기능
    def 새파일(self):
        if self.수정됨:
            if not messagebox.askyesno("확인", "저장하지 않은 변경사항이 있습니다. 계속하시겠습니까?"):
                return

        self.편집기.코드설정하기("")
        self.현재파일 = None
        self.수정됨 = False
        self._update_title()
        self.상태바.상태설정("새 파일")

    def 열기(self):
        if self.수정됨:
            if not messagebox.askyesno("확인", "저장하지 않은 변경사항이 있습니다. 계속하시겠습니까?"):
                return

        path = filedialog.askopenfilename(
            filetypes=[("한랭 파일", "*.hanlang"), ("모든 파일", "*.*")]
        )
        if path:
            self._on_file_select(path)

    def 저장(self):
        if self.현재파일:
            self._save_file(self.현재파일)
        else:
            self.다른이름으로저장()

    def 다른이름으로저장(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".hanlang",
            filetypes=[("한랭 파일", "*.hanlang"), ("모든 파일", "*.*")]
        )
        if path:
            self._save_file(path)

    def _save_file(self, path: str):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.편집기.코드가져오기())
            self.현재파일 = path
            self.수정됨 = False
            self._update_title()
            self.상태바.상태설정(f"저장됨: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("오류", f"파일을 저장할 수 없습니다: {e}")

    def 폴더열기(self):
        path = filedialog.askdirectory()
        if path:
            self.파일탐색기.폴더열기(path)
            self.상태바.상태설정(f"폴더 열림: {os.path.basename(path)}")

    def _open_examples_folder(self):
        """예제 폴더 열기"""
        # 현재 스크립트 위치 기준으로 examples 폴더 찾기
        script_dir = os.path.dirname(os.path.abspath(__file__))
        examples_path = os.path.join(script_dir, 'examples')

        if os.path.exists(examples_path):
            self.파일탐색기.폴더열기(examples_path)
            self.상태바.상태설정("예제 폴더 열림")
        else:
            # examples 폴더가 없으면 현재 폴더 열기
            self.파일탐색기.폴더열기(script_dir)
            self.상태바.상태설정("프로젝트 폴더 열림")

    # 실행 기능
    def 실행(self):
        """코드 실행"""
        self.터미널.지우기()
        self.터미널.쓰기("▶ 한랭 프로그램 실행 중...", "정보")
        self.터미널.쓰기("-" * 40)
        self.상태바.상태설정("실행 중...")

        code = self.편집기.코드가져오기()

        def run_code():
            try:
                def output_callback(text):
                    self.출력큐.put((text, None))

                def input_callback(prompt):
                    # 입력 요청을 메인 스레드로 전달
                    입력완료 = threading.Event()
                    입력값 = [None]

                    def 입력처리(값):
                        입력값[0] = 값
                        입력완료.set()

                    self.after(0, lambda: self.터미널.입력요청(prompt, 입력처리))
                    입력완료.wait()  # 입력 완료까지 대기
                    return 입력값[0]

                interpreter = HanlangInterpreter(
                    output_callback=output_callback,
                    input_callback=input_callback
                )
                interpreter.run(code)

                self.출력큐.put(("-" * 40, None))
                self.출력큐.put(("✓ 프로그램이 정상적으로 종료되었습니다.", "성공"))
                self.after(0, lambda: self.상태바.상태설정("실행 완료"))

            except SyntaxError as e:
                self.출력큐.put(("-" * 40, None))
                self.출력큐.put((f"✗ 구문 오류: {e}", "오류"))
                self.after(0, lambda: self.상태바.상태설정("구문 오류"))

            except 런타임에러 as e:
                self.출력큐.put(("-" * 40, None))
                self.출력큐.put((f"✗ 런타임 오류: {e}", "오류"))
                self.after(0, lambda: self.상태바.상태설정("런타임 오류"))

            except Exception as e:
                self.출력큐.put(("-" * 40, None))
                self.출력큐.put((f"✗ 오류: {e}", "오류"))
                self.after(0, lambda: self.상태바.상태설정("오류 발생"))

        thread = threading.Thread(target=run_code, daemon=True)
        thread.start()

    # 도움말
    def 문법도움말(self):
        help_text = """
═══════════════════════════════════════════════════
           한랭(HanLang) 문법 가이드
           한준후랭귀지 v2.0
═══════════════════════════════════════════════════

【 변수 선언 】
  변수 이름 = "홍길동"
  변수 나이 = 25
  상수 파이 = 3.14159

【 자료형 】
  • 정수: 1, 42, -10
  • 실수: 3.14, -0.5
  • 문자열: "안녕하세요", '한랭'
  • 불리언: 참, 거짓
  • 리스트: [1, 2, 3], ["a", "b"]
  • 딕셔너리: {"키": "값", "이름": "홍길동"}
  • 없음: 없음

【 연산자 】
  • 산술: +, -, *, /, %, ** (거듭제곱)
  • 비교: ==, !=, <, >, <=, >=
  • 논리: 그리고, 또는, 아님
  • 삼항: 조건 ? 참값 : 거짓값

【 조건문 】
  만약 조건 {
      # 참일 때 실행
  } 아니면만약 다른조건 {
      # 다른 조건이 참일 때
  } 아니면 {
      # 모두 거짓일 때
  }

【 반복문 】
  반복 i = 1 : 10 {
      출력(i)
  }

  동안 조건 {
      # 조건이 참인 동안 반복
  }

  중단  # 반복 종료
  계속  # 다음 반복으로

【 함수 】
  함수 더하기(a, b) {
      반환 a + b
  }

  변수 결과 = 더하기(3, 5)

【 람다 함수 】
  변수 제곱 = (x) => x * x
  변수 더하기 = (a, b) => a + b
  출력(제곱(5))  # 25

【 클래스 】
  클래스 사람 {
      함수 생성(이름) {
          나.이름 = 이름
      }

      함수 인사() {
          출력("안녕, 나는", 나.이름)
      }
  }

  변수 철수 = 사람("김철수")
  철수.인사()

【 예외 처리 】
  시도 {
      # 오류가 발생할 수 있는 코드
      던지기 "오류 발생!"
  } 잡기 (오류) {
      출력("오류:", 오류)
  } 마침내 {
      출력("항상 실행됨")
  }

【 딕셔너리 】
  변수 사람 = {"이름": "홍길동", "나이": 30}
  출력(사람["이름"])
  사람["직업"] = "개발자"
  출력(키값들(사람))
  출력(값들(사람))

【 내장 함수 - 기본 】
  • 출력(값, ...)  - 화면에 출력
  • 입력(프롬프트) - 사용자 입력
  • 길이(대상)     - 길이 반환
  • 정수변환(값)   - 정수로 변환
  • 실수변환(값)   - 실수로 변환
  • 문자열변환(값) - 문자열로 변환
  • 타입(값)       - 자료형 반환
  • 범위(시작, 끝) - 범위 리스트

【 내장 함수 - 수학 】
  • 제곱근(x)      - 제곱근
  • 거듭제곱(x, n) - 거듭제곱
  • 올림(x)        - 올림
  • 내림(x)        - 내림
  • 반올림(x, n)   - 반올림
  • 사인/코사인/탄젠트(x) - 삼각함수
  • 로그(x)/로그10(x) - 로그
  • 파이, 자연상수  - 상수
  • 랜덤()         - 0~1 난수
  • 랜덤정수(a, b) - 정수 난수

【 내장 함수 - 문자열 】
  • 대문자(s)/소문자(s) - 대소문자 변환
  • 분리(s, 구분자)    - 문자열 분리
  • 결합(리스트, 구분자) - 문자열 결합
  • 교체(s, 찾기, 바꾸기) - 문자열 교체
  • 공백제거(s)        - 양쪽 공백 제거
  • 찾기(s, 검색어)    - 위치 반환
  • 자르기(s, 시작, 끝) - 부분 문자열

【 내장 함수 - 리스트/딕셔너리 】
  • 추가(리스트, 값)   - 리스트에 추가
  • 제거(리스트, 값)   - 리스트에서 제거
  • 삽입(리스트, i, 값) - 위치에 삽입
  • 정렬(리스트)       - 정렬
  • 뒤집기(대상)       - 뒤집기
  • 키값들(딕셔너리)   - 키 목록
  • 값들(딕셔너리)     - 값 목록
  • 항목들(딕셔너리)   - (키, 값) 목록

【 주석 】
  # 한 줄 주석

  /* 여러 줄
     주석 */

═══════════════════════════════════════════════════
        IDE 단축키
═══════════════════════════════════════════════════
  Ctrl+N      새 파일
  Ctrl+O      파일 열기
  Ctrl+S      저장
  Ctrl+Shift+S  다른 이름으로 저장
  F5          실행
  Ctrl+F      찾기
  Ctrl+H      찾기/바꾸기
  Ctrl+Space  자동완성
  Ctrl+Z      실행 취소
  Ctrl+Y      다시 실행

  ▼/▶ 클릭   코드 접기/펼치기

═══════════════════════════════════════════════════
"""
        help_window = tk.Toplevel(self)
        help_window.title("한랭 문법 도움말")
        help_window.geometry("650x800")
        help_window.configure(bg='#1E1E1E')

        text = tk.Text(help_window, wrap=tk.WORD, bg='#1E1E1E', fg='#D4D4D4',
                      font=('D2Coding', 11), padx=20, pady=20)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert('1.0', help_text)
        text.configure(state=tk.DISABLED)

    def 정보(self):
        messagebox.showinfo(
            "한랭 IDE 정보",
            "한랭 IDE v1.0\n\n"
            "한준후랭귀지 (HanLang)\n"
            "한글로 코딩하는 프로그래밍 언어\n\n"
            "© 2024 한준후"
        )

    def _찾기열기(self):
        """찾기 다이얼로그 열기"""
        찾기바꾸기대화상자(self, self.편집기, 바꾸기모드=False)

    def _바꾸기열기(self):
        """찾기/바꾸기 다이얼로그 열기"""
        찾기바꾸기대화상자(self, self.편집기, 바꾸기모드=True)


def main():
    app = HanlangIDE()
    app.mainloop()


if __name__ == "__main__":
    main()
