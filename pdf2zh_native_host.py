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
        self.translated_dir = self.base_dir / "translated_pdf"
        self.translated_dir.mkdir(exist_ok=True)
        self.server_port = 8081
        
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
    
    def translate_pdf(self, pdf_path: str, service: str = "plamo", language: str = "ja") -> str:
        """pdf2zhを使用してPDFを翻訳"""
        try:
            # pdf2zhコマンドを実行
            cmd = ["pdf2zh", pdf_path, "-s", service, "-lo", language]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # 仮想環境をアクティベート
            venv_path = self.base_dir / ".venv" / "bin" / "activate"
            if venv_path.exists():
                cmd = ["/bin/bash", "-c", f"source {venv_path} && {' '.join(cmd)}"]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5分でタイムアウト
            )
            
            if result.returncode != 0:
                logger.error(f"pdf2zh failed: {result.stderr}")
                raise Exception(f"Translation failed: {result.stderr}")
            
            logger.info(f"pdf2zh completed successfully: {result.stdout}")
            
            # 翻訳済みファイルのパスを取得
            pdf_name = os.path.basename(pdf_path)
            translated_path = self.translated_dir / pdf_name
            
            if not translated_path.exists():
                raise Exception(f"Translated file not found: {translated_path}")
            
            return str(translated_path)
            
        except subprocess.TimeoutExpired:
            logger.error("pdf2zh command timed out")
            raise Exception("Translation timed out")
        except Exception as e:
            logger.error(f"Error translating PDF: {e}")
            raise
    
    def start_server(self, filename: str) -> str:
        """翻訳結果を表示するサーバーを起動"""
        try:
            # check_and_run_server.pyを実行
            server_script = self.base_dir / "check_and_run_server.py"
            if not server_script.exists():
                raise Exception("Server script not found")
            
            cmd = ["python", str(server_script), filename]
            logger.info(f"Starting server: {' '.join(cmd)}")
            
            # バックグラウンドでサーバーを起動
            subprocess.Popen(
                cmd,
                cwd=str(self.base_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # サーバーの起動を待つ
            time.sleep(2)
            
            url = f"http://localhost:{self.server_port}/{filename}"
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
            
            logger.info(f"Processing translation request for: {pdf_url}")
            
            # PDFをダウンロード
            pdf_path = self.download_pdf(pdf_url)
            
            try:
                # PDF翻訳
                translated_path = self.translate_pdf(pdf_path, service, language)
                filename = os.path.basename(translated_path)
                
                # サーバー起動
                server_url = self.start_server(filename)
                
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