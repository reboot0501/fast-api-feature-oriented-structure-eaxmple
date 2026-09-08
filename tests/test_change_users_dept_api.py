from fastapi import FastAPI
from fastapi.testclient import TestClient

from route.organization.organization_flow_route import router
from route.organization.request_organization_command import ChangeUsersDeptCommand
from shared.models import IdNameValues


app = FastAPI()
app.include_router(router)


def test_change_users_dept_request_model_accepts_batch_payload():
  request = ChangeUsersDeptCommand(
    users=[
      {
        "id": "user-001",
        "nameValues": [{"name": "dept_id", "value": "dept-002"}],
      },
      {
        "id": "user-002",
        "nameValues": [{"name": "dept_id", "value": "dept-002"}],
      },
    ]
  )

  assert all(isinstance(item, IdNameValues) for item in request.users)
  assert [item.id for item in request.users] == ["user-001", "user-002"]
  assert [item.get_value("dept_id") for item in request.users] == [
    "dept-002",
    "dept-002",
  ]