# Composition Root 패턴 (svcs 기반 IoC 컨테이너 부트스트랩 패턴)

> 관련 문서: [`DI 팩토리 보일러 플에이트 제거 검토.md`](./DI%20팩토리%20보일러%20플에이트%20제거%20검토.md) — 왜 이 패턴을 도입했는지에 대한 배경/비교 검토는 그 문서를 참고. 이 문서는 **실제 적용된 패턴 자체를 정의**하고, **작업 순서와 예시 코드**를 정리한다.

## 1. 개념 정의

**Composition Root**는 Mark Seemann이 정립한 DI(의존성 주입) 용어로, "애플리케이션에서 객체 그래프(의존성 관계)를 조립하는 단 하나의 위치"를 뜻한다. 이상적으로는 애플리케이션 전체에서 **딱 한 곳**에서만 구체 클래스들을 알고 조립하며, 나머지 코드(도메인 클래스들)는 서로 타입으로만 관계를 맺고 "누가 나를 만들어주는지"는 전혀 몰라야 한다.

이 프로젝트는 [`svcs`](https://svcs.hynek.me/) 라이브러리를 IoC(제어의 역전) 컨테이너로 사용해 이 패턴을 구현했다. 표준 용어와 이 프로젝트의 실제 구성 요소를 매핑하면 다음과 같다.

| 표준 DI 용어 | 이 프로젝트에서의 실체 |
|---|---|
| **Composition Root** | `app/bootstrap.py`(`register_services`) + 이를 실행하는 `app/app.py`의 `lifespan` |
| **IoC Container** | `svcs.Registry`(등록소, 앱 전체 수명) + `svcs.Container`(해석기, 요청 단위 수명) |
| **Bootstrap(등록 단계)** | `register_services(registry)`가 실행되는 시점 — "어떤 타입에 어떤 팩토리를 쓸지" 등록만 하고, 아직 인스턴스는 안 만듦 |
| **Lifespan/Scope** | FastAPI의 `lifespan` 훅이 `Registry`(앱 수명)를, 매 HTTP 요청이 `Container`(요청 수명)를 결정 |
| **Autowiring** | `svcs.autowire(SomeClass)` — 클래스의 생성자 타입 힌트를 읽어 자동으로 의존성을 채움 |

> ⚠️ **Service Locator와의 구분**: `container.get(타입)`을 호출하는 코드가 svcs 문서상 기술적으로는 "Service Locator" 패턴이다. 이걸 **Composition Root(=라우트 핸들러, 즉 `route/*.py`) 안에서만** 호출하면 결과적으로 올바른 Dependency Injection이 되고, 반대로 `UserLogic`이나 `SignupFlow` 같은 **비즈니스 로직 내부**에서 직접 `container.get(...)`을 호출하면 안티패턴(진짜 Service Locator 남용)이 된다. 이 프로젝트는 `container.get(...)` 호출을 라우트 파일에서만 하고 있고, 도메인/피처 클래스는 svcs를 아예 import하지 않으므로 이 원칙을 지키고 있다.

## 2. 이 프로젝트에서의 구조

```
[앱 시작 1회]
app/app.py  @svcs.fastapi.lifespan
   └─ app/bootstrap.py  register_services(registry)   ← Composition Root
        ├─ registry.register_factory(Session, get_db)
        ├─ domain/user/user_dependency.py   register(registry)   ← 도메인 내부에서만 Repository 참조
        ├─ domain/dept/dept_dependency.py   register(registry)
        ├─ feature/signup/signup_dependency.py        register(registry)
        └─ feature/organization/organization_dependency.py  register(registry)

[매 HTTP 요청마다]
route/*/xxx_route.py
   └─ services: svcs.fastapi.DepContainer   ← 요청 스코프 Container 주입
        └─ services.get(SignupFlow)          ← 여기서만 컨테이너에 직접 조회
             └─ (svcs가 자동으로) UserLogic → UserRepository → Session 까지 재귀적으로 조립
```

핵심은 **"등록(register)"과 "조회(get)"가 완전히 분리**되어 있다는 점이다. 등록은 앱 시작 시 1번, 각 도메인/피처가 자기 자신을 스스로 등록하는 방식(캡슐화 유지)으로 이루어지고, 조회는 요청마다 라우트 계층에서만 일어난다. `UserLogic`, `SignupFlow` 같은 실제 비즈니스 클래스는 이 둘 중 어느 것도 몰라도 된다 — 생성자에 필요한 타입만 평범하게 선언하면 끝이다.

## 3. 작업 순서

새 프로젝트에 이 패턴을 처음 도입할 때, 또는 새 도메인/피처를 추가할 때 따르는 절차다.

### 3-1. (최초 1회) 패턴 도입 순서

1. **라이브러리 설치** — `uv add svcs`
2. **각 도메인이 자기 자신을 등록하는 함수 작성** — `domain/<도메인>/<도메인>_dependency.py`에 `register(registry: svcs.Registry) -> None` 함수를 만들고, 그 도메인의 `Repository`→`Logic`을 `svcs.autowire(...)`로 등록. Repository는 이 파일(자기 도메인 폴더 안)에서만 import한다.
3. **각 피처가 자기 자신을 등록하는 함수 작성** — `feature/<피처>/<피처>_dependency.py`에 같은 방식으로 `Flow`/`Fetch`를 등록.
4. **중앙 조립 파일(Composition Root) 작성** — `app/bootstrap.py`에 `register_services(registry)`를 만들고, 인프라 자원(DB 세션 등)과 각 도메인/피처의 `register(registry)`를 순서대로 호출.
5. **FastAPI lifespan을 svcs 인식형으로 교체** — `app/app.py`에서 `@asynccontextmanager` 대신 `@svcs.fastapi.lifespan`을 쓰고, `lifespan(app, registry)` 안에서 `register_services(registry)` 호출.
6. **라우트 계층 교체** — 각 라우트 핸들러 파라미터를 `services: svcs.fastapi.DepContainer`로 바꾸고, 함수 본문 첫 줄에서 `services.get(필요한클래스)`로 꺼내 쓴다.
7. **기존 개별 팩토리 함수/re-export 정리** — 라우트/도메인 `__init__.py`에서 더 이상 쓰지 않는 `get_xxx_logic` 등의 re-export를 제거.
8. **검증** — 아래 4절 참고.

### 3-2. (반복) 새 도메인/피처를 추가할 때

기존 도메인/피처 코드는 전혀 건드리지 않고, 아래 2단계만 반복한다.

1. 새 도메인(`domain/<new>/`)에 `<new>_dependency.py`를 만들어 `register(registry)` 작성(3-1의 2번과 동일한 요령).
2. `app/bootstrap.py`의 `register_services`에 `register_new(registry)` 호출 **한 줄**만 추가.

## 4. 예시 코드 (실제 이 프로젝트에 적용된 코드)

### 4-1. 도메인이 자기 자신을 등록 — `domain/user/user_dependency.py`

```python
# domain/user/user_dependency.py
"""
User 도메인 계층의 svcs 등록

Repository는 오직 domain/user 패키지 내부에서만 참조되며(캡슐화 원칙 유지),
외부(app/bootstrap.py)에는 register(registry) 함수만 노출한다.
UserLogic/UserRepository 클래스 자체는 svcs.autowire가 생성자 타입 힌트를
읽어 자동으로 조립하므로 수정하지 않는다.
"""

import svcs

# 🔒 domain 내부에서만 은밀하게 Repository를 참조
from domain.user.user_repository import UserRepository
from domain.user.user_logic import UserLogic


def register(registry: svcs.Registry) -> None:
  registry.register_factory(UserRepository, svcs.autowire(UserRepository))
  registry.register_factory(UserLogic, svcs.autowire(UserLogic))
```

`domain/dept/dept_dependency.py`도 클래스명만 다를 뿐 동일한 구조다. **`UserLogic`/`UserRepository` 클래스 정의부에는 `svcs`나 `Depends`를 전혀 import하지 않는다** — 순수한 생성자 타입 힌트만 있으면 된다.

```python
# domain/user/user_logic.py — 이 패턴 도입 전후로 단 한 줄도 바뀌지 않음
class UserLogic:
  def __init__(self, user_repo: UserRepository):   # 평범한 타입 힌트
    self.repo = user_repo
```

### 4-2. 피처가 자기 자신을 등록 — `feature/signup/signup_dependency.py`

```python
# feature/signup/signup_dependency.py
"""
Signup 피처의 svcs 등록

SignupFlow/SignupFetch 클래스는 수정하지 않는다. svcs.autowire가 생성자의
UserLogic/DeptLogic 타입 힌트를 읽어 Registry에 등록된 인스턴스를 자동으로 조립한다.
"""

import svcs

from feature.signup.signup_flow import SignupFlow
from feature.signup.signup_fetch import SignupFetch


def register(registry: svcs.Registry) -> None:
  registry.register_factory(SignupFlow, svcs.autowire(SignupFlow))
  registry.register_factory(SignupFetch, svcs.autowire(SignupFetch))
```

### 4-3. Composition Root — `app/bootstrap.py`

```python
# app/bootstrap.py
"""
svcs 서비스 등록 최상위 조립 파일

각 도메인/피처의 Repository/Logic/Flow/Fetch 클래스는 전혀 수정하지 않는다.
Repository는 doc/ 원칙(자기 도메인 폴더 밖에서 import 금지)에 따라 여전히
각 도메인 자신의 xxx_dependency.py 안에서만 참조되고, 여기서는 각 도메인/피처가
스스로 노출하는 register(registry) 함수를 호출해 모으기만 한다.
도메인/피처가 늘어날 때 이 함수에 register 호출 한 줄만 추가하면 된다.
"""

import svcs
from sqlalchemy.orm import Session

from app.config.database import get_db
from domain.user.user_dependency import register as register_user
from domain.dept.dept_dependency import register as register_dept
from feature.signup.signup_dependency import register as register_signup
from feature.organization.organization_dependency import register as register_organization


def register_services(registry: svcs.Registry) -> None:
    """도메인/피처가 늘어날 때마다 이 함수에 register 호출을 추가하면 된다."""

    # 인프라: get_db()는 제너레이터 함수라 register_factory가 자동으로
    # contextmanager로 감싸 요청 종료 시 db.close()까지 대신 처리해준다.
    registry.register_factory(Session, get_db)

    register_user(registry)
    register_dept(registry)
    register_signup(registry)
    register_organization(registry)
```

이 파일이 **이 프로젝트에서 유일하게 "전체 서비스 목록"을 한눈에 보여주는 곳**이다. 새 팀원 온보딩 시 이 파일 하나만 보면 어떤 서비스들이 있고 서로 어떻게 연결되는지 파악할 수 있다.

### 4-4. FastAPI Lifespan을 통한 부트스트랩 실행 — `app/app.py`

```python
# app/app.py

import svcs
from fastapi import FastAPI

from app.config.database import engine
from app.bootstrap import register_services
from shared.models import Base
from domain.user.user_entity import User  # noqa: F401
from domain.dept.dept_entity import Dept  # noqa: F401

from route.signup import signup_flow_router, signup_fetch_router
from route.organization import organization_flow_router, organization_fetch_router


@svcs.fastapi.lifespan
async def lifespan(app: FastAPI, registry: svcs.Registry):
    """startup : 테이블 없으면 생성, 있으면 그대로 (데이터 유지) + svcs 서비스 등록"""
    Base.metadata.create_all(bind=engine)
    register_services(registry)          # ← Composition Root 실행
    print("[OK] Database tables created")
    yield
    print("[INFO] Application is shutting down")


app = FastAPI(
    title="Fast API Feature Oriented Stuctucture (DDD)",
    lifespan=lifespan,
)

app.include_router(signup_flow_router)
app.include_router(signup_fetch_router)
app.include_router(organization_flow_router)
app.include_router(organization_fetch_router)
```

`@svcs.fastapi.lifespan`이 `Registry`를 만들고, `app.state`에 붙였다가 앱 종료 시 자동으로 정리(`close()`)해준다. `register_services(registry)` 호출 한 줄이 이 앱의 **Composition Root가 실행되는 유일한 지점**이다.

### 4-5. 요청 스코프에서 조회 — `route/signup/signup_flow_route.py`

```python
# route/signup/signup_flow_route.py

import svcs
from feature.signup import SignupFlow
from route.signup import SignupCommand
from domain.user import UserResponse
from fastapi import APIRouter

router = APIRouter(
  prefix="/signup",
  tags=["회원가입 관리"],
  responses={404: {"description": "Not found"}}
)

@router.post("/", response_model=UserResponse)
def signup(
  request: SignupCommand,
  services: svcs.fastapi.DepContainer,   # ← 요청마다 생성되는 컨테이너 1개만 주입
):
  signup_flow = services.get(SignupFlow)  # ← 여기서만 컨테이너에 직접 조회 (Composition Root의 연장)
  return signup_flow.signup(request.request)
```

`services.get(SignupFlow)`를 호출하는 순간, svcs가 내부적으로 다음을 재귀적으로 수행한다.

```
SignupFlow 필요
 └─ 생성자 확인: __init__(self, user_logic: UserLogic, dept_logic: DeptLogic)
     ├─ UserLogic 필요
     │    └─ 생성자 확인: __init__(self, user_repo: UserRepository)
     │         └─ UserRepository 필요
     │              └─ 생성자 확인: __init__(self, db: Session)
     │                   └─ Session 필요 → 등록된 get_db() 팩토리 호출 → Session 인스턴스
     └─ DeptLogic 필요 (User와 동일한 방식으로 DeptRepository → Session 재사용)
```

같은 요청(같은 `Container`) 안에서는 같은 타입을 두 번 요청해도 처음 만든 인스턴스를 그대로 재사용한다(캐싱) — 예를 들어 `UserLogic`이 `SignupFlow`와 `OrganizationFlow` 양쪽에서 필요해도 한 요청 안에서는 인스턴스가 1개만 생성된다.

## 5. `register_factory` vs `register_value` — 이 프로젝트는 어느 쪽인가

### 5-1. 결론: `Session`에 의존하는 9개는 `register_factory`(Request Scope), 로거 1개만 `register_value`(Singleton)

실제 코드를 전수 검색(`grep -rn "register_factory\|register_value"`)한 결과, 도메인/피처 관련 9개 서비스는 전부 `register_factory`이고, 여기에 더해 **`logging.Logger` 1개만 `register_value`로 등록**되어 있다(스레드 세이프한 공유 자원이라 5-4에서 실제로 추가함).

| 등록 위치 | 등록된 타입 | 방식 |
|---|---|---|
| `app/bootstrap.py` | `Session` | `register_factory(Session, get_db)` |
| `domain/user/user_dependency.py` | `UserRepository`, `UserLogic` | `register_factory(..., svcs.autowire(...))` |
| `domain/dept/dept_dependency.py` | `DeptRepository`, `DeptLogic` | 〃 |
| `feature/signup/signup_dependency.py` | `SignupFlow`, `SignupFetch` | 〃 |
| `feature/organization/organization_dependency.py` | `OrganizationFlow`, `OrganizationFetch` | 〃 |

즉 이 프로젝트의 `UserLogic`, `UserRepository`, `SignupFlow` 등은 **전부 Request Scope(요청 단위)** 로 동작한다 — 4절 마지막에서 설명한 "같은 요청 안에서는 캐시되어 재사용되지만, 다른 요청과는 절대 공유되지 않는다"는 동작이 지금 이 프로젝트의 실제 상태다. 4절 예시 코드(`domain/user/user_dependency.py` 등)를 다시 보면 전부 `register_factory`만 쓰고 있는 것을 확인할 수 있다. 이는 우연이 아니라 **의도된 설계**다 — 이유는 아래 5-3에서 설명한다.

### 5-2. 왜 `register_factory`인지 — 메커니즘

`svcs`의 두 등록 메서드는 근본적으로 다른 게 아니라, `register_value`가 `register_factory`를 감싼 문법 설탕이다(`svcs/_core.py` 소스 기준).

```python
# register_value(타입, 값) 내부적으로는 이렇게 동작한다
def register_value(self, svc_type, value, ...):
    self._register_factory(svc_type, lambda: value, ...)  # "항상 같은 value를 돌려주는 팩토리"로 변환
```

| | `register_factory(타입, 팩토리)` | `register_value(타입, 값)` |
|---|---|---|
| 등록하는 것 | "만드는 방법"(호출 가능한 팩토리) | 이미 완성된 객체 그 자체 |
| `container.get()` 호출 시 | 매 요청(Container)마다 **새로 실행**해서 인스턴스 생성 | 항상 등록 당시의 **동일 객체**를 그대로 반환 |
| 요청 간 인스턴스 공유 | ❌ 공유 안 됨 | ✅ 완전히 동일한 객체(`is` 비교 True) 공유 |
| Spring 대응 스코프 | `@RequestScope`에 가까움 | 기본 `@Service`(Singleton)와 동일 |

`domain/user/user_dependency.py`의 `registry.register_factory(UserLogic, svcs.autowire(UserLogic))`는 `svcs.autowire(UserLogic)`이 "호출될 때마다 `UserLogic(...)`을 새로 만드는 함수"이기 때문에, 요청이 올 때마다 `UserLogic` 인스턴스가 새로 생성된다.

### 5-3. 왜 지금 이 방식(전부 `register_factory`)이 올바른 설계인가

`register_factory`로 등록된 9개 서비스는 전부 체인 끝에서 SQLAlchemy `Session`에 의존한다.

```
SignupFlow → UserLogic → UserRepository → Session (get_db()가 매 요청마다 새로 만듦)
```

`Session`은 스레드 안전하지 않고 동시 요청 간 공유하면 안 되는 자원이다. 만약 이 체인의 어느 하나라도 `register_value`로 등록했다면(예: `registry.register_value(UserRepository, repo)`), 앱이 뜰 때 만들어진 **단 하나의 `Session`을 모든 동시 요청이 공유**하게 되어 데이터가 뒤섞이거나 예외가 발생하는 심각한 동시성 버그로 이어진다. 이 9개가 전부 `register_factory`인 것은, `Session`에 의존하는 체인을 안전하게 요청 단위로 격리하기 위한 **의도된 선택**이다.

### 5-4. `register_value`가 적합한 서비스 — 적용 사례와 향후 후보

`Session`과 무관한, 앱 전체에서 상태를 공유해도 안전한 서비스에는 `register_value`를 쓴다. 판단 기준은 3가지다.

1. **불변(immutable)이거나 동시 접근에 안전(thread/async-safe)** 하다
2. **요청마다 다시 만들 이유가 없다** — 오히려 매번 새로 만드는 게 자원 낭비다
3. **내부에 `Session`처럼 요청 단위로 격리돼야 하는 자원을 물고 있지 않다**

**① `logging.Logger` — 이 프로젝트에 실제로 적용됨**

`shared/utils/logging_helper.py`의 `logger`는 파이썬 표준 `logging` 모듈 자체가 스레드 세이프하게 설계되어 있어, 위 3가지 조건을 모두 만족한다. `app/bootstrap.py`에 다음처럼 실제로 등록되어 있다.

```python
# app/bootstrap.py (실제 코드)
import logging
from shared.utils.logging_helper import logger

def register_services(registry: svcs.Registry) -> None:
    ...
    registry.register_value(logging.Logger, logger)
```

라우트에서는 다음처럼 꺼내 쓴다(`route/organization/organization_fetch_route.py`에 실제 적용됨).

```python
# route/organization/organization_fetch_route.py (실제 코드)
@router.post("/find_users", response_model=OffsetElementList[UserResponse])
def find_users(request: FindUsersFetch, services: svcs.fastapi.DepContainer):
  log = services.get(logging.Logger)   # 앱 전체에서 동일한 로거 인스턴스(싱글톤)
  log.info(
    "find_users 실행됨 (user_name=%s, dept_id=%s, page=%s, size=%s, order=%s)",
    request.user_name, request.dept_id, request.page, request.size, request.order,
  )
  organization_fetch = services.get(OrganizationFetch)
  return organization_fetch.find_users(...)
```

검증: 서로 다른 `Container`(=서로 다른 요청)에서 `container.get(logging.Logger)`를 호출해도 완전히 같은 객체(`is` 비교 `True`)가 반환됨을 확인했고, 실제 `TestClient`로 `/organization/find_users`를 호출했을 때 `find_users 실행됨 (...)` 로그가 정상 출력됨을 확인했다. 별도의 락(lock)을 코드에 추가하지 않아도, `logging.Logger.info()` 자체가 내부적으로 스레드 세이프하게 구현되어 있어 동시 요청에서도 로그가 섞이거나 깨지지 않는다.

**② `AppSettings`(환경설정) — 향후 후보**

```python
class AppSettings:
    def __init__(self, db_driver: str, debug: bool):
        self.db_driver = db_driver
        self.debug = debug

settings = AppSettings(db_driver=os.getenv("DB_DRIVER"), debug=...)
registry.register_value(AppSettings, settings)  # 환경변수는 앱 시작 시 한 번만 읽으면 충분
```

**③ 커넥션 풀을 갖는 외부 클라이언트(`httpx.Client`, `redis.Redis` 등) — 향후 후보**

```python
email_client = httpx.Client(base_url="https://api.email-provider.com", timeout=5.0)
registry.register_value(httpx.Client, email_client)  # 요청마다 새로 만들면 매번 TCP 연결을 새로 맺어야 함
```

이런 클라이언트는 앱 종료 시 `close()`로 정리해야 하므로, 실제 도입 시에는 `register_value` 대신 `register_factory` + `on_registry_close` 콜백 조합도 함께 검토한다.

## 6. 체크리스트 (규칙 요약)

- ✅ `svcs.autowire(SomeClass)`는 **등록 시점**(`register_factory` 호출부)에서만 감싼다. `SomeClass` 정의부에 데코레이터로 붙이지 않는다(클래스 이름이 함수로 바뀌어버리는 버그가 됨).
- ✅ `container.get(...)` / `services.get(...)` 호출은 **라우트 계층(Composition Root)에서만** 한다. `Logic`/`Flow`/`Repository` 내부에서 호출하면 안티패턴이 된다.
- ✅ `Repository`는 항상 자기 도메인 폴더 안의 `xxx_dependency.py`에서만 import한다 — `app/bootstrap.py`나 다른 도메인에서 직접 import하지 않는다.
- ✅ 새 도메인/피처를 추가할 때 손대는 파일은 "그 도메인 자신의 `_dependency.py`"와 "`app/bootstrap.py`의 한 줄"뿐이어야 한다. 그 이상을 건드리고 있다면 패턴이 깨지고 있다는 신호다.
- ✅ `Session`(또는 `Session`에 의존하는 어떤 클래스든)은 반드시 `register_factory`로 등록한다. `register_value`로 등록하면 모든 요청이 동일 세션을 공유하는 동시성 버그가 된다. `register_value`는 `Session`과 무관한 무상태 공유 자원(설정값, 캐시 클라이언트 등)에만 사용한다.
