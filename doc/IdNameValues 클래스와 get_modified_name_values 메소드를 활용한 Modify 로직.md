# `IdNameValues` 클래스와 `get_modified_name_values` 메소드를 활용한 Modify 로직

## 1. 목적

부서 수정 API는 수정 대상 부서의 ID와 변경할 속성 목록을 함께 전달하는 `IdNameValues` 구조를 사용합니다.

```text
IdNameValues
  - id: 수정 대상 Entity ID
  - nameValues: 수정할 속성명과 값의 목록
```

이 문서는 다음 두 가지를 설명합니다.

1. `IdNameValues`를 사용해 부서의 `name`과 `desc`를 함께 수정하는 요청 형식
2. `get_modified_name_values()`를 사용해 실제로 변경된 속성만 추출하고, 변경 사항이 있을 때만 Modify 로직을 실행하는 방법

관련 구현:

- `shared/models/id_name_values.py`
- `shared/models/name_value.py`
- `shared/utils/name_value_helper.py`
- `feature/organization/organization_flow.py`
- `domain/dept/dept_logic.py`

## 2. 수정 요청 JSON

부서 ID가 `dept-001`인 부서의 이름과 설명을 동시에 변경하는 요청은 다음과 같습니다.

```json
{
  "depts": [
    {
      "id": "dept-001",
      "nameValues": [
        {
          "name": "name",
          "value": "개발팀"
        },
        {
          "name": "desc",
          "value": "플랫폼 개발 및 운영을 담당하는 부서"
        }
      ]
    }
  ]
}
```

`nameValues`에는 다음 두 변경 사항이 담깁니다.

| name   | value                                 |
| :----- | :------------------------------------ |
| `name` | `개발팀`                              |
| `desc` | `플랫폼 개발 및 운영을 담당하는 부서` |

`nameValues`는 JSON의 `camelCase` 이름이고, Pydantic의 `alias="nameValues"` 설정을 통해 Python 코드에서는 `name_values`로 접근합니다.

## 3. `IdNameValues` 내부 구조

### 3.1 `NameValue`

`NameValue`는 속성명과 값을 하나의 객체로 표현합니다.

```python
NameValue(name="name", value="개발팀")
NameValue(name="desc", value="플랫폼 개발 및 운영을 담당하는 부서")
```

`NameValue.of()`를 사용하면 값을 `NameValue` 형식으로 만들 수 있습니다.

```python
from shared.models import NameValue

name_value = NameValue.of("name", "개발팀")
desc_value = NameValue.of(
  "desc",
  "플랫폼 개발 및 운영을 담당하는 부서",
)
```

`NameValue.of()`는 기본형 값을 문자열로 변환합니다. 현재 부서의 `name`, `desc` 컬럼이 문자열이므로 이 동작은 부서 수정에 적합합니다.

### 3.2 `IdNameValues`

```python
from shared.models import IdNameValues, NameValue

modify_request = IdNameValues(
  id="dept-001",
  name_values=[
    NameValue.of("name", "개발팀"),
    NameValue.of("desc", "플랫폼 개발 및 운영을 담당하는 부서"),
  ],
)
```

`to_dict()`는 `nameValues` 목록을 Entity 수정에 사용할 수 있는 dictionary로 변환합니다.

```python
update_data = modify_request.to_dict()

# 결과
{
  "name": "개발팀",
  "desc": "플랫폼 개발 및 운영을 담당하는 부서"
}
```

현재 부서 수정 호출 흐름은 다음과 같습니다.

```text
ModifyDeptsCommand
  -> OrganizationFlow.modify_depts()
    -> OrganizationFlow.modify_dept()
      -> IdNameValues.to_dict()
        -> DeptLogic.modify_dept()
          -> DeptRepository.update_dept()
```

## 4. 현재 Modify 로직

현재 `OrganizationFlow.modify_dept()`는 요청의 `IdNameValues`를 받아 대상 Entity를 조회합니다. 이후 요청값을 복사본에 반영하고 `get_modified_name_values()`로 실제 변경 속성만 계산한 뒤, 변경이 있을 때만 Domain Logic으로 전달합니다.

```python
@transactional
def modify_dept(self, dept_update: IdNameValues) -> DeptResponse:
  dept = self.dept_logic.retrieve_dept_by_id(dept_update.id)
  if not dept:
    raise DeptNotFoundException(dept_update.id)

  candidate_dept = copy(dept)
  for key, value in dept_update.to_dict().items():
    setattr(candidate_dept, key, value)

  modified_values = get_modified_name_values(dept, candidate_dept)
  if not modified_values:
    return DeptResponse.model_validate(dept)

  update_data = {
    name_value.name: name_value.value
    for name_value in modified_values
  }
  updated_dept = self.dept_logic.modify_dept(dept, update_data)
  return DeptResponse.model_validate(updated_dept)
```

Repository는 전달된 dictionary의 각 항목을 Entity에 적용합니다.

```python
def update_dept(
  self,
  dept: Dept,
  update_data: dict | None = None,
) -> Dept:
  if update_data:
    for key, value in update_data.items():
      setattr(dept, key, value)

  self.db.flush()
  self.db.refresh(dept)
  return dept
```

## 5. `get_modified_name_values()`의 역할

`get_modified_name_values(old_entity, new_entity)`는 두 Entity를 비교해 값이 달라진 속성만 `list[NameValue]`로 추출합니다.

```python
from shared.utils import get_modified_name_values

modified_values = get_modified_name_values(old_dept, new_dept)
```

예를 들어 기존 Entity와 변경 후보 Entity가 다음과 같다고 가정합니다.

```text
old_dept
  name = "개발1팀"
  desc = "서비스 개발"

new_dept
  name = "개발팀"
  desc = "플랫폼 개발 및 운영을 담당하는 부서"
```

실행 결과는 다음과 같습니다.

```python
[
  NameValue(name="name", value="개발팀"),
  NameValue(
    name="desc",
    value="플랫폼 개발 및 운영을 담당하는 부서",
  ),
]
```

값이 변경되지 않은 속성은 결과에서 제외됩니다.

```text
old_dept.name == new_dept.name
  -> name 제외

old_dept.desc != new_dept.desc
  -> desc 포함
```

기본적으로 다음 속성은 비교 대상에서 제외됩니다.

```python
DEFAULT_IGNORED_PROPERTIES = frozenset({
  "id",
  "created_at",
  "created_by",
  "_sa_instance_state",
})
```

따라서 ID나 감사 컬럼이 변경된 것으로 잘못 판단되어 수정되는 것을 방지합니다.

## 6. 변경 목록이 존재할 때만 Modify 실행

수정 후보 Entity를 만든 뒤 `get_modified_name_values()`를 호출하고, 결과가 비어 있지 않을 때만 수정 작업을 실행합니다.

```python
from shared.utils import get_modified_name_values

modified_values = get_modified_name_values(
  old_entity=dept,
  new_entity=new_dept,
)

if not modified_values:
  # 변경된 값이 없으므로 DB update를 수행하지 않는다.
  return DeptResponse.model_validate(dept)

update_data = {
  item.name: item.value
  for item in modified_values
}

updated_dept = self.dept_logic.modify_dept(
  dept,
  update_data,
)
return DeptResponse.model_validate(updated_dept)
```

처리 순서는 다음과 같습니다.

```text
1. ID로 기존 부서 조회
2. 요청값을 반영한 new_dept 생성
3. old_dept와 new_dept 비교
4. 변경 목록 추출
5. 변경 목록이 비어 있으면 update 생략
6. 변경 목록이 있으면 dictionary로 변환
7. DeptLogic.modify_dept() 호출
8. Repository에서 실제 Entity 수정 및 flush
```

## 7. `IdNameValues`와 `get_modified_name_values()`의 관계

두 기능은 서로 다른 목적을 가집니다.

| 기능                           | 역할                                                     |
| :----------------------------- | :------------------------------------------------------- |
| `IdNameValues`                 | 클라이언트가 어떤 속성을 어떤 값으로 바꿀지 전달         |
| `to_dict()`                    | 요청 목록을 Entity 수정용 dictionary로 변환              |
| `get_modified_name_values()`   | 기존 Entity와 변경 후보 Entity를 비교해 실제 변경만 추출 |
| `DeptLogic.modify_dept()`      | 변경 dictionary를 Repository로 전달                      |
| `DeptRepository.update_dept()` | Entity에 값을 적용하고 `flush()` 수행                    |

즉, 요청값 자체를 바로 적용하는 단순한 흐름은 다음과 같습니다.

```text
IdNameValues -> to_dict() -> modify_dept()
```

현재 프로젝트가 사용하는 실제 변경 감지 흐름은 다음과 같습니다.

```text
IdNameValues
  -> 변경 후보 Entity 생성
  -> get_modified_name_values(old, new)
  -> 변경 목록이 있을 때만 to_dict/update 실행
```

## 8. 사용자 부서 변경에 `IdNameValues`를 재사용하는 경우

부서 수정과 사용자 부서 변경 모두 `ID + 변경 속성 목록`이라는 입력 형태를 사용하므로, 사용자 부서 변경에도 `IdNameValues`를 사용할 수 있습니다.

```json
{
  "users": [
    {
      "id": "user-001",
      "nameValues": [
        {
          "name": "dept_id",
          "value": "dept-002"
        }
      ]
    },
    {
      "id": "user-002",
      "nameValues": [
        {
          "name": "dept_id",
          "value": "dept-002"
        }
      ]
    }
  ]
}
```

### 8.1 계층별 처리 책임

`IdNameValues`는 HTTP 요청 형식과 범용 수정 표현을 담당합니다. 따라서 Route와 Feature 계층에서 해석하고 검증해야 합니다.

```text
Route
  -> list[IdNameValues] 요청 파싱
Feature
  -> id 추출
  -> nameValues에서 dept_id 추출
  -> dept_id 외 속성 포함 여부 검증
  -> 사용자/부서 존재 여부 확인
UserLogic
  -> user Entity와 new_dept_id 문자열만 수신
  -> dept_id 변경 규칙 수행
UserRepository
  -> {"dept_id": new_dept_id} 적용 및 flush
```

`UserLogic`까지 `IdNameValues`를 전달하지 않는 이유는 다음과 같습니다.

1. `IdNameValues`는 Pydantic 기반 HTTP 요청 DTO이므로 Domain Logic이 요청 형식에 결합되지 않아야 합니다.
2. `IdNameValues`는 `name`, `desc`, `password` 등 여러 속성을 표현할 수 있어 `dept_id`만 변경해야 하는 사용자 부서 변경 규칙을 보장하지 못합니다.
3. JSON의 `nameValues` alias, `to_dict()` 같은 요청 변환 책임은 Feature 계층에 두는 것이 적절합니다.
4. 요청 형식이 변경되어도 UserLogic은 `new_dept_id: str` 계약을 유지할 수 있습니다.

### 8.2 Feature에서 `dept_id`만 허용

사용자 부서 변경 Feature는 다음 규칙을 검증해야 합니다.

```python
update_data = user_change.to_dict()

if set(update_data) != {"dept_id"}:
  raise UpdateValueException()

new_dept_id = update_data["dept_id"]
```

다음 요청은 허용하지 않아야 합니다.

```json
{
  "id": "user-001",
  "nameValues": [
    {
      "name": "password",
      "value": "new-password"
    }
  ]
}
```

검증이 끝나면 Feature는 범용 DTO를 도메인 의미가 분명한 값으로 변환합니다.

```python
return self.user_logic.change_user_dept(
  user,
  new_dept_id,
)
```

UserLogic의 메서드 계약은 다음처럼 유지합니다.

```python
@transactional
def change_user_dept(
  self,
  user: User,
  new_dept_id: str,
) -> bool:
  return self.repo.update_user(
    user,
    {"dept_id": new_dept_id},
  ) is not None
```

### 8.3 사용자 부서 변경 호출 흐름

```text
ChangeUsersDeptCommand.users: list[IdNameValues]
  -> OrganizationFlow.change_users_dept()
    -> OrganizationFlow.change_user_dept(item: IdNameValues)
      -> item.id로 User 조회
      -> item.get_value("dept_id") 추출
      -> dept_id로 Dept 존재 확인
      -> UserLogic.change_user_dept(user, dept_id)
        -> UserRepository.update_user(user, {"dept_id": dept_id})
```

부서 수정과 사용자 부서 변경은 입력 모델을 공유할 수 있지만, 허용 속성은 서로 다릅니다.

| 기능             | 허용 속성      | Domain Logic 입력          |
| :--------------- | :------------- | :------------------------- |
| 부서 수정        | `name`, `desc` | `Dept`, `dict`             |
| 사용자 부서 변경 | `dept_id`만    | `User`, `new_dept_id: str` |

따라서 `IdNameValues`를 공유한다는 것은 요청 형식을 공유한다는 의미이지, 각 Domain Logic이 동일한 범용 DTO를 직접 받는다는 의미는 아닙니다.

## 9. 허용 가능한 속성 검증

클라이언트가 `password`, `id`, `created_at`처럼 수정해서는 안 되는 속성을 전달하지 못하도록 허용 목록을 검증해야 합니다.

```python
from shared.utils import (
  get_invalid_property_names,
  is_valid_update_property_name,
)

allowed_properties = {"name", "desc"}
name_values = modify_request.name_values

if not is_valid_update_property_name(
  allowed_properties,
  name_values,
):
  invalid_names = get_invalid_property_names(
    allowed_properties,
    name_values,
  )
  raise ValueError(
    f"수정할 수 없는 속성입니다: {invalid_names}"
  )
```

부서 수정에서는 최소한 다음 속성만 허용하는 것이 안전합니다.

```python
allowed_properties = {"name", "desc"}
```

`id`, `created_at`, `created_by`, `updated_at`, `updated_by`와 같은 시스템 속성은 클라이언트 요청으로 수정하지 않아야 합니다.

## 10. 빈 수정 요청 처리

다음 요청은 변경할 속성이 없으므로 Modify를 실행하면 안 됩니다.

```json
{
  "depts": [
    {
      "id": "dept-001",
      "nameValues": []
    }
  ]
}
```

권장 처리 방법은 두 가지입니다.

### 방법 1: 요청 단계에서 거부

`IdNameValues.name_values`에 `min_length=1`을 지정해 Pydantic이 `422`를 반환하게 합니다.

```python
name_values: list[NameValue] = Field(
  ...,
  min_length=1,
  alias="nameValues",
)
```

### 방법 2: Service 단계에서 조기 종료

이미 생성된 `IdNameValues`를 처리해야 한다면 다음처럼 빈 목록을 확인합니다.

```python
if not dept_update.name_values:
  return DeptResponse.model_validate(dept)
```

실제 변경 비교를 사용하는 경우에는 `get_modified_name_values()` 결과를 기준으로 조기 종료합니다.

```python
modified_values = get_modified_name_values(dept, new_dept)
if not modified_values:
  return DeptResponse.model_validate(dept)
```

## 11. Transaction 관계

부서 수정은 다음 두 transaction 경계를 거칩니다.

```text
OrganizationFlow.modify_dept()  @transactional  Root
  -> DeptLogic.modify_dept()    @transactional  Child
    -> DeptRepository.update_dept()             flush only
```

`OrganizationFlow.modify_depts()`는 여러 부서 수정 전체를 하나의 작업으로 묶습니다.

```text
OrganizationFlow.modify_depts() @transactional
  -> modify_dept(dept-001)
  -> modify_dept(dept-002)
  -> modify_dept(dept-003)
  -> 모두 성공하면 commit 1회
  -> 하나라도 예외가 발생하면 전체 rollback
```

따라서 Repository에서 `commit()`을 호출하지 않고 `flush()`만 호출해야 합니다.

## 12. 핵심 정리

1. 클라이언트는 `IdNameValues`의 `nameValues`에 수정할 속성 목록을 전달합니다.
2. `name`과 `desc`는 하나의 요청에서 동시에 전달할 수 있습니다.
3. `to_dict()`는 `NameValue` 목록을 Entity 수정용 dictionary로 바꿉니다.
4. `get_modified_name_values()`는 실제 값이 바뀐 속성만 추출합니다.
5. 변경 목록이 비어 있으면 `modify` 로직과 DB `flush()`를 실행하지 않습니다.
6. 수정 가능한 속성은 `name`, `desc`처럼 허용 목록으로 제한해야 합니다.
7. Feature는 transaction Root, Domain Logic은 Child, Repository는 `flush()` 담당입니다.
8. 현재 프로젝트의 `OrganizationFlow.modify_dept()`는 요청값을 Entity 복사본에 반영한 뒤 `get_modified_name_values()`로 실제 변경 목록을 추출하고, 변경이 있을 때만 `DeptLogic.modify_dept()`를 호출합니다.
9. 사용자 부서 변경에서 `IdNameValues`를 사용할 경우 `dept_id`만 허용하고, Feature에서 값을 추출한 뒤 UserLogic에는 문자열만 전달합니다.
