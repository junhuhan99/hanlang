# -*- coding: utf-8 -*-
"""
한랭(HanLang) 렉서 - 토큰 분석기
한준후랭귀지의 어휘 분석을 담당합니다.
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    # 리터럴
    정수 = auto()
    실수 = auto()
    문자열 = auto()
    참거짓 = auto()

    # 키워드
    변수 = auto()
    상수 = auto()
    함수 = auto()
    반환 = auto()
    만약 = auto()
    아니면 = auto()
    아니면만약 = auto()
    반복 = auto()
    동안 = auto()
    중단 = auto()
    계속 = auto()
    클래스 = auto()
    참 = auto()
    거짓 = auto()
    없음 = auto()
    그리고 = auto()
    또는 = auto()
    아님 = auto()
    출력 = auto()
    입력 = auto()
    시도 = auto()
    잡기 = auto()
    마침내 = auto()
    던지기 = auto()

    # 연산자
    더하기 = auto()        # +
    빼기 = auto()          # -
    곱하기 = auto()        # *
    나누기 = auto()        # /
    나머지 = auto()        # %
    거듭제곱 = auto()      # **
    대입 = auto()          # =
    같음 = auto()          # ==
    다름 = auto()          # !=
    작음 = auto()          # <
    큼 = auto()            # >
    작거나같음 = auto()    # <=
    크거나같음 = auto()    # >=
    더하기대입 = auto()    # +=
    빼기대입 = auto()      # -=
    곱하기대입 = auto()    # *=
    나누기대입 = auto()    # /=

    # 삼항 연산자
    물음표 = auto()        # ?

    # 람다
    화살표함수 = auto()    # =>

    # 구분자
    왼쪽괄호 = auto()      # (
    오른쪽괄호 = auto()    # )
    왼쪽중괄호 = auto()    # {
    오른쪽중괄호 = auto()  # }
    왼쪽대괄호 = auto()    # [
    오른쪽대괄호 = auto()  # ]
    쉼표 = auto()          # ,
    콜론 = auto()          # :
    세미콜론 = auto()      # ; (선택적)
    점 = auto()            # .
    화살표 = auto()        # ->

    # 기타
    식별자 = auto()
    줄바꿈 = auto()
    파일끝 = auto()
    주석 = auto()

@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {repr(self.value)}, 줄:{self.line}, 열:{self.column})"

class HanlangLexer:
    """한랭 렉서 - 소스 코드를 토큰으로 분석"""

    KEYWORDS = {
        '변수': TokenType.변수,
        '상수': TokenType.상수,
        '함수': TokenType.함수,
        '반환': TokenType.반환,
        '만약': TokenType.만약,
        '아니면': TokenType.아니면,
        '아니면만약': TokenType.아니면만약,
        '반복': TokenType.반복,
        '동안': TokenType.동안,
        '중단': TokenType.중단,
        '계속': TokenType.계속,
        '클래스': TokenType.클래스,
        '참': TokenType.참,
        '거짓': TokenType.거짓,
        '없음': TokenType.없음,
        '그리고': TokenType.그리고,
        '또는': TokenType.또는,
        '아님': TokenType.아님,
        '출력': TokenType.출력,
        '입력': TokenType.입력,
        '시도': TokenType.시도,
        '잡기': TokenType.잡기,
        '마침내': TokenType.마침내,
        '던지기': TokenType.던지기,
    }

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def error(self, message: str):
        raise SyntaxError(f"렉서 오류 (줄 {self.line}, 열 {self.column}): {message}")

    def peek(self, offset: int = 0) -> Optional[str]:
        pos = self.pos + offset
        if pos < len(self.source):
            return self.source[pos]
        return None

    def advance(self) -> Optional[str]:
        if self.pos < len(self.source):
            char = self.source[self.pos]
            self.pos += 1
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            return char
        return None

    def skip_whitespace(self):
        while self.peek() and self.peek() in ' \t\r':
            self.advance()

    def skip_comment(self):
        if self.peek() == '#':
            while self.peek() and self.peek() != '\n':
                self.advance()
            return True
        # 여러 줄 주석 /* */
        if self.peek() == '/' and self.peek(1) == '*':
            self.advance()  # /
            self.advance()  # *
            while self.peek():
                if self.peek() == '*' and self.peek(1) == '/':
                    self.advance()  # *
                    self.advance()  # /
                    return True
                self.advance()
            self.error("종료되지 않은 주석")
        return False

    def skip_hanlang_special(self):
        """한랭 특수 구문 건너뛰기 (시작/끝 문구)"""
        특수문구들 = ["개발자한준후가 만든언어입니다.", "감사합니다."]

        for 문구 in 특수문구들:
            if self.source[self.pos:].startswith(문구):
                for _ in range(len(문구)):
                    self.advance()
                return True
        return False

    def read_string(self) -> Token:
        start_line = self.line
        start_column = self.column
        quote = self.advance()  # " 또는 '
        result = ""

        while self.peek() and self.peek() != quote:
            if self.peek() == '\\':
                self.advance()
                escape_char = self.advance()
                if escape_char == 'n':
                    result += '\n'
                elif escape_char == 't':
                    result += '\t'
                elif escape_char == '\\':
                    result += '\\'
                elif escape_char == quote:
                    result += quote
                else:
                    result += escape_char
            elif self.peek() == '\n':
                self.error("문자열이 닫히지 않았습니다")
            else:
                result += self.advance()

        if not self.peek():
            self.error("문자열이 닫히지 않았습니다")

        self.advance()  # 닫는 따옴표
        return Token(TokenType.문자열, result, start_line, start_column)

    def read_number(self) -> Token:
        start_line = self.line
        start_column = self.column
        result = ""
        has_dot = False

        while self.peek() and (self.peek().isdigit() or self.peek() == '.'):
            if self.peek() == '.':
                if has_dot:
                    break
                if not (self.peek(1) and self.peek(1).isdigit()):
                    break
                has_dot = True
            result += self.advance()

        if has_dot:
            return Token(TokenType.실수, float(result), start_line, start_column)
        return Token(TokenType.정수, int(result), start_line, start_column)

    def read_identifier(self) -> Token:
        start_line = self.line
        start_column = self.column
        result = ""

        while self.peek() and (self.peek().isalnum() or self.peek() == '_' or ord(self.peek()) > 127):
            result += self.advance()

        # 키워드 확인
        if result in self.KEYWORDS:
            token_type = self.KEYWORDS[result]
            if result == '참':
                return Token(token_type, True, start_line, start_column)
            elif result == '거짓':
                return Token(token_type, False, start_line, start_column)
            elif result == '없음':
                return Token(token_type, None, start_line, start_column)
            return Token(token_type, result, start_line, start_column)

        return Token(TokenType.식별자, result, start_line, start_column)

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()

            if self.pos >= len(self.source):
                break

            # 주석 건너뛰기
            if self.skip_comment():
                continue

            # 한랭 특수 구문 건너뛰기
            if self.skip_hanlang_special():
                continue

            char = self.peek()
            start_line = self.line
            start_column = self.column

            # 줄바꿈
            if char == '\n':
                self.advance()
                self.tokens.append(Token(TokenType.줄바꿈, '\n', start_line, start_column))
                continue

            # 문자열
            if char in '"\'':
                self.tokens.append(self.read_string())
                continue

            # 숫자
            if char.isdigit():
                self.tokens.append(self.read_number())
                continue

            # 식별자 또는 키워드
            if char.isalpha() or char == '_' or ord(char) > 127:
                self.tokens.append(self.read_identifier())
                continue

            # 연산자 및 구분자
            if char == '+':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.더하기대입, '+=', start_line, start_column))
                else:
                    self.tokens.append(Token(TokenType.더하기, '+', start_line, start_column))
                continue

            if char == '-':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.빼기대입, '-=', start_line, start_column))
                elif self.peek() == '>':
                    self.advance()
                    self.tokens.append(Token(TokenType.화살표, '->', start_line, start_column))
                else:
                    self.tokens.append(Token(TokenType.빼기, '-', start_line, start_column))
                continue

            if char == '*':
                self.advance()
                if self.peek() == '*':
                    self.advance()
                    self.tokens.append(Token(TokenType.거듭제곱, '**', start_line, start_column))
                elif self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.곱하기대입, '*=', start_line, start_column))
                else:
                    self.tokens.append(Token(TokenType.곱하기, '*', start_line, start_column))
                continue

            if char == '/':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.나누기대입, '/=', start_line, start_column))
                else:
                    self.tokens.append(Token(TokenType.나누기, '/', start_line, start_column))
                continue

            if char == '%':
                self.advance()
                self.tokens.append(Token(TokenType.나머지, '%', start_line, start_column))
                continue

            if char == '=':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.같음, '==', start_line, start_column))
                elif self.peek() == '>':
                    self.advance()
                    self.tokens.append(Token(TokenType.화살표함수, '=>', start_line, start_column))
                else:
                    self.tokens.append(Token(TokenType.대입, '=', start_line, start_column))
                continue

            if char == '!':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.다름, '!=', start_line, start_column))
                else:
                    self.error(f"예상치 못한 문자: !")
                continue

            if char == '<':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.작거나같음, '<=', start_line, start_column))
                else:
                    self.tokens.append(Token(TokenType.작음, '<', start_line, start_column))
                continue

            if char == '>':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.크거나같음, '>=', start_line, start_column))
                else:
                    self.tokens.append(Token(TokenType.큼, '>', start_line, start_column))
                continue

            # 구분자
            simple_tokens = {
                '(': TokenType.왼쪽괄호,
                ')': TokenType.오른쪽괄호,
                '{': TokenType.왼쪽중괄호,
                '}': TokenType.오른쪽중괄호,
                '[': TokenType.왼쪽대괄호,
                ']': TokenType.오른쪽대괄호,
                ',': TokenType.쉼표,
                ':': TokenType.콜론,
                ';': TokenType.세미콜론,
                '.': TokenType.점,
                '?': TokenType.물음표,
            }

            if char in simple_tokens:
                self.advance()
                self.tokens.append(Token(simple_tokens[char], char, start_line, start_column))
                continue

            self.error(f"예상치 못한 문자: {char}")

        self.tokens.append(Token(TokenType.파일끝, None, self.line, self.column))
        return self.tokens


if __name__ == "__main__":
    # 테스트
    code = '''
변수 이름 = "한준후"
변수 나이 = 25

함수 인사하기(이름) {
    출력("안녕하세요, " + 이름 + "님!")
}

만약 나이 >= 20 {
    출력("성인입니다")
} 아니면 {
    출력("미성년자입니다")
}
'''
    lexer = HanlangLexer(code)
    tokens = lexer.tokenize()
    for token in tokens:
        if token.type != TokenType.줄바꿈:
            print(token)
