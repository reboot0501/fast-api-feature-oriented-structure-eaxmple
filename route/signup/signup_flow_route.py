# route/signup/signup_flow_route.py

import svcs
from feature.signup import SignupFlow
from route.signup import SignupCommand, ModifyUserCommand
from domain.user import UserResponse
from fastapi import APIRouter

router = APIRouter(
  prefix="/signup",
  tags=["회원가입 관리"],
  responses={
    404: {"description": "Not found"}
  }
)

@router.post("/", response_model=UserResponse)
def signup(
  request: SignupCommand,
  services: svcs.fastapi.DepContainer,  # ✅ 컨테이너 1개만 주입받으면 됨
):
  signup_flow = services.get(SignupFlow)
  return signup_flow.signup(request.request)

@router.post("/modify_user", response_model=UserResponse)
def modify_user(
  request: ModifyUserCommand,
  services: svcs.fastapi.DepContainer,
):
  signup_flow = services.get(SignupFlow)
  return signup_flow.modify_user(request.user_id, request.request)
