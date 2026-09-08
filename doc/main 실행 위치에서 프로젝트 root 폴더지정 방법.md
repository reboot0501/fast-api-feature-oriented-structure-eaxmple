# main.py 실행 위치에서 프로젝트 Root 폴더 지정 방법

`python app/main.py`처럼 하위 디렉터리에 위치한 실행 스크립트를 직접 구동할 때 발생하는 모듈 경로 탐색 오류(`ModuleNotFoundError: No module named 'app'`)를 해결하고, 프로젝트 루트 경로를 동적으로 등록하는 원리와 방법을 정리한 문서입니다.

---

## 1. 문제 배경

파이썬 스크립트를 직접 실행하면 파이썬 인터프리터는 **실행된 파일이 존재하는 디렉터리(`.../app/`)**를 최우선 모듈 탐색 경로(`sys.path[0]`)로 자동 지정합니다.

* 따라서 `app/main.py` 내부에서 `import app.xxx` 또는 `uvicorn.run("app.main:app", ...)`과 같이 **`app` 패키지부터 시작하는 절대 경로**를 호출하면, 파이썬이 `app/` 폴더 안에서 또 다른 `app` 폴더를 찾으려 하므로 `No module named 'app'` 에러가 발생합니다.

---

## 2. 해결 코드

[app/main.py](file:///d:/project-workspace/fast-api-feature-oriented-structure-eaxmple/app/main.py) 파일 상단에 아래 코드를 추가하여 파이썬 모듈 탐색 경로에 프로젝트 루트 폴더를 최우선으로 등록합니다.

```python
import sys
from pathlib import Path

# 프로젝트 루트 디렉터리를 sys.path 최우선(0순위)에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

---

## 3. 단계별 경로 해석 과정

현재 실행 파일 위치가 `d:/project-workspace/fast-api-feature-oriented-structure-eaxmple/app/main.py`일 때:

| 코드 구문 | 실제 가리키는 경로 | 설명 |
| :--- | :--- | :--- |
| **`__file__`** | `d:/.../app/main.py` | 현재 실행 중인 파일의 상대/절대 경로 |
| **`Path(__file__).resolve()`** | `d:/project-workspace/fast-api-feature-oriented-structure-eaxmple/app/main.py` | 심볼릭 링크 등을 모두 해석한 완전한 **절대 경로** |
| **`.parent` (1단계 상위)** | `d:/project-workspace/fast-api-feature-oriented-structure-eaxmple/app` | `main.py`가 위치한 **`app` 디렉터리** |
| **`.parent.parent` (2단계 상위)** | `d:/project-workspace/fast-api-feature-oriented-structure-eaxmple` | `app`의 상위 디렉터리인 **프로젝트 루트 디렉터리** |
| **`str(...)`** | `"d:/project-workspace/fast-api-feature-oriented-structure-eaxmple"` | `sys.path` 리스트에 담기 위해 `Path` 객체를 문자열로 변환 |

---

## 4. `sys.path.insert(0, ...)`의 역할

* **`sys.path`란?**  
  파이썬 인터프리터가 `import` 문을 만났을 때 모듈이나 패키지를 순서대로 탐색하는 디렉터리 경로들의 리스트입니다.
* **`insert(0, ...)`의 의미**:  
  리스트의 맨 앞(0번 인덱스)에 경로를 삽입함으로써 **파이썬의 모듈 탐색 최우선 순위**로 지정합니다.
* **효과**:  
  터미널의 현재 작업 디렉터리(CWD)가 어디이든 상관없이, 프로젝트 루트 폴더를 기준으로 `app` 패키지를 즉시 인식할 수 있어 `from app.main import app` 및 `uvicorn.run("app.main:app")`이 정상 동작합니다.

---

## 5. 실무 관점 요약

| 구분 | 파일 직접 실행 (`python app/main.py`) | CLI 명령어 실행 (`uvicorn app.main:app`) |
| :--- | :--- | :--- |
| **루트 경로 지정 필요 여부** | **필수** (`sys.path.insert` 적용 필요) | **불필요** (실행 위치가 루트이면 자동 인식) |
| **주 사용 용도** | IDE 디버거(F5) 실행, 간단한 로컬 테스트 | 로컬 표준 개발, Docker 컨테이너 및 운영 배포 |
