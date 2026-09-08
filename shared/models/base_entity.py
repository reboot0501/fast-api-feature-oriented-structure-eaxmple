# shared/models/base_entity.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# 상단에 SQL 표현식 객체를 한 번만 선언
CURRENT_TIMESTAMP = func.now()

# Defualt User 정의
DEFAULT_USER = "SYSTEM"  

# 1. SQLAlchemy 2.0 최상위 Base 클래스 (모든 엔티티 모델이 상속)
class Base(DeclarativeBase):
    """모든 도메인 엔티티의 최상위 Base"""
    pass


# 2. 감사(Audit) 공통 믹스인: 생성/수정 일시 및 생성/수정자 정보
class AuditMixin:
    """모든 테이블에 공통 감사(Audit) 컬럼을 부여하는 믹스인"""
    
    # [ 생성 정보 ]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=CURRENT_TIMESTAMP,
        nullable=False,
        comment="생성일시",
    )

    created_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=DEFAULT_USER, # DEFAULT_USER를 DB 레벨에서 관리
        comment="생성자 ID",
    )

    # [ 수정 정보 ]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=CURRENT_TIMESTAMP,
        onupdate=CURRENT_TIMESTAMP,
        nullable=False,
        comment="수정일시",
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=DEFAULT_USER,
        comment="수정자 ID",
    )


# 3. 범용 UUID PK + Audit 컬럼을 포함하는 BaseEntity 추상 클래스
class BaseEntity(Base, AuditMixin):
    """
    Oracle, PostgreSQL, MySQL 모두에서 동작하는 UUID 기본키(PK) 및 Audit 추상 엔티티
    도메인 모델에서 상속하여 사용합니다.
    """
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,  # Python 레벨에서 표준 UUID v4 자동 생성
        comment="기본키 (UUID)",
    )
