"""
safety.py - 파일 보호 + 비상 복구 + 실행 보고 시스템

기능:
  1. 파일 삭제 대신 _deleted_items/ 폴더로 이동
  2. 실행 시작 시 타임스탬프 백업 자동 생성
  3. 비상 복구 명령어 안내
  4. API 사용량 추적 및 비용 보고
"""

import os
import shutil
import time
from datetime import datetime, timezone


# ── 프로젝트 루트 경로 ──
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DELETED_DIR = os.path.join(PROJECT_ROOT, "_deleted_items")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "_backups")


class UsageTracker:
    """API 사용량 및 자원 소모를 추적합니다."""

    def __init__(self):
        self.start_time = time.time()
        self.api_calls = {
            "gemini": 0,
            "twitter_read": 0,
            "twitter_write": 0,
            "google_index": 0,
            "pinterest": 0,
            "indexnow": 0,
        }
        self.errors = {
            "gemini": 0,
            "twitter": 0,
            "other": 0,
        }
        self.consecutive_errors = 0

    def log_api_call(self, service: str):
        """API 호출 1회 기록"""
        if service in self.api_calls:
            self.api_calls[service] += 1
        self.consecutive_errors = 0  # 성공이면 리셋

    def log_error(self, service: str):
        """에러 1회 기록"""
        if service in self.errors:
            self.errors[service] += 1
        self.consecutive_errors += 1

    def is_abnormal(self, max_consecutive: int = 3) -> bool:
        """비정상 동작 여부 판단"""
        total_calls = sum(self.api_calls.values())
        if self.consecutive_errors >= max_consecutive:
            return True
        if total_calls > 50:  # 하루 50회 이상이면 비정상
            return True
        return False

    def print_report(self):
        """실행 보고서를 출력합니다."""
        elapsed = time.time() - self.start_time
        total_calls = sum(self.api_calls.values())
        total_errors = sum(self.errors.values())

        print()
        print("=" * 60)
        print("  API 사용량 및 비용 보고서")
        print("=" * 60)
        print(f"  총 실행 시간:      {elapsed:.1f}초")
        print(f"  총 API 호출:       {total_calls}회")
        print(f"  총 에러:           {total_errors}회")
        print()
        print("  [호출 상세]")
        for service, count in self.api_calls.items():
            if count > 0:
                print(f"    {service}: {count}회")
        print()
        print("  [비용 추정]")
        print(f"    Gemini API:      {self.api_calls['gemini']}회 (무료 티어 내)")
        print(f"    Twitter API:     {self.api_calls['twitter_read'] + self.api_calls['twitter_write']}회 (무료 티어 내)")
        print(f"    서버 비용:       $0 (GitHub Actions ephemeral)")
        print("=" * 60)


# ── 전역 트래커 ──
tracker = UsageTracker()


def safe_delete(file_path: str) -> str:
    """
    파일을 삭제하는 대신 _deleted_items/ 폴더로 이동합니다.

    반환값: 이동된 경로
    """
    if not os.path.exists(file_path):
        print(f"[안전장치] 파일이 존재하지 않음: {file_path}")
        return ""

    os.makedirs(DELETED_DIR, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(file_path)
    dest = os.path.join(DELETED_DIR, f"{timestamp}_{base_name}")

    shutil.move(file_path, dest)
    print(f"[안전장치] 파일을 삭제하지 않고 이동함: {base_name} → _deleted_items/")
    return dest


def create_backup() -> str:
    """
    실행 시작 시 docs/ 폴더의 타임스탬프 백업을 생성합니다.

    반환값: 백업 폴더 경로
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}")

    docs_dir = os.path.join(PROJECT_ROOT, "docs")
    if os.path.exists(docs_dir):
        shutil.copytree(docs_dir, backup_path, dirs_exist_ok=True)
        file_count = len(os.listdir(backup_path))
        print(f"[백업] docs/ 폴더 백업 완료 → _backups/backup_{timestamp} ({file_count}개 파일)")
    else:
        os.makedirs(backup_path, exist_ok=True)
        print(f"[백업] docs/ 폴더가 비어있어 빈 백업 생성")

    return backup_path


def print_recovery_commands():
    """비상 복구 명령어를 로그에 출력합니다."""
    print()
    print("=" * 60)
    print("  비상 복구 명령어 (파일이 사라졌을 때)")
    print("=" * 60)
    print()
    print("  1. 삭제된 파일 확인:")
    print("     ls _deleted_items/")
    print()
    print("  2. 삭제된 파일 복구:")
    print("     cp _deleted_items/[파일명] docs/[원래이름]")
    print()
    print("  3. 최근 백업에서 전체 복구:")
    print("     cp -r _backups/backup_[최신타임스탬프]/* docs/")
    print()
    print("  4. git에서 복구 (커밋된 파일):")
    print("     git checkout HEAD -- docs/")
    print()
    print("  5. 특정 커밋에서 복구:")
    print("     git log --oneline")
    print("     git checkout [커밋해시] -- docs/[파일명]")
    print("=" * 60)
