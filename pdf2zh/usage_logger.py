import os
from datetime import datetime, timezone
from filelock import FileLock
from typing import Optional
from .price_scraper import PriceData

# ログファイルのパス
LOG_DIR = os.path.expanduser("~/.llm_usage_log")
LOG_FILE = os.path.join(LOG_DIR, "openai.txt")
LOCK_FILE = os.path.join(LOG_DIR, "openai.txt.lock")

# 価格データマネージャーの初期化
price_data = PriceData()


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    モデルとトークン数から料金を計算
    
    Args:
        model: 使用したモデル名
        input_tokens: 入力トークン数
        output_tokens: 出力トークン数
        
    Returns:
        float: 計算されたコスト（ドル）
    """
    # 価格情報の更新チェック
    price_data.update_if_needed()
    
    # モデルの価格を取得
    prices = price_data.get_price(model)
    if prices is None:
        # 価格が見つからない場合はデフォルト価格を使用
        print(f"Warning: Price not found for model {model}. Using default.")
        prices = {"input": 0.01, "output": 0.03}  # デフォルト価格
    
    # コストを計算（価格は1Mトークンあたり）
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    
    return input_cost + output_cost


def log_usage(tokens: int, cost: Optional[float] = None, model: Optional[str] = None,
              input_tokens: Optional[int] = None, output_tokens: Optional[int] = None):
    """
    使用量をログファイルに記録します。
    
    Args:
        tokens: 消費した総トークン数
        cost: かかった金額（省略時は自動計算）
        model: 使用したモデル名（cost自動計算時に必要）
        input_tokens: 入力トークン数（cost自動計算時に必要）
        output_tokens: 出力トークン数（cost自動計算時に必要）
    """
    # コストが指定されていない場合は計算
    if cost is None:
        if model is None or input_tokens is None or output_tokens is None:
            raise ValueError("Cost calculation requires model, input_tokens, and output_tokens")
        cost = calculate_cost(model, input_tokens, output_tokens)
    # ディレクトリ作成
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # 初期値
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
                daily_usage["tokens"] = tokens
                daily_usage["cost"] = cost

            # ログファイルを更新
            with open(LOG_FILE, "w") as f:
                # Total行を最初に書き込む
                f.write(
                    f"Total: tokens: {total_usage['tokens']}, cost: {total_usage['cost']:.4f}\n\n"
                )
                # 既存のDaily行を再書き込み（今日の分は除く）
                if 'lines' in locals():
                    for line in lines:
                        if line.startswith("Daily:"):
                            date_str = line.split(", ")[0].split(": ")[2]
                            if date_str != today:
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
                        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        parts = line.split(", ")
                        date = parts[0]
                        tok = parts[1]
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
