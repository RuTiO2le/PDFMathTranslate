#!/bin/bash
# PDFファイルを日本語に翻訳するスクリプト
# 使用方法:
#   単一ファイル: ./readable.sh file.pdf
#   複数ファイル: ./readable.sh file1.pdf file2.pdf file3.pdf

if [ -z "$VIRTUAL_ENV" ]; then
	source .venv/bin/activate
fi

if [ $# -eq 1 ]; then
	# 単一ファイルの場合
	f="$1"
	filename=$(basename "$f")
	# osascript -e "display dialog \"$filename 翻訳開始\""

	# pdf2zh "$f" -s plamo -lo ja
    pdf2zh "$f" -s openai:gpt-4.1 -lo ja
    
	# osascript -e "display dialog \"$filename 翻訳終了\""

	python check_and_run_server.py "$filename" > /tmp/server_log.txt  
	# open -a "Google Chrome" "http://localhost:8081/$filename"
else
	# 複数ファイルの場合（従来のループ処理）
	for f in "$@"
	do
		filename=$(basename "$f")
		osascript -e "display dialog \"$filename 翻訳開始\""
		pdf2zh "$f" -s plamo -lo ja
		# osascript -e "display dialog \"$filename 翻訳終了\""

		python check_and_run_server.py "$filename" > /tmp/server_log.txt  
		# open -a "Google Chrome" "http://localhost:8081/$filename"
	done
fi

pid=$(lsof -ti :8081) && [ -n "$pid" ] && kill $pid
