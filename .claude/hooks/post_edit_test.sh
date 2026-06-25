#!/bin/bash
# .py または structure.json を編集したとき自動でテストを実行する
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# .py または structure.json のみ対象
if [[ "$FILE_PATH" =~ \.py$ ]] || [[ "$FILE_PATH" =~ structure\.json$ ]]; then
  cd /Users/yoheyhey/projects/funnel-generator
  echo "--- 自動テスト実行中 ($( basename "$FILE_PATH" ) を変更) ---"
  python3 test_all.py
fi
