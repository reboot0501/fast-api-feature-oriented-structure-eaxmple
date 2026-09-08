# Database Layer 와 가장 가까운 Repository 캡슐화 원칙 반영과 Feature 및 Route Layer 조립 방법 정리

본 문서는 Feature-Oriented 및 DDD(Domain-Driven Design) 아키텍처에서 **데이터베이스 접근 계층인 Repository를 완전히 캡슐화**하고, FastAPI의 **의존성 체이닝(Dependency Chaining)**을 활용하여 **각 계층(Domain $\rightarrow$ Feature $\rightarrow$ Route)이 단방향으로 깔끔하게 조립(Wire-up)되는 설계 원칙**을 정리한 문서입니다.

---

## 1. 문제 배경: Route Layer에서 Repository를 조립하는 안티 패턴

초기 구현에서는 라우터 파일(`signup_fetch_route.py`) 내부에서 DB 세션(`get_db`)을 받고, 하위 도메인의 `UserRepository`, `DeptRepository`를 직접 꺼내와 조립하는 실수가 자주 발생합니다.

```python
# ❌ 안티 패턴: 라우터 파일에서 직접 저수준 Repository를 import하고 조립하는 구조
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db

from domain.user.user_repository import UserRepository  # 👈 도메인 내부 구현에 직접 침범
from domain.user import UserLogic
from domain.dept.dept_repository import DeptRepository  # 👈 도메인 내부 구현에 직접 침범
from domain.dept import DeptLogic
from feature.signup import SignupFetch

# 라우터 파일 안에서 저수준 DB 접근 객체를 직접 생성
def get_signup_fetch(db: Session = Depends(get_db)) -> SignupFetch:
    user_logic = UserLogic(UserRepository(db))
    dept_logic = DeptLogic(DeptRepository(db))
    return SignupFetch(user_logic, dept_logic)
```

### 왜 이것이 심각한 설계적 모순인가?

1. **도메인 캡슐화(정보 은닉)의 무력화**:
   * 도메인 설계 시 `domain/user/__init__.py`에서 `UserRepository`를 노출 목록(`__all__`)에서 제외하여 외부 침범을 막았습니다.
   * 하지만 라우터가 세부 경로(`domain.user.user_repository`)로 우회 접근하여 Repository를 생성한다면, **"앞문은 잠가놓고 가장 바깥쪽 웹 계층이 뒷문을 열고 들어간 형국"**이 됩니다.
2. **단일 책임 원칙(SRP) 위반 및 계층 오염**:
   * 라우터(Route)는 **"HTTP 요청 파싱 및 응답 포맷팅"**만을 담당해야 합니다.
   * 라우터가 DB 세션 커넥션 관리와 Repository 생성이라는 인프라 세부 관심사까지 떠안게 되어 계층 간 결합도가 극도로 높아집니다.

---

## 2. 해결 원칙: 계층별 자율 조립과 의존성 체이닝 (Dependency Chaining)

**"각 계층은 자기 바로 아래 계층만 알고, 자기 자신을 완성하는 조립 팩토리를 스스로 제공한다."**

FastAPI의 `Depends()`는 하위 의존성을 자동으로 해결하는 **의존성 체이닝(Chaining)**을 기본 지원합니다. 이를 통해 각 계층의 캡슐화를 온전히 지키면서 객체를 조립할 수 있습니다.

```
┌────────────────────────────────────────────────────────┐
│                      Route Layer                       │
│  "나는 SignupFetch만 알면 돼! (DB, Repo, Logic 모름)"  │
└───────────────────────────┬────────────────────────────┘
                            │ Depends(get_signup_fetch)
                            ▼
┌────────────────────────────────────────────────────────┐
│                     Feature Layer                      │
│  "나는 UserLogic, DeptLogic만 알면 돼! (Repo 모름)"    │
└─────────────┬────────────────────────────┬─────────────┘
              │ Depends(get_user_logic)    │ Depends(get_dept_logic)
              ▼                            ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│       User Domain       │  │       Dept Domain       │
│  "Repository는 나만     │  │  "Repository는 나만     │
│   알고, 내가 조립해서   │  │   알고, 내가 조립해서   │
│   UserLogic을 제공할게" │  │   DeptLogic을 제공할게" │
└─────────────────────────┘  └─────────────────────────┘
```

---

## 3. 계층별 세부 구현 표준

### 1) 도메인 계층 (Domain Layer): 자체 조립 팩토리 제공

`UserRepository`는 오직 `domain/user` 패키지 내부에서만 참조되며, 외부에는 완성된 `UserLogic` 인스턴스를 제공하는 **`get_user_logic()`** 팩토리 함수를 노출합니다.

#### ① `domain/user/user_dependency.py` (신규 정의)
```python
# domain/user/user_dependency.py

from fastapi import Depends
from sqlalchemy.orm import Session
from app.config.database import get_db

# 🔒 도메인 내부에서만 은밀하게 Repository를 참조
from domain.user.user_repository import UserRepository
from domain.user.user_logic import UserLogic


def get_user_logic(db: Session = Depends(get_db)) -> UserLogic:
    """
    User 도메인이 스스로 DB 세션과 Repository를 주입하여 Logic을 생성하는 팩토리
    """
    return UserLogic(UserRepository(db))
```

#### ② `domain/user/__init__.py` (Re-export 등록)
```python
# domain/user/__init__.py

from domain.user.user_entity import User
from domain.user.user_dto import UserCreate, UserUpdate, UserResponse
from domain.user.user_logic import UserLogic
from domain.user.user_dependency import get_user_logic  # 👈 팩토리 함수 노출

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogic",
    "get_user_logic",  # 외부 계층은 이것만 주입받으면 됨!
]
```
*(동일하게 `domain/dept`에서도 `dept_dependency.py`를 통해 `get_dept_logic`을 노출합니다.)*

---

### 2) 피처 계층 (Feature Layer): 도메인 Logic들을 조합하여 자율 조립

Feature 계층은 `Repository`의 존재를 1%도 알 필요가 없습니다. 도메인에서 제공하는 `get_user_logic`과 `get_dept_logic`을 체이닝하여 자신을 조립합니다.

#### ① `feature/signup/signup_dependency.py` (신규 정의)
```python
# feature/signup/signup_dependency.py

from fastapi import Depends
# ✅ Repository는 전혀 보이지 않고, 오직 Logic과 Logic 팩토리만 주입받음
from domain.user import UserLogic, get_user_logic
from domain.dept import DeptLogic, get_dept_logic
from feature.signup.signup_fetch import SignupFetch
from feature.signup.signup_flow import SignupFlow


def get_signup_fetch(
    user_logic: UserLogic = Depends(get_user_logic),
    dept_logic: DeptLogic = Depends(get_dept_logic),
) -> SignupFetch:
    """
    SignupFetch 조립 팩토리
    """
    return SignupFetch(user_logic, dept_logic)


def get_signup_flow(
    user_logic: UserLogic = Depends(get_user_logic),
    dept_logic: DeptLogic = Depends(get_dept_logic),
) -> SignupFlow:
    """
    SignupFlow 조립 팩토리
    """
    return SignupFlow(user_logic, dept_logic)
```

#### ② `feature/signup/__init__.py` (Re-export 등록)
```python
# feature/signup/__init__.py

from feature.signup.signup_flow import SignupFlow
from feature.signup.signup_fetch import SignupFetch
from feature.signup.signup_dependency import get_signup_fetch, get_signup_flow


__all__ = [
    "SignupFlow",
    "SignupFetch",
    "get_signup_fetch",
    "get_signup_flow",
]
```

---

### 3) 라우트 계층 (Route Layer): 극도로 단순화된 순수 웹 계층

이제 라우터는 **`DB Session`, `Repository`, `Domain Logic`의 존재조차 알 필요가 없습니다.**  
오직 자신이 호출할 Feature와 DTO만 알고 요청을 위임합니다.

```python
# route/signup/signup_fetch_route.py

from fastapi import APIRouter, Depends
from domain.user import UserResponse
from domain.dept import DeptResponse

# ✅ 라우터는 오직 Feature와 조립 팩토리만 import! (Repository, DB 세션 완전 제거)
from feature.signup import SignupFetch, get_signup_fetch
from route.signup import FindSignedUserFetch
from route.organiztion.request_organization_fetch import FindDeptsFetch

router = APIRouter(prefix="/signup", tags=["signup"])


@router.post("/find_signed_user", response_model=UserResponse)
def find_signed_user(
  request: FindSignedUserFetch,
  signup_fetch: SignupFetch = Depends(get_signup_fetch)  # 👈 단 1줄로 조립 완료
):
    request.validate()
    return signup_fetch.find_signed_user(request.user_id)


@router.post("/find_depts", response_model=list[DeptResponse])
def find_depts(
  request: FindDeptsFetch,
  signup_fetch: SignupFetch = Depends(get_signup_fetch)
):
    request.validate()
    return signup_fetch.find_depts(request.dept_name)
```

---

## 4. 아키텍처 비교 요약

| 구분 | Before (라우터 직접 조립) | After (계층별 DI 체이닝 - 권장) |
| :--- | :--- | :--- |
| **Repository 접근 범위** | Route, Feature 등 어디서나 직접 접근 | **오직 해당 Domain 내부로 100% 캡슐화** |
| **Route의 관심사** | HTTP + DB 세션 관리 + Repo 생성 + 조립 | **순수 HTTP 라우팅 및 입출력 위임만 전담** |
| **의존성 방향** | Route $\rightarrow$ Repo, Logic, Feature 전방위 결합 | **Route $\rightarrow$ Feature $\rightarrow$ Domain Logic 단방향 흐름** |
| **유닛 테스트 용이성** | 라우터 테스트 시 DB 세션, Repo 모킹 필수 | `app.dependency_overrides[get_signup_fetch]`로 **Mock 1줄 교체 가능** |
| **변경 영향도** | DB 엔진이나 Repo 변경 시 라우터 코드까지 수정 | **도메인 내부만 수정되며 Feature/Route는 수정 0건** |

---

## 5. 결론 및 실무 가이드라인

1. **Repository는 절대 도메인 밖으로 내보내지 않는다.**
   - `domain/user` 폴더 밖의 그 어떤 코드에서도 `from domain.user.user_repository import ...` 구문이 존재해서는 안 됩니다.
2. **도메인은 `Logic`과 함께 `get_xxx_logic`을 외부에 제공한다.**
   - 상위 계층은 이 팩토리를 통해 도메인 비즈니스 로직을 주입받습니다.
3. **피처(Feature)는 도메인 Logic들을 엮어 상위 유스케이스를 구성하고 `get_xxx_flow/fetch`를 제공한다.**
4. **라우트(Route)는 피처 팩토리(`get_xxx`) 하나만 `Depends()`하여 실행한다.**
