import os
import datetime
from filelock import FileLock

# ログファイルのパス
LOG_DIR = os.path.expanduser("~/.llm_usage_log")
LOG_FILE = os.path.join(LOG_DIR, "openai.txt")
LOCK_FILE = os.path.join(LOG_DIR, "openai.txt.lock")


def log_usage(tokens, cost):
    """
    使用量をログファイルに記録します。
    :param tokens: 消費したトークン数
    :param cost: かかった金額
    """
    # ディレクトリ作成
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # 初期値
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    daily_usage = {"date": today, "tokens": tokens, "cost": cost}
    total_usage = {"tokens": tokens, "cost": cost}

    # ファイルロックを使用して排他的アクセスを確保
    lock = FileLock(LOCK_FILE, timeout=10)
    try:
        with lock:
            # ファイルが存在すれば読み込んで更新
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    lines = f.readlines()
                    today_found = False
                    for line in lines:
                        if line.startswith("Daily:"):
                            # 日次使用量を解析
                            date, tok, cst = line.split(", ")
                            if date.split(": ")[2] == today:
                                today_found = True
                                daily_usage["tokens"] += int(tok.split(": ")[1])
                                daily_usage["cost"] += float(cst.split(": ")[1])
                        elif line.startswith("Total:"):
                            # 合計使用量を解析
                            tok, cst = line.split(", ")
                            total_usage["tokens"] += int(tok.split(": ")[2])
                            total_usage["cost"] += float(cst.split(": ")[1])

            # 今日の記録がなければ初期値を設定
            if not today_found:
                daily_usage["tokens"] = 0
                daily_usage["cost"] = 0

            # ログファイルを更新
            with open(LOG_FILE, "w") as f:
                # Total行を最初に書き込む
                f.write(
                    f"Total: tokens: {total_usage['tokens']}, cost: {total_usage['cost']:.4f}\n\n"
                )
                # 既存のDaily行を再書き込み
                for line in lines[:-1]:
                    if line.startswith("Daily:"):
                        f.write(line)
                # 今日の記録を一番下に追加または更新
                f.write(
                    f"Daily: date: {daily_usage['date']}, tokens: {daily_usage['tokens']}, cost: {daily_usage['cost']:.4f}\n"
                )
    except TimeoutError:
        print("Warning: Could not acquire lock for usage log within timeout period.")


def check_daily_limit():
    """
    1日のトークン数が100万トークンを超えそうな場合、エラーメッセージを表示します。
    """
    if not os.path.exists(LOG_FILE):
        return

    lock = FileLock(LOCK_FILE, timeout=5)
    try:
        with lock:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("Daily:"):
                        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
                        date, tok, cst = line.split(", ")
                        if date.split(": ")[2] == today:
                            tokens = int(tok.split(": ")[1])
                            if tokens > 990000:
                                print(
                                    "Warning: Daily token limit exceeded (1,000,000 tokens)."
                                )
                                exit()
    except TimeoutError:
        print("Warning: Could not check daily limit due to lock timeout.")


# テストコード
if __name__ == "__main__":
    # テスト用のトークン数とコスト
    test_tokens = 1000
    test_cost = 0.01

    # ログを記録
    log_usage(test_tokens, test_cost)

    # ログファイルの内容を表示
    lock = FileLock(LOCK_FILE)
    with lock:
        with open(LOG_FILE, "r") as f:
            print(f.read())
