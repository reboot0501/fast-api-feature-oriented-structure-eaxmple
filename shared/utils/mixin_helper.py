import uuid
from typing import Any, Self

from pydantic import BaseModel, field_validator, model_validator

from shared.models.exception import UpdateValueException


class AtLeastOneValueMixin(BaseModel):
  """수정 DTO에 하나 이상의 실제 값이 포함되었는지 검증하는 공용 Mixin"""

  @model_validator(mode="after")
  def validate_at_least_one_value(self) -> Self:
    provided_values = [
      getattr(self, field)
      for field in self.model_fields_set
    ]

    if (
      not self.model_fields_set
      or all(value is None for value in provided_values)
    ):
      raise UpdateValueException()

    return self


class UuidToStrMixin(BaseModel):
  """
  ORM 엔티티의 UUID 기본키(id)를 응답 DTO의 문자열 id 필드로 자동 변환하는 공용 Mixin.

  BaseEntity.id는 SQLAlchemy Uuid(as_uuid=True)라 조회 시 uuid.UUID 객체로 채워지는데,
  응답 DTO는 id: str로 선언되어 있다. Pydantic v2는 uuid.UUID -> str을 자동으로
  강제 변환(coerce)하지 않으므로(ResponseValidationError 발생), 여기서 명시적으로 변환한다.
  """

  @field_validator("id", mode="before", check_fields=False)
  @classmethod
  def _stringify_id(cls, value: Any) -> Any:
    if isinstance(value, uuid.UUID):
      return str(value)
    return value
