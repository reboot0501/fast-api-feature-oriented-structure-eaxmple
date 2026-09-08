# domain/dept/dept_entity.py

from shared.models import BaseEntity
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

""" SQLAlchemy 2.0 스타일
Mapped[T] 와 mapped_column() 을 사용해서 컬럼을 정의
타입 힌트 (int, str) 와 매핑이 연결되므로 IDE 자동완성, 타입 검증 지원이 강화됩니다.
"""

class Dept(BaseEntity):
  __tablename__ = "tb_dept"
  """
  id(UUID), created_at, created_by, updated_at, updated_by 컬럼이 자동 생성
  """
  name: Mapped[str] = mapped_column(String(50), nullable=False)
  desc: Mapped[str] = mapped_column(String(255), nullable=True)