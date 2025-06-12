#!/usr/bin/env python3
"""
PDF Math Translate Native Messaging Host
Chrome拡張機能からのリクエストを受け取り、pdf2zhで翻訳処理を実行
"""

import json
import sys
import struct
import subprocess
import os
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import threading
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/pdf2zh_native_host.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NativeMessagingHost:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.translated_dir = Path("/Users/ytakeda/codes/PDFMathTranslate/translated_pdf")
        self.translated_dir.mkdir(exist_ok=True)
        self.server_port = None  # 動的に設定される
        
    def read_message(self) -> Optional[Dict[str, Any]]:
        """Chrome拡張機能からのメッセージを読み取り"""
        try:
            # メッセージ長を読み取り（4バイト）
            raw_length = sys.stdin.buffer.read(4)
            if not raw_length:
                return None
                
            message_length = struct.unpack('=I', raw_length)[0]
            
            # メッセージ本体を読み取り
            message_data = sys.stdin.buffer.read(message_length)
            message = json.loads(message_data.decode('utf-8'))
            
            logger.info(f"Received message: {message}")
            return message
            
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            return None
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """Chrome拡張機能にメッセージを送信"""
        try:
            message_json = json.dumps(message).encode('utf-8')
            message_length = len(message_json)
            
            # メッセージ長を送信（4バイト）
            sys.stdout.buffer.write(struct.pack('=I', message_length))
            # メッセージ本体を送信
            sys.stdout.buffer.write(message_json)
            sys.stdout.buffer.flush()
            
            logger.info(f"Sent message: {message}")
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    def download_pdf(self, url: str) -> str:
        """PDFファイルをダウンロード"""
        try:
            # URLからファイル名を取得
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            # 一時ファイルにダウンロード
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, filename)
            
            logger.info(f"Downloading PDF from {url} to {temp_path}")
            urllib.request.urlretrieve(url, temp_path)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            raise
    
    def translate_pdf(self, pdf_path: str, service: str = "plamo", language: str = "ja", output_format: str = "dual") -> str:
        """pdf2zhを使用してPDFを翻訳"""
        try:
            # 翻訳済みファイルが既に存在するか確認
            pdf_name = os.path.basename(pdf_path)
            pdf_name_without_ext = os.path.splitext(pdf_name)[0]
            
            translated_path_dual = self.translated_dir / f"{pdf_name_without_ext}-dual.pdf"
            translated_path_mono = self.translated_dir / f"{pdf_name_without_ext}-mono.pdf"
            
            # 既に翻訳済みの場合はスキップ
            if translated_path_dual.exists():
                logger.info(f"Translation already exists: {translated_path_dual}")
                return str(translated_path_dual)
            elif translated_path_mono.exists():
                logger.info(f"Translation already exists: {translated_path_mono}")
                return str(translated_path_mono)
            
            logger.info("No existing translation found. Starting translation...")
            
            # 仮想環境のpdf2zhコマンドを直接使用
            pdf2zh_cmd = "/Users/ytakeda/codes/PDFMathTranslate/.venv/bin/pdf2zh"
            
            # コマンドが存在するか確認
            if not os.path.exists(pdf2zh_cmd):
                logger.error(f"pdf2zh command not found at: {pdf2zh_cmd}")
                raise Exception(f"pdf2zh command not found at: {pdf2zh_cmd}")
            
            # 翻訳コマンドを構築
            cmd = [pdf2zh_cmd, pdf_path, "-s", service, "-lo", language]
            
            # 出力形式の設定
            if output_format == "mono":
                cmd.append("--mono")
            # dual形式はデフォルトなので特別なオプションは不要
            
            # デバッグ用：--debugオプションをコメントアウト（正常に動くかテスト）
            # cmd.append("--debug")
            # フォント処理エラー回避用オプション（現在コメントアウト中）
            # cmd.append("--skip-subset-fonts")
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # 作業ディレクトリをPDFMathTranslateに設定
            working_dir = "/Users/ytakeda/codes/PDFMathTranslate"
            
            # 環境変数を継承（APIキーなど）
            env = os.environ.copy()
            
            # zshrcから環境変数を読み込み（一時的にコメントアウト）
            # config.jsonでbase_urlが設定されているため、環境変数読み込みは必須ではない
            logger.info("Skipping zshrc environment loading - using config.json settings")
            
            # デバッグ用：環境変数をログ出力
            important_vars = ['PLAMO_API_KEY', 'PLAMO_TRANSLATE_API_KEY', 'PLAMO_TRANSLATE_BASE_URL', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
            for var in important_vars:
                if var in env:
                    logger.info(f"Environment variable {var}: {'*' * 10}")
                else:
                    logger.warning(f"Environment variable {var}: NOT SET")
            
            logger.info(f"Starting pdf2zh subprocess...")
            start_time = time.time()
            
            # 非同期でプロセスを実行し、進捗をログ出力
            process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # 標準入力を閉じる
                text=True,
                env=env
            )
            
            # プロセスの進行状況を監視
            timeout_seconds = 180  # 3分でタイムアウト（一時的に延長）
            poll_interval = 5     # 5秒ごとにチェック
            elapsed = 0
            
            while process.poll() is None and elapsed < timeout_seconds:
                time.sleep(poll_interval)
                elapsed += poll_interval
                logger.info(f"pdf2zh still running... elapsed: {elapsed}s / {timeout_seconds}s")
                
                # プロセスが生きているかチェック
                if process.poll() is not None:
                    break
            
            if process.poll() is None:
                # タイムアウト
                logger.error(f"pdf2zh process timed out after {elapsed}s - killing process")
                process.kill()
                stdout, stderr = process.communicate()
                elapsed_time = time.time() - start_time
                logger.error(f"Process killed after {elapsed_time:.2f} seconds")
                logger.error(f"Stdout: {stdout}")
                logger.error(f"Stderr: {stderr}")
                raise Exception("Translation timed out")
            else:
                # 正常完了
                stdout, stderr = process.communicate()
                result_code = process.returncode
                elapsed_time = time.time() - start_time
                logger.info(f"pdf2zh completed in {elapsed_time:.2f} seconds")
                logger.info(f"Return code: {result_code}")
                logger.info(f"Stdout: {stdout}")
                if stderr:
                    logger.warning(f"Stderr: {stderr}")
                
                # 結果オブジェクトを作成
                class Result:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                
                result = Result(result_code, stdout, stderr)
            
            if result.returncode != 0:
                logger.error(f"pdf2zh failed: {result.stderr}")
                raise Exception(f"Translation failed: {result.stderr}")
            
            logger.info(f"pdf2zh completed successfully: {result.stdout}")
            
            # 翻訳済みファイルのパスを取得
            pdf_name = os.path.basename(pdf_path)
            pdf_name_without_ext = os.path.splitext(pdf_name)[0]
            
            # 出力形式に応じて適切なファイルを探す
            translated_path_dual = self.translated_dir / f"{pdf_name_without_ext}-dual.pdf"
            translated_path_mono = self.translated_dir / f"{pdf_name_without_ext}-mono.pdf"
            
            if output_format == "mono":
                # mono形式が指定された場合
                if translated_path_mono.exists():
                    translated_path = translated_path_mono
                elif translated_path_dual.exists():
                    # monoが存在しない場合はdualを使用
                    translated_path = translated_path_dual
                    logger.info("Mono format requested but not found, using dual format")
                else:
                    raise Exception(f"Translated file not found: {translated_path_mono} or {translated_path_dual}")
            else:
                # dual形式（デフォルト）
                if translated_path_dual.exists():
                    translated_path = translated_path_dual
                elif translated_path_mono.exists():
                    translated_path = translated_path_mono
                    logger.info("Dual format requested but not found, using mono format")
                else:
                    raise Exception(f"Translated file not found: {translated_path_dual} or {translated_path_mono}")
            
            return str(translated_path)
            
        except subprocess.TimeoutExpired:
            logger.error("pdf2zh command timed out")
            raise Exception("Translation timed out")
        except Exception as e:
            import traceback
            logger.error(f"Error translating PDF: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def start_server(self, filename: str) -> str:
        """翻訳結果を表示するサーバーを起動"""
        try:
            # PDFMathTranslateディレクトリのcheck_and_run_server.pyを実行
            server_script = Path("/Users/ytakeda/codes/PDFMathTranslate/check_and_run_server.py")
            if not server_script.exists():
                logger.warning("check_and_run_server.py not found, returning file path instead")
                # サーバースクリプトがない場合は、ファイルパスを直接返す
                return f"file://{filename}"
            
            # Pythonコマンドを仮想環境のものを使用
            python_cmd = "/Users/ytakeda/codes/PDFMathTranslate/.venv/bin/python"
            cmd = [python_cmd, str(server_script), filename]
            logger.info(f"Starting server: {' '.join(cmd)}")
            
            # バックグラウンドでサーバーを起動
            process = subprocess.Popen(
                cmd,
                cwd="/Users/ytakeda/codes/PDFMathTranslate",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # サーバーの起動を待つ
            time.sleep(2)
            
            # プロセスの出力を取得（check_and_run_server.pyは正常終了する）
            stdout, stderr = process.communicate()
            logger.info(f"Server script output: stdout={stdout}, stderr={stderr}")
            
            # プロセスの出力からポート番号を取得する必要があるが、
            # check_and_run_server.pyが出力するメッセージから推測する
            # 簡易的に8081または範囲内のポートを想定
            for port in [8081] + list(range(10000, 10100)):
                try:
                    import socket
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        if s.connect_ex(("localhost", port)) == 0:
                            self.server_port = port
                            break
                except:
                    continue
            
            if self.server_port is None:
                self.server_port = 8081  # フォールバック
            
            url = f"http://localhost:{self.server_port}/translated_pdf/{os.path.basename(filename)}"
            logger.info(f"Server started, URL: {url}")
            
            return url
            
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            raise
    
    def handle_translate_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """翻訳リクエストを処理"""
        try:
            pdf_url = message.get('pdfUrl')
            if not pdf_url:
                raise Exception("PDF URL not provided")
            
            options = message.get('options', {})
            service = options.get('service', 'plamo')
            language = options.get('language', 'ja')
            output_format = options.get('outputFormat', 'dual')
            
            logger.info(f"Processing translation request for: {pdf_url}")
            logger.info(f"Translation options: service={service}, language={language}, format={output_format}")
            
            # PDFをダウンロード
            pdf_path = self.download_pdf(pdf_url)
            
            try:
                # PDF翻訳
                translated_path = self.translate_pdf(pdf_path, service, language, output_format)
                filename = os.path.basename(translated_path)
                
                # サーバー起動（フルパスを渡す）
                server_url = self.start_server(translated_path)
                
                return {
                    'success': True,
                    'url': server_url,
                    'filename': filename,
                    'message': 'Translation completed successfully'
                }
                
            finally:
                # 一時ファイルを削除
                try:
                    os.remove(pdf_path)
                    os.rmdir(os.path.dirname(pdf_path))
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Translation request failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run(self):
        """メインループ"""
        logger.info("PDF Math Translate Native Host started")
        
        try:
            while True:
                message = self.read_message()
                if message is None:
                    break
                
                action = message.get('action')
                
                if action == 'translate':
                    response = self.handle_translate_request(message)
                    self.send_message(response)
                else:
                    self.send_message({
                        'success': False,
                        'error': f'Unknown action: {action}'
                    })
                    
        except KeyboardInterrupt:
            logger.info("Native host interrupted")
        except Exception as e:
            logger.error(f"Native host error: {e}")
        finally:
            logger.info("PDF Math Translate Native Host stopped")

def main():
    host = NativeMessagingHost()
    host.run()

if __name__ == '__main__':
    main()