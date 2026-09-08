from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domain.dept.dept_entity import Dept
from feature.organization.organization_flow import OrganizationFlow
from shared.models import IdNameValues


class FakeDeptLogic:
  def __init__(self, dept: Dept, db: Session):
    self.dept = dept
    self.db = db
    self.modify_calls = []

  def retrieve_dept_by_id(self, dept_id: str) -> Dept | None:
    return self.dept if str(self.dept.id) == dept_id else None

  def modify_dept(self, dept: Dept, update_data: dict) -> Dept:
    self.modify_calls.append(update_data)
    for key, value in update_data.items():
      setattr(dept, key, value)
    return dept


def build_flow(dept: Dept):
  engine = create_engine("sqlite:///:memory:")
  db = Session(bind=engine)
  dept_logic = FakeDeptLogic(dept, db)
  return OrganizationFlow(None, dept_logic), dept_logic, db


def test_modify_dept_passes_only_changed_properties_to_domain_logic():
  dept = Dept(name="개발1팀", desc="서비스 개발")
  dept.id = "dept-001"
  flow, dept_logic, db = build_flow(dept)

  request = IdNameValues.of(
    str(dept.id),
    {
      "name": "개발팀",
      "desc": "플랫폼 개발 및 운영",
    },
  )

  flow.modify_dept(request)

  assert dept_logic.modify_calls == [
    {
      "name": "개발팀",
      "desc": "플랫폼 개발 및 운영",
    }
  ]
  db.close()


def test_modify_dept_skips_domain_logic_when_nothing_changed():
  dept = Dept(name="개발팀", desc="플랫폼 개발 및 운영")
  dept.id = "dept-001"
  flow, dept_logic, db = build_flow(dept)

  request = IdNameValues.of(
    str(dept.id),
    {
      "name": "개발팀",
      "desc": "플랫폼 개발 및 운영",
    },
  )

  result = flow.modify_dept(request)

  assert result.name == "개발팀"
  assert dept_logic.modify_calls == []
  db.close()


def test_modify_dept_passes_only_desc_when_name_is_unchanged():
  dept = Dept(name="개발팀", desc="서비스 개발")
  dept.id = "dept-001"
  flow, dept_logic, db = build_flow(dept)

  request = IdNameValues.of(
    str(dept.id),
    {
      "name": "개발팀",
      "desc": "플랫폼 개발 및 운영",
    },
  )

  flow.modify_dept(request)

  assert dept_logic.modify_calls == [
    {"desc": "플랫폼 개발 및 운영"}
  ]
  db.close()


def test_modify_dept_skips_domain_logic_when_update_list_is_empty():
  dept = Dept(name="개발팀", desc="플랫폼 개발 및 운영")
  dept.id = "dept-001"
  flow, dept_logic, db = build_flow(dept)

  result = flow.modify_dept(IdNameValues(id=str(dept.id)))

  assert result.name == "개발팀"
  assert dept_logic.modify_calls == []
  db.close()