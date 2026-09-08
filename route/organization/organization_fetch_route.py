# route/organization/organization_fetch_route.py

import logging

import svcs
from fastapi import APIRouter
from shared.models import OffsetElementList
from domain.user import UserResponse
from domain.dept import DeptResponse
from feature.organization import OrganizationFetch
from route.organization.request_organization_fetch import FindUsersFetch, FindDeptsFetch

router = APIRouter(
  prefix="/organization", 
  tags=["조직 관리"],
  responses={404: {"description": "Not found"}}
)

@router.post("/find_users", response_model=OffsetElementList[UserResponse])
def find_users(
  request: FindUsersFetch,
  services: svcs.fastapi.DepContainer,  # ✅ 컨테이너 1개만 주입받으면 됨
):
  # logging.Logger는 register_value로 등록된 앱 전체 공유 싱글톤이며,
  # 파이썬 표준 logging 모듈 자체가 스레드 세이프하므로 별도 락 없이 안전하게 호출 가능.
  log = services.get(logging.Logger)
  log.info(
    "find_users 실행됨 (user_name=%s, dept_id=%s, page=%s, size=%s, order=%s)",
    request.user_name, request.dept_id, request.page, request.size, request.order,
  )
  organization_fetch = services.get(OrganizationFetch)
  return organization_fetch.find_users(request.user_name, request.dept_id, request.page, request.size, request.order)

@router.post("/find_depts", response_model=OffsetElementList[DeptResponse])
def find_depts(
  request: FindDeptsFetch,
  services: svcs.fastapi.DepContainer,
):
  log = services.get(logging.Logger)
  log.info(
    "find_depts 실행됨 (dept_name=%s, page=%s, size=%s, order=%s)",
    request.dept_name, request.page, request.size, request.order,
  )
  organization_fetch = services.get(OrganizationFetch)
  return organization_fetch.find_depts(request.dept_name, request.page, request.size, request.order)
