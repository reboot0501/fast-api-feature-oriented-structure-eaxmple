import uuid


def to_uuid(value: str | uuid.UUID) -> uuid.UUID:
  """
  문자열 또는 uuid.UUID를 uuid.UUID 인스턴스로 정규화한다.

  BaseEntity.id는 SQLAlchemy Uuid(as_uuid=True) 컬럼이라 실제 값은 uuid.UUID
  객체여야 한다. 라우트로 들어온 요청 값은 JSON 문자열(str)이라, 문자열을 그대로
  Session.get()/filter()의 PK 조건으로 넘기면 일부 DB 드라이버(Oracle 등)의 바인드
  프로세서가 str.hex를 호출하려다 AttributeError를 낸다. 조회/삭제 전 이 함수로
  항상 uuid.UUID로 변환한다.

  형식이 올바르지 않은 문자열이면 uuid.UUID()가 그대로 ValueError를 던진다 —
  "존재하지 않는 대상"과 "형식이 잘못된 요청"을 구분해야 하는 호출부는 대신
  to_uuid_or_none()을 사용한다.
  """
  return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


def to_uuid_or_none(value: str | uuid.UUID) -> uuid.UUID | None:
  """
  to_uuid()와 동일하되, UUID 형식이 아닌 문자열이면 예외 대신 None을 반환한다.

  ID로 단건 조회/삭제하는 경우, 형식이 잘못된 값은 어차피 어떤 행과도 매칭될 수
  없으므로 "존재하지 않음"과 동일하게 취급해 None을 돌려주고, 호출부가 조회 실패로
  자연스럽게 처리하도록 한다(대상이 있는지 없는지 판별하는 목적일 때 사용).
  """
  try:
    return to_uuid(value)
  except (ValueError, AttributeError, TypeError):
    return None
