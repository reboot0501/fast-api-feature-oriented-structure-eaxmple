# shared/models/offset_element_list.py
import math
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

# 제네릭 타입 변수 선언 (UserResponse, DeptResponse 등 어떤 DTO든 수용 가능)
T = TypeVar("T")


class OffsetElementList(BaseModel, Generic[T]):
    """
    오프셋 기반 페이징 공통 응답 제네릭 DTO
    Java의 OffsetElementList<T> 패턴을 Pydantic v2 제네릭 모델로 구현
    """
    model_config = ConfigDict(
        from_attributes=True, 
        populate_by_name=True, 
        arbitrary_types_allowed=True
    )

    results: list[T] = Field(default_factory=list, description="조회된 데이터 목록")
    total_count: int = Field(..., alias="totalCount", description="전체 데이터 건수")
    offset: int = Field(..., description="조회 시작 위치 (0-based)")
    limit: int = Field(..., description="조회 건수 제한 (size와 동일)")
    page: int = Field(..., description="현재 페이지 번호 (1-based)")
    size: int = Field(..., description="페이지당 건수")
    total_pages: int = Field(..., alias="totalPages", description="전체 페이지 수")
    has_next: bool = Field(..., alias="hasNext", description="다음 페이지 존재 여부")
    has_previous: bool = Field(..., alias="hasPrevious", description="이전 페이지 존재 여부")

    @property
    def elements(self) -> list[T]:
        return self.results

    @classmethod
    def of(

        cls,
        results: list[T],
        total_count: int,
        page: int = 1,
        size: int = 10,
    ) -> "OffsetElementList[T]":
        """
        데이터 목록과 총 건수, 페이지 번호, 사이즈를 받아
        offset, limit, totalPages, hasNext, hasPrevious를 자동 계산하여 생성하는 팩토리 메서드
        """
        page = max(1, page)
        size = max(1, size)
        offset = (page - 1) * size
        total_pages = math.ceil(total_count / size) if total_count > 0 else 0

        return cls(
            results=results,
            total_count=total_count,
            offset=offset,
            limit=size,
            page=page,
            size=size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
