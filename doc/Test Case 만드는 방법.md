# Test Case 만드는 방법

> `tests/` 아래 실제로 작성된 13개 파일·36개 테스트 케이스를 근거로, 이 프로젝트에서 새 테스트를 작성할 때 따라야 할 패턴을 유형별로 정리한 문서입니다. 각 절의 예시 코드는 실제 `tests/`에 있는 코드를 그대로 가져오거나 그 패턴을 그대로 재현한 것입니다. 전체 테스트 목록/개수는 `README.md`의 "6. 테스트 스위트" 절을 참고하세요.

## 0. 이 프로젝트 테스트의 기본 원칙

1. **`unittest.mock`을 쓰지 않고, 손으로 만든 "Fake" 클래스를 쓴다.** 필요한 메서드 몇 개만 최소한으로 구현한 클래스를 그때그때 만들어서 진짜 `Repository`/`Logic` 자리에 끼워 넣습니다(덕 타이핑). `Mock()`/`patch()`보다 코드가 더 명시적이고, 무엇을 호출했는지(`self.calls.append(...)`) 직접 기록해 검증하기 쉽습니다.
2. **실제 Oracle DB, 실제 FastAPI 서버, 실제 svcs 컨테이너를 쓰지 않는다.** `Session`이 꼭 필요하면 `sqlite:///:memory:`(메모리 SQLite)로 대체하고, 라우트를 테스트해야 하면 앱 전체(`app.app`)가 아니라 **그 테스트에 필요한 라우터/엔드포인트만 담은 작고 독립적인 `FastAPI()` 인스턴스**를 그 자리에서 새로 만듭니다. 그래서 테스트 36개 전체가 1초 이내에 끝납니다.
3. **파일명은 `test_*.py`, 함수명은 `test_*`**로 시작해야 `pytest`가 자동으로 찾습니다(자세한 수집 규칙은 README 6절 참고).
4. **함수명만 읽어도 무엇을 검증하는지 알 수 있게** 짓습니다. 예: `test_register_dept_rejects_duplicate_name`, `test_delete_dept_returns_false_when_entity_does_not_exist`.

---

## 1. 유형별 작성 가이드

### 1-1. Domain Logic 단위 테스트 — Fake Repository로 비즈니스 규칙만 검증

**언제 쓰는가**: `UserLogic`/`DeptLogic`처럼 `domain/*/xxx_logic.py`의 메서드 하나를 검증하고 싶을 때. Repository를 진짜로 만들지 않고, 필요한 메서드만 흉내 낸 Fake로 대체합니다.

**만드는 순서**
1. 대상 Logic이 의존하는 Repository의 메서드 중, 이 테스트에서 실제로 호출될 메서드만 골라 Fake 클래스에 구현한다.
2. Fake 생성자에서 "미리 존재하는 데이터"를 받아두고, 조회 메서드는 그 데이터를 기준으로 응답한다.
3. Fake에 `self.created_dept = None` 같은 필드를 두고, 쓰기 메서드가 호출되면 그 값을 기록한다 — 이후 `assert`로 "정말 호출됐는지·어떤 값으로 호출됐는지"를 검증한다.
4. `Logic(FakeRepository())`로 조립해서 메서드를 직접 호출한다.

**실제 예시** (`tests/test_dept_logic.py`):

```python
import pytest
from domain.dept.dept_dto import DeptCreate
from domain.dept.dept_entity import Dept
from domain.dept.dept_logic import DeptLogic
from shared.models.exception import DeptAlreadyExistsException


class FakeDeptRepository:
  def __init__(self, existing_dept: Dept | None = None):
    self.existing_dept = existing_dept
    self.created_dept = None          # 호출 여부/내용을 기록할 자리

  def get_dept_by_name(self, name: str) -> Dept | None:
    if self.existing_dept and self.existing_dept.name == name:
      return self.existing_dept
    return None

  def create_dept(self, dept: Dept) -> Dept:
    self.created_dept = dept          # 실제로 무엇으로 호출됐는지 기록
    return dept


def test_register_dept_converts_create_dto_to_entity():
  repository = FakeDeptRepository()
  logic = DeptLogic(repository)

  result = logic.register_dept(DeptCreate(name="Platform", desc="Core team"))

  assert isinstance(repository.created_dept, Dept)   # DTO가 Entity로 변환됐는지
  assert repository.created_dept.name == "Platform"
  assert result is repository.created_dept


def test_register_dept_rejects_duplicate_name():
  existing_dept = Dept(name="Platform")
  repository = FakeDeptRepository(existing_dept)
  logic = DeptLogic(repository)

  with pytest.raises(DeptAlreadyExistsException):     # 중복 이름이면 예외가 나야 함
    logic.register_dept(DeptCreate(name="Platform"))

  assert repository.created_dept is None              # 실패했으니 생성 시도 자체가 없어야 함
```

---

### 1-2. Feature Flow 단위 테스트 — Fake Logic으로 오케스트레이션만 검증

**언제 쓰는가**: `SignupFlow`/`OrganizationFlow`처럼 `feature/*/xxx_flow.py`가 여러 Logic을 조합하는 로직(오케스트레이션)을 검증하고 싶을 때. 이번엔 Repository가 아니라 **Logic 자체를 Fake로 대체**합니다.

**핵심 포인트**: Flow 생성자가 요구하는 타입(`UserLogic`, `DeptLogic`)을 실제로 상속할 필요는 없습니다 — 파이썬은 덕 타이핑이라 필요한 메서드만 구현하면 그대로 끼워집니다. `db: Session`이 필요한 자리는 `sqlite:///:memory:`로 채워 넣습니다.

**실제 예시** (`tests/test_change_users_dept_flow.py`):

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from domain.dept.dept_entity import Dept
from domain.user.user_entity import User
from feature.organization.organization_flow import OrganizationFlow
from shared.models import IdNameValues
from shared.models.exception import UpdateValueException


class FakeUserLogic:
  def __init__(self, user: User, db: Session):
    self.user = user
    self.db = db
    self.change_calls = []                       # 호출 기록용

  def retrieve_user_by_id(self, user_id: str) -> User | None:
    return self.user if user_id == "user-001" else None

  def change_user_dept(self, user: User, new_dept_id: str) -> bool:
    self.change_calls.append((user, new_dept_id))
    return True


class FakeDeptLogic:
  def __init__(self, dept: Dept, db: Session):
    self.dept = dept
    self.db = db

  def retrieve_dept_by_id(self, dept_id: str) -> Dept | None:
    return self.dept if dept_id == "dept-002" else None


def build_flow():
  db = Session(bind=create_engine("sqlite:///:memory:"))   # 진짜 DB 대신 메모리 SQLite
  user = User(email="user@example.com", name="User", password="x", dept_id="dept-001")
  dept = Dept(name="New Department")
  return OrganizationFlow(FakeUserLogic(user, db), FakeDeptLogic(dept, db)), db


def test_change_users_dept_extracts_dept_id_from_id_name_values():
  flow, db = build_flow()

  result = flow.change_users_dept([IdNameValues.of("user-001", {"dept_id": "dept-002"})])

  assert result == [True]
  db.close()                                     # 테스트 끝나면 세션 정리


def test_change_users_dept_rejects_non_dept_id_properties():
  flow, db = build_flow()

  with pytest.raises(UpdateValueException):        # dept_id가 아닌 다른 필드는 이 API로 못 바꿈
    flow.change_users_dept([IdNameValues.of("user-001", {"name": "Changed User"})])

  db.close()
```

---

### 1-3. DTO 검증 테스트 — Pydantic 모델을 직접 생성해 검증

**언제 쓰는가**: `UserUpdate`/`DeptUpdate`처럼 요청 DTO의 필드 검증(`@field_validator`, Mixin 등)이 의도대로 동작하는지 확인하고 싶을 때. FastAPI도, DB도 전혀 필요 없이 **Pydantic 모델을 바로 인스턴스화**합니다.

**실제 예시** (`tests/test_update_dto_validation.py`):

```python
import pytest
from domain.dept.dept_dto import DeptUpdate
from domain.user.user_dto import UserUpdate
from shared.models.exception import UpdateValueException


@pytest.mark.parametrize("update_type", [UserUpdate, DeptUpdate])
def test_update_dto_requires_at_least_one_value(update_type):
  with pytest.raises(UpdateValueException):
    update_type()                      # 필드를 하나도 안 주면 예외가 나야 함(AtLeastOneValueMixin)


def test_update_dto_accepts_one_value():
  assert UserUpdate(name="User").name == "User"     # 값 하나만 줘도 정상 생성
```

---

### 1-4. 예외 계약(Contract) 테스트 — 예외 클래스 자체의 시그니처/상태코드 검증

**언제 쓰는가**: `shared/models/exception.py`의 커스텀 예외가 올바른 `status_code`/`detail`을 갖는지 확인할 때. `@pytest.mark.parametrize`로 여러 예외 타입을 한 함수에서 반복 검증하면 코드 중복이 줄어듭니다.

**실제 예시** (`tests/test_exception_contract.py`):

```python
import pytest
from shared.models.exception import DeptNotFoundException, UserNotFoundException


@pytest.mark.parametrize(
  ("exception_type", "identifier", "status_code", "detail"),
  [
    (UserNotFoundException, "user-id", 404, "user-id"),
    (DeptNotFoundException, "dept-id", 404, "dept-id"),
  ],
)
def test_not_found_exception_accepts_identifier(exception_type, identifier, status_code, detail):
  exception = exception_type(identifier)

  assert exception.status_code == status_code
  assert detail in exception.detail
```

이 함수 하나는 실제로 `test_not_found_exception_accepts_identifier[UserNotFoundException-user-id-404-user-id]`, `[DeptNotFoundException-...]` **2개의 독립된 테스트 케이스**로 실행됩니다.

---

### 1-5. 트랜잭션 데코레이터 적용 여부 테스트 — 실행하지 않고 "적용됐는지"만 확인

**언제 쓰는가**: `@transactional`이 특정 메서드에 실제로 붙어있는지 검증하고 싶을 때. 트랜잭션을 실제로 굴리지 않고도, `functools.wraps`가 원본 함수를 `__wrapped__` 속성에 보존해두는 성질을 이용해 **데코레이터 적용 여부만 정적으로 확인**합니다.

**실제 예시** (`tests/test_transaction_boundaries.py`):

```python
from domain.dept.dept_logic import DeptLogic

def test_dept_mutating_logic_methods_are_transactional():
  assert hasattr(DeptLogic.register_dept, "__wrapped__")
  assert hasattr(DeptLogic.modify_dept, "__wrapped__")
  assert hasattr(DeptLogic.remove_dept, "__wrapped__")
```

같은 파일에서 `app.config.transaction._extract_session`처럼 데코레이터 **내부** 헬퍼 함수를 직접 import해서 단위 테스트하기도 합니다 — 이렇게 해도 되는 이유는, 이 프로젝트가 "Repository는 자기 도메인 밖에서 import 금지"라는 캡슐화 규칙만 지키면 되고, 트랜잭션 내부 구현 자체를 테스트하는 건 그 규칙과 무관하기 때문입니다.

---

### 1-6. Export/캡슐화 계약 테스트 — "어디서 import 가능해야 하는가"를 코드로 강제

**언제 쓰는가**: `shared/models/__init__.py`, `shared/utils/__init__.py`처럼 "이 이름은 여기서 export되어야 하고, 저기서는 안 되어야 한다"는 아키텍처 규칙을 리팩토링 중 실수로 깨뜨리지 않게 막고 싶을 때.

**실제 예시** (`tests/test_exception_exports.py`):

```python
import shared.models
import shared.utils
from shared.models import UserNotFoundException


def test_exceptions_are_publicly_exported_from_shared_models():
  assert shared.models.UserNotFoundException is UserNotFoundException

def test_exceptions_are_not_reexported_from_shared_utils():
  assert not hasattr(shared.utils, "UserNotFoundException")   # utils에는 없어야 정상
```

---

### 1-7. 라우트(API) 계약 테스트 — 그 테스트만을 위한 "작은" FastAPI 앱

**언제 쓰는가**: 실제 HTTP 요청이 라우터의 `response_model`/상태 코드로 올바르게 직렬화되는지 확인하고 싶을 때. **주의**: `app.app`(진짜 앱, svcs 부트스트랩 + 실제 DB 필요)을 통째로 띄우지 않습니다. 대신 그 테스트에 필요한 라우터/엔드포인트만 담은 **일회용 `FastAPI()` 인스턴스**를 그 자리에서 만들고, DI는 Fake를 직접 클로저로 주입합니다.

**실제 예시** (`tests/test_delete_api.py`):

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from domain.dept.dept_logic import DeptLogic


class FakeDeptRepository:
  def delete_dept(self, dept_id: str) -> bool:
    return dept_id != "missing-dept"


app = FastAPI()                              # 진짜 app.app이 아니라 이 테스트 전용 앱
dept_logic = DeptLogic(FakeDeptRepository())  # svcs 없이 그냥 직접 조립

@app.post("/organization/delete_depts", response_model=list[bool])
def delete_depts(dept_ids: list[str]):
  return [dept_logic.remove_dept(dept_id) for dept_id in dept_ids]

client = TestClient(app)

def test_delete_depts_returns_boolean_results():
  response = client.post("/organization/delete_depts", json=["dept-id", "missing-dept"])

  assert response.status_code == 200
  assert response.json() == [True, False]
```

실제 라우터 파일(`route/organization/organization_flow_route.py`)을 그대로 `include_router`해서 **요청 스키마 검증만** 확인하고 싶을 때는 `tests/test_change_users_dept_api.py`처럼 라우터는 실제 걸 가져오되, DI 조회(`services.get(...)`)까지는 건드리지 않고 Pydantic 모델 파싱 결과만 검증하는 방식도 씁니다.

---

## 2. 공통 패턴 모음

| 상황 | 이렇게 한다 |
| :--- | :--- |
| `db: Session`이 타입상 꼭 필요함 | `Session(bind=create_engine("sqlite:///:memory:"))`, 테스트 끝에 `db.close()` |
| Repository/Logic을 대체해야 함 | `unittest.mock` 대신 필요한 메서드만 구현한 `FakeXxx` 클래스 작성 |
| "몇 번, 무엇으로 호출됐는지" 검증 | Fake 안에 `self.xxx_calls = []`를 두고 호출마다 `append` |
| 예외가 발생해야 함을 검증 | `with pytest.raises(SomeException):` |
| 같은 검증을 여러 입력에 반복 | `@pytest.mark.parametrize("param", [값1, 값2])` |
| HTTP 계층까지 검증하고 싶음 | 실제 `app.app`이 아니라 테스트 전용 `FastAPI()` + `TestClient` |
| SQLAlchemy 쿼리 체인을 흉내 내야 함 | `order_by`/`filter`/`offset`/`limit`/`all` 등 실제 쓰이는 메서드만 구현한 Fake Query 클래스 (`tests/test_pagination_helper.py`의 `FakeQuery` 참고) |

---

## 3. 새 테스트 작성 체크리스트

1. **무엇을 검증할지 한 문장으로 먼저 정한다** → 그 문장이 곧 함수 이름이 된다(`test_<대상>_<기대동작>`).
2. **테스트 대상이 어느 계층인지 정한다** → 1절의 표에서 맞는 유형을 고른다(Logic 단위? Flow 단위? DTO? 예외? 라우트?).
3. **의존 대상 중 이 테스트에 필요한 메서드만 Fake로 만든다** → 안 쓰는 메서드까지 구현하지 않는다(과剩 구현 금지).
4. **`Session`이 필요하면 `sqlite:///:memory:`로, HTTP가 필요하면 전용 `FastAPI()`로** → 절대 실제 Oracle/실제 앱을 띄우지 않는다.
5. **`assert`는 "결과값"과 "부수효과(Fake에 기록된 호출 내역)" 둘 다 확인한다** — 반환값만 보고 내부적으로 아무 일도 안 했는지는 놓치기 쉽다.
6. **테스트 끝에서 `db.close()`로 정리한다**(메모리 SQLite를 썼다면).
7. **파일을 `tests/test_<주제>.py`로 저장**하면 별도 등록 없이 `uv run pytest`가 자동으로 찾는다.

---

## 4. 실행 명령어 모음

```bash
uv run pytest                              # 전체 실행
uv run pytest tests/test_dept_logic.py     # 파일 하나만
uv run pytest -k "duplicate_name"          # 함수명에 특정 키워드가 들어간 것만
uv run pytest --collect-only -q            # 실행 없이, 수집되는 테스트 목록만 확인
uv run pytest -v                           # 각 테스트 이름을 한 줄씩 자세히 출력
```
