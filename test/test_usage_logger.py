import pytest
import os
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from pdf2zh.usage_logger import log_usage, calculate_cost, check_daily_limit
from pdf2zh.price_scraper import PriceData


class TestUsageLogger:
    """使用量ロギング機能のテスト"""

    @pytest.fixture
    def temp_log_dir(self):
        """一時的なログディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_calculate_cost(self):
        """コスト計算のテスト"""
        # モックの価格データを設定
        with patch.object(PriceData, 'get_price') as mock_get_price:
            mock_get_price.return_value = {"input": 10.0, "output": 30.0}
            
            # GPT-4のコスト計算
            cost = calculate_cost("gpt-4", 1000, 500)
            # (1000/1M * 10) + (500/1M * 30) = 0.01 + 0.015 = 0.025
            assert abs(cost - 0.025) < 0.0001
            
            # 価格が見つからない場合
            mock_get_price.return_value = None
            cost = calculate_cost("unknown-model", 1000, 500)
            # デフォルト価格: (1000/1M * 0.01) + (500/1M * 0.03) = 0.00001 + 0.000015 = 0.000025
            assert abs(cost - 0.000025) < 0.000001

    @patch('pdf2zh.usage_logger.LOG_DIR')
    @patch('pdf2zh.usage_logger.LOG_FILE')
    @patch('pdf2zh.usage_logger.LOCK_FILE')
    def test_log_usage_with_cost(self, mock_lock, mock_file, mock_dir, temp_log_dir):
        """コスト指定でのログ記録テスト"""
        mock_dir.return_value = temp_log_dir
        mock_file.return_value = os.path.join(temp_log_dir, "openai.txt")
        mock_lock.return_value = os.path.join(temp_log_dir, "openai.txt.lock")
        
        # ログ記録
        log_usage(1000, 0.05)
        
        # ファイルの確認
        log_file = os.path.join(temp_log_dir, "openai.txt")
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Total: tokens: 1000, cost: 0.0500" in content
            assert "Daily:" in content

    @patch('pdf2zh.usage_logger.LOG_DIR')
    @patch('pdf2zh.usage_logger.LOG_FILE')
    @patch('pdf2zh.usage_logger.LOCK_FILE')
    @patch('pdf2zh.usage_logger.calculate_cost')
    def test_log_usage_with_auto_calc(self, mock_calc, mock_lock, mock_file, mock_dir, temp_log_dir):
        """自動コスト計算でのログ記録テスト"""
        mock_dir.return_value = temp_log_dir
        mock_file.return_value = os.path.join(temp_log_dir, "openai.txt")
        mock_lock.return_value = os.path.join(temp_log_dir, "openai.txt.lock")
        mock_calc.return_value = 0.025
        
        # ログ記録（コスト自動計算）
        log_usage(1500, model="gpt-4", input_tokens=1000, output_tokens=500)
        
        # calculate_costが呼ばれたことを確認
        mock_calc.assert_called_once_with("gpt-4", 1000, 500)
        
        # ファイルの確認
        log_file = os.path.join(temp_log_dir, "openai.txt")
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Total: tokens: 1500, cost: 0.0250" in content

    def test_log_usage_missing_params(self):
        """必要なパラメータが不足している場合のテスト"""
        with pytest.raises(ValueError, match="Cost calculation requires"):
            log_usage(1000)  # costもmodelも指定なし

    @patch('pdf2zh.usage_logger.LOG_DIR')
    @patch('pdf2zh.usage_logger.LOG_FILE')
    @patch('pdf2zh.usage_logger.LOCK_FILE')
    def test_check_daily_limit(self, mock_lock, mock_file, mock_dir, temp_log_dir):
        """日次制限チェックのテスト"""
        mock_dir.return_value = temp_log_dir
        log_file = os.path.join(temp_log_dir, "openai.txt")
        mock_file.return_value = log_file
        mock_lock.return_value = os.path.join(temp_log_dir, "openai.txt.lock")
        
        # 制限内のログファイル作成
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(log_file, 'w') as f:
            f.write(f"Total: tokens: 500000, cost: 5.0000\\n\\n")
            f.write(f"Daily: date: {today}, tokens: 500000, cost: 5.0000\\n")
        
        # エラーなし
        check_daily_limit()
        
        # 制限超過のログファイル作成
        with open(log_file, 'w') as f:
            f.write(f"Total: tokens: 1000000, cost: 10.0000\\n\\n")
            f.write(f"Daily: date: {today}, tokens: 995000, cost: 9.9500\\n")
        
        # SystemExitが発生することを確認
        with pytest.raises(SystemExit):
            check_daily_limit()