import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# .env 환경 변수 로드
load_dotenv()

def _read_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    raise ValueError(f"{' or '.join(names)} is not defined in the environment")


# Oracle Database 접속 URL 생성
DATABASE_URL = URL.create(
    drivername=_read_env("DB_DRIVER"),
    username=_read_env("DB_USER"),
    password=_read_env("DB_PASSWORD"),
    host=_read_env("DB_HOST"),
    port=int(_read_env("DB_PORT")),
    query={"service_name": _read_env("DB_SERVICE_NAME")},
)

# DEBUG 환경 변수에 따라 쿼리 로그(echo) 여부 결정
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
engine = create_engine(DATABASE_URL, echo=DEBUG)

# SessionLocal: 데이터베이스 세션(Session) 생성 Factory 클래스 정의 (API 요청마다)
SessionLocal = sessionmaker(
    autocommit=False,       # 개발자가 의도한 시점에 명시적으로 db.commit() 또는 db.rollback() 호출
    autoflush=False,        # 트랜잭션 내에서 쿼리 실행 전 객체 변경 사항이 DB로 자동 flush되지 않도록 방지
    expire_on_commit=False, # 커밋 후 Pydantic 모델로 변환(JSON 직렬화)할 때 객체 속성을 안전하게 읽을 수 있도록 만료 방지
    bind=engine,            # 엔진 연결
)

# FastAPI 의존성 주입(Dependency)용 DB 세션 제너레이터 함수
def get_db() -> Generator[Session, None, None]:
    """
    API 요청마다 독립된 DB 세션을 생성하고,
    요청 처리가 끝나면 반드시 세션을 닫아 커넥션 풀에 반환합니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()