# route/signup/signup_fetch_route.py

import svcs
from domain.dept import DeptResponse
from route.signup.request_signup_fetch import FindSignupDeptsFetch
from fastapi import APIRouter

from domain.user import UserResponse
# ✅ 라우터는 오직 Feature와 svcs 컨테이너만 알면 됨 (Repository, DB 세션 완전 제거)
from feature.signup import SignupFetch
from route.signup import FindSignedUserFetch

router = APIRouter(
  prefix="/signup", 
  tags=["회원가입 관리"], 
  responses={404: {"description": "Not found"}}
)

@router.post("/find_signed_user", response_model=UserResponse)
def find_signed_user(
  request: FindSignedUserFetch,
  services: svcs.fastapi.DepContainer,
):
    signup_fetch = services.get(SignupFetch)
    return signup_fetch.find_signed_user(request.user_id)

@router.post("/find_depts", response_model=list[DeptResponse])
def find_depts(
  request: FindSignupDeptsFetch,
  services: svcs.fastapi.DepContainer,
):
    signup_fetch = services.get(SignupFetch)
    return signup_fetch.find_depts(request.dept_name)
