# Feature-Oriented Structure with FastAPI & Pydantic v2 & SQLAlchemy 2.0

FastAPI 기반의 기능 중심 구조(Feature-Oriented Architecture) 예제 프로젝트입니다.  
`fast-api-sqlalchemy-transactional-example` 프로젝트의 아키텍처 및 라이브러리 구성을 분석하여 동일한 스택을 지원하도록 구성되었으며, 이후 `svcs` 기반 Composition Root 패턴 도입 등 자체적인 리팩토링을 거쳤습니다.

---

## 1. 기술 스택

| 구분 | 기술 | 역할 |
| :--- | :--- | :--- |
| 언어 | **Python 3.12** (`.python-version`) | 런타임 |
| 웹 프레임워크 | **FastAPI** `>=0.116.1` | 비동기 웹 API, 라우팅, 의존성 주입 |
| ASGI 서버 | **Uvicorn** `>=0.35.0` | 애플리케이션 구동 |
| 데이터 검증 | **Pydantic v2** `>=2.10.0` | 요청/응답 스키마 검증 및 직렬화 |
| ORM | **SQLAlchemy 2.0** `>=2.0.43` | DB 세션·트랜잭션·엔티티 매핑 |
| 데이터베이스 | **Oracle Database** (`oracledb` `>=3.4.0`) | 영속 계층 |
| DI / 컴포지션 루트 | **svcs** `>=26.2.0` | 서비스 등록·조회를 담당하는 IoC 컨테이너 (4절 참고) |
| 인증/보안 | **passlib[bcrypt]** `>=1.7.4` + **bcrypt** `<4.1` | 비밀번호 단방향 해싱 |
| 패키지 관리 | **uv** | 의존성 설치·잠금(`uv.lock`)·실행 |
| 테스트 | **pytest** `>=8.3.2` | 단위/계약 테스트 (`tests/`, 36개) |

---

## 2. 프로젝트 생성 및 가상환경 설정 가이드

### 1) 프로젝트 생성 및 이동 (최초 1회)

```bash
uv init fast-api-feature-oriented-structure-eaxmple
cd fast-api-feature-oriented-structure-eaxmple
```

### 2) 패키지 라이브러리 설치

#### ① 런타임(핵심) 의존성

`pyproject.toml`의 `[project.dependencies]` 기준입니다.

| 패키지명            | 버전 기준   | 역할 및 용도                                                 |
| :------------------ | :---------- | :----------------------------------------------------------- |
| **fastapi**         | `>=0.116.1` | 고성능 비동기 웹 API 프레임워크 (라우팅, 의존성 주입 등)     |
| **uvicorn**         | `>=0.35.0`  | 고성능 ASGI 서버 (애플리케이션 구동)                         |
| **sqlalchemy**      | `>=2.0.43`  | 차세대 Python ORM 및 데이터베이스 세션/트랜잭션 관리         |
| **oracledb**        | `>=3.4.0`   | Oracle Database 공식 클라이언트 드라이버 (`oracle+oracledb`) |
| **pydantic**        | `>=2.10.0`  | 데이터 유효성 검증 및 Schemas 직렬화/역직렬화                |
| **email-validator** | `>=2.3.0`   | Pydantic `EmailStr` 이메일 형식 유효성 검증 지원             |
| **passlib[bcrypt]** | `>=1.7.4`   | 비밀번호 안전한 단방향 해싱 및 암호화 (`bcrypt`)             |
| **bcrypt**          | `<4.1`      | `passlib 1.7.4`가 `bcrypt.__about__`를 참조하는데 `bcrypt>=4.1`부터 이 속성이 제거되어 해싱 시 `ValueError`가 발생한다 — 호환 가능한 상한선을 명시적으로 고정 |
| **cryptography**    | `>=45.0.7`  | 데이터 암호화 및 DB 통신/보안 프로토콜 지원                  |
| **python-dotenv**   | `>=1.1.1`   | `.env` 파일 기반 환경 변수 로드 및 설정 관리                 |
| **svcs**            | `>=26.2.0`  | Composition Root/IoC 컨테이너 — 도메인·피처 서비스 등록 및 요청 스코프 조회 (4절 참고) |

#### ② 개발(테스트) 의존성

`pyproject.toml`의 `[dependency-groups] dev` 기준이며, `uv sync` 시 함께 설치됩니다.

| 패키지명       | 버전 기준  | 역할 및 용도                                   |
| :------------- | :--------- | :---------------------------------------------- |
| **pytest**     | `>=8.3.2`  | `tests/` 아래 단위·계약 테스트 실행             |
| **httpx2**     | `>=2.12.0` | `fastapi.testclient.TestClient`가 내부적으로 사용하는 HTTP 클라이언트 |

#### ③ uv 의존성 동기화

```bash
uv sync
```

### 3) 환경 변수 설정

`.env.example`을 `.env`로 복사한 뒤 로컬 DB 접속 정보를 입력합니다. `.env`에는 자격 증명이 포함되므로 `.gitignore`에 등록되어 Git에 추가되지 않습니다.

```powershell
Copy-Item .env.example .env
```

### 4) 테스트 실행

```bash
uv run pytest
```

`pyproject.toml`의 `[tool.pytest.ini_options] pythonpath = ["."]` 설정 덕분에 별도로 `PYTHONPATH`를 지정하지 않아도 `app`/`domain`/`feature`/`route`/`shared` 모듈을 바로 import할 수 있습니다.

---

## 3. 프로젝트 구조 (Feature-Oriented Structure)

```
fast-api-feature-oriented-structure-eaxmple/
│
├── pyproject.toml           # uv 프로젝트 설정, 의존성 메타데이터, pytest 설정
├── uv.lock                  # 잠금된 패키지 의존성 버전 파일
├── .env.example             # 환경 변수 예시 템플릿
├── project_run.bat          # 로컬 개발 서버 실행 스크립트(Windows)
│
├── app/                     # 애플리케이션 부트스트랩 계층
│   ├── main.py               # 진입점 (uvicorn CLI가 이 모듈의 app 객체를 구동)
│   ├── app.py                 # FastAPI 인스턴스 생성, lifespan, 라우터 등록
│   ├── bootstrap.py            # svcs Composition Root — register_services() (4절 참고)
│   └── config/
│       ├── database.py          # SQLAlchemy 엔진/SessionLocal/get_db()
│       └── transaction.py        # @transactional 데코레이터 (트랜잭션 경계 관리)
│
├── route/                   # HTTP 계층 — 요청 DTO, FastAPI 라우터
│   ├── signup/                # 회원가입 관리 (signup_flow_route.py, signup_fetch_route.py, request_*.py)
│   └── organization/           # 조직 관리 (organization_flow_route.py, organization_fetch_route.py, request_*.py)
│
├── feature/                 # 유스케이스 오케스트레이션 계층 — Flow(쓰기)/Fetch(읽기)
│   ├── signup/                # SignupFlow, SignupFetch
│   └── organization/           # OrganizationFlow, OrganizationFetch
│
├── domain/                  # 도메인 서비스 계층 — 도메인별 완전히 독립된 수직 슬라이스
│   ├── user/                  # user_entity / user_dto / user_logic / user_repository / user_dependency
│   └── dept/                   # dept_entity / dept_dto / dept_logic / dept_repository / dept_dependency
│
├── shared/                  # 도메인 간 공유되는 모델·유틸리티
│   ├── models/                # BaseEntity, NameValue, IdNameValues, OffsetElementList, exception
│   └── utils/                  # hash_helper, pagination_helper, mixin_helper, uuid_helper, logging_helper 등
│
├── tests/                   # pytest 단위/계약 테스트 (36개)
│
└── doc/                     # 아키텍처 의사결정 기록(설계 배경, 패턴 설명)
```

**계층 간 의존 방향**: `route → feature → domain → shared` 한 방향으로만 흐릅니다. `domain/<sub>/xxx_repository.py`는 자기 도메인 폴더 밖에서 import되지 않도록 캡슐화되어 있고(예: `UserRepository`는 `domain/user/user_dependency.py` 안에서만 참조), 이 규칙은 `doc/Database Layer 와 가장 가까운 Repository 캡슐화 원칙 반영과 feature 와 route Layer 조립방법 정리.md`에 정리되어 있습니다.

---

## 4. Composition Root 패턴 (svcs 기반 IoC 컨테이너)

> 전체 설계 배경과 마이그레이션 과정은 [`doc/Composition Root 패턴(svcs 기반 IoC 컨테이너 부트스트랩 패턴).md`](<doc/Composition Root 패턴(svcs 기반 IoC 컨테이너 부트스트랩 패턴).md>) 문서를 참고하세요.

이 프로젝트는 `svcs`를 IoC 컨테이너로 사용해 **등록(registration)**과 **조회(resolution)**를 완전히 분리했습니다.

- **등록은 앱 시작 시 한 번, `app/bootstrap.py`에서만** 이루어집니다. 각 도메인/피처는 자기 자신을 스스로 등록하는 `register(registry)` 함수를 노출하고(`domain/user/user_dependency.py` 등), `bootstrap.py`는 그 함수들을 호출해 모으기만 합니다.
- **조회는 요청마다 라우트 계층에서만** 이루어집니다. `Logic`/`Flow`/`Repository` 클래스는 `svcs`를 전혀 import하지 않는 순수한 생성자 타입 힌트만 가지며, `svcs.autowire(...)`가 그 타입 힌트를 읽어 자동으로 의존성을 조립합니다.

```python
# app/bootstrap.py — 등록은 여기서 한 번
def register_services(registry: svcs.Registry) -> None:
    registry.register_factory(Session, get_db)
    register_user(registry)          # domain/user/user_dependency.py의 register()
    register_dept(registry)
    register_signup(registry)
    register_organization(registry)

# route/signup/signup_flow_route.py — 조회는 여기서만
@router.post("/", response_model=UserResponse)
def signup(request: SignupCommand, services: svcs.fastapi.DepContainer):
    signup_flow = services.get(SignupFlow)   # 여기서 전체 의존성 그래프가 자동 조립됨
    return signup_flow.signup(request.request)
```

도메인/피처가 늘어날 때 새로 손대야 하는 파일은 "그 도메인 자신의 `xxx_dependency.py`"와 "`app/bootstrap.py`의 등록 호출 한 줄"뿐입니다.

---

## 5. 프로젝트 실행 방법

> 아래 두 방법 모두 **Uvicorn CLI 방식**(`uv run uvicorn app.main:app ...`)을 기준으로 합니다. `app/main.py`를 `python app/main.py`로 직접 실행하는 방법(`if __name__ == "__main__":` + `sys.path.insert(...)`)도 파일 안에 남아있어 IDE 디버거로 원클릭 구동할 때 쓸 수 있지만, 실무 표준은 아래 CLI 방식입니다. 두 방식을 비교한 이유는 [`doc/실무에서 Uvicorn CLI 명령어 방식으로 프로젝트 실행.md`](<doc/실무에서 Uvicorn CLI 명령어 방식으로 프로젝트 실행.md>)에 정리되어 있으며, 핵심만 요약하면 다음과 같습니다.
>
> - **운영(Docker/K8s) 환경과의 일관성** — 컨테이너 배포 시 결국 `CMD ["uvicorn", ...]`처럼 CLI로 구동하므로, 로컬도 처음부터 CLI로 맞추면 로컬·운영 간 동작 괴리가 없다.
> - **`sys.path` 조작 불필요** — CLI는 항상 프로젝트 루트를 기준으로 모듈을 탐색하므로, 직접 실행 방식에 필요한 `sys.path.insert(0, ...)` 같은 코드가 필요 없다.
> - **관심사 분리** — `app/main.py`(비즈니스 앱 정의)와 Uvicorn(포트 바인딩, 워커 수, 리로드 등 서버 인프라 제어)의 책임이 명확히 나뉜다.
> - **인프라 파라미터 유연성** — 호스트, 포트, 워커 수, 로그 레벨 등을 코드 수정 없이 커맨드라인 인자만으로 환경별로 바꿀 수 있다.

### 5-1. 실무에서 권장하는 실행 방법 (운영 지향)

핫 리로드 없이, 여러 워커 프로세스로, 모든 인터페이스에 바인딩해 구동합니다.

```bash
# 워커 4개, 리로드 비활성화, 모든 인터페이스에 바인딩
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

컨테이너 배포 시에는 동일한 커맨드를 그대로 `Dockerfile`의 `CMD`에 사용합니다(다중 프로세스가 필요하면 Gunicorn + Uvicorn 워커 조합도 널리 쓰입니다).

```dockerfile
# 1) 단일 프로세스
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 2) 프로덕션 멀티 프로세스 (Gunicorn 마스터 + Uvicorn 워커)
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### 5-2. 로컬 테스트용 실행 방법 (개발 지향)

핫 리로드를 켜서 코드 변경이 저장 즉시 반영되도록, `localhost`에만 바인딩해 구동합니다.

```bash
# uv를 사용한 개발 서버 구동 (핫 리로드 활성화)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Windows에서는 `project_run.bat`을 더블 클릭하거나 `.\project_run.bat`으로 동일한 커맨드를 바로 실행할 수 있습니다.

- Swagger API Docs: `http://127.0.0.1:8000/docs`
- Redoc API Docs: `http://127.0.0.1:8000/redoc`

서버를 띄우지 않고 로직 변경을 빠르게 검증하려면 테스트 스위트를 실행합니다(자세한 내용은 6절 참고).

```bash
uv run pytest
```

---

## 6. 테스트 스위트 (`tests/`)

`uv run pytest`는 **`tests/` 아래 작성된 테스트를 파일·함수 구분 없이 전부** 실행합니다. 별도로 어떤 파일을 실행할지 지정할 필요가 없습니다.

### 왜 전부 자동으로 실행되는가

`pytest`는 기본적으로 프로젝트 루트부터 재귀적으로 훑으면서 **`test_*.py`(또는 `*_test.py`) 이름 규칙에 맞는 파일**을 찾고, 그 안에서 **`test_`로 시작하는 함수**를 전부 실행 대상으로 수집합니다. `pyproject.toml`의 `[tool.pytest.ini_options]`에는 `pythonpath`만 지정했을 뿐 실행 범위(`testpaths`)를 제한하지 않았으므로, 이 기본 규칙 그대로 프로젝트 전체(사실상 `tests/`)를 대상으로 삼습니다.

### 현재 수집되는 테스트 (13개 파일, 36개 케이스)

`uv run pytest --collect-only -q`로 직접 확인한 목록입니다.

| 파일 | 테스트 케이스 수 | 검증 대상 |
| :--- | :---: | :--- |
| `test_change_users_dept_api.py` | 1 | 사용자 일괄 부서변경 요청 모델 |
| `test_change_users_dept_flow.py` | 2 | 부서변경 Flow의 `IdNameValues` 파싱/검증 |
| `test_delete_api.py` | 1 | 삭제 API의 불리언 응답 |
| `test_delete_contract.py` | 5 | Repository 삭제 성공/실패 시 반환값 계약 |
| `test_dept_logic.py` | 2 | 부서 등록 시 DTO→Entity 변환, 중복 이름 거부 |
| `test_exception_api.py` | 3 | 커스텀 예외의 HTTP 상태 코드 매핑 |
| `test_exception_contract.py` | 3 | 예외 생성자 시그니처 계약(파라미터화) |
| `test_exception_exports.py` | 2 | 예외 클래스의 공개 export 위치 |
| `test_organization_modify_flow.py` | 4 | 부서 수정 시 변경된 속성만 반영되는지 |
| `test_pagination_helper.py` | 3 | 공용 `paginate()` 헬퍼의 페이징/정렬 |
| `test_transaction_boundaries.py` | 3 | `@transactional` 트랜잭션 경계 |
| `test_update_dto_validation.py` | 6 | Update DTO "최소 1개 필드" 검증(파라미터화) |
| `test_user_change_dept.py` | 1 | 사용자 단건 부서변경 |
| **합계** | **36** | |

### 함수 개수(33)보다 테스트 케이스 수(36)가 더 많은 이유

`@pytest.mark.parametrize`로 작성된 테스트는 함수 1개가 여러 개의 테스트 케이스로 자동 확장됩니다.

```python
@pytest.mark.parametrize("update_type", [UserUpdate, DeptUpdate])
def test_update_dto_requires_at_least_one_value(update_type):
    ...
```

이 함수 하나는 실제로는 `test_update_dto_requires_at_least_one_value[UserUpdate]`와 `[DeptUpdate]` **2개의 독립된 케이스**로 실행·집계됩니다. `test_exception_contract.py`, `test_update_dto_validation.py`가 이 방식을 쓰고 있어, 정의된 함수 수(33개)보다 실제 실행되는 테스트 케이스 수(36개)가 더 많습니다.
