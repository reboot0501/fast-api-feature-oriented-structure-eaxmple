# 서브 도메인의 `__init__.py`를 통한 간편한 Import 및 Repository 캡슐화

Feature-Oriented / DDD 아키텍처에서 **최상위 `domain/__init__.py`는 비워두고, 각 서브 도메인 단위(`domain/user/__init__.py`)에서 Re-export를 제공**하여 도메인 경계(Bounded Context)를 보존하고, **내부 구현 세부 사항인 Repository를 캡슐화**하는 설계 원칙을 정리한 문서입니다.

---

## 1. 최상위 `domain/__init__.py`를 비워두는 이유

초기 설계 시 최상위 `domain/__init__.py`에 모든 도메인의 클래스를 모아두고 싶은 유혹이 들 수 있습니다. 하지만 이는 다음과 같은 치명적인 문제를 야기합니다.

### 왜 최상위 `domain/__init__.py`는 빈 파일이어야 하는가?
1. **도메인 경계(Bounded Context) 오염**:
   * 각 도메인(`user`, `dept`, `order`, `product` 등)은 독립적인 비즈니스 경계를 가져야 합니다. 이를 한곳에 섞어버리면 도메인 간의 독립성이 훼손됩니다.
2. **이름 충돌(Name Collision)**:
   * 여러 도메인에서 흔히 사용하는 이름(예: `CreateRequest`, `UpdateDTO`, `Status`, `Item` 등)이 겹칠 때 최상위 네임스페이스에서 충돌이 일어납니다.
3. **거대 모듈(God Module) 및 순환 참조(Circular Import)**:
   * 도메인이 10개, 20개로 증가할수록 최상위 `__init__.py`가 지나치게 거대해지고, 도메인 간 상호 참조 시 순환 참조 에러가 발생하기 쉽습니다.

👉 따라서 **최상위 `domain/__init__.py`는 패키지 인식용 빈 파일(`""`)로 유지**합니다.

---

## 2. 서브 도메인 단위(`domain/user/__init__.py`)의 Re-export

개별 서브 도메인 디렉토리 내부에서만 Re-export를 제공하여 **외부 계층(Feature Layer, Router 등)이 깔끔한 경로로 접근**하도록 지원합니다.

### 1) Before (개별 내부 파일 직접 참조 - 의존성 높음)
```python
from domain.user.user_entity import User
from domain.user.user_dto import UserCreate, UserResponse
from domain.user.user_logic import UserLogic
```

### 2) After (도메인 패키지 단위 import - 권장)
```python
# ✅ 도메인 경계가 명확하고 한 줄로 직관적인 import
from domain.user import User, UserLogic, UserCreate, UserResponse
```

---

## 3. 왜 `UserRepository`는 외부 노출에서 제외하는가? (핵심 설계)

[domain/user/__init__.py](file:///d:/project-workspace/fast-api-feature-oriented-structure-eaxmple/domain/user/__init__.py)의 노출 목록(`__all__`)을 보면 **`UserRepository`가 의도적으로 제외**되어 있습니다.

```python
# domain/user/__init__.py
from domain.user.user_entity import User
from domain.user.user_dto import UserCreate, UserUpdate, UserResponse
from domain.user.user_logic import UserLogic

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogic",  # 👈 Repository는 제외됨!
]
```

### 1) 정보 은닉과 캡슐화 (Information Hiding)
* **Repository**는 데이터베이스와의 직접적인 SQL 쿼리 생성, `flush` 등을 수행하는 **하위 데이터 접근 계층(Data Access Layer)**입니다.
* 외부 계층(Feature Layer)이 Repository를 직접 다루게 되면, **도메인 비즈니스 규칙(유효성 검증, 상태 전이 등)을 우회하여 DB 데이터를 조작하는 안티 패턴**이 발생합니다.

### 2) 단일 창구 원칙 (Single Entry Point)
* 외부 계층은 항상 **`UserLogic`을 통해서만 도메인과 상호작용**해야 합니다.
* `UserLogic` 내부에서 필요한 Repository 조작과 `@transactional` 제어를 전담함으로써 도메인의 일관성과 무결성이 보장됩니다.

```
[외부 Feature / Service Layer]
             │
             ▼ (오직 Logic / Entity / DTO 만 접근 허용)
        [UserLogic]  ──> 비즈니스 규칙 검증 및 트랜잭션 관리
             │
             ▼ (도메인 내부에서만 은밀하게 캡슐화)
     [UserRepository] ──> DB 쿼리 생성 및 flush
```

---

## 4. Feature Layer에서의 실전 활용 및 Caller-Callee 트랜잭션 유지 메커니즘

서브 도메인에서 선별적으로 Re-export된 요소들은 **Feature Layer(예: `feature/user/user_service.py`)**에서 비즈니스 유스케이스를 구현할 때 다음과 같이 사용됩니다.  
특히 여러 도메인이 얽히는 유스케이스에서 **Caller(Feature Service)의 트랜잭션을 Callee(Domain Logic)가 승계받아 원자성(ACID)을 유지하는 메커니즘**이 핵심입니다.

### 1) Feature Service 구현 예시 (`feature/user/user_service.py`)

```python
# feature/user/user_service.py

# ✅ 각 도메인의 __init__.py 덕분에 단 한 줄로 깔끔하게 import!
from domain.user import User, UserLogic, UserCreate, UserResponse
from domain.dept import DeptLogic
from app.config.transaction import transactional
from shared.utils.exception import DeptNotFoundException


class UserService:
    """
    Feature Layer: 비즈니스 유스케이스 조율 (Orchestration)
    - Domain의 내부 DB 조작(Repository)을 직접 알 필요 없이 Logic과 DTO만 다룹니다.
    """
    def __init__(self, user_logic: UserLogic, dept_logic: DeptLogic):
        self.user_logic = user_logic
        self.dept_logic = dept_logic

    @transactional  # 👈 [Caller] 트랜잭션 경계의 시작점 (Root Transaction)
    def register_user_with_dept_check(self, dto: UserCreate) -> str:
        """
        [유스케이스] 소속 부서 존재 여부를 검증하고 사용자를 등록하는 회원가입
        """
        # 1. Dept 도메인 확인 (부서가 없으면 404 예외 발생)
        dept = self.dept_logic.retrieve_dept_by_id(dto.dept_id)
        if not dept:
            raise DeptNotFoundException(dto.dept_id)

        # 2. User 도메인 호출 -> [Callee] UserLogic의 @transactional 로직 실행
        #    Caller의 기존 활성 트랜잭션에 그대로 참여(조기 커밋 방지)
        new_user: User = self.user_logic.register_user(dto)

        return UserResponse.model_validate(new_user)
```

---

### 2) Caller - Callee 간 트랜잭션 유지 메커니즘

`@transactional`은 `ContextVar` 기반의 깊이(`depth`) 추적을 통해 **상위 호출자(Caller)의 트랜잭션을 하위 피호출자(Callee)가 자연스럽게 승계**하도록 동작합니다.

```text
[Caller (Feature Layer)] 
  UserService.register_user_with_dept_check()
  ├── depth: 0 -> 1 (is_root = True) ──> 최상위 트랜잭션 시작
  │
  ├── 1) dept_logic.retrieve_dept_by_id() (조회)
  │
  ├── 2) user_logic.register_user() ──> [Callee (Domain Layer)]
  │        ├── depth: 1 -> 2 (is_root = False) ──> 기존 트랜잭션 승계(참여)
  │        ├── repo.create_user() 실행 (flush 수행, ID 확정)
  │        └── [Callee 정상 종료] is_root=False 이므로 커밋 보류! (Caller 트랜잭션 유지)
  │
  ├── 3) 후속 비즈니스 작업 수행...
  │
[Caller 정상 종료]
  └── is_root = True 이므로 비로소 전체 작업에 대해 최종 db.commit() 1회 실행!
```

#### ① 조기 커밋 방지 (Deferred Commit & Propagation)
- 하위 도메인인 `UserLogic.register_user`에도 `@transactional`이 선언되어 있습니다.
- 하지만 이미 Caller(`UserService`)에서 트랜잭션이 시작되었으므로(`depth > 0`), Callee는 자신이 중첩 트랜잭션(`is_root = False`)임을 인지합니다.
- 따라서 `UserLogic`이 끝나는 시점에 **조기 `commit()`을 실행하지 않고, 데이터 상태(`flush`)를 Caller의 트랜잭션 컨텍스트에 그대로 유지**합니다.

#### ② 전체 원자적 롤백 (Atomic Rollback)
- 만약 `UserLogic` 실행이 정상적으로 끝난 뒤, Caller의 다음 단계(예: 환영 이메일 큐 등록, 부서 테이블 카운트 갱신 등)에서 에러가 발생하면:
- Root인 Caller 레벨의 예외 처리기에서 `db.rollback()`을 호출하여 **Callee(`UserLogic`)가 수행했던 유저 생성 작업까지 모두 취소**됩니다.

#### ③ 최종 1회 커밋 (Single Root Commit)
- 모든 하위 도메인의 작업이 완전히 성공하고 최상위 Caller(`is_root = True`)가 리턴될 때, **단 1회의 `db.commit()`으로 DB에 영구 반영**됩니다.

---

### 3) FastAPI Router에서의 의존성 주입(DI) 조립

FastAPI의 엔드포인트에서는 `Depends`를 통해 도메인 객체들을 조립하여 Feature Service에 주입합니다.

```python
# feature/user/user_router.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db

from domain.user import UserCreate, UserResponse, UserLogic
from domain.user.user_repository import UserRepository
from domain.dept import DeptLogic
from domain.dept.dept_repository import DeptRepository
from .user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    # 동일한 DB 세션(db)을 공유하며 도메인 조립
    user_logic = UserLogic(UserRepository(db))
    dept_logic = DeptLogic(DeptRepository(db))
    return UserService(user_logic, dept_logic)

@router.post("", response_model=UserResponse)
def signup(dto: UserCreate, service: UserService = Depends(get_user_service)):
    return service.register_user_with_dept_check(dto)
```

---

## 5. 핵심 요약

| 구성 요소 | 위치 및 상태 | 핵심 역할 및 트랜잭션 처리 |
| :--- | :---: | :--- |
| **`domain/__init__.py`** | **빈 파일** | 도메인 경계 오염 방지, 이름 충돌 방지, 순환 참조 예방 |
| **`domain/user/__init__.py`** | **선별적 Re-export** | `User`, `UserLogic`, DTO만 공개하여 외부 계층에 깔끔한 1줄 import 제공 |
| **`UserRepository`** | **비공개 (Private)** | DB 세부 접근 및 `flush()` 전담, 외부의 비즈니스 규칙 우회 차단 |
| **`Feature Service`** | **Caller (상위 계층)** | 여러 도메인 유스케이스 조율 및 최상위 트랜잭션 경계(`is_root=True`) 주도 |
| **`Domain Logic`** | **Callee (하위 계층)** | 단일 도메인 비즈니스 규칙 처리 및 Caller의 트랜잭션을 승계(`is_root=False`)하여 조기 커밋 방지 |
