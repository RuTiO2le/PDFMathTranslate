import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta, timezone
from pdf2zh.price_scraper import PriceScraper, PriceData


class TestPriceScraper:
    """価格スクレイピング機能のテスト"""

    def test_fetch_default_pricing(self):
        """デフォルト価格の取得テスト"""
        scraper = PriceScraper()
        prices = scraper.fetch_pricing()
        
        assert prices is not None
        assert "gpt-4" in prices
        assert "gpt-4o" in prices
        assert "gpt-3.5-turbo" in prices
        assert prices["gpt-4.1"]["input"] == 2.0
        assert prices["gpt-4.1"]["output"] == 8.0
        assert prices["gpt-4o"]["input"] == 2.5
        assert prices["gpt-4o"]["output"] == 10.0

    def test_fetch_pricing_returns_default(self):
        """価格取得が常にデフォルトを返すテスト"""
        scraper = PriceScraper()
        prices = scraper.fetch_pricing()
        
        assert prices is not None
        assert isinstance(prices, dict)
        assert prices == scraper.DEFAULT_PRICES

    def test_default_prices_structure(self):
        """デフォルト価格の構造テスト"""
        scraper = PriceScraper()
        
        for model, prices in scraper.DEFAULT_PRICES.items():
            assert "input" in prices
            assert "output" in prices
            assert isinstance(prices["input"], (int, float))
            assert isinstance(prices["output"], (int, float))
            assert prices["input"] >= 0
            assert prices["output"] >= 0

    def test_price_data_save_and_load(self, tmp_path):
        """価格データの保存と読み込みのテスト"""
        price_file = tmp_path / "openai_pricing.json"
        price_data = PriceData(price_file)
        
        # 価格データの保存
        test_prices = {
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5}
        }
        price_data.save_prices(test_prices)
        
        # 価格データの読み込み
        loaded_prices = price_data.load_prices()
        
        assert loaded_prices is not None
        assert loaded_prices["prices"] == test_prices
        assert "last_updated" in loaded_prices
        assert price_file.exists()

    def test_price_data_needs_update(self, tmp_path):
        """価格データの更新必要性チェックのテスト"""
        price_file = tmp_path / "openai_pricing.json"
        price_data = PriceData(price_file)
        
        # 自動更新が無効化されているため、常にFalse
        assert price_data.needs_update() is False
        
        # 価格データを保存しても、自動更新は無効
        test_prices = {"gpt-4": {"input": 30.0, "output": 60.0}}
        price_data.save_prices(test_prices)
        assert price_data.needs_update() is False

    def test_get_price_for_model(self, tmp_path):
        """特定モデルの価格取得のテスト"""
        price_file = tmp_path / "openai_pricing.json"
        price_data = PriceData(price_file)
        
        test_prices = {
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5}
        }
        price_data.save_prices(test_prices)
        
        # 存在するモデル
        gpt4_price = price_data.get_price("gpt-4")
        assert gpt4_price == {"input": 30.0, "output": 60.0}
        
        # 存在しないモデル
        unknown_price = price_data.get_price("unknown-model")
        assert unknown_price is None

    def test_update_prices_disabled(self, tmp_path):
        """自動更新が無効化されていることのテスト"""
        price_file = tmp_path / "openai_pricing.json"
        price_data = PriceData(price_file)
        
        # 自動更新は常にFalseを返す
        assert price_data.update_if_needed() is False
        
        # 価格を保存しても自動更新は無効
        test_prices = {"gpt-4": {"input": 30.0, "output": 60.0}}
        price_data.save_prices(test_prices)
        assert price_data.update_if_needed() is False