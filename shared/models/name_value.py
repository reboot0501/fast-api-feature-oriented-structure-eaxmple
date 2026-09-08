# shared/models/name_value.py

import json
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class NameValue(BaseModel):
    """
    이름-값(Key-Value) 쌍을 표현하는 범용 공통 모델
    Java의 NameValue 패턴을 Pydantic v2 기반으로 구현
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    name: str = Field(..., description="속성명 (Name/Key)")
    value: str | None = Field(default=None, description="속성값 (Value)")

    @classmethod
    def of(cls, name: str, value: Any = None) -> "NameValue":
        """
        팩토리 메서드:
        - value가 None이면 None 유지
        - value가 BaseModel 객체이면 model_dump_json()으로 직렬화
        - value가 dict, list 등 복합 객체이면 json.dumps()로 직렬화
        - 그 외 기본형(str, int, float, bool 등)이면 str() 문자열 변환
        """
        if value is None:
            formatted_value = None
        elif isinstance(value, BaseModel):
            formatted_value = value.model_dump_json()
        elif isinstance(value, (dict, list)):
            formatted_value = json.dumps(value, ensure_ascii=False)
        else:
            formatted_value = str(value)

        return cls(name=name, value=formatted_value)

    @classmethod
    def from_json(cls, json_str: str) -> "NameValue":
        """JSON 문자열로부터 NameValue 인스턴스 역직렬화 생성"""
        return cls.model_validate_json(json_str)

    def to_json(self) -> str:
        """JSON 문자열로 직렬화 반환"""
        return self.model_dump_json()

    def to_simple_string(self) -> str:
        """'name:value' 형식의 단순 문자열로 반환"""
        val = "" if self.value is None else self.value
        return f"{self.name}:{val}"

    @classmethod
    def from_simple_string(cls, name_value_str: str) -> "NameValue":
        """
        'name:value' 형식의 문자열을 파싱하여 NameValue 인스턴스 생성
        (Java의 StringTokenizer 동작 모사)
        """
        parts = name_value_str.split(":", 1)
        name = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        return cls(name=name, value=value)

    def __str__(self) -> str:
        """Java toString()과 동일하게 JSON 문자열 반환"""
        return self.to_json()

    def __eq__(self, other: object) -> bool:
        """객체 동등성 비교"""
        if not isinstance(other, NameValue):
            return False
        return self.name == other.name and self.value == other.value

    def __hash__(self) -> int:
        """해시코드 생성"""
        return hash((self.name, self.value))

    @classmethod
    def sample(cls) -> "NameValue":
        """테스트 및 예시용 샘플 인스턴스"""
        return cls(name="name", value="Cheolsoo Kim")


if __name__ == "__main__":
    from shared.utils.logging_helper import logger

    sample = NameValue.sample()
    logger.info("toString(): %s", sample)
    logger.info("toSimpleString(): %s", sample.to_simple_string())

    # 복합 객체 of() 테스트
    nv = NameValue.of("user", {"id": 1, "name": "Hong"})
    logger.info("of(dict): %s", nv)

    # from_simple_string 테스트
    parsed = NameValue.from_simple_string("dept:Development")
    logger.info("from_simple_string(): %s", parsed)
