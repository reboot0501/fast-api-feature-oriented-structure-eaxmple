# Request 파라미터 객체 속성들의 유효성 검증 방법 정리

본 문서는 FastAPI 및 Pydantic v2 환경에서 **핸들러 내부의 수동 `validate()`/`assert` 방식을 지양하고, Pydantic의 `Field(...)` 및 타입 시스템을 활용한 선언적 자동 유효성 검증(Validation) 원칙과 실무 패턴**을 정리한 문서입니다.

---

## 1. 문제 배경: 수동 `validate()`와 `assert` 사용 시의 한계

초기 구현에서는 요청 DTO 클래스에 `validate()` 메서드를 두고, 라우트 핸들러 내부에서 이를 수동으로 호출하는 패턴을 자주 사용합니다.

```python
# ❌ 안티 패턴: 수동 검증 메서드와 assert 사용
class FindSignedUserFetch:
    user_id: str | None

    def validate(self):
        assert self.user_id is not None, "'user_id' is required"

@router.post("/find_signed_user")
def find_signed_user(request: FindSignedUserFetch):
    request.validate()  # 👈 핸들러마다 일일이 수동 호출
    return fetch.find_signed_user(request.user_id)
```

### 왜 이것이 실무에서 치명적인 문제가 되는가?

1. **`AssertionError`로 인한 500 Internal Server Error 발생**:
   * `assert` 키워드는 테스트나 내부 단언용입니다. 요청 파라미터가 누락되었을 때 `assert`가 실패하면 `AssertionError`가 발생하며, 이는 FastAPI의 일반 예외 핸들러에 의해 **클라이언트 오류(4xx)가 아닌 서버 장애(500)**로 응답됩니다.
2. **보일러플레이트(반복 코드) 발생**:
   * 모든 라우트 핸들러의 첫 줄마다 `request.validate()`를 빼놓지 않고 호출해야 하며, 누락 시 치명적인 버그가 됩니다.
3. **OpenAPI (Swagger UI) 문서화 불가**:
   * `assert` 로직은 실행 시점에만 동작하므로, Swagger UI 문서에 "이 필드가 필수인지, 최소 몇 자인지, 정렬 옵션에 어떤 값이 허용되는지"가 전혀 표시되지 않습니다.
4. **파이썬 최적화 모드(`-O`) 취약점**:
   * 운영 환경에서 파이썬을 `python -O`로 구동할 경우, 인터프리터가 모든 `assert` 구문을 컴파일 단계에서 제거하므로 검증 로직이 완전히 무력화됩니다.

---

## 2. 해결 원칙: Pydantic v2 + FastAPI 선언적 자동 검증

FastAPI는 엔드포인트 함수가 실행되기 전에 **Pydantic 모델을 통해 요청 데이터를 먼저 직렬화/역직렬화하고 검증**합니다.

```
[클라이언트 요청]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI / Pydantic 엔진                  │
│  - 타입 변환 (str -> int, UUID 파싱)                  │
│  - Field(...) 제약 조건 검증 (min_length, ge, pattern) │
└───────────────────────┬────────────────────────────────┘
                        │
       ┌────────────────┴────────────────┐
 [검증 실패 ❌]                      [검증 성공 ✅]
       ▼                                 ▼
 즉시 422 Unprocessable           핸들러 함수 실행
 Entity 응답 반환                 (순수 비즈니스 로직만 수행)
 (어느 필드가 왜 틀렸는지 상세 JSON)
```

따라서 라우트 핸들러 내부에서는 `request.validate()` 같은 코드를 **단 한 줄도 작성할 필요가 없습니다.**

---

## 3. Pydantic `Field(...)` 핵심 검증 옵션 가이드

### 1) 필수값 vs 선택값/기본값 지정

| 형식 | 의미 | 설명 |
| :--- | :--- | :--- |
| `Field(...)` | **필수값 (Required)** | 요청 Body에 이 필드가 없으면 즉시 422 반환 |
| `Field(default=None)` | **선택값 (Optional)** | 생략 시 `None`으로 자동 설정 |
| `Field(default=10)` | **기본값 지정** | 생략 시 지정된 기본값이 설정됨 |

### 2) 데이터 타입별 세부 제약 조건

#### ① 문자열 (String) 제약 조건
* `min_length=1`: 빈 문자열(`""`) 방지
* `max_length=50`: 최대 글자 수 제한
* `pattern="정규표현식"`: 허용 포맷 제약 (예: `pattern="^(asc|desc)$"`)

#### ② 숫자 (Integer / Float) 제약 조건
* `ge=1`: 크거나 같음 ($\ge$, Greater than or Equal)
* `gt=0`: 초과 ($>$, Greater Than)
* `le=100`: 작거나 같음 ($\le$, Less than or Equal)
* `lt=100`: 미만 ($<$, Less Than)

#### ③ 컬렉션 (List) 제약 조건
* `min_length=1`: 최소 1개 이상의 원소를 포함해야 함 (빈 배열 `[]` 차단)
* `max_length=100`: 최대 원소 개수 제한 (대량 트래픽 DoS 방지)

#### ④ 특수 타입 활용
* `EmailStr`: 이메일 형식 자동 검증 (예: `user@example.com`)
* `uuid.UUID`: UUID 표준 형식 자동 파싱 및 검증

---

## 4. 실무 적용 예시 (Before vs After)

### 1) Command DTO: 일괄 등록/수정/삭제 (`request_organization_command.py`)

빈 리스트(`[]`)가 들어와 의미 없는 DB 쿼리가 실행되는 것을 방지합니다.

```python
# route/organiztion/request_organization_command.py

from pydantic import BaseModel, Field
from domain.dept import DeptCreate, DeptUpdate

class RegisterDeptsCommand(BaseModel):
    # ✅ min_length=1: 등록할 부서 목록이 최소 1건 이상이어야 함
    depts: list[DeptCreate] = Field(..., min_length=1, description="등록할 부서 목록")

class ModifyDeptsCommand(BaseModel):
    depts: list[DeptUpdate] = Field(..., min_length=1, description="수정할 부서 목록")

class RemoveDeptsCommand(BaseModel):
    depts: list[str] = Field(..., min_length=1, description="삭제할 부서 ID 목록")
```

---

### 2) Fetch DTO: 페이징 및 정렬 제약 (`request_organization_fetch.py`)

사용자가 음수 페이지를 요청하거나 비정상적인 대량 페이지 크기(`size=999999`)를 요청하는 것을 방지합니다.

```python
# route/organiztion/request_organization_fetch.py

from pydantic import BaseModel, Field

class FindUsersFetch(BaseModel):
    user_name: str | None = Field(default=None, description="검색할 사용자 이름")
    dept_id: str | None = Field(default=None, description="소속 부서 ID")
    
    # ✅ page는 1 이상이어야 함
    page: int = Field(default=1, ge=1, description="페이지 번호 (1부터 시작)")
    
    # ✅ size는 최소 1개 ~ 최대 100개까지만 허용 (DB 부하 방지)
    size: int = Field(default=10, ge=1, le=100, description="페이지당 개수")
    
    # ✅ order는 오직 'asc' 또는 'desc'만 허용
    order: str = Field(default="desc", pattern="^(asc|desc)$", description="정렬 방향")
```

---

### 3) Route 핸들러의 변화 (완전한 책임 분리)

#### ❌ Before: 수동 검증으로 지저분한 라우터
```python
@router.post("/register_depts")
def register_depts(request: RegisterDeptsCommand, flow = Depends(...)):
    request.validate()  # 👈 수동 검증 (실패 시 500 에러 위험)
    return flow.register_depts(request.depts)
```

#### ✅ After: 비즈니스 흐름에만 집중하는 클린 라우터
```python
@router.post("/register_depts", response_model=list[DeptResponse])
def register_depts(
    request: RegisterDeptsCommand, 
    flow: OrganizationFlow = Depends(get_organization_flow)
):
    # ✅ 라우터 진입 전에 Pydantic이 모든 유효성을 보증하므로 바로 위임!
    return flow.register_depts(request.depts)
```

---

## 5. 고급: 교차 필드 검증이 필요한 경우 (`@model_validator`)

단일 필드의 범위 검증을 넘어 **"여러 필드 간의 상호 관계"**를 검증해야 할 때는 `@model_validator(mode="after")`를 사용합니다.

### 예시: 수정 요청 시 최소 1개 필드는 입력되었는지 검증 ([`domain/dept/dept_dto.py`](file:///d:/project-workspace/fast-api-feature-oriented-structure-eaxmple/domain/dept/dept_dto.py#L30))

```python
class DeptUpdate(BaseModel):
    name: str | None = None
    desc: str | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        # 1) 요청 JSON에 필드 자체가 하나도 전송되지 않은 경우 ({})
        # 2) 또는 전송된 필드들의 값이 모두 None인 경우 방어
        provided_values = [getattr(self, field) for field in self.model_fields_set]
        if not self.model_fields_set or all(v is None for v in provided_values):
            raise UpdateValueException() # 422 상태 코드 반환
        return self
```

---

## 6. 핵심 요약 및 실무 가이드라인

1. **`assert` 키워드는 웹 요청 검증에 절대 사용하지 않는다.**
   - 클라이언트 입력값 검증 실패는 서버 에러(500)가 아닌 클라이언트 입력 에러(422)여야 합니다.
2. **모든 요청 DTO(Command, Fetch)는 `BaseModel`을 상속하고 `Field(...)`로 제약을 선언한다.**
   - 필수값은 `...`, 빈 배열 방지는 `min_length=1`, 페이징 크기 상한선은 `le=100`을 명시합니다.
3. **Route 계층에서는 검증 로직을 완전히 제거한다.**
   - 라우터 핸들러는 `request`가 무조건 유효하다고 신뢰하고 비즈니스 흐름(`flow`/`fetch`) 호출에만 집중합니다.
4. **Swagger UI를 적극 활용한다.**
   - `Field(..., description="...")`를 작성해 두면 프론트엔드 개발자 및 API 사용자가 API 문서를 보고 제약 조건을 즉시 파악할 수 있습니다.
