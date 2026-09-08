from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config.transaction import _extract_session
from domain.dept.dept_logic import DeptLogic
from domain.dept.dept_repository import DeptRepository
from domain.user.user_logic import UserLogic
from domain.user.user_repository import UserRepository
from feature.organization.organization_flow import OrganizationFlow


def test_dept_mutating_logic_methods_are_transactional():
  assert hasattr(DeptLogic.register_dept, "__wrapped__")
  assert hasattr(DeptLogic.modify_dept, "__wrapped__")
  assert hasattr(DeptLogic.remove_dept, "__wrapped__")


def test_organization_mutating_methods_are_transactional():
  assert hasattr(OrganizationFlow.register_dept, "__wrapped__")
  assert hasattr(OrganizationFlow.register_depts, "__wrapped__")
  assert hasattr(OrganizationFlow.modify_dept, "__wrapped__")
  assert hasattr(OrganizationFlow.modify_depts, "__wrapped__")
  assert hasattr(OrganizationFlow.remove_dept, "__wrapped__")
  assert hasattr(OrganizationFlow.remove_depts, "__wrapped__")


def test_transaction_session_is_found_through_domain_and_feature_objects():
  engine = create_engine("sqlite:///:memory:")
  db = Session(bind=engine)
  user_logic = UserLogic(UserRepository(db))
  dept_logic = DeptLogic(DeptRepository(db))
  organization_flow = OrganizationFlow(user_logic, dept_logic)

  assert _extract_session((dept_logic,), {}) is db
  assert _extract_session((organization_flow,), {}) is db

  db.close()