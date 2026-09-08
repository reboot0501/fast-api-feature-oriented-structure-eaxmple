# domain/dept/dept_dependency.py
"""
Dept 도메인 계층의 svcs 등록

DeptRepository는 오직 domain/dept 패키지 내부에서만 참조되며(캡슐화 원칙 유지),
외부(app/bootstrap.py)에는 register(registry) 함수만 노출한다.
"""

import svcs

# 🔒 도메인 내부에서만 은밀하게 Repository를 참조
from domain.dept.dept_repository import DeptRepository
from domain.dept.dept_logic import DeptLogic


def register(registry: svcs.Registry) -> None:
  registry.register_factory(DeptRepository, svcs.autowire(DeptRepository))
  registry.register_factory(DeptLogic, svcs.autowire(DeptLogic))
