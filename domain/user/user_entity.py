# domain/user/user_entity.py

from sqlalchemy import String
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from shared.models import BaseEntity
from shared.utils import get_current_time

""" SQLAlchemy 2.0 스타일
Mapped[T] 와 mapped_column() 을 사용해서 컬럼을 정의
타입 힌트 (int, str) 와 매핑이 연결되므로 IDE 자동완성, 타입 검증 지원이 강화됩니다.
"""

class User(BaseEntity):
  __tablename__ = "tb_user"
  """
  id(UUID), created_at, created_by, updated_at, updated_by 컬럼이 자동 생성
  """
  email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
  name: Mapped[str] = mapped_column(String(50), nullable=False)
  password: Mapped[str] = mapped_column(String(255), nullable=False)
  dept_id: Mapped[str] = mapped_column(String(36), nullable=False)
  # created_at(감사용 DB 서버 시각)과 별개로, 회원가입 시점을 애플리케이션 시계 기준
  # ISO 문자열로 남기는 비즈니스 속성. get_current_time()이 INSERT 시점에 Python
  # 레벨에서 호출되어 채워진다(SQLAlchemy의 클라이언트 사이드 default).
  signed_up_at: Mapped[str] = mapped_column(
    String(50),
    default=get_current_time,
    nullable=False,
    comment="회원가입일시",
  )
  