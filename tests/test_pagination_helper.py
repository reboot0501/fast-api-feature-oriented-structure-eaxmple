from dataclasses import dataclass

import pytest

from shared.utils.pagination_helper import paginate


@dataclass
class FakeColumn:
  def asc(self):
    return "asc"

  def desc(self):
    return "desc"


class FakeQuery:
  def __init__(self):
    self.operations = []

  def order_by(self, value=None):
    self.operations.append(("order_by", value))
    return self

  def count(self):
    self.operations.append(("count",))
    return 25

  def offset(self, value):
    self.operations.append(("offset", value))
    return self

  def limit(self, value):
    self.operations.append(("limit", value))
    return self

  def all(self):
    self.operations.append(("all",))
    return ["item"]


def test_paginate_returns_items_metadata_and_applies_query_operations():
  query = FakeQuery()

  result = paginate(query, FakeColumn(), page=2, size=10, order="asc")

  assert result.items == ["item"]
  assert result.total_count == 25
  assert result.page == 2
  assert result.size == 10
  assert query.operations == [
    ("order_by", None),
    ("count",),
    ("order_by", "asc"),
    ("offset", 10),
    ("limit", 10),
    ("all",),
  ]


def test_paginate_normalizes_invalid_page_and_size():
  result = paginate(FakeQuery(), FakeColumn(), page=0, size=0)

  assert result.page == 1
  assert result.size == 1


def test_paginate_rejects_invalid_order():
  with pytest.raises(ValueError, match="asc.*desc"):
    paginate(FakeQuery(), FakeColumn(), order="invalid")