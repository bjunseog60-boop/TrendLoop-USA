#!/bin/bash
# TrendLoop USA 실행 스크립트 (API 키를 .env에서 자동 로드)

set -e
cd "$(dirname "$0")"

# .env 파일에서 환경 변수 로드
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
    echo "[보안] .env 환경 변수 로드 완료"
else
    echo "[오류] .env 파일이 없습니다! 먼저 .env를 설정해 주세요."
    exit 1
fi

# 가상환경 활성화
source venv/bin/activate

# 실행 전 자동 백업
BACKUP_DIR="_backups/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
if [ -d docs ]; then
    cp -r docs/* "$BACKUP_DIR/" 2>/dev/null || true
    echo "[백업] docs/ → $BACKUP_DIR 완료"
fi

# 메인 실행
python3 main.py

echo "[완료] TrendLoop USA 실행 끝"
