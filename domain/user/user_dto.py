# domain/user/user_dto.py
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr
from shared.utils import AtLeastOneValueMixin, UuidToStrMixin

# 사용자 생성
class UserCreate(BaseModel):
  email: EmailStr
  name: str
  password: str
  dept_id: str


# 사용자 응답 데이터 ( 사용자 정보 리턴 )
class UserResponse(UuidToStrMixin):
  """
  1. ORM 엔티티의 UUID 기본키(id)를 응답 DTO의 문자열 id 필드로 자동 변환하는 공용 Mixin 클래스(UuidToStrMixin) 상속
  2. SQLAlchemy의 ORM 객체를 Pydantic DTO(응답 모델)로 자동 변환
  model_config = ConfigDict(from_attributes=True) 일때

  user = db.get(User, user_id)  # SQLAlchemy 객체
  # 1줄로 자동 변환 (또는 라우터에서 그냥 return user 만 해도 FastAPI가 자동 변환)
  return UserResponse.model_validate(user)
  """
  model_config = ConfigDict(from_attributes=True)  # ORM 객체 자동 변환 지원

  id: str
  email: str
  name: str
  dept_id: str
  dept_name: str | None = None
  signed_up_at: str


# 사용자 수정
class UserUpdate(AtLeastOneValueMixin):
  """
  1. 수정 DTO에 하나 이상의 속성이 포함되었는지 검증하는 공용 Mixin 클래스(AtLeastOneValueMixin) 상속
  """
  name: str | None = None
  dept_id: str | None = None
  email: EmailStr | None = None
  password: str | None = None
