# -*- coding: utf-8 -*-
"""
한랭(HanLang) 파서 - 구문 분석기
토큰을 AST(추상 구문 트리)로 변환합니다.
"""

from dataclasses import dataclass
from typing import List, Optional, Any
from hanlang_lexer import Token, TokenType, HanlangLexer

# AST 노드 정의
@dataclass
class ASTNode:
    pass

@dataclass
class 프로그램(ASTNode):
    문장들: List[ASTNode]

@dataclass
class 숫자리터럴(ASTNode):
    값: float

@dataclass
class 문자열리터럴(ASTNode):
    값: str

@dataclass
class 불리언리터럴(ASTNode):
    값: bool

@dataclass
class 없음리터럴(ASTNode):
    pass

@dataclass
class 리스트리터럴(ASTNode):
    요소들: List[ASTNode]

@dataclass
class 딕셔너리리터럴(ASTNode):
    쌍들: List[tuple]  # (키, 값) 튜플 리스트

@dataclass
class 식별자(ASTNode):
    이름: str

@dataclass
class 이항연산(ASTNode):
    왼쪽: ASTNode
    연산자: str
    오른쪽: ASTNode

@dataclass
class 단항연산(ASTNode):
    연산자: str
    피연산자: ASTNode

@dataclass
class 변수선언(ASTNode):
    이름: str
    초기값: Optional[ASTNode]
    상수여부: bool = False

@dataclass
class 대입문(ASTNode):
    대상: ASTNode
    연산자: str
    값: ASTNode

@dataclass
class 함수선언(ASTNode):
    이름: str
    매개변수들: List[str]
    본문: List[ASTNode]

@dataclass
class 함수호출(ASTNode):
    함수: ASTNode
    인자들: List[ASTNode]

@dataclass
class 반환문(ASTNode):
    값: Optional[ASTNode]

@dataclass
class 조건문(ASTNode):
    조건: ASTNode
    참블록: List[ASTNode]
    거짓블록: Optional[List[ASTNode]]

@dataclass
class 반복문(ASTNode):
    변수: str
    시작: ASTNode
    끝: ASTNode
    본문: List[ASTNode]

@dataclass
class 동안문(ASTNode):
    조건: ASTNode
    본문: List[ASTNode]

@dataclass
class 중단문(ASTNode):
    pass

@dataclass
class 계속문(ASTNode):
    pass

@dataclass
class 출력문(ASTNode):
    값들: List[ASTNode]

@dataclass
class 입력문(ASTNode):
    프롬프트: Optional[ASTNode]

@dataclass
class 인덱스접근(ASTNode):
    대상: ASTNode
    인덱스: ASTNode

@dataclass
class 속성접근(ASTNode):
    대상: ASTNode
    속성: str

@dataclass
class 클래스선언(ASTNode):
    이름: str
    본문: List[ASTNode]

@dataclass
class 시도문(ASTNode):
    시도블록: List[ASTNode]
    잡기변수: Optional[str]
    잡기블록: Optional[List[ASTNode]]
    마침내블록: Optional[List[ASTNode]]

@dataclass
class 던지기문(ASTNode):
    값: ASTNode

@dataclass
class 삼항연산(ASTNode):
    조건: ASTNode
    참값: ASTNode
    거짓값: ASTNode

@dataclass
class 람다식(ASTNode):
    매개변수들: List[str]
    본문: ASTNode


class HanlangParser:
    """한랭 파서 - 토큰을 AST로 변환"""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def error(self, message: str):
        token = self.current()
        raise SyntaxError(f"파싱 오류 (줄 {token.line}, 열 {token.column}): {message}")

    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF

    def peek(self, offset: int = 0) -> Token:
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]

    def advance(self) -> Token:
        token = self.current()
        self.pos += 1
        return token

    def skip_newlines(self):
        while self.current().type == TokenType.줄바꿈:
            self.advance()

    def expect(self, token_type: TokenType, message: str = None) -> Token:
        if self.current().type != token_type:
            msg = message or f"{token_type.name} 토큰이 필요합니다"
            self.error(msg)
        return self.advance()

    def match(self, *token_types: TokenType) -> bool:
        return self.current().type in token_types

    def parse(self) -> 프로그램:
        문장들 = []
        self.skip_newlines()

        while self.current().type != TokenType.파일끝:
            문장 = self.parse_statement()
            if 문장:
                문장들.append(문장)
            self.skip_newlines()

        return 프로그램(문장들)

    def parse_statement(self) -> Optional[ASTNode]:
        self.skip_newlines()

        token = self.current()

        if token.type == TokenType.변수:
            return self.parse_variable_declaration(상수=False)
        elif token.type == TokenType.상수:
            return self.parse_variable_declaration(상수=True)
        elif token.type == TokenType.함수:
            return self.parse_function_declaration()
        elif token.type == TokenType.반환:
            return self.parse_return_statement()
        elif token.type == TokenType.만약:
            return self.parse_if_statement()
        elif token.type == TokenType.반복:
            return self.parse_for_statement()
        elif token.type == TokenType.동안:
            return self.parse_while_statement()
        elif token.type == TokenType.중단:
            self.advance()
            return 중단문()
        elif token.type == TokenType.계속:
            self.advance()
            return 계속문()
        elif token.type == TokenType.출력:
            return self.parse_print_statement()
        elif token.type == TokenType.클래스:
            return self.parse_class_declaration()
        elif token.type == TokenType.시도:
            return self.parse_try_statement()
        elif token.type == TokenType.던지기:
            return self.parse_throw_statement()
        else:
            return self.parse_expression_statement()

    def parse_variable_declaration(self, 상수: bool) -> 변수선언:
        self.advance()  # 변수/상수 키워드
        이름 = self.expect(TokenType.식별자, "변수 이름이 필요합니다").value

        초기값 = None
        if self.match(TokenType.대입):
            self.advance()
            초기값 = self.parse_expression()

        return 변수선언(이름, 초기값, 상수)

    def parse_function_declaration(self) -> 함수선언:
        self.advance()  # 함수 키워드
        이름 = self.expect(TokenType.식별자, "함수 이름이 필요합니다").value

        self.expect(TokenType.왼쪽괄호, "( 가 필요합니다")
        매개변수들 = []

        if not self.match(TokenType.오른쪽괄호):
            매개변수들.append(self.expect(TokenType.식별자, "매개변수 이름이 필요합니다").value)
            while self.match(TokenType.쉼표):
                self.advance()
                매개변수들.append(self.expect(TokenType.식별자, "매개변수 이름이 필요합니다").value)

        self.expect(TokenType.오른쪽괄호, ") 가 필요합니다")
        본문 = self.parse_block()

        return 함수선언(이름, 매개변수들, 본문)

    def parse_block(self) -> List[ASTNode]:
        self.skip_newlines()
        self.expect(TokenType.왼쪽중괄호, "{ 가 필요합니다")
        self.skip_newlines()

        문장들 = []
        while not self.match(TokenType.오른쪽중괄호, TokenType.파일끝):
            문장 = self.parse_statement()
            if 문장:
                문장들.append(문장)
            self.skip_newlines()

        self.expect(TokenType.오른쪽중괄호, "} 가 필요합니다")
        return 문장들

    def parse_return_statement(self) -> 반환문:
        self.advance()  # 반환 키워드

        값 = None
        if not self.match(TokenType.줄바꿈, TokenType.오른쪽중괄호, TokenType.파일끝):
            값 = self.parse_expression()

        return 반환문(값)

    def parse_if_statement(self) -> 조건문:
        self.advance()  # 만약 키워드
        조건 = self.parse_expression()
        참블록 = self.parse_block()

        self.skip_newlines()
        거짓블록 = None

        if self.match(TokenType.아니면만약):
            # 아니면만약은 중첩된 조건문으로 처리
            거짓블록 = [self.parse_if_statement()]
        elif self.match(TokenType.아니면):
            self.advance()
            거짓블록 = self.parse_block()

        return 조건문(조건, 참블록, 거짓블록)

    def parse_for_statement(self) -> 반복문:
        self.advance()  # 반복 키워드
        변수 = self.expect(TokenType.식별자, "반복 변수 이름이 필요합니다").value

        self.expect(TokenType.대입, "= 가 필요합니다")
        시작 = self.parse_expression()

        # ~ 또는 .. 으로 범위 표현 (여기서는 콜론 사용)
        self.expect(TokenType.콜론, ": 가 필요합니다")
        끝 = self.parse_expression()

        본문 = self.parse_block()

        return 반복문(변수, 시작, 끝, 본문)

    def parse_while_statement(self) -> 동안문:
        self.advance()  # 동안 키워드
        조건 = self.parse_expression()
        본문 = self.parse_block()

        return 동안문(조건, 본문)

    def parse_print_statement(self) -> 출력문:
        self.advance()  # 출력 키워드
        self.expect(TokenType.왼쪽괄호, "( 가 필요합니다")

        값들 = []
        if not self.match(TokenType.오른쪽괄호):
            값들.append(self.parse_expression())
            while self.match(TokenType.쉼표):
                self.advance()
                값들.append(self.parse_expression())

        self.expect(TokenType.오른쪽괄호, ") 가 필요합니다")
        return 출력문(값들)

    def parse_class_declaration(self) -> 클래스선언:
        self.advance()  # 클래스 키워드
        이름 = self.expect(TokenType.식별자, "클래스 이름이 필요합니다").value
        본문 = self.parse_block()

        return 클래스선언(이름, 본문)

    def parse_try_statement(self) -> 시도문:
        self.advance()  # 시도 키워드
        시도블록 = self.parse_block()

        self.skip_newlines()
        잡기변수 = None
        잡기블록 = None
        마침내블록 = None

        if self.match(TokenType.잡기):
            self.advance()
            if self.match(TokenType.왼쪽괄호):
                self.advance()
                잡기변수 = self.expect(TokenType.식별자, "예외 변수명이 필요합니다").value
                self.expect(TokenType.오른쪽괄호, ") 가 필요합니다")
            잡기블록 = self.parse_block()
            self.skip_newlines()

        if self.match(TokenType.마침내):
            self.advance()
            마침내블록 = self.parse_block()

        return 시도문(시도블록, 잡기변수, 잡기블록, 마침내블록)

    def parse_throw_statement(self) -> 던지기문:
        self.advance()  # 던지기 키워드
        값 = self.parse_expression()
        return 던지기문(값)

    def _is_lambda(self) -> bool:
        """괄호 다음이 람다인지 확인 (룩어헤드)"""
        saved_pos = self.pos

        if not self.match(TokenType.왼쪽괄호):
            return False

        self.advance()  # (

        # 빈 괄호 () => 형태 확인
        if self.match(TokenType.오른쪽괄호):
            self.advance()
            is_lambda = self.match(TokenType.화살표함수)
            self.pos = saved_pos
            return is_lambda

        # 식별자, 쉼표 패턴 확인
        while True:
            if not self.match(TokenType.식별자):
                self.pos = saved_pos
                return False
            self.advance()

            if self.match(TokenType.오른쪽괄호):
                self.advance()
                is_lambda = self.match(TokenType.화살표함수)
                self.pos = saved_pos
                return is_lambda

            if not self.match(TokenType.쉼표):
                self.pos = saved_pos
                return False
            self.advance()

    def parse_lambda(self) -> 람다식:
        """람다 표현식 파싱: (x, y) => 표현식"""
        self.advance()  # (
        매개변수들 = []

        if not self.match(TokenType.오른쪽괄호):
            매개변수들.append(self.expect(TokenType.식별자, "매개변수 이름이 필요합니다").value)
            while self.match(TokenType.쉼표):
                self.advance()
                매개변수들.append(self.expect(TokenType.식별자, "매개변수 이름이 필요합니다").value)

        self.expect(TokenType.오른쪽괄호, ") 가 필요합니다")
        self.expect(TokenType.화살표함수, "=> 가 필요합니다")
        본문 = self.parse_expression()

        return 람다식(매개변수들, 본문)

    def parse_expression_statement(self) -> Optional[ASTNode]:
        expr = self.parse_expression()

        # 대입문 처리
        if self.match(TokenType.대입, TokenType.더하기대입, TokenType.빼기대입,
                      TokenType.곱하기대입, TokenType.나누기대입):
            연산자 = self.advance().value
            값 = self.parse_expression()
            return 대입문(expr, 연산자, 값)

        return expr

    def parse_expression(self) -> ASTNode:
        return self.parse_ternary()

    def parse_ternary(self) -> ASTNode:
        조건 = self.parse_or()

        if self.match(TokenType.물음표):
            self.advance()
            참값 = self.parse_expression()
            self.expect(TokenType.콜론, ": 가 필요합니다")
            거짓값 = self.parse_expression()
            return 삼항연산(조건, 참값, 거짓값)

        return 조건

    def parse_or(self) -> ASTNode:
        left = self.parse_and()

        while self.match(TokenType.또는):
            op = self.advance().value
            right = self.parse_and()
            left = 이항연산(left, op, right)

        return left

    def parse_and(self) -> ASTNode:
        left = self.parse_not()

        while self.match(TokenType.그리고):
            op = self.advance().value
            right = self.parse_not()
            left = 이항연산(left, op, right)

        return left

    def parse_not(self) -> ASTNode:
        if self.match(TokenType.아님):
            op = self.advance().value
            operand = self.parse_not()
            return 단항연산(op, operand)

        return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        left = self.parse_additive()

        while self.match(TokenType.같음, TokenType.다름, TokenType.작음,
                        TokenType.큼, TokenType.작거나같음, TokenType.크거나같음):
            op = self.advance().value
            right = self.parse_additive()
            left = 이항연산(left, op, right)

        return left

    def parse_additive(self) -> ASTNode:
        left = self.parse_multiplicative()

        while self.match(TokenType.더하기, TokenType.빼기):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = 이항연산(left, op, right)

        return left

    def parse_multiplicative(self) -> ASTNode:
        left = self.parse_power()

        while self.match(TokenType.곱하기, TokenType.나누기, TokenType.나머지):
            op = self.advance().value
            right = self.parse_power()
            left = 이항연산(left, op, right)

        return left

    def parse_power(self) -> ASTNode:
        left = self.parse_unary()

        if self.match(TokenType.거듭제곱):
            op = self.advance().value
            right = self.parse_power()  # 우결합
            left = 이항연산(left, op, right)

        return left

    def parse_unary(self) -> ASTNode:
        if self.match(TokenType.빼기):
            op = self.advance().value
            operand = self.parse_unary()
            return 단항연산(op, operand)

        return self.parse_call()

    def parse_call(self) -> ASTNode:
        expr = self.parse_primary()

        while True:
            if self.match(TokenType.왼쪽괄호):
                self.advance()
                인자들 = []

                if not self.match(TokenType.오른쪽괄호):
                    인자들.append(self.parse_expression())
                    while self.match(TokenType.쉼표):
                        self.advance()
                        인자들.append(self.parse_expression())

                self.expect(TokenType.오른쪽괄호, ") 가 필요합니다")
                expr = 함수호출(expr, 인자들)

            elif self.match(TokenType.왼쪽대괄호):
                self.advance()
                인덱스 = self.parse_expression()
                self.expect(TokenType.오른쪽대괄호, "] 가 필요합니다")
                expr = 인덱스접근(expr, 인덱스)

            elif self.match(TokenType.점):
                self.advance()
                속성 = self.expect(TokenType.식별자, "속성 이름이 필요합니다").value
                expr = 속성접근(expr, 속성)

            else:
                break

        return expr

    def parse_primary(self) -> ASTNode:
        token = self.current()

        if token.type == TokenType.정수:
            self.advance()
            return 숫자리터럴(token.value)

        if token.type == TokenType.실수:
            self.advance()
            return 숫자리터럴(token.value)

        if token.type == TokenType.문자열:
            self.advance()
            return 문자열리터럴(token.value)

        if token.type in (TokenType.참, TokenType.거짓):
            self.advance()
            return 불리언리터럴(token.value)

        if token.type == TokenType.없음:
            self.advance()
            return 없음리터럴()

        if token.type == TokenType.식별자:
            self.advance()
            return 식별자(token.value)

        if token.type == TokenType.입력:
            self.advance()
            self.expect(TokenType.왼쪽괄호, "( 가 필요합니다")
            프롬프트 = None
            if not self.match(TokenType.오른쪽괄호):
                프롬프트 = self.parse_expression()
            self.expect(TokenType.오른쪽괄호, ") 가 필요합니다")
            return 입력문(프롬프트)

        if token.type == TokenType.왼쪽괄호:
            # 람다인지 그룹 표현식인지 확인
            if self._is_lambda():
                return self.parse_lambda()
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.오른쪽괄호, ") 가 필요합니다")
            return expr

        if token.type == TokenType.왼쪽대괄호:
            self.advance()
            요소들 = []

            if not self.match(TokenType.오른쪽대괄호):
                요소들.append(self.parse_expression())
                while self.match(TokenType.쉼표):
                    self.advance()
                    요소들.append(self.parse_expression())

            self.expect(TokenType.오른쪽대괄호, "] 가 필요합니다")
            return 리스트리터럴(요소들)

        if token.type == TokenType.왼쪽중괄호:
            self.advance()
            self.skip_newlines()
            쌍들 = []

            if not self.match(TokenType.오른쪽중괄호):
                # 첫 번째 키-값 쌍 파싱
                키 = self.parse_expression()
                self.expect(TokenType.콜론, ": 가 필요합니다")
                값 = self.parse_expression()
                쌍들.append((키, 값))

                while self.match(TokenType.쉼표):
                    self.advance()
                    self.skip_newlines()
                    if self.match(TokenType.오른쪽중괄호):
                        break  # 후행 쉼표 허용
                    키 = self.parse_expression()
                    self.expect(TokenType.콜론, ": 가 필요합니다")
                    값 = self.parse_expression()
                    쌍들.append((키, 값))

            self.skip_newlines()
            self.expect(TokenType.오른쪽중괄호, "} 가 필요합니다")
            return 딕셔너리리터럴(쌍들)

        self.error(f"예상치 못한 토큰: {token.type.name}")


if __name__ == "__main__":
    code = '''
변수 이름 = "한준후"
변수 나이 = 25

함수 인사하기(이름) {
    출력("안녕하세요, " + 이름 + "님!")
    반환 참
}

만약 나이 >= 20 {
    출력("성인입니다")
} 아니면 {
    출력("미성년자입니다")
}

반복 i = 1 : 5 {
    출력(i)
}
'''
    lexer = HanlangLexer(code)
    tokens = lexer.tokenize()
    parser = HanlangParser(tokens)
    ast = parser.parse()

    def print_ast(node, indent=0):
        prefix = "  " * indent
        if isinstance(node, 프로그램):
            print(f"{prefix}프로그램:")
            for stmt in node.문장들:
                print_ast(stmt, indent + 1)
        elif isinstance(node, 변수선언):
            print(f"{prefix}변수선언: {node.이름} {'(상수)' if node.상수여부 else ''}")
            if node.초기값:
                print_ast(node.초기값, indent + 1)
        elif isinstance(node, 함수선언):
            print(f"{prefix}함수선언: {node.이름}({', '.join(node.매개변수들)})")
            for stmt in node.본문:
                print_ast(stmt, indent + 1)
        elif isinstance(node, 조건문):
            print(f"{prefix}조건문:")
            print(f"{prefix}  조건:")
            print_ast(node.조건, indent + 2)
            print(f"{prefix}  참블록:")
            for stmt in node.참블록:
                print_ast(stmt, indent + 2)
            if node.거짓블록:
                print(f"{prefix}  거짓블록:")
                for stmt in node.거짓블록:
                    print_ast(stmt, indent + 2)
        elif isinstance(node, 반복문):
            print(f"{prefix}반복문: {node.변수}")
            print_ast(node.시작, indent + 1)
            print_ast(node.끝, indent + 1)
            for stmt in node.본문:
                print_ast(stmt, indent + 1)
        elif isinstance(node, 출력문):
            print(f"{prefix}출력문:")
            for val in node.값들:
                print_ast(val, indent + 1)
        elif isinstance(node, 반환문):
            print(f"{prefix}반환문:")
            if node.값:
                print_ast(node.값, indent + 1)
        elif isinstance(node, 이항연산):
            print(f"{prefix}이항연산: {node.연산자}")
            print_ast(node.왼쪽, indent + 1)
            print_ast(node.오른쪽, indent + 1)
        elif isinstance(node, 숫자리터럴):
            print(f"{prefix}숫자: {node.값}")
        elif isinstance(node, 문자열리터럴):
            print(f"{prefix}문자열: \"{node.값}\"")
        elif isinstance(node, 불리언리터럴):
            print(f"{prefix}불리언: {node.값}")
        elif isinstance(node, 식별자):
            print(f"{prefix}식별자: {node.이름}")
        else:
            print(f"{prefix}{type(node).__name__}: {node}")

    print_ast(ast)
