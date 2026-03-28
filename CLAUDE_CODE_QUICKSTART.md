# Claude Code 실행 가이드 — AI Trading Assistant

## 1단계: 자동 승인 설정 확인

### 글로벌 설정 확인
```bash
cat ~/.claude/settings.json
```

### 자동 승인이 설정되어 있다면 이런 내용이 보입니다:
```json
{
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "Bash(*)"
    ]
  }
}
```

### 설정이 없거나 부족한 경우, 아래 방법 중 하나를 선택:

**방법 A: Shift+Tab으로 모드 전환 (세션별)**
Claude Code 실행 후 `Shift+Tab`을 반복 누르면:
- normal-mode → **auto-accept edit on** → plan mode on → (반복)
- "auto-accept edit on" 상태에서 파일 편집은 자동 승인됩니다.
- 단, 쉘 명령은 여전히 확인이 필요할 수 있습니다.

**방법 B: settings.json에 영구 설정 (추천)**
```bash
# 글로벌 설정 편집
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [
      "Edit",
      "MultiEdit",
      "Write",
      "Bash(python *)",
      "Bash(pip install *)",
      "Bash(npm *)",
      "Bash(git *)",
      "Bash(mkdir *)",
      "Bash(cp *)",
      "Bash(mv *)",
      "Bash(cat *)",
      "Bash(ls *)",
      "Bash(cd *)",
      "Bash(pytest *)",
      "Bash(streamlit *)"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(sudo rm *)"
    ]
  }
}
EOF
```

**방법 C: CLI 플래그로 실행 (1회성, 가장 빠름)**
```bash
claude --permission-mode bypassPermissions
```
⚠️ 이 옵션은 모든 권한을 무조건 승인합니다. 신뢰할 수 있는 프로젝트에서만 사용하세요.

---

## 2단계: 프로젝트 시작

```bash
# 작업 디렉토리 생성
mkdir ~/ai-trading-assistant
cd ~/ai-trading-assistant

# Claude Code 시작
claude
```

## 3단계: 첫 번째 프롬프트

Claude Code가 시작되면 아래 프롬프트를 입력하세요.
두 파일(CLAUDE.md, AI_TRADING_ASSISTANT_SPEC.md)을 프로젝트 루트에 먼저 복사해두세요.

```
이 프로젝트의 CLAUDE.md와 AI_TRADING_ASSISTANT_SPEC.md를 읽고,
Sprint 1부터 순서대로 전체 구현을 진행해줘.

각 Sprint 완료 후 테스트를 실행하고,
모든 Sprint가 끝나면 전체 시스템 동작을 확인해줘.

자동 승인 모드가 켜져 있으니 중간에 멈추지 말고 끝까지 진행해.
```

## 4단계: 파일 복사

다운로드한 두 파일을 프로젝트에 복사:
```bash
cp ~/Downloads/AI_TRADING_ASSISTANT_SPEC.md ~/ai-trading-assistant/
cp ~/Downloads/CLAUDE.md ~/ai-trading-assistant/
```

---

## 참고: 현재 글로벌 설정 확인 방법

```bash
# 현재 설정 확인
cat ~/.claude/settings.json 2>/dev/null || echo "설정 파일 없음"

# Claude Code 내에서 확인
# /allowedTools 명령어 입력
```

## 참고: 문제 발생 시

- **yfinance 에러**: 시장 마감 시간(미국 기준)에 따라 데이터가 지연될 수 있음
- **Tesseract 설치**: `sudo apt-get install tesseract-ocr tesseract-ocr-kor`
- **Streamlit 배포**: GitHub repo를 share.streamlit.io에 연결하여 배포
- **Telegram bot token**: @BotFather에서 봇 생성 후 token 획득
