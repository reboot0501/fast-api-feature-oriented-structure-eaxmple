# shared/utils/name_value_utils.py

from typing import Any, Iterable, TypeVar
from pydantic import BaseModel
from shared.models import NameValue

T = TypeVar("T")

# 수정 감지 대상에서 제외할 기본 시스템/불변 속성
DEFAULT_IGNORED_PROPERTIES = frozenset({
    "id",
    "created_at",
    "created_by",
    "_sa_instance_state",
})


def is_valid_update_property_name(
    domain_property_names: Iterable[str], 
    name_values: list[NameValue]
) -> bool:
    """
    name_values에 포함된 name들이 허용된 도메인 속성 목록(domain_property_names)에 모두 존재하는지 검증합니다.

    :param domain_property_names: 수정 가능한 도메인 속성 이름 목록 (list, set, tuple 등)
    :param name_values: 클라이언트가 전달한 NameValue 목록
    :return: 
      - name_values 중 domain_property_names에 없는 name이 하나라도 존재하면 False
      - 모든 name이 domain_property_names에 존재하면 True (비어있는 경우도 True)
    """
    if not name_values:
        return True

    allowed_names = set(domain_property_names)
    input_names = {nv.name for nv in name_values}

    # input_names가 allowed_names의 부분집합인지 확인
    return input_names.issubset(allowed_names)


def get_invalid_property_names(
    domain_property_names: Iterable[str], 
    name_values: list[NameValue]
) -> list[str]:
    """
    도메인 속성 목록에 존재하지 않는 잘못된(허용되지 않은) name 목록을 반환합니다.
    - 예외 메시지나 로깅 시 유용하게 사용할 수 있습니다.

    :param domain_property_names: 허용된 도메인 속성 이름 목록
    :param name_values: 클라이언트가 전달한 NameValue 목록
    :return: 허용되지 않은 속성명 리스트
    """
    allowed_names = set(domain_property_names)
    return [nv.name for nv in name_values if nv.name not in allowed_names]


def _extract_property_names(entity: Any) -> list[str]:
    """엔티티 객체(SQLAlchemy 모델, Pydantic 모델, 일반 클래스)로부터 비교 대상 속성명 목록 추출"""
    if hasattr(entity, "__table__"):
        # SQLAlchemy ORM 모델인 경우 테이블 컬럼명 추출
        return [col.key for col in entity.__table__.columns]
    elif isinstance(entity, BaseModel):
        # Pydantic 모델인 경우 필드명 추출
        return list(entity.model_fields.keys())
    elif hasattr(entity, "__dict__"):
        # 일반 파이썬 클래스 객체
        return [
            k for k, v in vars(entity).items()
            if not k.startswith("_") and not callable(v)
        ]
    return []


def get_modified_name_values(
    old_entity: T, 
    new_entity: T,
    ignored_properties: Iterable[str] | None = None,
) -> list[NameValue]:
    """
    기존 엔티티(old_entity)와 새 엔티티(new_entity)를 비교하여 변경된 속성 목록을
    list[NameValue] 형태로 반환합니다.
    (Java Entities.getModifiedNameValues(DomainEntity oldEntity, DomainEntity newEntity) 대응)

    :param old_entity: 수정 전 기존 도메인 엔티티 객체
    :param new_entity: 수정 후 신규 도메인 엔티티 객체
    :param ignored_properties: 변경 감지 대상에서 제외할 속성명 (기본: id, created_at, created_by 등)
    :return: 변경된 속성명과 새 값을 담은 NameValue 리스트
    """
    if old_entity is None or new_entity is None:
        return []

    ignore_set = set(DEFAULT_IGNORED_PROPERTIES)
    if ignored_properties:
        ignore_set.update(ignored_properties)

    # 비교 대상 속성명 추출 (old_entity 우선, 없으면 new_entity)
    prop_names = _extract_property_names(old_entity)
    if not prop_names:
        prop_names = _extract_property_names(new_entity)

    name_values: list[NameValue] = []
    for prop in prop_names:
        if prop in ignore_set:
            continue

        old_val = getattr(old_entity, prop, None)
        new_val = getattr(new_entity, prop, None)

        # 두 값이 다른 경우에만 NameValue로 추출 (deepEquals 대응)
        if old_val != new_val:
            name_values.append(NameValue.of(prop, new_val))

    return name_values


if __name__ == "__main__":
    from shared.utils.logging_helper import logger

    allowed_props = ["name", "desc", "dept_id"]

    # 케이스 1: 모든 속성이 유효한 경우 -> True
    valid_nv = [
        NameValue.of("name", "개발팀"),
        NameValue.of("desc", "신규 플랫폼 개발"),
    ]
    logger.info("모두 유효할 때: %s", is_valid_update_property_name(allowed_props, valid_nv))  # True

    # 케이스 2: 허용되지 않은 속성('password', 'created_at')이 포함된 경우 -> False
    invalid_nv = [
        NameValue.of("name", "개발팀"),
        NameValue.of("password", "1234"),  # 허용되지 않음!
    ]
    logger.info("없는 속성이 있을 때: %s", is_valid_update_property_name(allowed_props, invalid_nv))  # False
    logger.info("잘못된 속성 목록: %s", get_invalid_property_names(allowed_props, invalid_nv))  # ['password']
