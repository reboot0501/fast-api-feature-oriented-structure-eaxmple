# DI 팩토리 보일러플레이트 제거 검토

> 관련 이슈: [리팩토링 분석 리포트] `#16 Flow/Fetch용 DI 팩토리 보일러플레이트 중복`
> 질문: "Spring의 `@Service`처럼, 별도 DI 팩토리 함수 없이 개선할 수 없을까?"
> 결론: **가능하다.** FastAPI가 이미 내장하고 있는 "클래스를 그대로 `Depends()`에 전달하는" 패턴(공식 문서 용어: *Classes as Dependencies*)을 쓰면, Spring의 생성자 주입(`@Service` + `@Autowired` 생성자)과 동일한 효과를 외부 라이브러리 없이 얻을 수 있다.

---

## 1. 현재 구조 — 왜 팩토리 함수가 4~6개나 필요한가

현재 의존성 조립 체인은 `Route → Feature(Flow/Fetch) → Domain(Logic) → Domain(Repository) → DB Session` 4단계이며, 각 단계 전환마다 "팩토리 함수"가 하나씩 붙어 있다.

```
route/*/…_route.py
   └─ Depends(get_signup_flow)              ← feature/signup/signup_dependency.py
        └─ Depends(get_user_logic)          ← domain/user/user_dependency.py
        └─ Depends(get_dept_logic)          ← domain/dept/dept_dependency.py
             └─ Depends(get_db)             ← app/config/database.py (이건 진짜 필요, 세션 생성 로직이 있음)
```

**현재 파일 4개, 내용 비교**

| 파일 | 핵심 코드 |
|---|---|
| `domain/user/user_dependency.py` | `def get_user_logic(db=Depends(get_db)): return UserLogic(UserRepository(db))` |
| `domain/dept/dept_dependency.py` | `def get_dept_logic(db=Depends(get_db)): return DeptLogic(DeptRepository(db))` |
| `feature/signup/signup_dependency.py` | `def get_signup_flow(user_logic=Depends(get_user_logic), dept_logic=Depends(get_dept_logic)): return SignupFlow(user_logic, dept_logic)` + `get_signup_fetch` 동일 패턴 |
| `feature/organization/organization_dependency.py` | 위와 완전히 동일한 구조, 클래스명만 `Organization*`으로 교체 |

즉 각 클래스(`UserLogic`, `SignupFlow` 등) **본인은 생성자에 평범한 파라미터**(`def __init__(self, user_repo: UserRepository)`)만 받고, "이 파라미터들을 어떻게 채울지"는 전부 클래스 밖의 별도 함수가 담당한다. Spring으로 비유하면 `@Service`를 안 붙이고, `@Configuration` 클래스에 `@Bean` 메서드를 일일이 작성해 수동 조립하는 것과 같은 방식이다(Spring도 가능은 하지만 보일러플레이트 때문에 실무에서는 `@Autowired` 생성자 주입을 선호한다).

이 구조에서 도메인이 2개(`user`, `dept`), 피처가 2개(`signup`, `organization`)뿐인데도 **거의 동일한 조립 함수 6개**(`get_user_logic`, `get_dept_logic`, `get_signup_flow`, `get_signup_fetch`, `get_organization_flow`, `get_organization_fetch`)가 생겼고, 실제로 `domain/dept/dept_dependency.py`의 독스트링엔 `"User 도메인이 스스로 DB 세션과..."`라는 **복붙 오타**까지 남아있었다 — 반복 작업이 실수를 재생산한 실증 사례다.

---

## 2. FastAPI의 "클래스를 그 자체로 의존성으로 쓰기" 메커니즘

FastAPI의 `Depends()`는 인자로 "콜러블(callable)"을 받는다. 함수뿐 아니라 **클래스도 콜러블**이므로(`SomeClass(...)`처럼 호출 가능) `Depends(SomeClass)`라고 쓰면, FastAPI는 다음을 수행한다.

1. `inspect.signature(SomeClass)`로 `__init__`의 파라미터 목록(첫 번째 `self` 제외)을 읽는다.
2. 각 파라미터의 기본값이 `Depends(...)`이면, 그 값도 재귀적으로 먼저 해석(resolve)한다.
3. 모든 파라미터가 해석되면 `SomeClass(파라미터1=값1, 파라미터2=값2, ...)`를 호출해 인스턴스를 만들어 반환한다.

이건 정확히 Spring 컨테이너가 빈(Bean)의 생성자 시그니처를 리플렉션으로 읽고 각 파라미터 타입에 맞는 빈을 찾아 주입한 뒤 `new`로 인스턴스를 만드는 것과 동일한 절차다. 차이는 "빈 등록"을 어노테이션 스캔이 아니라 **생성자 파라미터 자체의 기본값**으로 표현한다는 점뿐이다.

---

## 3. Before / After — 체인 전체 다시 쓰기

### 3-1. Repository 계층

```python
# domain/user/user_repository.py  (Before)
class UserRepository:
  def __init__(self, db: Session):
    self.db = db
```

```python
# domain/user/user_repository.py  (After)
from fastapi import Depends
from app.config.database import get_db

class UserRepository:
  def __init__(self, db: Session = Depends(get_db)):
    self.db = db
```

`Dept` 쪽도 동일하게 `db: Session = Depends(get_db)`로 바꾼다.

### 3-2. Logic 계층 — `user_dependency.py` / `dept_dependency.py` 파일 자체를 삭제

```python
# domain/user/user_logic.py  (Before)
class UserLogic:
  def __init__(self, user_repo: UserRepository):
    self.repo = user_repo
```

```python
# domain/user/user_logic.py  (After)
from fastapi import Depends

class UserLogic:
  def __init__(self, user_repo: UserRepository = Depends(UserRepository)):
    self.repo = user_repo
```

→ `domain/user/user_dependency.py`, `domain/dept/dept_dependency.py` **파일 자체가 필요 없어진다.** `domain/user/__init__.py`가 `get_user_logic`을 re-export하고 있다면, 그 부분만 `UserLogic`(클래스 자체) re-export로 바꿔주면 된다.

### 3-3. Flow / Fetch 계층 — `signup_dependency.py` / `organization_dependency.py` 파일 자체를 삭제

```python
# feature/signup/signup_flow.py  (Before)
class SignupFlow:
  def __init__(self, user_logic: UserLogic, dept_logic: DeptLogic):
    self.user_logic = user_logic
    self.dept_logic = dept_logic
```

```python
# feature/signup/signup_flow.py  (After)
from fastapi import Depends
from domain.user import UserLogic
from domain.dept import DeptLogic

class SignupFlow:
  def __init__(
    self,
    user_logic: UserLogic = Depends(UserLogic),
    dept_logic: DeptLogic = Depends(DeptLogic),
  ):
    self.user_logic = user_logic
    self.dept_logic = dept_logic
```

`SignupFetch`, `OrganizationFlow`, `OrganizationFetch`도 동일하게 생성자에 `Depends(UserLogic)`, `Depends(DeptLogic)`만 추가하면 끝난다. (참고: `OrganizationFlow`는 실제로 `user_logic`을 `change_user_dept`/`change_users_dept`에서 사용하고 있어 현재는 dead dependency가 아님 — 최초 분석 시점 이후 기능이 추가되며 실제로 쓰이게 됐다.)

### 3-4. Route 계층

```python
# route/signup/signup_flow_route.py  (Before)
from feature.signup import get_signup_flow
...
def signup(request: SignupCommand, signup_flow: SignupFlow = Depends(get_signup_flow)):
  return signup_flow.signup(request.request)
```

```python
# route/signup/signup_flow_route.py  (After)
from feature.signup import SignupFlow
...
def signup(request: SignupCommand, signup_flow: SignupFlow = Depends(SignupFlow)):
  return signup_flow.signup(request.request)
```

**결과: 삭제되는 파일 4개**

- `domain/user/user_dependency.py`
- `domain/dept/dept_dependency.py`
- `feature/signup/signup_dependency.py`
- `feature/organization/organization_dependency.py`

라우트 코드에서 바뀌는 부분은 `Depends(get_xxx_flow)` → `Depends(XxxFlow)` 딱 한 군데(`import`문 포함 두 줄)뿐이라, 라우트 계층에 대한 영향은 최소화된다.

---

## 4. 아키텍처 원칙과의 정합성 검토

이 프로젝트 `doc/`에는 다음 두 원칙이 명시되어 있다.

1. `domain/<sub>/xxx_repository.py`는 자기 도메인 폴더 밖에서 import 금지
2. `domain/__init__.py`는 비워두고, 각 서브 도메인이 선택적으로 re-export

**두 원칙 모두 위 변경으로 깨지지 않는다.**

- `route/signup_flow_route.py`는 여전히 `UserRepository`를 전혀 몰라도 된다. `Depends(SignupFlow)`를 해석하는 과정에서 FastAPI가 재귀적으로 `Depends(UserLogic)` → `Depends(UserRepository)` → `Depends(get_db)`까지 자동으로 타고 들어가지만, **그 재귀 해석은 각 클래스의 생성자 안에서만 일어난다.** 즉 "누가 `UserRepository`를 import하는가"라는 캡슐화 기준은 여전히 `domain/user/user_logic.py` 한 곳뿐이다.
- 캡슐화는 "팩토리 함수가 있냐 없냐"가 아니라 "import 관계"로 지켜지는 것이므로, 팩토리 함수 제거는 이 원칙과 직교(orthogonal)한 문제다.

---

## 5. 트레이드오프 — Spring과 완전히 같지는 않다

| 항목 | Spring `@Service` | FastAPI `Depends(Class)` |
|---|---|---|
| 빈 등록 방식 | 클래스패스 스캔(`@ComponentScan`) — 어노테이션만 붙이면 자동 등록 | **자동 스캔 없음.** 생성자 파라미터의 기본값(`Depends(...)`)이 곧 등록 정보. 각 클래스가 스스로 "나는 이걸 필요로 한다"를 명시해야 함 |
| 기본 스코프 | 싱글톤(앱 전체에서 인스턴스 1개) | **요청(request) 단위.** 매 HTTP 요청마다 새로 생성(단, 같은 요청 안에서는 `use_cache=True`(기본값)로 중복 생성 방지) |
| 이 프로젝트 적합성 | - | `db: Session`이 애초에 요청 단위 자원이므로, `UserRepository`/`UserLogic`도 요청마다 새로 만드는 게 오히려 올바른 동작. **스코프 차이가 실질적 문제를 일으키지 않음** |
| 순수성(계층 결합) | 도메인 클래스가 프레임워크를 몰라도 됨 (어노테이션은 있지만 실행 로직과는 분리) | `UserRepository`/`UserLogic`의 `__init__` 시그니처에 `from fastapi import Depends`가 직접 등장 — **도메인 계층이 FastAPI를 import하게 됨** (단, 이미 `sqlalchemy.orm.Session`을 직접 참조하고 있어 완전한 프레임워크 무관성은 애초에 아니었음) |
| 테스트 시 목(mock) 교체 | `@MockBean` 등으로 컨테이너 레벨에서 교체 | `app.dependency_overrides[UserRepository] = lambda: FakeRepo()` 로 라우트 테스트 시 교체 가능(FastAPI 표준 기능) — 단위 테스트(라우트를 거치지 않는 순수 클래스 테스트)에서는 원래대로 생성자에 직접 fake 객체를 넘기면 되므로 오히려 더 간단 |

**핵심 트레이드오프는 "순수성(4번째 행)"이다.** 지금처럼 `UserRepository.__init__(self, db: Session)`이 FastAPI를 전혀 모르는 상태를 유지하고 싶다면, 이 리팩토링은 그 원칙을 일부 양보하는 셈이다. 다만:

- 이미 `sqlalchemy.orm.Session`이라는 인프라 타입을 도메인 클래스가 직접 참조하고 있어 "프레임워크·인프라로부터 완전히 자유로운 순수 도메인" 상태는 아니었다.
- 실제 비즈니스 로직(메서드 본문)에는 FastAPI가 전혀 등장하지 않고, `__init__` 시그니처 한 줄에만 등장하므로 결합의 "깊이"는 얕다.
- 이 결합이 부담스럽다면 5절이 아니라 6절(3rd-party DI 컨테이너)이 대안이 될 수 있다.

---

## 6. 대안 비교 — 더 Spring에 가까운 방식을 원한다면

| 방식 | 설명 | 장점 | 단점 | 이 프로젝트 적합도 |
|---|---|---|---|---|
| **A. 현행 유지** (팩토리 함수) | 지금처럼 `get_xxx_logic` 함수를 수동 작성 | 명시적, 외부 의존성 없음 | 보일러플레이트/복붙 오타 반복 (#16 이슈 자체) | 낮음 — 개선 여지 있음 |
| **B. FastAPI 클래스 의존성** (본 문서 제안) | 생성자에 `Depends(...)` 기본값 직접 명시 | 외부 라이브러리 불필요, FastAPI 공식 패턴, 캡슐화 원칙 유지 | 도메인 클래스가 `fastapi.Depends`를 import(경미한 결합) | **높음 — 지금 규모에 가장 적합** |
| **C. `python-dependency-injector`** | `containers.DeclarativeContainer` + `providers.Factory`/`Singleton` + `@inject` 데코레이터로 명시적 컨테이너 구성 | 싱글톤/스코프 세밀 제어, `container.override()`로 테스트 목 교체 용이, Spring `@Configuration`과 가장 유사 | 컨테이너 정의·wiring 설정 코드가 새로 필요, 학습 곡선, 프로젝트에 새 의존성 추가 | 중간 — 도메인이 5개 이상으로 늘어나면 재검토 |
| **D. `svcs`** (`autowire` 포함) | 경량 서비스 로케이터, FastAPI 통합 지원, `svcs.autowire`로 등록 자동화 | 컨테이너 설정이 C보다 단순, **도메인 클래스가 프레임워크를 전혀 몰라도 됨**(B안의 순수성 트레이드오프 해소), 인터페이스 기반 등록·헬스체크·자동 리소스 정리 지원 | 등록 자체는 여전히 수동(자동 스캔 없음), `Registry`/`Container` 개념 학습 필요 | **도메인 2개 규모에선 과함 / 도메인이 늘어날 계획이면 B보다 먼저 검토할 가치 있음 → 7절 참고** |

**결론(현재 규모 기준): 도메인 2개, 피처 2개인 지금은 B안(FastAPI 클래스 의존성)이 가장 합리적이다.** 외부 의존성 추가 없이 `#16` 중복을 근본적으로 제거하고, 캡슐화 원칙도 유지되며, FastAPI 공식 문서가 권장하는 관용적 패턴이기도 하다.

**다만 "도메인이 많고 구조가 복잡한 형태로 확장"이 이미 정해진 방향이라면 이야기가 달라진다.** D안(`svcs`), 그중에서도 `autowire` 기반 등록 방식은 단순 비교표 이상의 이유로 B안보다 먼저 검토할 가치가 있다 — 자세한 내용은 아래 7절에서 쉽게 풀어 설명한다.

---

## 7. 확장 시나리오에서는 `svcs autowire`를 B안보다 먼저 검토해야 하는 이유

> 이 절은 "도메인 2~3개짜리 소규모"가 아니라 **"도메인 10개, 20개까지 늘어나는 큰 프로젝트"를 가정했을 때**의 이야기다. 지금 당장 적용하라는 뜻이 아니라, 그런 방향으로 갈 경우 B안보다 이 방식을 먼저 검토하라는 의미다.

### 7-1. 비유로 먼저 이해하기 — "각자 주문서를 쓰는 것" vs "명찰만 달면 창고지기가 알아서 갖다주는 것"

- **B안 (`Depends(Class)`)**: 새로운 클래스를 만들 때마다, 그 클래스 스스로 생성자에 "나는 `UserRepository`가 필요해요, `Depends(UserRepository)`로 갖다주세요"라는 **주문서를 직접 작성**해야 한다. 클래스 하나하나가 FastAPI라는 창고 시스템의 존재를 알아야 하고, 그 문법(`Depends`)을 직접 써야 한다.
- **svcs `autowire`**: 클래스는 그냥 평소처럼 "나는 생성자에서 `UserRepository` 타입을 받는다"는 **평범한 타입 힌트만** 적어 놓으면 끝이다(`Depends`도, `svcs`도 import할 필요 없음). 그 대신 창고지기 역할을 하는 **레지스트리(등록부)** 한 곳에 "`UserLogic`이 필요하면 `autowire(UserLogic)`으로 알아서 조립해서 줘"라는 규칙을 **딱 한 줄** 적어두면, 어디서든 `container.get(UserLogic)`이라고 요청하는 순간 창고지기가 필요한 재료(`UserRepository` 등)를 자동으로 찾아서 조립해 건네준다.

즉 **"각 클래스가 스스로 요청서를 쓰느냐(B안)" vs "클래스는 아무것도 모른 채 그냥 존재하고, 중앙 창고지기가 알아서 조립해주느냐(svcs)"**의 차이다. Spring의 `@Service`가 주는 느낌("어노테이션 하나 붙이면 끝, 나머지는 컨테이너가 알아서")에 훨씬 가까운 쪽은 후자다.

### 7-2. 코드로 보는 차이

**B안 — 도메인이 늘어날수록 "모든 클래스"를 건드려야 한다**

```python
# 도메인이 10개면, 10개의 Logic 클래스 전부 이렇게 고쳐야 함
class UserLogic:
    def __init__(self, user_repo: UserRepository = Depends(UserRepository)):  # ← fastapi.Depends를 직접 import
        self.repo = user_repo

class ProductLogic:
    def __init__(self, product_repo: ProductRepository = Depends(ProductRepository)):  # ← 여기도, 저기도 반복
        self.repo = product_repo
# ... 도메인마다 계속 반복
```

**svcs `autowire` — 클래스는 그대로, 등록부에만 한 줄씩 추가한다**

```python
# domain/user/user_logic.py — 지금 코드와 완전히 동일, 아무것도 안 바뀜
class UserLogic:
    def __init__(self, user_repo: UserRepository):
        self.repo = user_repo

# domain/product/product_logic.py — 역시 그대로
class ProductLogic:
    def __init__(self, product_repo: ProductRepository):
        self.repo = product_repo
```

```python
# app/bootstrap.py — 도메인이 늘어날 때 여기에만 한 줄씩 추가 (딱 이 파일 하나만 보면 전체 그림이 보임)
import svcs

@svcs.fastapi.lifespan
async def lifespan(app, registry: svcs.Registry):
    registry.register_factory(Session, get_db_session)          # 인프라
    registry.register_factory(UserRepository, svcs.autowire(UserRepository))
    registry.register_factory(UserLogic,      svcs.autowire(UserLogic))
    registry.register_factory(ProductRepository, svcs.autowire(ProductRepository))
    registry.register_factory(ProductLogic,      svcs.autowire(ProductLogic))
    # 도메인이 늘어날수록 여기 두 줄씩만 추가되고, 도메인 클래스 자체는 절대 안 바뀐다
    yield
```

```python
# route/user/user_route.py
@router.get("/users/{id}")
def get_user(id: str, services: svcs.fastapi.DepContainer):
    user_logic = services.get(UserLogic)   # 라우트에서만 svcs를 알면 됨
    ...
```

### 7-3. B안보다 먼저 검토해야 하는 4가지 구체적 이유

1. **도메인 클래스가 끝까지 "순수"하게 남는다.** B안은 도메인이 몇 개 안 될 땐 괜찮지만, 10~20개로 늘어나면 "모든 Logic/Repository 클래스가 FastAPI를 알아야 한다"는 결합이 프로젝트 전체에 광범위하게 퍼진다. svcs는 이 결합을 **`app/bootstrap.py` 딱 한 파일로 봉인**한다. 나중에 FastAPI를 다른 프레임워크로 바꾸더라도(예: 다른 웹 프레임워크로 이전), 도메인 코드는 한 줄도 안 바꿔도 된다.
2. **`_dependency.py` 파일이 아예 안 생긴다.** 지금 구조는 도메인/피처가 늘 때마다 `xxx_dependency.py` 파일이 하나씩 늘어난다(현재도 4개). 도메인 20개면 관리해야 할 파일이 20개+ 늘어난다. svcs는 그 모든 조립 정보가 **중앙 `bootstrap.py` 한 파일에 도메인당 1~2줄**로 모이므로, "이 프로젝트에 어떤 서비스들이 있고 서로 어떻게 연결되는지"를 파일 하나만 열어보면 한눈에 파악할 수 있다 — 새 팀원 온보딩에도 유리하다.
3. **구현체 교체(포트-어댑터)가 쉬워진다.** 도메인이 많아지고 구조가 복잡해질수록 "테스트할 땐 가짜 Repository로, 운영에선 진짜 Oracle Repository로" 같은 요구가 자주 생긴다. svcs는 `registry.register_factory(추상타입, 구현체)`처럼 **타입(인터페이스) 기준으로 등록**하므로, 등록부 한 줄만 바꾸면 전체 시스템의 구현체를 교체할 수 있다. B안은 구체 클래스가 시그니처에 그대로 박혀 있어 이런 교체가 훨씬 번거롭다.
4. **테스트/헬스체크가 구조적으로 쉬워진다.** 서비스 개수가 많아질수록 "지금 이 서비스들 중 뭐가 죽었는지" 확인하거나(`ServicePing` 기반 헬스체크 일괄 실행), 테스트에서 특정 서비스만 목(mock)으로 바꿔치기(`registry.overwrite_value`)할 일이 잦아지는데, svcs는 이 두 가지를 프레임워크 차원에서 지원한다. B안은 이런 기능이 아예 없어 직접 구현해야 한다.

### 7-4. 그럼에도 남는 단점 (도입 전 인지할 것)

- **완전 자동은 아니다.** Spring의 클래스패스 스캔처럼 "클래스만 만들면 끝"은 아니고, `bootstrap.py`에 도메인당 한 줄은 계속 추가해야 한다. 다만 그 한 줄이 "새 파일 하나 통째로 작성"보다 훨씬 저렴하다는 게 핵심이다.
- **`container.get()`을 아무 데서나 부르면 안 된다.** svcs 공식 문서도 "비즈니스 로직 안에서 직접 `get()`을 호출하지 말고, 라우트(컴포지션 루트)에서만 호출하라"고 권고한다. `autowire`를 쓰면 도메인 클래스가 애초에 `svcs`를 모르므로 이 규율이 자연히 지켜지지만, 팀 컨벤션으로 한 번은 명시해둘 필요가 있다.
- **새 외부 의존성**이 프로젝트에 추가된다는 부담은 여전히 남는다.

### 7-5. 결론

지금(도메인 2개) 기준으로는 여전히 B안이 더 가볍고 적절하다. 그러나 **"도메인이 많고 구조가 복잡한 형태로 확장"이 이미 정해진 방향이라면**, B안으로 먼저 갔다가 나중에 다시 svcs로 갈아엎는 것보다 — 도메인 수가 임계점(3~4개)을 넘기기 전에 **처음부터 svcs `autowire` 기반으로 방향을 잡는 것이 전체 마이그레이션 비용을 더 낮춘다.** B안은 "지금 당장은 쉽지만 나중에 또 손대야 하는 선택", svcs는 "지금은 살짝 더 배워야 하지만 나중에 또 손댈 일이 없는 선택"이라고 요약할 수 있다.

---

## 8. 로컬 설치본(`svcs==26.2.0`) 소스 코드로 재검증

> 7절까지는 Context7을 통한 공식 문서 기준 설명이었다. 이후 실제로 `uv add svcs`로 로컬 설치(`.venv/Lib/site-packages/svcs`)가 이루어져, **설치된 버전의 실제 소스 코드**를 직접 열어 앞선 설명이 정확한지 재검증했다. 아래는 그 결과이며, 문서/버전 간 오차 없이 일치하는 부분과, 문서에는 없었지만 소스에서 추가로 확인된 세부사항을 함께 정리한다.

### 8-1. 설치 정보

- **버전**: `svcs==26.2.0` (`uv pip show svcs` 확인)
- **`pyproject.toml`**: `"svcs>=26.2.0"` 로 추가됨, `uv.lock`에도 반영됨
- **신규 전이 의존성**: `attrs`, `typing-extensions` (svcs 자체가 `attrs`로 구현되어 있음 — `svcs/fastapi.py`의 `lifespan` 클래스가 `@attrs.define`)
- **패키지 구성 파일**(`.venv/Lib/site-packages/svcs/`): `__init__.py`, `_core.py`(핵심 `Registry`/`Container`), `_autowire.py`(`autowire`/`aautowire`), `exceptions.py`, 그리고 프레임워크별 통합 모듈 `fastapi.py` / `flask.py` / `aiohttp.py` / `starlette.py`

### 8-2. 최상위 export 확인 (`svcs/__init__.py`)

```python
from ._autowire import aautowire, autowire
from ._core import Container, RegisteredService, Registry, ServicePing

__all__ = ["Container", "RegisteredService", "Registry", "ServicePing", "aautowire", "autowire", "exceptions"]

try:
    from . import fastapi   # FastAPI가 설치되어 있을 때만 자동으로 로드됨
except ImportError:
    ...
```

`svcs.fastapi`는 **FastAPI가 설치된 경우에만 자동으로 활성화**되는 optional 서브모듈이다(이 프로젝트는 FastAPI가 이미 있으므로 바로 사용 가능). `flask`/`aiohttp`/`starlette` 통합도 같은 방식이라, 나중에 다른 프레임워크로 옮기더라도 svcs 쪽 코드가 깨지지 않는 구조다.

### 8-3. `register_factory` 실제 전체 시그니처 (문서에 없던 옵션 확인)

```python
# svcs/_core.py:279
def register_factory(
    self,
    svc_type: _ServiceType,
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | Awaitable | None = None,
    suppress_context_exit: bool = True,
) -> None: ...
```

7절까지 소개한 `registry.register_factory(타입, 팩토리)` 두 파라미터 사용법은 정확했고, 추가로 다음 키워드 옵션이 실제로 존재함을 확인했다.

| 옵션 | 기본값 | 의미 |
|---|---|---|
| `enter` | `True` | 팩토리가 제너레이터/컨텍스트 매니저를 반환하면 자동으로 진입·정리(cleanup)를 수행할지 여부. 현재 `get_db()`처럼 `yield db` 후 `db.close()`하는 패턴을 그대로 팩토리로 등록하면, `Container`가 요청 종료 시 자동으로 정리해준다 |
| `ping` | `None` | 이전 문서에서 언급한 헬스체크(`ServicePing`)용 콜백 |
| `on_registry_close` | `None` | 레지스트리(앱 종료) 시점에 실행할 정리 콜백 |
| `suppress_context_exit` | `True` | 컨텍스트 매니저 종료 시 예외를 억제할지 여부 |

즉 `get_db()`를 그대로 svcs 팩토리로 등록하면(`registry.register_factory(Session, get_db)`), 지금 `app/config/database.py`의 `try/finally: db.close()` 로직을 svcs의 `enter=True` 자동 정리가 대체할 수 있다 — 별도 코드 변경 없이 등록 한 줄로 흡수 가능하다는 뜻이다.

### 8-4. `autowire` 실제 동작 — 소스 docstring에서 확인된 중요 사실

```python
# svcs/_autowire.py:128
def autowire(fn_or_cls: Callable[..., _T]) -> Callable[[Container], _T]:
    """
    ...
    .. warning::
        Do **not** decorate classes at definition time! Decorating a class
        using ``@autowire`` notation replaces the class with the autowire
        factory, so its name suddenly refers to a function, not a type.

        Wrap the class only at register time.
    """
```

- **⚠️ 클래스 정의부에 `@autowire` 데코레이터로 직접 붙이면 안 된다** — 그러면 클래스 이름이 클래스가 아니라 팩토리 함수로 바뀌어버려서, 타입으로서 참조가 불가능해진다. **반드시 등록 시점에만 `svcs.autowire(UserLogic)`처럼 감싸야 한다.** 7절에서 제시한 예시(`registry.register_factory(UserLogic, svcs.autowire(UserLogic))`)가 정확히 이 올바른 사용법이었음을 소스로 확인했다 — 도메인 클래스(`domain/user/user_logic.py`) 쪽에는 데코레이터를 절대 붙이지 않아야 한다는 점을 문서에 명시해둘 필요가 있다.
- **누락된 서비스는 기본값으로 폴백**: 파라미터에 기본값이 있고 해당 타입이 컨테이너에 등록되어 있지 않으면, 에러 대신 그 기본값을 사용한다(`_default_or_raise`). 선택적 의존성을 다룰 때 유용하다.
- **`Container` 타입으로 애너테이션된 파라미터는 컨테이너 자신이 주입**된다 — 드물게 팩토리 안에서 직접 다른 서비스를 동적으로 조회해야 할 때 탈출구로 쓸 수 있다.
- **bare generator 팩토리는 거부됨** — `def factory(): yield conn` 형태를 `autowire`에 그대로 넘기면 `TypeError`. `@contextlib.contextmanager`로 먼저 감싸야 한다(정리 로직이 유실되는 것을 막기 위한 안전장치).
- `aautowire`는 비동기 버전으로, 동기 서비스에도 동작하므로 "비동기 앱이면 그냥 이것만 쓰라"고 소스 주석에 명시되어 있다.

### 8-5. FastAPI 통합 모듈(`svcs/fastapi.py`) 실제 구조

```python
@attrs.define
class lifespan:  # svcs.fastapi.lifespan
    _lifespan: SomeLifespan
    registry: svcs.Registry = attrs.field(factory=svcs.Registry)
    async def __call__(self, app: FastAPI) -> AsyncGenerator[dict, None]: ...

async def container(request: Request) -> AsyncGenerator[svcs.Container, None]:
    async with svcs.Container(getattr(request.state, _KEY_REGISTRY)) as cont:
        yield cont

DepContainer = Annotated[svcs.Container, Depends(container)]

# 26.2.0에서 신규 추가:
async def registry(request: Request) -> svcs.Registry: ...
DepRegistry = Annotated[svcs.Registry, Depends(registry)]
```

- 7절 예시 코드(`@svcs.fastapi.lifespan` 데코레이터, `svcs.fastapi.DepContainer`)는 실제 구현과 정확히 일치한다.
- **동기/비동기 호환성 — 이 프로젝트(완전 동기 코드베이스) 기준으로 중요한 확인 사항**: `svcs.fastapi.container` 의존성 함수 자체는 `async def`이지만, 이는 "요청마다 컨테이너 객체 하나를 꺼내오는" FastAPI 배관(plumbing) 코드일 뿐이다. 정작 라우트/팩토리 안에서 실제로 호출하는 **`Container.get(타입)`은 평범한 동기(sync) 메서드**다(`_core.py`에 `def get(...)`과 `async def aget(...)`이 별도로 존재). 즉 `async def container(...)`를 쓰더라도 `UserRepository`, `UserLogic`처럼 완전히 동기식인 이 프로젝트의 도메인 코드는 **아무 수정 없이 그대로 `container.get(UserLogic)`으로 꺼내 쓸 수 있다.** FastAPI가 async 의존성과 sync 의존성이 섞인 그래프를 알아서 처리해주므로, 이 프로젝트가 지금처럼 라우트를 `def`(동기)로 유지하든 나중에 `async def`로 바꾸든 svcs 도입 자체가 걸림돌이 되지 않는다.
- **26.2.0 신규 기능 확인**: `svcs.fastapi.registry`/`DepRegistry`(레지스트리 자체를 라우트에서 직접 주입받는 기능)가 이 설치 버전에 정확히 `versionadded: 26.2.0`으로 방금 추가된 최신 기능임을 소스에서 확인했다 — 관리자/디버그용 라우트에서 "현재 등록된 서비스 목록"을 조회하는 용도 등에 활용 가능하다.

### 8-6. 예외 처리 — `svcs.exceptions.ServiceNotFoundError`

```python
# svcs/exceptions.py
class ServiceNotFoundError(Exception):
    """Raised when the requested service type is not registered."""
```

svcs가 노출하는 예외는 이 하나뿐이다. 등록을 빠뜨린 타입을 `container.get()`으로 요청하면 이 예외가 발생하므로, 도입 시 `app/app.py`에 **전역 예외 핸들러**(현재 프로젝트엔 아직 없음 — 별도 리팩토링 리포트의 5순위 항목)를 등록해 `ServiceNotFoundError`를 500으로 안전하게 변환하고 로깅하는 처리를 함께 추가하는 것을 권장한다.

### 8-7. 재검증 결론

7절에서 설명한 내용(등록 방식, `autowire` 사용법, FastAPI 통합 코드 예시)은 실제 설치된 `svcs==26.2.0` 소스와 **모두 일치**했다. 다만 다음 세부사항은 이번 소스 확인을 통해 새로 보강되었다.

1. `register_factory`에 `enter`/`ping`/`on_registry_close`/`suppress_context_exit` 옵션이 있어, 현재 `get_db()`의 수동 `try/finally` 정리 로직을 등록 옵션만으로 대체할 수 있다.
2. `autowire`는 **클래스 정의부가 아니라 등록 시점에만** 감싸야 한다는 공식 경고가 소스에 명시되어 있다 — 7절 예시가 이미 올바른 방식이었음을 재확인.
3. `svcs.fastapi.container`가 async여도 `Container.get()` 자체는 동기 메서드라, 이 프로젝트의 완전 동기식 SQLAlchemy 코드와 **수정 없이 호환**된다.
4. `svcs.fastapi.registry`/`DepRegistry`는 26.2.0에 막 추가된 최신 기능이다.
5. `ServiceNotFoundError` 전역 처리를 도입 계획에 포함해야 한다.

---

## 9. 마이그레이션 절차 제안 (svcs `autowire` 기준)

> 확장 로드맵이 정해져 있어 7~8절의 svcs 방식으로 갈 경우의 절차다. **핵심 특징은 `Repository`/`Logic`/`Flow`/`Fetch` 클래스 코드는 단 한 줄도 안 바뀐다는 것** — 오직 "새 등록 파일 1개 추가", "`app.py` lifespan 교체", "라우트에서 컨테이너로 서비스 꺼내는 방식으로 교체", "기존 `_dependency.py` 4개 삭제"만 하면 된다.

### 9-1. 의존성 추가 — 완료됨

`uv add svcs`로 이미 설치됨(`svcs==26.2.0`, `pyproject.toml`에 `svcs>=26.2.0` 반영 확인).

### 9-2. 중앙 등록 파일 신설 — `app/bootstrap.py`

도메인/피처가 늘어날 때 앞으로 계속 손댈 **유일한 파일**이다. 각 클래스는 지금 코드 그대로 두고, 여기서만 타입↔팩토리를 연결한다.

```python
# app/bootstrap.py  (신규)
import svcs
from sqlalchemy.orm import Session

from app.config.database import get_db
from domain.user import UserLogic, UserRepository
from domain.dept import DeptLogic, DeptRepository
from feature.signup import SignupFlow, SignupFetch
from feature.organization import OrganizationFlow, OrganizationFetch


def register_services(registry: svcs.Registry) -> None:
    """도메인/피처가 늘어날 때마다 이 함수에 등록 라인만 추가하면 된다."""

    # 인프라: get_db()는 제너레이터 함수라 register_factory가 자동으로
    # contextmanager로 감싸 요청 종료 시 db.close()까지 대신 처리해준다 (8-3 참고).
    registry.register_factory(Session, get_db)

    # domain/user, domain/dept — 클래스 코드 변경 없음
    registry.register_factory(UserRepository, svcs.autowire(UserRepository))
    registry.register_factory(DeptRepository, svcs.autowire(DeptRepository))
    registry.register_factory(UserLogic, svcs.autowire(UserLogic))
    registry.register_factory(DeptLogic, svcs.autowire(DeptLogic))

    # feature/signup, feature/organization — 클래스 코드 변경 없음
    registry.register_factory(SignupFlow, svcs.autowire(SignupFlow))
    registry.register_factory(SignupFetch, svcs.autowire(SignupFetch))
    registry.register_factory(OrganizationFlow, svcs.autowire(OrganizationFlow))
    registry.register_factory(OrganizationFetch, svcs.autowire(OrganizationFetch))
```

> 주의(8-4 참고): `svcs.autowire(UserLogic)`처럼 **등록 시점에만** 감싸야 한다. `domain/user/user_logic.py`의 `UserLogic` 클래스 정의부에는 어떤 데코레이터도 추가하지 않는다.

### 9-3. `app/app.py` — lifespan을 svcs 인식형으로 교체

```python
# app/app.py  (Before → After)

import svcs                                    # 추가
from fastapi import FastAPI

from app.config.database import engine
from app.bootstrap import register_services     # 추가
from shared.models import Base
from domain.user.user_entity import User  # noqa: F401
from domain.dept.dept_entity import Dept  # noqa: F401

from route.signup import signup_flow_router, signup_fetch_router
from route.organization import organization_flow_router, organization_fetch_router


@svcs.fastapi.lifespan                          # @asynccontextmanager 대신
async def lifespan(app: FastAPI, registry: svcs.Registry):   # registry 파라미터 추가
    """startup : 테이블 없으면 생성, 있으면 그대로 (데이터 유지)"""
    Base.metadata.create_all(bind=engine)
    register_services(registry)                 # 서비스 등록 한 줄 추가
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

기존 테이블 생성/로그 로직은 그대로 두고, `@asynccontextmanager` → `@svcs.fastapi.lifespan`로 바꾸고 `registry` 파라미터와 `register_services(registry)` 호출 한 줄만 추가하면 된다.

### 9-4. Route 계층 — 컨테이너에서 꺼내 쓰는 방식으로 교체

```python
# route/signup/signup_flow_route.py  (Before)
from feature.signup import get_signup_flow
...
def signup(request: SignupCommand, signup_flow: SignupFlow = Depends(get_signup_flow)):
  return signup_flow.signup(request.request)
```

```python
# route/signup/signup_flow_route.py  (After)
import svcs
from feature.signup import SignupFlow
...
def signup(request: SignupCommand, services: svcs.fastapi.DepContainer):
  signup_flow = services.get(SignupFlow)
  return signup_flow.signup(request.request)
```

- `services: svcs.fastapi.DepContainer`는 요청마다 컨테이너를 주입받는 표준 별칭이다.
- `services.get(SignupFlow)`는 **동기 메서드**이므로(8-5 참고), 라우트를 지금처럼 `def`(동기)로 유지해도 그대로 동작한다.
- `organization_flow_route.py`, `organization_fetch_route.py`, `signup_fetch_route.py`도 동일하게 `Depends(get_xxx_...)` → `services.get(Xxx...)`로 바꾼다.

### 9-5. 기존 팩토리 파일 삭제 및 `__init__.py` 정리

- 삭제: `domain/user/user_dependency.py`, `domain/dept/dept_dependency.py`, `feature/signup/signup_dependency.py`, `feature/organization/organization_dependency.py`
- `domain/user/__init__.py` 등에서 `get_user_logic` re-export 제거:

```python
# domain/user/__init__.py (After)
from domain.user.user_entity import User
from domain.user.user_dto import UserCreate, UserUpdate, UserResponse
from domain.user.user_logic import UserLogic

__all__ = ["User", "UserCreate", "UserUpdate", "UserResponse", "UserLogic"]
```

`feature/signup/__init__.py`도 같은 방식으로 `get_signup_flow`/`get_signup_fetch` re-export만 제거한다.

### 9-6. 예외 처리 보강 (권장)

8-6에서 확인한 `svcs.exceptions.ServiceNotFoundError`(등록 누락 시 발생)를 `app/app.py`에 전역 예외 핸들러로 추가해, 등록을 빠뜨렸을 때 원인 불명 500 대신 명확한 로그/응답이 나오도록 한다.

### 9-7. 테스트에서 목(mock) 교체 방법

```python
from svcs.fastapi import get_registry

def test_signup_with_fake_repo(app):
    registry = get_registry(app)
    registry.register_factory(UserRepository, lambda: FakeUserRepository())
    # 이후 TestClient로 호출하면 FakeUserRepository가 주입됨
```

### 9-8. 동작 확인

회원가입, 조직 관리(등록/수정/삭제/부서변경) 엔드포인트를 순서대로 호출해 기존과 동일하게 동작하는지 확인한다. 9-2(등록 파일)~9-5(파일 삭제)는 서로 독립적이지 않으므로 — bootstrap 파일과 app.py 교체 → 라우트 교체 → 기존 파일 삭제 순서로 한 번에 진행하되, 새 도메인을 추가하는 이후 작업부터는 9-2 파일에 두 줄만 추가하면 되므로 반복 비용이 크게 줄어든다.

---

## 10. 마이그레이션 절차 제안 (B안 기준)

> 아래는 "지금 당장, 소규모 유지" 전제의 B안(FastAPI 클래스 의존성) 마이그레이션 절차다. 확장 로드맵이 이미 정해져 있다면 9절의 svcs `autowire` 방식을 우선 검토하고, 이 절차는 건너뛰는 것을 권장한다.

1. **Repository 먼저**: `UserRepository`, `DeptRepository`의 `__init__`에 `db: Session = Depends(get_db)` 기본값 추가.
2. **Logic**: `UserLogic`, `DeptLogic`의 `__init__`에 `Depends(UserRepository)` / `Depends(DeptRepository)` 추가 → `domain/user/user_dependency.py`, `domain/dept/dept_dependency.py` 삭제, 각 도메인 `__init__.py`의 re-export를 `get_user_logic` → `UserLogic`으로 정리.
3. **Flow/Fetch**: `SignupFlow`, `SignupFetch`, `OrganizationFlow`, `OrganizationFetch`의 `__init__`에 `Depends(UserLogic)` / `Depends(DeptLogic)` 추가 → `feature/signup/signup_dependency.py`, `feature/organization/organization_dependency.py` 삭제.
4. **Route**: 각 라우트 파일에서 `Depends(get_signup_flow)` 등을 `Depends(SignupFlow)`로 교체하고 관련 import 정리.
5. **동작 확인**: 회원가입, 조직 관리(등록/수정/삭제/부서변경) 엔드포인트를 순서대로 호출해 기존과 동일하게 동작하는지 확인. (2~4단계는 계층별로 독립적이라 한 계층씩 나눠서 커밋해도 무방)

각 단계는 이전 계층에 의존하지 않고 파일 몇 개만 바뀌는 국소적 변경이라, 한 번에 전체를 바꾸기보다 계층별로 나눠 진행하면 리스크를 줄일 수 있다.
