# -*- coding: utf-8 -*-
"""
한랭(HanLang) 인터프리터 - 코드 실행기
AST를 실행하여 결과를 반환합니다.
"""

import math
from typing import Dict, List, Any, Optional, Callable
from hanlang_lexer import HanlangLexer
from hanlang_parser import (
    HanlangParser, ASTNode, 프로그램, 숫자리터럴, 문자열리터럴, 불리언리터럴,
    없음리터럴, 리스트리터럴, 딕셔너리리터럴, 식별자, 이항연산, 단항연산, 변수선언, 대입문,
    함수선언, 함수호출, 반환문, 조건문, 반복문, 동안문, 중단문, 계속문,
    출력문, 입력문, 인덱스접근, 속성접근, 클래스선언, 시도문, 던지기문, 삼항연산, 람다식
)

class 반환예외(Exception):
    """함수에서 반환할 때 사용하는 예외"""
    def __init__(self, 값):
        self.값 = 값

class 중단예외(Exception):
    """반복문을 중단할 때 사용하는 예외"""
    pass

class 계속예외(Exception):
    """반복문의 다음 반복으로 건너뛸 때 사용하는 예외"""
    pass

class 런타임에러(Exception):
    """런타임 오류"""
    pass

class 사용자예외(Exception):
    """사용자 정의 예외 (던지기 문으로 발생)"""
    def __init__(self, 값):
        self.값 = 값
        super().__init__(str(값))

class 한랭함수:
    """사용자 정의 함수"""
    def __init__(self, 선언: 함수선언, 환경: 'Environment'):
        self.선언 = 선언
        self.클로저 = 환경

    def __repr__(self):
        return f"<함수 {self.선언.이름}>"

class 한랭람다:
    """람다 함수"""
    def __init__(self, 선언: 람다식, 환경: 'Environment'):
        self.매개변수들 = 선언.매개변수들
        self.본문 = 선언.본문
        self.클로저 = 환경

    def __repr__(self):
        return f"<람다 ({', '.join(self.매개변수들)})>"

class 한랭클래스:
    """사용자 정의 클래스"""
    def __init__(self, 이름: str, 메서드들: Dict[str, 한랭함수]):
        self.이름 = 이름
        self.메서드들 = 메서드들

    def __repr__(self):
        return f"<클래스 {self.이름}>"

class 한랭인스턴스:
    """클래스의 인스턴스"""
    def __init__(self, 클래스: 한랭클래스):
        self.클래스 = 클래스
        self.필드들: Dict[str, Any] = {}

    def __repr__(self):
        return f"<{self.클래스.이름} 인스턴스>"

class Environment:
    """변수 환경 (스코프)"""
    def __init__(self, parent: Optional['Environment'] = None):
        self.variables: Dict[str, Any] = {}
        self.constants: set = set()
        self.parent = parent

    def define(self, name: str, value: Any, is_constant: bool = False):
        self.variables[name] = value
        if is_constant:
            self.constants.add(name)

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise 런타임에러(f"정의되지 않은 변수: {name}")

    def set(self, name: str, value: Any):
        if name in self.variables:
            if name in self.constants:
                raise 런타임에러(f"상수는 변경할 수 없습니다: {name}")
            self.variables[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        raise 런타임에러(f"정의되지 않은 변수: {name}")

    def exists(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.exists(name)
        return False


class HanlangInterpreter:
    """한랭 인터프리터"""

    def __init__(self, output_callback: Callable[[str], None] = None,
                 input_callback: Callable[[str], str] = None):
        self.global_env = Environment()
        self.output_callback = output_callback or print
        self.input_callback = input_callback or input
        self.output_buffer: List[str] = []
        self._setup_builtins()

    def _setup_builtins(self):
        """내장 함수 설정"""
        # 기본 함수
        self.global_env.define('길이', lambda x: len(x))
        self.global_env.define('정수변환', lambda x: int(x))
        self.global_env.define('실수변환', lambda x: float(x))
        self.global_env.define('문자열변환', lambda x: str(x))
        self.global_env.define('타입', lambda x: type(x).__name__)
        self.global_env.define('범위', lambda *args: list(range(*args)))
        self.global_env.define('절대값', lambda x: abs(x))
        self.global_env.define('최대값', lambda *args: max(args) if len(args) > 1 else max(args[0]))
        self.global_env.define('최소값', lambda *args: min(args) if len(args) > 1 else min(args[0]))
        self.global_env.define('합계', lambda x: sum(x))
        self.global_env.define('정렬', lambda x: sorted(x))
        self.global_env.define('뒤집기', lambda x: list(reversed(x)) if isinstance(x, list) else x[::-1])
        self.global_env.define('추가', lambda lst, item: lst.append(item) or lst)
        self.global_env.define('제거', lambda lst, item: lst.remove(item) or lst)
        self.global_env.define('포함', lambda container, item: item in container)

        # 수학 함수
        self.global_env.define('제곱근', lambda x: math.sqrt(x))
        self.global_env.define('거듭제곱', lambda x, y: math.pow(x, y))
        self.global_env.define('올림', lambda x: math.ceil(x))
        self.global_env.define('내림', lambda x: math.floor(x))
        self.global_env.define('반올림', lambda x, n=0: round(x, n))
        self.global_env.define('사인', lambda x: math.sin(x))
        self.global_env.define('코사인', lambda x: math.cos(x))
        self.global_env.define('탄젠트', lambda x: math.tan(x))
        self.global_env.define('아크사인', lambda x: math.asin(x))
        self.global_env.define('아크코사인', lambda x: math.acos(x))
        self.global_env.define('아크탄젠트', lambda x: math.atan(x))
        self.global_env.define('로그', lambda x, base=math.e: math.log(x, base) if base != math.e else math.log(x))
        self.global_env.define('로그10', lambda x: math.log10(x))
        self.global_env.define('파이', math.pi)
        self.global_env.define('자연상수', math.e)
        self.global_env.define('무한대', math.inf)
        self.global_env.define('랜덤', lambda: __import__('random').random())
        self.global_env.define('랜덤정수', lambda a, b: __import__('random').randint(a, b))

        # 문자열 함수
        self.global_env.define('대문자', lambda s: s.upper())
        self.global_env.define('소문자', lambda s: s.lower())
        self.global_env.define('분리', lambda s, sep=' ': s.split(sep))
        self.global_env.define('결합', lambda sep, lst: sep.join(str(x) for x in lst))
        self.global_env.define('교체', lambda s, old, new: s.replace(old, new))
        self.global_env.define('공백제거', lambda s: s.strip())
        self.global_env.define('왼쪽공백제거', lambda s: s.lstrip())
        self.global_env.define('오른쪽공백제거', lambda s: s.rstrip())
        self.global_env.define('찾기', lambda s, sub: s.find(sub))
        self.global_env.define('시작확인', lambda s, prefix: s.startswith(prefix))
        self.global_env.define('끝확인', lambda s, suffix: s.endswith(suffix))
        self.global_env.define('자르기', lambda s, start=0, end=None: s[start:end] if end else s[start:])
        self.global_env.define('반복문자', lambda s, n: s * n)
        self.global_env.define('채우기', lambda s, width, char=' ': s.center(width, char))
        self.global_env.define('왼쪽채우기', lambda s, width, char=' ': s.ljust(width, char))
        self.global_env.define('오른쪽채우기', lambda s, width, char=' ': s.rjust(width, char))

        # 딕셔너리 함수
        self.global_env.define('키값들', lambda d: list(d.keys()))
        self.global_env.define('값들', lambda d: list(d.values()))
        self.global_env.define('항목들', lambda d: list(d.items()))
        self.global_env.define('딕셔너리', lambda: {})

        # 리스트 함수 추가
        self.global_env.define('삽입', lambda lst, i, item: lst.insert(i, item) or lst)
        self.global_env.define('빼기', lambda lst, i=-1: lst.pop(i))
        self.global_env.define('인덱스', lambda lst, item: lst.index(item))
        self.global_env.define('개수', lambda lst, item: lst.count(item))
        self.global_env.define('복사', lambda x: x.copy() if hasattr(x, 'copy') else list(x))
        self.global_env.define('비우기', lambda lst: lst.clear() or lst)

    def run(self, source: str) -> Any:
        """소스 코드 실행"""
        self.output_buffer = []
        lexer = HanlangLexer(source)
        tokens = lexer.tokenize()
        parser = HanlangParser(tokens)
        ast = parser.parse()
        return self.execute(ast, self.global_env)

    def execute(self, node: ASTNode, env: Environment) -> Any:
        """AST 노드 실행"""
        method_name = f'execute_{type(node).__name__}'
        method = getattr(self, method_name, None)
        if method:
            return method(node, env)
        raise 런타임에러(f"실행할 수 없는 노드 타입: {type(node).__name__}")

    def execute_프로그램(self, node: 프로그램, env: Environment) -> Any:
        result = None
        for 문장 in node.문장들:
            result = self.execute(문장, env)
        return result

    def execute_숫자리터럴(self, node: 숫자리터럴, env: Environment) -> float:
        return node.값

    def execute_문자열리터럴(self, node: 문자열리터럴, env: Environment) -> str:
        return node.값

    def execute_불리언리터럴(self, node: 불리언리터럴, env: Environment) -> bool:
        return node.값

    def execute_없음리터럴(self, node: 없음리터럴, env: Environment) -> None:
        return None

    def execute_리스트리터럴(self, node: 리스트리터럴, env: Environment) -> list:
        return [self.execute(요소, env) for 요소 in node.요소들]

    def execute_딕셔너리리터럴(self, node: 딕셔너리리터럴, env: Environment) -> dict:
        return {self.execute(키, env): self.execute(값, env) for 키, 값 in node.쌍들}

    def execute_식별자(self, node: 식별자, env: Environment) -> Any:
        return env.get(node.이름)

    def execute_이항연산(self, node: 이항연산, env: Environment) -> Any:
        left = self.execute(node.왼쪽, env)
        right = self.execute(node.오른쪽, env)
        op = node.연산자

        if op == '+':
            return left + right
        elif op == '-':
            return left - right
        elif op == '*':
            return left * right
        elif op == '/':
            if right == 0:
                raise 런타임에러("0으로 나눌 수 없습니다")
            return left / right
        elif op == '%':
            return left % right
        elif op == '**':
            return left ** right
        elif op == '==':
            return left == right
        elif op == '!=':
            return left != right
        elif op == '<':
            return left < right
        elif op == '>':
            return left > right
        elif op == '<=':
            return left <= right
        elif op == '>=':
            return left >= right
        elif op == '그리고':
            return left and right
        elif op == '또는':
            return left or right
        else:
            raise 런타임에러(f"알 수 없는 연산자: {op}")

    def execute_단항연산(self, node: 단항연산, env: Environment) -> Any:
        operand = self.execute(node.피연산자, env)
        op = node.연산자

        if op == '-':
            return -operand
        elif op == '아님':
            return not operand
        else:
            raise 런타임에러(f"알 수 없는 단항 연산자: {op}")

    def execute_변수선언(self, node: 변수선언, env: Environment) -> None:
        초기값 = None
        if node.초기값:
            초기값 = self.execute(node.초기값, env)
        env.define(node.이름, 초기값, node.상수여부)

    def execute_대입문(self, node: 대입문, env: Environment) -> Any:
        값 = self.execute(node.값, env)

        if node.연산자 == '=':
            pass
        elif node.연산자 == '+=':
            현재값 = self.execute(node.대상, env)
            값 = 현재값 + 값
        elif node.연산자 == '-=':
            현재값 = self.execute(node.대상, env)
            값 = 현재값 - 값
        elif node.연산자 == '*=':
            현재값 = self.execute(node.대상, env)
            값 = 현재값 * 값
        elif node.연산자 == '/=':
            현재값 = self.execute(node.대상, env)
            값 = 현재값 / 값

        if isinstance(node.대상, 식별자):
            env.set(node.대상.이름, 값)
        elif isinstance(node.대상, 인덱스접근):
            대상 = self.execute(node.대상.대상, env)
            인덱스 = self.execute(node.대상.인덱스, env)
            if isinstance(대상, dict):
                대상[인덱스] = 값  # 딕셔너리는 키를 그대로 사용
            else:
                대상[int(인덱스)] = 값  # 리스트는 정수 인덱스
        elif isinstance(node.대상, 속성접근):
            대상 = self.execute(node.대상.대상, env)
            if isinstance(대상, 한랭인스턴스):
                대상.필드들[node.대상.속성] = 값
            else:
                raise 런타임에러("속성에 값을 할당할 수 없습니다")
        else:
            raise 런타임에러("잘못된 대입 대상")

        return 값

    def execute_함수선언(self, node: 함수선언, env: Environment) -> None:
        함수 = 한랭함수(node, env)
        env.define(node.이름, 함수)

    def execute_함수호출(self, node: 함수호출, env: Environment) -> Any:
        함수 = self.execute(node.함수, env)
        인자들 = [self.execute(인자, env) for 인자 in node.인자들]

        if callable(함수) and not isinstance(함수, (한랭함수, 한랭람다)):
            # 내장 함수
            try:
                return 함수(*인자들)
            except Exception as e:
                raise 런타임에러(f"내장 함수 실행 오류: {e}")

        if isinstance(함수, 한랭람다):
            if len(인자들) != len(함수.매개변수들):
                raise 런타임에러(
                    f"람다 함수는 {len(함수.매개변수들)}개의 인자가 필요하지만 "
                    f"{len(인자들)}개가 전달되었습니다"
                )

            람다_env = Environment(함수.클로저)
            for 이름, 값 in zip(함수.매개변수들, 인자들):
                람다_env.define(이름, 값)

            return self.execute(함수.본문, 람다_env)

        if isinstance(함수, 한랭함수):
            if len(인자들) != len(함수.선언.매개변수들):
                raise 런타임에러(
                    f"함수 '{함수.선언.이름}'은(는) {len(함수.선언.매개변수들)}개의 "
                    f"인자가 필요하지만 {len(인자들)}개가 전달되었습니다"
                )

            함수_env = Environment(함수.클로저)
            for 이름, 값 in zip(함수.선언.매개변수들, 인자들):
                함수_env.define(이름, 값)

            try:
                for 문장 in 함수.선언.본문:
                    self.execute(문장, 함수_env)
            except 반환예외 as e:
                return e.값

            return None

        if isinstance(함수, 한랭클래스):
            인스턴스 = 한랭인스턴스(함수)
            # 생성자 호출
            if '생성' in 함수.메서드들:
                생성자 = 함수.메서드들['생성']
                함수_env = Environment(생성자.클로저)
                함수_env.define('나', 인스턴스)
                for 이름, 값 in zip(생성자.선언.매개변수들, 인자들):
                    함수_env.define(이름, 값)
                try:
                    for 문장 in 생성자.선언.본문:
                        self.execute(문장, 함수_env)
                except 반환예외:
                    pass
            return 인스턴스

        raise 런타임에러(f"호출할 수 없는 객체: {함수}")

    def execute_반환문(self, node: 반환문, env: Environment):
        값 = None
        if node.값:
            값 = self.execute(node.값, env)
        raise 반환예외(값)

    def execute_조건문(self, node: 조건문, env: Environment) -> Any:
        조건 = self.execute(node.조건, env)

        if 조건:
            for 문장 in node.참블록:
                self.execute(문장, env)
        elif node.거짓블록:
            for 문장 in node.거짓블록:
                self.execute(문장, env)

    def execute_반복문(self, node: 반복문, env: Environment) -> Any:
        시작 = int(self.execute(node.시작, env))
        끝 = int(self.execute(node.끝, env))

        반복_env = Environment(env)

        for i in range(시작, 끝 + 1):
            반복_env.define(node.변수, i)
            try:
                for 문장 in node.본문:
                    self.execute(문장, 반복_env)
            except 중단예외:
                break
            except 계속예외:
                continue

    def execute_동안문(self, node: 동안문, env: Environment) -> Any:
        while self.execute(node.조건, env):
            try:
                for 문장 in node.본문:
                    self.execute(문장, env)
            except 중단예외:
                break
            except 계속예외:
                continue

    def execute_중단문(self, node: 중단문, env: Environment):
        raise 중단예외()

    def execute_계속문(self, node: 계속문, env: Environment):
        raise 계속예외()

    def execute_출력문(self, node: 출력문, env: Environment) -> None:
        값들 = [self.execute(값, env) for 값 in node.값들]
        출력문자열 = ' '.join(str(v) for v in 값들)
        self.output_buffer.append(출력문자열)
        self.output_callback(출력문자열)

    def execute_입력문(self, node: 입력문, env: Environment) -> str:
        프롬프트 = ""
        if node.프롬프트:
            프롬프트 = str(self.execute(node.프롬프트, env))
        return self.input_callback(프롬프트)

    def execute_인덱스접근(self, node: 인덱스접근, env: Environment) -> Any:
        대상 = self.execute(node.대상, env)
        인덱스 = self.execute(node.인덱스, env)

        try:
            if isinstance(대상, dict):
                return 대상[인덱스]  # 딕셔너리는 키를 그대로 사용
            return 대상[int(인덱스)]  # 리스트/문자열은 정수 인덱스
        except (IndexError, KeyError, TypeError) as e:
            raise 런타임에러(f"인덱스 오류: {e}")

    def execute_속성접근(self, node: 속성접근, env: Environment) -> Any:
        대상 = self.execute(node.대상, env)

        if isinstance(대상, 한랭인스턴스):
            if node.속성 in 대상.필드들:
                return 대상.필드들[node.속성]
            if node.속성 in 대상.클래스.메서드들:
                # 바인딩된 메서드 반환
                메서드 = 대상.클래스.메서드들[node.속성]
                return lambda *args: self._call_method(대상, 메서드, args)
            raise 런타임에러(f"'{대상.클래스.이름}'에 '{node.속성}' 속성이 없습니다")

        # 문자열, 리스트 등의 내장 속성
        if hasattr(대상, node.속성):
            return getattr(대상, node.속성)

        raise 런타임에러(f"'{type(대상).__name__}'에 '{node.속성}' 속성이 없습니다")

    def _call_method(self, 인스턴스: 한랭인스턴스, 메서드: 한랭함수, 인자들: tuple) -> Any:
        함수_env = Environment(메서드.클로저)
        함수_env.define('나', 인스턴스)

        for 이름, 값 in zip(메서드.선언.매개변수들, 인자들):
            함수_env.define(이름, 값)

        try:
            for 문장 in 메서드.선언.본문:
                self.execute(문장, 함수_env)
        except 반환예외 as e:
            return e.값

        return None

    def execute_클래스선언(self, node: 클래스선언, env: Environment) -> None:
        메서드들 = {}

        for 문장 in node.본문:
            if isinstance(문장, 함수선언):
                메서드들[문장.이름] = 한랭함수(문장, env)

        클래스 = 한랭클래스(node.이름, 메서드들)
        env.define(node.이름, 클래스)

    def execute_시도문(self, node: 시도문, env: Environment) -> Any:
        try:
            for 문장 in node.시도블록:
                self.execute(문장, env)
        except 사용자예외 as e:
            if node.잡기블록:
                잡기_env = Environment(env)
                if node.잡기변수:
                    잡기_env.define(node.잡기변수, e.값)
                for 문장 in node.잡기블록:
                    self.execute(문장, 잡기_env)
        except 런타임에러 as e:
            if node.잡기블록:
                잡기_env = Environment(env)
                if node.잡기변수:
                    잡기_env.define(node.잡기변수, str(e))
                for 문장 in node.잡기블록:
                    self.execute(문장, 잡기_env)
        finally:
            if node.마침내블록:
                for 문장 in node.마침내블록:
                    self.execute(문장, env)

    def execute_던지기문(self, node: 던지기문, env: Environment):
        값 = self.execute(node.값, env)
        raise 사용자예외(값)

    def execute_삼항연산(self, node: 삼항연산, env: Environment) -> Any:
        조건 = self.execute(node.조건, env)
        if 조건:
            return self.execute(node.참값, env)
        else:
            return self.execute(node.거짓값, env)

    def execute_람다식(self, node: 람다식, env: Environment) -> 한랭람다:
        return 한랭람다(node, env)


if __name__ == "__main__":
    code = '''
# 한랭 프로그래밍 언어 테스트

변수 이름 = "한준후"
변수 나이 = 25

출력("=== 한랭 언어 테스트 ===")
출력("이름:", 이름)
출력("나이:", 나이)

# 함수 정의
함수 더하기(a, b) {
    반환 a + b
}

함수 팩토리얼(n) {
    만약 n <= 1 {
        반환 1
    }
    반환 n * 팩토리얼(n - 1)
}

출력("3 + 5 =", 더하기(3, 5))
출력("5! =", 팩토리얼(5))

# 조건문
만약 나이 >= 20 {
    출력("성인입니다")
} 아니면 {
    출력("미성년자입니다")
}

# 반복문
출력("1부터 5까지:")
반복 i = 1 : 5 {
    출력(i)
}

# 리스트
변수 숫자들 = [1, 2, 3, 4, 5]
출력("리스트:", 숫자들)
출력("리스트 길이:", 길이(숫자들))
출력("리스트 합계:", 합계(숫자들))

# 클래스
클래스 사람 {
    함수 생성(이름, 나이) {
        나.이름 = 이름
        나.나이 = 나이
    }

    함수 소개() {
        출력("안녕하세요, 저는", 나.이름, "이고", 나.나이, "살입니다.")
    }
}

변수 철수 = 사람("김철수", 30)
철수.소개()
'''
    interpreter = HanlangInterpreter()
    interpreter.run(code)
