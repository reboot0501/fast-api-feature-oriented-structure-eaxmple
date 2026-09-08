from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.dept.dept_logic import DeptLogic


class FakeDeptRepository:
  def delete_dept(self, dept_id: str) -> bool:
    return dept_id != "missing-dept"


app = FastAPI()
dept_logic = DeptLogic(FakeDeptRepository())


@app.post("/organization/delete_depts", response_model=list[bool])
def delete_depts(dept_ids: list[str]):
  # 삭제 결과가 API response_model의 boolean 배열로 전달되는지 검증한다.
  return [dept_logic.remove_dept(dept_id) for dept_id in dept_ids]


client = TestClient(app)


def test_delete_depts_returns_boolean_results():
  response = client.post(
    "/organization/delete_depts",
    json=["dept-id", "missing-dept"],
  )

  assert response.status_code == 200
  assert response.json() == [True, False]