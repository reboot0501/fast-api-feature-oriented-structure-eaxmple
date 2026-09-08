# 프로젝트 각 폴더에 `__init__.py` 파일을 생성하는 이유

Python 프로젝트(특히 FastAPI, SQLAlchemy 등을 활용한 웹 애플리케이션)를 구성할 때 각 패키지/모듈 폴더마다 `__init__.py`를 생성해야 하는지에 대한 기술적 배경과 실무 권장 사항을 정리한 문서입니다.

---

## 1. 결론 요약

* **기술적 관점**: **필수가 아닙니다.** (Python 3.3 이후)
* **실무 표준 관점**: **생성하는 것을 강력히 권장합니다 (Best Practice).**

---

## 2. 기술적 배경: 암시적 네임스페이스 패키지 (PEP 420)

Python 3.3 이전에는 디렉터리 안에 `__init__.py` 파일이 반드시 있어야만 Python 인터프리터가 해당 디렉터리를 패키지(Package)로 인식하여 `import`할 수 있었습니다.

하지만 Python 3.3부터 **[PEP 420 (Implicit Namespace Packages)](https://peps.python.org/pep-0420/)**가 도입되면서, `__init__.py` 파일이 없어도 디렉터리 내의 모듈을 정상적으로 import할 수 있게 되었습니다.

```python
# __init__.py가 없어도 문법적으로는 동작 가능
from app.core.config import settings
```

---

## 3. 실무에서 `__init__.py` 생성을 권장하는 핵심 이유

문법적으로 동작함에도 불구하고 대다수의 오픈소스 및 엔터프라이즈 환경에서 `__init__.py`를 명시적으로 생성하는 이유는 다음과 같습니다.

### 1) IDE 및 정적 분석 도구의 안정적인 지원
* **대상 도구**: VS Code (Pylance), PyCharm, `mypy`, `pyright`, `ruff` 등
* `__init__.py`가 없는 폴더는 도구에 따라 일반 패키지가 아닌 네임스페이스 패키지로 분류되어, 다음과 같은 문제가 발생할 수 있습니다.
  * 모듈 자동 완성(IntelliSense) 누락 또는 지연
  * 모듈 경로를 제대로 해석하지 못해 잘못된 타입 경고(Unresolved import) 발생

### 2) 테스트 러너(`pytest`)의 모듈 탐색 오류 방지
* `pytest`는 테스트를 실행할 때 프로젝트의 루트 디렉터리와 패키지 구조를 스캔합니다.
* `__init__.py`가 누락된 경우 `rootdir` 계산 방식의 차이나 동일한 이름을 가진 테스트 파일/모듈 간의 이름 충돌로 인해 `ModuleNotFoundError` 또는 중복 import 오류가 발생하기 쉽습니다.

### 3) 패키지 공개 인터페이스(Public API / Re-export) 관리
* `__init__.py`를 활용하면 외부로 노출할 핵심 객체(Router, Service, Schema 등)를 재익스포트(re-export)하여 import 경로를 깔끔하게 단축할 수 있습니다.

```python
# app/features/users/__init__.py
from .routes import router as users_router
from .models import User

__all__ = ["users_router", "User"]
```

```python
# 외부 사용처 (main.py 등)
# 지저분한 세부 경로 대신 패키지 단위로 import 가능
from app.features.users import users_router
```

### 4) 일반 패키지(Regular Package)로서의 명확한 의도 표현
* 해당 폴더가 단순 정적 리소스나 문서 모음이 아니라, **런타임에 실행되는 Python 패키지 단위**임을 팀원과 도구에 명확하게 전달합니다.

### 5) 프레임워크 및 ORM/마이그레이션 도구 호환성
* **SQLAlchemy & Alembic**: 모델 클래스를 자동 감지하거나 마이그레이션 메타데이터를 수집할 때 패키지 단위의 명시적인 import 구조가 유지되어야 순환 참조나 누락 문제를 방지할 수 있습니다.

---

## 4. 실무 적용 가이드

1. **소스 코드 하위 폴더에는 항상 생성**:
   * 소스 코드가 포함되는 모든 디렉터리(`app/`, `app/core/`, `app/features/`, `app/features/users/` 등)에는 기본적으로 `__init__.py`를 생성합니다.
2. **내용은 비워두어도 무방**:
   * 특별한 re-export나 초기화 로직이 필요하지 않다면 **0바이트 빈 파일**로 두어도 충분합니다.
3. **불필요한 초기화 로직 지양**:
   * `__init__.py` 내부에서 무거운 DB 커넥션 생성이나 복잡한 비즈니스 로직을 실행하면 순환 참조(Circular Import)가 발생할 수 있으므로, 단순 심볼 노출(`__all__`)이나 문서화(docstring) 용도로만 제한하는 것이 안전합니다.
