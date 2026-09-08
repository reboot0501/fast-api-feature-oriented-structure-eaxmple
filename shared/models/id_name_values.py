# shared/models/id_name_values.py

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
try:
    from .name_value import NameValue
except ImportError:
    from shared.models.name_value import NameValue


class IdNameValues(BaseModel):
    """
    특정 식별자(ID)와 변경할 속성 목록(NameValue 리스트)을 묶은 범용 모델
    - 주로 단건/다건 동적 수정(PATCH/UPDATE) 요청이나 엔티티 속성 변경에 사용됩니다.
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: str = Field(..., description="대상 엔티티 ID")
    name_values: list[NameValue] = Field(
        default_factory=list, 
        alias="nameValues", 
        description="수정/적용할 Name-Value 목록"
    )

    @classmethod
    def of(cls, entity_id: str, values: list[NameValue] | dict[str, Any]) -> "IdNameValues":
        """
        팩토리 메서드:
        - values가 dict인 경우: 자동으로 list[NameValue]로 변환하여 생성
        - values가 list[NameValue]인 경우: 그대로 전달하여 생성
        """
        if isinstance(values, dict):
            nv_list = [NameValue.of(name=k, value=v) for k, v in values.items()]
        else:
            nv_list = values

        return cls(id=entity_id, name_values=nv_list)

    def to_dict(self) -> dict[str, Any]:
        """
        name_values 리스트를 딕셔너리 {name: value} 형태로 변환
        (Repository update나 엔티티 setattr 시 매우 유용)
        """
        return {nv.name: nv.value for nv in self.name_values}

    def get_value(self, name: str, default: Any = None) -> Any:
        """
        특정 속성명(name)의 값을 단건 조회
        """
        for nv in self.name_values:
            if nv.name == name:
                return nv.value
        return default

    @classmethod
    def from_json(cls, json_str: str) -> "IdNameValues":
        """JSON 문자열로부터 인스턴스 역직렬화"""
        return cls.model_validate_json(json_str)

    def to_json(self) -> str:
        """JSON 문자열로 직렬화"""
        return self.model_dump_json()

    def __str__(self) -> str:
        return self.to_json()

    @classmethod
    def sample(cls) -> "IdNameValues":
        """테스트 및 예시용 샘플 인스턴스"""
        return cls.of(
            entity_id="dept-001",
            values={
                "name": "플랫폼개발팀",
                "desc": "클라우드 및 백엔드 플랫폼 개발",
            }
        )


if __name__ == "__main__":
    from shared.utils.logging_helper import logger

    sample = IdNameValues.sample()
    logger.info("Sample JSON: %s", sample)
    logger.info("to_dict(): %s", sample.to_dict())
    logger.info("get_value('name'): %s", sample.get_value("name"))
