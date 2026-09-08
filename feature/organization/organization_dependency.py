# feature/organization/organization_dependency.py
"""
Organization 피처의 svcs 등록

OrganizationFlow/OrganizationFetch 클래스는 수정하지 않는다. svcs.autowire가
생성자의 UserLogic/DeptLogic 타입 힌트를 읽어 자동으로 조립한다.
"""

import svcs

from feature.organization.organization_flow import OrganizationFlow
from feature.organization.organization_fetch import OrganizationFetch


def register(registry: svcs.Registry) -> None:
  registry.register_factory(OrganizationFlow, svcs.autowire(OrganizationFlow))
  registry.register_factory(OrganizationFetch, svcs.autowire(OrganizationFetch))
