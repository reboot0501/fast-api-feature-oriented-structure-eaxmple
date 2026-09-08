# [Clause 분석 리포트] 프로젝트 개선 리팩토링 계획

> 작성 배경: `app/route/shared`, `domain`, `feature` 세 영역을 전수 조사(Explore 서브에이전트 3개 병렬 분석 + 핵심 항목 직접 재검증)하여 발견한 리팩토링 대상을 정리한 문서입니다.

## 0. 아키텍처 개요 및 총평

이 프로젝트는 `route(HTTP) → feature(유스케이스 오케스트레이션, Flow/Fetch) → domain(도메인 서비스, Logic/Repository/Entity/Dto) → shared(공통)` 4계층 구조이며, `doc/` 문서에 명시된 아래 규칙들은 실제 코드에서도 잘 지켜지고 있습니다.

- `domain/<sub>/xxx_repository.py`는 자기 도메인 폴더 밖에서 import되지 않음 (레포지토리 캡슐화 원칙 준수)
- `domain/__init__.py`는 비어 있고, 각 서브 도메인 `__init__.py`가 선택적으로 re-export (경계 컨텍스트 오염 방지)
- `route → feature → domain` 의존 방향 위반 없음 (grep으로 확인: domain이 feature/route를 import하는 곳 없음)
- 트랜잭션은 `@transactional`(ContextVar 기반 depth 추적)로 Logic/Flow가 소유, Repository는 `flush()`만 수행

다만 **`user` 도메인과 `dept` 도메인 사이의 구현 일관성이 깨져 있어**, 이로 인한 실행 시 즉시 발생하는 버그가 다수 확인되었습니다. 또한 중복 코드, 죽은 코드(dead code), 문서/설정 불일치도 함께 정리가 필요합니다.

---

## 1순위 — 런타임 버그 (즉시 수정 필요)

실제 API 호출 시 500 에러로 이어지는 항목들입니다.

| #   | 문제                                                      | 위치                                                                                                                   | 상세                                                                                                                                                                                                                                                                                                                                                                                                          |
| --- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 부서 등록 시 Pydantic DTO를 ORM 엔티티 자리에 그대로 전달 | `domain/dept/dept_logic.py:15`, `feature/organization/organization_flow.py:17-21`, `domain/dept/dept_repository.py:12` | `DeptLogic.register_dept(self, dept: Dept)`가 실제로는 `DeptCreate`(Pydantic)를 그대로 받아 `Repository.create_dept`의 `db.add(dept)`로 전달됨 → `session.add()`에 매핑되지 않은 객체를 넘겨 `UnmappedInstanceError` 발생. `domain/user/user_logic.py:19-33`의 `User(**user_data)`처럼 DTO→Entity 변환 단계가 빠져 있음. 이로 인해 `DeptAlreadyExistsException` 중복 체크 로직도 아예 존재하지 않음.          |
| 2   | 존재하지 않는 메서드 호출                                 | `feature/organization/organization_flow.py:47-51`                                                                      | `self.dept_logic.remove_dept(dept_id)` 호출하지만 `DeptLogic`에는 `delete_dept`만 존재(`domain/dept/dept_logic.py:68`) → `AttributeError`. `POST /organization/delete_depts` 엔드포인트가 완전히 깨져 있음.                                                                                                                                                                                                   |
| 3   | 공용 예외 클래스 생성자와 호출부 시그니처 불일치          | `shared/utils/exception.py` 전체, 호출부 7곳                                                                           | `UserNotFoundException` 등 모든 예외가 `__init__(self)` (인자 없음)로 정의되어 있으나, 호출부는 전부 `XxxException(id)` 형태로 인자를 전달함(`domain/user/user_logic.py:40,55,67`, `feature/signup/signup_fetch.py:19,23`, `feature/signup/signup_flow.py:19`, `feature/organization/organization_flow.py:35`). 의도한 404/400 대신 `TypeError`로 500 발생 — **에러 처리 경로 전체가 사실상 동작 불능** 상태. |
| 4   | 삭제 메서드가 선언된 반환 타입을 지키지 않음              | `domain/dept/dept_repository.py`, `domain/user/user_repository.py`의 `delete_dept`/`delete_user`                       | `return`문이 없어 항상 `None` 반환. `response_model=list[bool]`, 상위 메서드의 `-> bool` 시그니처와 불일치.                                                                                                                                                                                                                                                                                                   |

---

## 2순위 — 보안 / 설정

| #   | 문제                           | 상세                                                                                                                                                                             |
| --- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5   | `.env` Git 제외 설정 완료      | `.gitignore`에 `.env`를 추가해 로컬 자격 증명이 `git add .` 대상에 포함되지 않도록 수정했다. `git check-ignore .env`로 제외 상태를 확인한다.                                     |
| 6   | 환경 변수명 `DB_DRIVER`로 통일 | `.env.example`, 실제 `.env`, `app/config/database.py`가 모두 `DB_DRIVER`를 사용하도록 통일하고 fallback 조회를 제거했다.                                                         |
| 7   | uv 단일 의존성 관리로 정리     | `pyproject.toml`과 `uv.lock`만 의존성 기준으로 사용하도록 정리하고, 중복 `requirements.txt`와 오타 파일 안내를 제거했다. README도 `uv sync`와 `uv run pytest` 기준으로 갱신했다. |

---

## 3순위 — 도메인 간 일관성 (user vs dept)

같은 패턴으로 구현돼야 할 두 도메인이 서로 다르게 구현되어 있으며, 이는 1순위 버그들의 근본 원인이기도 합니다.

| #   | 문제                              | 상세                                                                                                                                                                                                                                                                                          |
| --- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 8   | `@transactional` 적용 범위 불일치 | `UserLogic`은 `register/modify/remove_user` 전부 데코레이터 적용, `DeptLogic`은 어떤 변경 메서드에도 미적용. `OrganizationFlow.register_depts`도 `modify_depts`/`remove_depts`와 달리 `@transactional` 누락 → 부서 일괄 등록 중 일부 실패 시 롤백되지 않음.                                   |
| 9   | 삭제 메서드 네이밍 불일치         | `UserLogic.remove_user` vs `DeptLogic.delete_dept` — 버그 #2의 직접적 원인.                                                                                                                                                                                                                   |
| 10  | 응답 DTO 비대칭                   | `DeptResponse`엔 `id` 필드가 있지만(`domain/dept/dept_dto.py:25`) `UserResponse`엔 없음(`domain/user/user_dto.py`) → 회원가입 응답이 클라이언트에 PK를 전혀 알려주지 않음.                                                                                                                    |
| 11  | 문서(독스트링)와 실제 동작 불일치 | `UserLogic.remove_user` 독스트링은 "소프트 삭제(`deleted_yn`)"를 주장하지만 실제로는 `db.delete(user)` 하드 삭제이며, `User`/`AuditMixin`/`BaseEntity` 어디에도 `deleted_yn` 컬럼이 존재하지 않음.                                                                                            |
| 12  | 죽은 CRUD 경로                    | `UserUpdate` / `UserLogic.modify_user`는 어디서도 호출되지 않는 미완성 기능(수정 API 자체가 없음). `DeptUpdate` 및 그 "필드 최소 1개" 검증 로직도 실제 라우트(`ModifyDeptsCommand`는 `IdNameValues` 사용)에서 쓰이지 않아 dead code — 실제 부서 수정 경로에는 해당 검증이 전혀 적용되지 않음. |

---

## 4순위 — 중복 코드 추출 대상

| #   | 중복 내용                                 | 위치                                                                                                                                            | 제안                                                       |
| --- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 13  | 페이지네이션 보일러플레이트               | `UserRepository`/`DeptRepository`의 offset 계산, `order.lower()=="asc"` 분기, `.order_by().offset().limit().all()` 체인, `count_*_by_name_like` | 공용 `paginate()` 헬퍼 또는 `BaseRepository` 클래스로 추출 |
| 14  | "필드 최소 1개 필요" 검증기               | `UserUpdate`/`DeptUpdate`의 `@model_validator` 로직(한글 주석까지 동일하게 복붙됨)                                                              | `shared/`에 공용 mixin으로 추출                            |
| 15  | count → fetch → wrap 패턴 4회 반복        | `feature/organization/organization_fetch.py`의 `find_users`, `find_depts`                                                                       | 13번 헬퍼로 흡수 가능                                      |
| 16  | `Flow`/`Fetch`용 DI 팩토리 보일러플레이트 | `signup_dependency.py` vs `organization_dependency.py` (클래스명만 다르고 구조 동일)                                                            | 도메인이 늘어날 경우 팩토리 생성기 도입 고려               |

---

## 5순위 — 정리(Cleanup)

- **`route/organiztion` 디렉터리명 오타** ("organization"의 a 누락) — `from route.organiztion...` 형태로 import 경로 전체에 전파되어 있어, 이름 변경 시 관련 import 6곳 이상 수정 필요.
- **`logger` 미사용, `print()`로 대체됨** — `shared/utils/logging.py`에 로거가 구성돼 있지만 어디서도 import되지 않음. `app/app.py:20,23`의 lifespan 이벤트가 `print()` 사용 중 → 로거로 교체 필요.
- **미사용 코드** — `shared/utils/time_helper.py`(전체 미사용), `OrganizationFlow.__init__`의 `user_logic`(어떤 메서드에서도 사용되지 않음).
- **`__main__` 데모 블록이 프로덕션 모듈에 남아있음** — `shared/models/name_value.py`, `id_name_values.py`, `shared/utils/name_value_utils.py` 등. `tests/` 디렉터리가 프로젝트에 전혀 없고 `pytest` 등 테스트 의존성도 설치돼 있지 않음 → **자동화된 테스트 커버리지 0%**.
- **README가 실제 구조와 불일치** — README의 "프로젝트 구조" 절이 `app/core/`, `app/features/users/` 등 실제로 존재하지 않는 경로를 문서화하고 있어 신규 기여자에게 혼선을 줄 수 있음 → 실제 구조로 갱신 필요.
- **기타 사소한 오타/스타일** — `app.title`의 "Stuctucture" 오타, `route/signup`이 `route/organiztion`의 요청 모델을 직접 import하여 수직 슬라이스 격리가 깨짐, 생성(POST) 라우터의 응답 코드가 기본 200으로 남아 있음(201/204 미사용).

---

## 진행 제안

1. **1순위(런타임 버그 4건)**: 리스크 낮고 영향 범위 명확 — 최우선 적용 권장.
2. **2순위(보안/설정)**: `.gitignore` 수정은 즉시 처리, 의존성 파일 정리는 팀 컨벤션 확인 후 진행.
3. **3~4순위**: `dept` 도메인을 `user` 패턴에 맞춰 정렬하면서 동시에 공용 헬퍼(`paginate`, `AtLeastOneField` mixin)를 `shared/`로 추출하는 리팩토링. 두 도메인을 함께 손대야 효율적이므로 한 번에 진행 권장.
4. **5순위**: 별도 커밋으로 가볍게 정리. 단, 디렉터리 리네임(`organiztion` → `organization`)은 import 파급 범위가 커서 단독 커밋으로 분리 권장.
