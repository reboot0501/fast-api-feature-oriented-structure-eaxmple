from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginationResult(Generic[T]):
  items: list[T]
  total_count: int
  page: int
  size: int


def paginate(
  query,
  order_column,
  page: int = 1,
  size: int = 10,
  order: str = "desc",
) -> PaginationResult[T]:
  page = max(1, page)
  size = max(1, size)
  normalized_order = order.lower()

  if normalized_order not in {"asc", "desc"}:
    raise ValueError("order must be 'asc' or 'desc'")

  total_count = query.order_by(None).count()
  order_clause = (
    order_column.asc()
    if normalized_order == "asc"
    else order_column.desc()
  )
  offset = (page - 1) * size
  items = (
    query
    .order_by(order_clause)
    .offset(offset)
    .limit(size)
    .all()
  )

  return PaginationResult(
    items=items,
    total_count=total_count,
    page=page,
    size=size,
  )
