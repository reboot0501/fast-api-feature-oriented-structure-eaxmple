# shared/utils/hash.py
# 비밀 번호 해싱

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

## hash 공통 함수 기능 정의 부
def hash_password(password : str) -> str:
    """비밀 번호를 해싱 하는 함수"""
    return pwd_context.hash(password)

def verify_password(plain_password : str, hashed_password : str) -> bool:
    """입력된 비밀 번호가 저장된 해시와 일치 하는지 확인"""
    return pwd_context.verify(plain_password, hashed_password)

""" hash 공통 함수 사용 예시
from utils.hash import hash_password

def register_user(db: Session, user: UserCreate):
    user.password = hash_password(user.password) # 비밀 번호 생성
    return create_user(db, user)
"""

