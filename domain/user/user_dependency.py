# domain/user/user_dependency.py
"""
User 도메인 계층의 svcs 등록

Repository는 오직 domain/user 패키지 내부에서만 참조되며(캡슐화 원칙 유지),
외부(app/bootstrap.py)에는 register(registry) 함수만 노출한다.
UserLogic/UserRepository 클래스 자체는 svcs.autowire가 생성자 타입 힌트를
읽어 자동으로 조립하므로 수정하지 않는다.
"""

import svcs

# 🔒 domain 내부에서만 은밀하게 Repository를 참조
from domain.user.user_repository import UserRepository
from domain.user.user_logic import UserLogic


def register(registry: svcs.Registry) -> None:
  registry.register_factory(UserRepository, svcs.autowire(UserRepository))
  registry.register_factory(UserLogic, svcs.autowire(UserLogic))
