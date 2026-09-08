# app/app.py

import svcs
from fastapi import FastAPI

from app.config.database import engine
from app.bootstrap import register_services
from shared.models import Base
from shared.utils.logging_helper import logger
# 테이블 생성을 위해 메타데이터에 엔티티 등록 보장
from domain.user.user_entity import User  # noqa: F401
from domain.dept.dept_entity import Dept  # noqa: F401

from route.signup import signup_flow_router, signup_fetch_router
from route.organization import organization_flow_router, organization_fetch_router


@svcs.fastapi.lifespan
async def lifespan(app: FastAPI, registry: svcs.Registry):
    """startup : 테이블 없으면 생성, 있으면 그대로 (데이터 유지) + svcs 서비스 등록"""
    Base.metadata.create_all(bind=engine)
    register_services(registry)
    logger.info("[OK] Database tables created")
    yield  # 여기까지 실행되면 앱이 정상적으로 실행됨
    """shutdown"""
    logger.info("[INFO] Application is shutting down")


# FastAPI 앱 생성 (lifespan 등록)
app = FastAPI(
    title="Fast API Feature Oriented Stucture (DDD)",
    lifespan=lifespan,
)

# 라우터 등록
app.include_router(signup_flow_router)
app.include_router(signup_fetch_router)
app.include_router(organization_flow_router)
app.include_router(organization_fetch_router)
