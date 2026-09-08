# feature/signup/signup_dependency.py
"""
Signup 피처의 svcs 등록

SignupFlow/SignupFetch 클래스는 수정하지 않는다. svcs.autowire가 생성자의
UserLogic/DeptLogic 타입 힌트를 읽어 Registry에 등록된 인스턴스를 자동으로 조립한다.
"""

import svcs

from feature.signup.signup_flow import SignupFlow
from feature.signup.signup_fetch import SignupFetch


def register(registry: svcs.Registry) -> None:
  registry.register_factory(SignupFlow, svcs.autowire(SignupFlow))
  registry.register_factory(SignupFetch, svcs.autowire(SignupFetch))
