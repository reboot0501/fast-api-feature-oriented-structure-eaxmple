# shared/models/exception.py
# 외부 계층에서 직접 import하는 공통 예외 처리

from fastapi import HTTPException

class UserAlreadyExistsException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="이미 존재하는 사용자 입니다.")

class UserNotFoundException(HTTPException):
    def __init__(self, identifier: str | None = None):
        # 호출부가 전달한 ID 또는 email을 detail에 포함하되, 기존 무인자 호출도 허용한다.
        detail = "존재하지 않는 사용자 입니다."
        if identifier:
            detail += f" 식별자: {identifier}"
        super().__init__(status_code=404, detail=detail)


class DeptAlreadyExistsException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="이미 존재하는 부서 입니다.")

class DeptNotFoundException(HTTPException):
    def __init__(self, identifier: str | None = None):
        # 호출부가 전달한 부서 ID를 응답에 남겨 원인 파악이 가능하도록 한다.
        detail = "존재하지 않는 부서 입니다."
        if identifier:
            detail += f" 식별자: {identifier}"
        super().__init__(status_code=404, detail=detail)

class UpdateValueException(HTTPException):
    def __init__(self):
        super().__init__(status_code=422, detail="적어도 수정할 하나의 필드가 필요합니다.")

class DeptHasUsersException(HTTPException):
    def __init__(self, identifier: str | None = None):
        detail = "부서에 소속된 사용자가 존재하여 삭제할 수 없습니다."
        if identifier:
            detail += f" 식별자: {identifier}"
        super().__init__(status_code=400, detail=detail)


""" 서비스 적용 예시         
from shared.models.exception import UserAlreadyExistsException, UserNotFoundException
from utils.hash import hash_password
from repositories.user_repository import get_user_by_email, get_user, create_user

def register_user(db: Session, user: UserCreate):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise UserAlreadyExistsException()
    user.password = hash_password(user.password)
    return create_user(db, user)

def retrieve_user(db: Session, user_id: int):
    db_user = get_user(db, user_id=user_id)
    if not db_user:
        raise UserNotFoundException()
    return db_user
"""


