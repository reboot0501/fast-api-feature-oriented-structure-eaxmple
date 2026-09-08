from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.models.exception import (
  DeptAlreadyExistsException,
  DeptNotFoundException,
  UpdateValueException,
  UserNotFoundException,
)


app = FastAPI()


@app.get("/users/{user_id}")
def find_user(user_id: str):
  # 실제 feature에서 발생한 HTTPException이 FastAPI 응답으로 변환되는지 검증한다.
  raise UserNotFoundException(user_id)


@app.get("/depts/{dept_id}")
def find_dept(dept_id: str):
  raise DeptNotFoundException(dept_id)


@app.post("/users")
def create_user():
  raise DeptAlreadyExistsException()


@app.patch("/users")
def update_user():
  raise UpdateValueException()


client = TestClient(app)


def test_not_found_exception_is_returned_as_404():
  response = client.get("/users/missing-user")

  assert response.status_code == 404
  assert "missing-user" in response.json()["detail"]


def test_dept_not_found_exception_is_returned_as_404():
  response = client.get("/depts/missing-dept")

  assert response.status_code == 404
  assert "missing-dept" in response.json()["detail"]


def test_existing_and_validation_exceptions_keep_their_statuses():
  assert client.post("/users").status_code == 400
  assert client.patch("/users").status_code == 422