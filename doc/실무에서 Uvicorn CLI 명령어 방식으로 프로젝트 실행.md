# 실무에서 Uvicorn CLI 명령어 방식으로 프로젝트 실행을 더 선호하는 이유

FastAPI 애플리케이션을 구동할 때 사용되는 **두 가지 실행 방식(Python Main 직접 실행 vs Uvicorn CLI 명령어 실행)**을 비교 분석하고, 현업 실무에서 왜 Uvicorn CLI 방식을 표준(Facto Standard)으로 선호하는지 정리한 문서입니다.

---

## 1. 프로젝트 실행 방법 2가지 비교

### 방법 1. Python Main 직접 실행 방식 (Java의 `main()` 메서드 형태)

`app/main.py` 파일 내부에 `if __name__ == "__main__":` 블록을 두고, 파이썬 인터프리터가 해당 파일을 진입점으로 삼아 직접 구동하는 방식입니다.

#### ① 구현 코드 예시
```python
# app/main.py
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
from fastapi import FastAPI

# 프로젝트 루트 경로 등록 (직접 실행 시 모듈 탐색을 위해 필수)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()
HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", 8000))

app = FastAPI(title="Fast API Feature Oriented Structure")

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI Feature-Oriented Example!"}

# Java 클래스의 main 메서드처럼 실행하는 진입점 블록
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
```

#### ② 실행 명령어
```bash
uv run python app/main.py
```

#### ③ `"app.main:app"` 문자열 경로를 사용하는 이유
```
"app.main : app"
 └──①───┘   └②─┘
```
1. **구조 분석**:
   * **`app.main` (모듈 경로)**: 프로젝트 루트 디렉터리를 기준으로 `app/main.py` 파일을 가리키는 Python Import 경로입니다.
   * **`app` (변수명)**: `main.py` 파일 내부에서 생성한 FastAPI 인스턴스 변수 이름(`app = FastAPI()`)입니다.
2. **객체(`app`) 대신 문자열(`"app.main:app"`)로 넘기는 결정적 이유**:
   * `uvicorn.run(app)`처럼 객체 자체를 넘기면 이미 메모리에 올라간 단일 인스턴스만 전달됩니다.
   * 하지만 **`reload=True`(핫 리로드)** 또는 **멀티 워커(`workers > 1`)** 옵션을 사용할 때는, Uvicorn 프로세스 감시자가 코드 변경을 감지했을 때 모듈을 동적으로 다시 불러와야(Re-import) 합니다.
   * 따라서 반드시 모듈의 위치를 추적할 수 있는 **문자열 형태의 Import 경로(`import string`)**로 전달해야 리로드 기능이 정상 작동합니다.

---

### 방법 2. Uvicorn CLI 명령어 실행 방식 (실무 표준 권장)

`app/main.py`에는 순수하게 FastAPI 앱 객체와 라우팅 명세만 남겨두고, 서버 인프라 구동은 외부 ASGI 도구인 Uvicorn CLI에 위임하는 방식입니다.

#### ① 구현 코드 예시 (깔끔한 순수 앱 형태)
```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(title="Fast API Feature Oriented Structure")

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI Feature-Oriented Example!"}
```

#### ② 실행 명령어
```bash
# 터미널 직접 실행
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### ③ 실행 편의 스크립트 활용
긴 CLI 명령어를 매번 입력하지 않기 위해 프로젝트 루트에 실행 스크립트를 배치하여 사용합니다.

* **Windows (`project_run.bat`)**:
  ```bat
  @echo off
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
  *PowerShell 실행*: `.\project_run.bat` 또는 파일 탐색기에서 더블 클릭
* **Linux / macOS (`run.sh`)**:
  ```bash
  #!/bin/bash
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```

---

## 2. 실무에서 Uvicorn CLI 방식을 더 선호하는 핵심 이유

### 1) 개발 환경과 운영(Docker/Kubernetes) 환경의 일관성
* **운영 배포 환경**에서는 파이썬 파일을 직접 실행하지 않고, Dockerfile의 `CMD` 또는 쿠버네티스 파드 실행 명령어로 서버 프로세스를 띄웁니다.
* **운영 환경 Dockerfile 배포 예시**:
  ```dockerfile
  # 1. 단일 프로세스 실행
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

  # 2. 프로덕션 멀티 프로세스 실행 (Gunicorn 마스터 + Uvicorn 워커)
  CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
  ```
* 로컬 개발부터 동일한 CLI 방식으로 실행하면, 로컬과 운영 환경 간의 동작 괴리를 없애 배포 시 발생할 수 있는 잠재적 오류를 완벽하게 차단할 수 있습니다.

### 2) 소스 코드 오염 방지 (`sys.path` 조작 불필요)
* 파일 직접 실행(`python app/main.py`) 시에는 파이썬이 `app/` 폴더를 최우선 탐색 경로로 잡아버려 `No module named 'app'` 에러가 발생하며, 이를 해결하기 위해 `sys.path.insert(0, ...)` 같은 하드코딩 경로 주입 코드가 코드 상단에 들어가야 합니다.
* **CLI 방식은 항상 프로젝트 루트 디렉터리를 기준**으로 모듈을 탐색하므로, 비즈니스 코드에 불필요한 시스템 경로 조작 코드를 일체 작성할 필요가 없습니다.

### 3) 관심사의 완벽한 분리 (Separation of Concerns)
* **`app/main.py`의 책임**: FastAPI 앱 설정, 라우터 등록, 미들웨어 연결 등 **"웹 애플리케이션 비즈니스 정의"**에만 집중합니다.
* **ASGI 서버(Uvicorn)의 책임**: 포트 바인딩, 워커 프로세스 수 관리, 소켓 연결, 프로세스 재시작(Reload) 등 **"서버 인프라 런타임 제어"**를 전담합니다.
* 서버 구동 인프라 로직과 비즈니스 로직이 완전히 분리되어 아키텍처가 견고해집니다.

### 4) 인프라 제어 및 파라미터 유연성
* 호스트 바인딩 IP, 포트 번호, 워커 프로세스 수(`--workers`), 로그 레벨(`--log-level`), SSL 인증서 경로 등을 **파이썬 코드를 단 한 줄도 수정하지 않고** 배포 환경에 따라 명령줄 인자나 환경 변수로 즉시 변경할 수 있습니다.

---

## 3. 종합 비교 요약

| 비교 항목 | 방법 1: Python Main 직접 실행 | 방법 2: Uvicorn CLI 실행 (실무 표준) |
| :--- | :--- | :--- |
| **실행 방식** | `python app/main.py` | `uvicorn app.main:app` |
| **`app/main.py` 형태** | `if __name__ == "__main__":` 및 `uvicorn.run()` 포함 | 순수 FastAPI 앱 및 라우터 정의만 유지 |
| **`sys.path` 수동 추가** | **필수** (`sys.path.insert(0, ...)`) | **불필요** (루트 경로 자동 인식) |
| **운영(Docker) 환경 일치도**| 낮음 (운영 환경에서는 결국 CLI로 전환 필요) | **완벽 일치** (로컬과 운영 명령어 동일) |
| **프로세스 관리/확장성** | 멀티 워커 및 프로덕션 옵션 제약 | Gunicorn 연계 및 멀티 워커 제어 탁월 |
| **주 사용 목적** | IDE 디버거(F5) 원클릭 구동, 초보자용 예제 | **현업 실무 표준, CI/CD 배포, 프로덕션 운영** |
