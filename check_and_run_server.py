import socket
import subprocess
import threading
import time
import sys

PORT = 8081
SHUTDOWN_DELAY = 10  # Time in seconds before shutting down the server

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

if len(sys.argv) < 2:
    print("使用方法: python check_and_run_server.py <filename>")
    sys.exit(1)
    
filename = sys.argv[1]

if is_port_in_use(PORT):
    print(f"ポート {PORT} はすでに使用中です。サーバは起動しません。")
else:
    print(f"ポート {PORT} は空いています。サーバを起動します。")
    server_process = subprocess.Popen(
        ["python", "-m", "http.server", str(PORT)],
        cwd="/Users/ytakeda/codes/PDFMathTranslate"
    )
    # Schedule server shutdown
    def shutdown_server():
        time.sleep(SHUTDOWN_DELAY)
        print(f"{SHUTDOWN_DELAY} 秒経過しました。サーバを終了します。")
        server_process.terminate()
    
    threading.Thread(target=shutdown_server, daemon=True).start()

    # Google Chromeで指定されたファイルを開く
    # url = f"http://localhost:{PORT}/{filename}"
    url = f"http://localhost:{PORT}/translated_pdf/{filename.replace('.pdf', '')}-dual.pdf"
    subprocess.run(["open", "-a", "Google Chrome", url])