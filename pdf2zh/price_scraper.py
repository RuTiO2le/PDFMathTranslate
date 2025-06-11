import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional, Any


class PriceScraper:
    """
    価格情報を管理するクラス
    
    注意: OpenAIのWebサイトはスクレイピングをブロックしているため、
    現在は手動で管理されるデフォルト価格を使用しています。
    価格情報の更新が必要な場合は、DEFAULT_PRICESを手動で更新してください。
    """
    
    # デフォルトの価格情報（2025年1月時点）
    DEFAULT_PRICES = {
        "gpt-4o": {"input": 2.5, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-4o-2024-05-13": {"input": 5.0, "output": 15.0},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4-turbo-2024-04-09": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4-0613": {"input": 30.0, "output": 60.0},
        "gpt-4-32k": {"input": 60.0, "output": 120.0},
        "gpt-4.1": {"input": 2.0, "output": 8.0},
        "gpt-4.1-mini": {"input": 0.4, "output": 1.6},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "gpt-3.5-turbo-0613": {"input": 0.5, "output": 1.5},
        "gpt-3.5-turbo-16k": {"input": 3.0, "output": 4.0},
        "gpt-3.5-turbo-instruct": {"input": 1.5, "output": 2.0},
        "text-embedding-3-small": {"input": 0.02, "output": 0.0},
        "text-embedding-3-large": {"input": 0.13, "output": 0.0},
        "text-embedding-ada-002": {"input": 0.1, "output": 0.0},
        "plamo-1.0-chat": {"input": 0.0, "output": 0.0},
        "plamo-1.0-instruct": {"input": 0.0, "output": 0.0},
        "o3": {"input": 0.0, "output": 0.0}
    }
    
    def fetch_pricing(self) -> Optional[Dict[str, Dict[str, float]]]:
        """
        価格情報を取得（デフォルト価格を返す）
        
        Returns:
            Dict[str, Dict[str, float]]: モデル名をキーとした価格情報
            例: {"gpt-4": {"input": 30.0, "output": 60.0}}
        """
        return self.DEFAULT_PRICES


class PriceData:
    """価格データの保存・読み込みを管理するクラス"""
    
    def __init__(self, price_file: str = None):
        """
        Args:
            price_file: 価格情報を保存するJSONファイルのパス
        """
        if price_file is None:
            self.price_file = os.path.expanduser("~/.llm_usage_log/openai_pricing.json")
        else:
            self.price_file = price_file
        
        # ディレクトリの作成
        os.makedirs(os.path.dirname(self.price_file), exist_ok=True)
    
    def save_prices(self, prices: Dict[str, Dict[str, float]]) -> None:
        """
        価格情報をファイルに保存
        
        Args:
            prices: モデル名をキーとした価格情報
        """
        data = {
            "prices": prices,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        with open(self.price_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_prices(self) -> Optional[Dict[str, Any]]:
        """
        価格情報をファイルから読み込み
        
        Returns:
            Dict[str, Any]: 価格情報と最終更新日時を含む辞書
        """
        if not os.path.exists(self.price_file):
            return None
        
        try:
            with open(self.price_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading price data: {e}")
            return None
    
    def needs_update(self) -> bool:
        """
        価格情報の更新が必要かチェック
        
        注意: 自動更新は無効化されています。
        価格情報はデフォルト値を使用するか、手動で更新してください。
        
        Returns:
            bool: 常にFalseを返す（自動更新無効）
        """
        return False
    
    def get_price(self, model_name: str) -> Optional[Dict[str, float]]:
        """
        特定モデルの価格情報を取得
        
        Args:
            model_name: モデル名
            
        Returns:
            Dict[str, float]: input/outputの価格情報
        """
        data = self.load_prices()
        if data is None:
            return None
        
        return data.get("prices", {}).get(model_name)
    
    def update_if_needed(self) -> bool:
        """
        必要に応じて価格情報を更新
        
        注意: 自動更新は無効化されています。
        価格情報を更新する場合は、手動でsave_prices()を呼び出してください。
        
        Returns:
            bool: 常にFalseを返す（自動更新無効）
        """
        # 自動更新は無効化されています
        return False