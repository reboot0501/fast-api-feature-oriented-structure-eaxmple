# route/organization/organization_flow_route.py

import svcs
from fastapi import APIRouter
from domain.dept import DeptResponse
from feature.organization import OrganizationFlow
from route.organization.request_organization_command import (
  RegisterDeptsCommand,
  ModifyDeptsCommand,
  RemoveDeptsCommand,
  ChangeUsersDeptCommand,
)

router = APIRouter(
  prefix="/organization", 
  tags=["조직 관리"],
  responses={404: {"description": "Not Found"}}
)

@router.post("/register_depts", response_model=list[DeptResponse])
def register_depts(
  request: RegisterDeptsCommand,
  services: svcs.fastapi.DepContainer,  # ✅ 컨테이너 1개만 주입받으면 됨
):
  organization_flow = services.get(OrganizationFlow)
  return organization_flow.register_depts(request.depts)

@router.post("/modify_depts", response_model=list[DeptResponse])
def modify_depts(
  request: ModifyDeptsCommand,
  services: svcs.fastapi.DepContainer,
):
  organization_flow = services.get(OrganizationFlow)
  return organization_flow.modify_depts(request.depts)

@router.post("/delete_depts", response_model=list[bool])
def delete_depts(
  request: RemoveDeptsCommand,
  services: svcs.fastapi.DepContainer,
):
  organization_flow = services.get(OrganizationFlow)
  return organization_flow.remove_depts(request.depts)


@router.post("/change_users_dept", response_model=list[bool])
def change_users_dept(
  request: ChangeUsersDeptCommand,
  services: svcs.fastapi.DepContainer,
):
  organization_flow = services.get(OrganizationFlow)
  return organization_flow.change_users_dept(request.users)
