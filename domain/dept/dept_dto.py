# domain/dept/dept_dto.py

from pydantic import ConfigDict
from pydantic import BaseModel
from shared.utils import AtLeastOneValueMixin, UuidToStrMixin

# 부서 생성
class DeptCreate(BaseModel):
  name: str
  desc: str | None = None

# 부서 응답 데이터 ( 부서 정보 리턴 )
class DeptResponse(UuidToStrMixin):
  """
  1. ORM 엔티티의 UUID 기본키(id)를 응답 DTO의 문자열 id 필드로 자동 변환하는 공용 Mixin 클래스(UuidToStrMixin) 상속
  2. SQLAlchemy의 ORM 객체를 Pydantic DTO(응답 모델)로 자동 변환
  model_config = ConfigDict(from_attributes=True) 일때

  dept = db.get(Dept, dept_id)  # SQLAlchemy 객체
  # 1줄로 자동 변환 (또는 라우터에서 그냥 return user 만 해도 FastAPI가 자동 변환)
  return DeptResponse.model_validate(dept)
  """
  model_config = ConfigDict(from_attributes=True)  # ORM 객체 자동 변환 지원

  id: str
  name: str
  desc: str | None = None

# 부서 수정
class DeptUpdate(AtLeastOneValueMixin):
  """
  1. 수정 DTO에 하나 이상의 속성이 포함되었는지 검증하는 공용 Mixin 클래스(AtLeastOneValueMixin) 상속
  """
  name: str | None = None
  desc: str | None = None
