import socket
import subprocess
import threading
import time
import sys
import os
import signal
import urllib.request
import urllib.error

# デフォルトポート範囲を定義
DEFAULT_PORT = 8081
FIVE_DIGIT_START = 10000
FIVE_DIGIT_END = 65535
SHUTDOWN_DELAY = 300  # 5分後に自動シャットダウン

# 有名なポート番号（避けるべきポート）
WELL_KNOWN_PORTS = {
    # Web servers
    10080, 10443,
    # Development servers  
    10000, 10001, 10002, 10003, 10004, 10005,
    # Database related
    13306, 15432, 16379, 17017,
    # Common application ports
    18080, 18443, 19000, 19001, 19090,
    # Docker/Container related
    12375, 12376, 12379, 15000,
    # Other common services
    11211, 16379, 25565, 27017, 28017,
}

def is_port_in_use(port):
    """指定されたポートが使用中かチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def find_available_port():
    """利用可能なポートを探す"""
    # まずデフォルトポートを試す
    if not is_port_in_use(DEFAULT_PORT):
        return DEFAULT_PORT
    
    # デフォルトがダメなら5桁の範囲で探す
    import random
    
    # ランダムな開始点から探索（同じポートばかり試すのを避ける）
    start_port = random.randint(FIVE_DIGIT_START, FIVE_DIGIT_END - 1000)
    
    # 開始点から最大1000ポート試す
    for i in range(1000):
        port = start_port + i
        if port > FIVE_DIGIT_END:
            port = FIVE_DIGIT_START + (port - FIVE_DIGIT_END - 1)
        
        # 有名なポートをスキップ
        if port in WELL_KNOWN_PORTS:
            continue
            
        if not is_port_in_use(port):
            return port
    
    return None

def check_server_response(port, path):
    """サーバーが正しく応答するかチェック"""
    try:
        url = f"http://localhost:{port}/{path}"
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, socket.timeout):
        return False

def is_pdf_server(port):
    """ポートがPDF表示用のHTTPサーバーかチェック"""
    try:
        # まず、基本的なHTTPサーバーかチェック
        root_url = f"http://localhost:{port}/"
        with urllib.request.urlopen(root_url, timeout=2) as response:
            content = response.read().decode('utf-8', errors='ignore')
            # Pythonの http.server の特徴的な文字列をチェック
            if "Directory listing for" in content or "Index of /" in content:
                # translated_pdf ディレクトリの存在をチェック
                translated_pdf_url = f"http://localhost:{port}/translated_pdf/"
                try:
                    with urllib.request.urlopen(translated_pdf_url, timeout=2) as resp:
                        if resp.status == 200:
                            return True
                except (urllib.error.URLError, socket.timeout):
                    pass
            return False
    except (urllib.error.URLError, socket.timeout):
        return False

def get_process_info(port):
    """ポートを使用しているプロセス情報を取得"""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-n", "-P"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # ヘッダーをスキップ
                parts = line.split()
                if len(parts) >= 2:
                    command = parts[0]
                    pid = parts[1]
                    # Pythonプロセスで、http.serverを実行している可能性が高い
                    if 'python' in command.lower():
                        return {'command': command, 'pid': pid, 'is_python': True}
                    else:
                        return {'command': command, 'pid': pid, 'is_python': False}
    except Exception as e:
        print(f"プロセス情報取得エラー: {e}")
    return None

def kill_process_on_port(port):
    """指定されたポートを使用しているプロセスを終了"""
    try:
        # lsofコマンドでポートを使用しているプロセスを探す
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = int(result.stdout.strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)  # プロセスが終了するまで待つ
            return True
    except Exception as e:
        print(f"プロセス終了エラー: {e}")
    return False

if len(sys.argv) < 2:
    print("使用方法: python check_and_run_server.py <filepath>")
    sys.exit(1)
    
filepath = sys.argv[1]
filename = os.path.basename(filepath)

# ファイルが存在するか確認
if not os.path.exists(filepath):
    print(f"エラー: ファイルが見つかりません: {filepath}")
    sys.exit(1)

# 正しいURLパスを生成
# /translated_pdf/内のファイルへの相対パス
relative_path = f"translated_pdf/{filename}"

# 既存のサーバーをチェック
server_found = False
server_port = None

# まずデフォルトポートをチェック
ports_to_check = [DEFAULT_PORT]

# 他のポートも少しチェック（8082-8090, 一部の5桁ポート）
ports_to_check.extend(range(8082, 8091))
ports_to_check.extend([10081, 10082, 10083, 10084, 10085, 20000, 30000, 40000, 50000])

for port in ports_to_check:
    if is_port_in_use(port):
        # ポートが使用中の場合、PDF表示用サーバーかチェック
        if is_pdf_server(port):
            # PDF表示用サーバーの場合、目的のファイルが存在するかチェック
            if check_server_response(port, relative_path):
                print(f"ポート {port} で適切なPDFサーバーが稼働中です。")
                server_found = True
                server_port = port
                break
            else:
                print(f"ポート {port} はPDFサーバーですが、目的のファイルがありません。そのまま使用します。")
                server_found = True
                server_port = port
                break
        else:
            # PDF表示用サーバーではない場合、プロセス情報を確認
            process_info = get_process_info(port)
            if process_info:
                if process_info['is_python']:
                    print(f"ポート {port} で他のPythonプロセス({process_info['command']})が稼働中。終了を試みます。")
                    if kill_process_on_port(port):
                        print(f"ポート {port} を解放しました。")
                else:
                    print(f"ポート {port} で他のサービス({process_info['command']})が稼働中。スキップします。")
            else:
                print(f"ポート {port} で不明なプロセスが稼働中。終了を試みます。")
                if kill_process_on_port(port):
                    print(f"ポート {port} を解放しました。")

# サーバーが見つからない場合は新規起動
if not server_found:
    server_port = find_available_port()
    if server_port is None:
        print("エラー: 利用可能なポートが見つかりません。")
        sys.exit(1)
    
    print(f"ポート {server_port} でサーバーを起動します。")
    server_process = subprocess.Popen(
        ["python", "-m", "http.server", str(server_port)],
        cwd="/Users/ytakeda/codes/PDFMathTranslate",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # サーバーの起動を待つ
    time.sleep(1)
    
    # 自動シャットダウンのスケジュール
    def shutdown_server():
        time.sleep(SHUTDOWN_DELAY)
        print(f"{SHUTDOWN_DELAY} 秒経過しました。サーバーを終了します。")
        server_process.terminate()
    
    threading.Thread(target=shutdown_server, daemon=True).start()

# ブラウザでファイルを開く
url = f"http://localhost:{server_port}/{relative_path}"
print(f"ブラウザで開きます: {url}")
# 拡張機能から呼び出される場合はブラウザの自動オープンを無効化
# subprocess.run(["open", "-a", "Google Chrome", url])