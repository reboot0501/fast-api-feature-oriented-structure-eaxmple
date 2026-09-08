# app/config/transaction.py

from contextvars import ContextVar
from functools import wraps
from sqlalchemy.orm import Session
from app.config.database import SessionLocal

# 동시성 요청(Concurrent Request / Thread-safe) 격리를 위한 ContextVar
_transaction_depth: ContextVar[int] = ContextVar("transaction_depth", default=0)

def _extract_session(args, kwargs) -> Session | None:
    """
    메서드의 self (또는 self.repo) 및 파라미터에서 활성화된 SQLAlchemy Session을 탐색합니다.
    """
    # 1. kwargs에서 db 파라미터 탐색
    if "db" in kwargs and isinstance(kwargs["db"], Session):
        return kwargs["db"]

    def find_session(target, visited: set[int]) -> Session | None:
        if isinstance(target, Session):
            return target
        if id(target) in visited:
            return None
        visited.add(id(target))

        # Feature -> Domain Logic -> Repository 경계를 따라 실제 session을 탐색한다.
        for attribute in ("db", "repo", "dept_repository", "user_logic", "dept_logic"):
            nested = getattr(target, attribute, None)
            if nested is not None:
                session = find_session(nested, visited)
                if session is not None:
                    return session
        return None

    # 2. 인스턴스 메서드(self)에서 feature/domain/repository session 탐색
    for target in args:
        session = find_session(target, set())
        if session is not None:
            return session

    # 3. args 위치 인자 목록에서 Session 탐색
    for arg in args:
        if isinstance(arg, Session):
            return arg

    return None


def transactional(func):
    """
    다중 도메인 로직 간 트랜잭션 전이(Transaction Propagation: REQUIRED 패턴)를 지원하는 데코레이터
    
    1. 단일 세션 공유:
       상위 Feature 계층과 하위 Domain 계층이 동일한 Session을 공유할 때 하나의 트랜잭션으로 묶입니다.
    2. 중첩 트랜잭션(조기 커밋) 방지:
       최상위(Root) 함수에서만 최종 db.commit()을 호출하고, 하위 도메인의 @transactional은 상위 트랜잭션에 참여합니다.
    3. 일괄 롤백(Atomic Rollback):
       어느 계층이든 예외가 발생하면 즉시 db.rollback()을 실행하여 전체 작업을 취소합니다.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = _extract_session(args, kwargs)

        if db is not None:
            depth = _transaction_depth.get()
            is_root_transaction = (depth == 0)
            _transaction_depth.set(depth + 1)  # 트랜잭션 깊이 증가

            try:
                result = func(*args, **kwargs)
                # 오직 가장 바깥쪽(최상위) 트랜잭션 성공 시에만 최종 커밋 수행
                if is_root_transaction:
                    db.commit()
                return result
            except Exception:
                # 중간 어디서든 에러가 터지면 즉시 전체 트랜잭션 롤백
                db.rollback()
                raise
            finally:
                _transaction_depth.set(_transaction_depth.get() - 1)  # 트랜잭션 깊이 복원

        # 세션이 없는 단독 함수 실행 시 (자체 세션 생명주기 관리)
        new_db = SessionLocal()
        try:
            result = func(*args, **kwargs)
            new_db.commit()
            return result
        except Exception:
            new_db.rollback()
            raise
        finally:
            new_db.close()

    return wrapper