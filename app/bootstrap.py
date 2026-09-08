# app/bootstrap.py
"""
svcs 서비스 등록 최상위 조립 파일

각 도메인/피처의 Repository/Logic/Flow/Fetch 클래스는 전혀 수정하지 않는다.
Repository는 doc/ 원칙(자기 도메인 폴더 밖에서 import 금지)에 따라 여전히
각 도메인 자신의 xxx_dependency.py 안에서만 참조되고, 여기서는 각 도메인/피처가
스스로 노출하는 register(registry) 함수를 호출해 모으기만 한다.
도메인/피처가 늘어날 때 이 함수에 register 호출 한 줄만 추가하면 된다.
"""

import logging

import svcs
from sqlalchemy.orm import Session

from app.config.database import get_db
from shared.utils.logging_helper import logger
from domain.user.user_dependency import register as register_user
from domain.dept.dept_dependency import register as register_dept
from feature.signup.signup_dependency import register as register_signup
from feature.organization.organization_dependency import register as register_organization


def register_services(registry: svcs.Registry) -> None:
    """도메인/피처가 늘어날 때마다 이 함수에 register 호출을 추가하면 된다."""

    # 인프라: get_db()는 제너레이터 함수라 register_factory가 자동으로
    # contextmanager로 감싸 요청 종료 시 db.close()까지 대신 처리해준다.
    registry.register_factory(Session, get_db)

    # logging.Logger는 Session과 달리 요청별 상태를 갖지 않고, 파이썬 표준
    # logging 모듈 자체가 스레드 세이프하게 설계되어 있어 앱 전체에서 동일
    # 인스턴스를 공유해도 안전하다 -> register_value로 등록(진짜 싱글톤).
    registry.register_value(logging.Logger, logger)

    register_user(registry)
    register_dept(registry)
    register_signup(registry)
    register_organization(registry)
