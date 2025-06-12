"""
Comprehensive tests for Japanese font and dynamic text sizing functionality.

This module tests the actual behavior of the implemented features.
"""
import unittest
from unittest.mock import Mock, patch
from pdf2zh.converter import TranslateConverter
from pdf2zh.high_level import download_remote_fonts
from pdfminer.pdfinterp import PDFResourceManager


class TestJapaneseFont(unittest.TestCase):
    """Comprehensive tests for Japanese font functionality."""
    
    def test_download_remote_fonts_returns_noto_sans_for_japanese(self):
        """Test that download_remote_fonts requests NotoSansJP for Japanese."""
        with patch('pdf2zh.high_level.get_font_and_metadata') as mock_get_font:
            from pathlib import Path
            mock_get_font.return_value = (Path("/test/NotoSansJP-Regular.ttf"), {})
            
            # When downloading font for Japanese
            font_path = download_remote_fonts("ja")
            
            # Then should request NotoSansJP-Regular.ttf
            mock_get_font.assert_called_once_with("NotoSansJP-Regular.ttf")


class TestDynamicTextSizingFunctionality(unittest.TestCase):
    """Comprehensive tests for dynamic text sizing functionality."""
    
    def setUp(self):
        """Set up test fixtures with proper mocks."""
        self.rsrcmgr = PDFResourceManager()
        self.layout = {1: Mock()}
        
        # Create converter with mocked dependencies
        with patch('pdf2zh.converter.TranslateConverter._setup_fonts'):
            self.converter = TranslateConverter(
                self.rsrcmgr,
                layout=self.layout,
                lang_in="en",
                lang_out="ja",
                service="google"
            )
            
        # Mock the font objects
        self.converter.noto = Mock()
        self.converter.fontmap = {"tiro": Mock()}
        self.converter.noto_name = "noto"
        
    def test_calculate_optimal_font_size_reduces_for_longer_text(self):
        """Test that font size is reduced when translated text is longer."""
        # Mock character widths
        self.converter.noto.char_lengths.return_value = [12.0]  # Japanese chars
        self.converter.fontmap["tiro"].to_unichr.side_effect = lambda x: chr(x)
        self.converter.fontmap["tiro"].char_width.return_value = 0.6  # ASCII chars
        
        # Given: Short English text becomes longer Japanese text
        original_text = "Hello"  # 5 ASCII chars
        translated_text = "こんにちは世界の皆さん"  # 11 Japanese chars
        original_size = 12.0
        available_width = 60.0  # Width that fits original but not translated
        
        # When: Calculating optimal font size
        optimal_size = self.converter.calculate_optimal_font_size(
            original_text, translated_text, original_size, available_width
        )
        
        # Then: Should reduce font size
        self.assertLess(optimal_size, original_size,
                       "Font size should be reduced for longer translated text")
        self.assertGreaterEqual(optimal_size, 6.0,
                               "Font size should not go below minimum threshold")
                               
    def test_calculate_optimal_font_size_respects_minimum(self):
        """Test that font size doesn't go below minimum even for very long text."""
        # Mock character widths
        self.converter.noto.char_lengths.return_value = [12.0]
        
        # Given: Very long translated text
        original_text = "Hi"
        translated_text = "非常に長い日本語の翻訳テキストです" * 20  # Very long
        original_size = 10.0
        available_width = 50.0  # Very small width
        
        # When: Calculating optimal font size
        optimal_size = self.converter.calculate_optimal_font_size(
            original_text, translated_text, original_size, available_width
        )
        
        # Then: Should not go below minimum
        self.assertEqual(optimal_size, 6.0,
                        "Font size should be minimum readable size")
                        
    def test_calculate_optimal_font_size_maintains_size_for_shorter_text(self):
        """Test that font size is maintained when translated text is shorter."""
        # Mock character widths
        self.converter.noto.char_lengths.return_value = [12.0]
        self.converter.fontmap["tiro"].to_unichr.side_effect = lambda x: chr(x)
        self.converter.fontmap["tiro"].char_width.return_value = 0.6
        
        # Given: Long English text becomes shorter Japanese text
        original_text = "This is a very long English sentence"
        translated_text = "短い"  # Much shorter
        original_size = 12.0
        available_width = 200.0
        
        # When: Calculating optimal font size
        optimal_size = self.converter.calculate_optimal_font_size(
            original_text, translated_text, original_size, available_width
        )
        
        # Then: Should maintain original size
        self.assertEqual(optimal_size, original_size,
                        "Font size should be maintained for shorter text")
                        
    def test_calculate_adjusted_line_height_proportional(self):
        """Test that line height is adjusted proportionally to font size change."""
        # Given: Font size reduction
        original_font_size = 12.0
        new_font_size = 8.0
        original_line_height = 1.1  # Japanese default
        
        # When: Calculating adjusted line height
        adjusted_line_height = self.converter.calculate_adjusted_line_height(
            original_font_size, new_font_size, original_line_height
        )
        
        # Then: Should be proportionally adjusted
        expected_ratio = new_font_size / original_font_size  # 8/12 = 0.667
        expected_line_height = original_line_height * expected_ratio
        self.assertAlmostEqual(adjusted_line_height, expected_line_height, places=3,
                              msg="Line height should be adjusted proportionally")
                              
    def test_get_char_width_handles_ascii_characters(self):
        """Test character width calculation for ASCII characters."""
        # Mock tiro font
        self.converter.fontmap["tiro"].to_unichr.return_value = "A"
        self.converter.fontmap["tiro"].char_width.return_value = 0.6
        
        # When: Getting width for ASCII character
        width = self.converter.get_char_width("A", 12.0)
        
        # Then: Should use tiro font calculation
        expected_width = 0.6 * 12.0  # char_width * font_size
        self.assertEqual(width, expected_width,
                        "ASCII character should use tiro font calculation")
                        
    def test_get_char_width_handles_japanese_characters(self):
        """Test character width calculation for Japanese characters."""
        # Mock that tiro font doesn't support Japanese
        self.converter.fontmap["tiro"].to_unichr.side_effect = Exception("Not supported")
        self.converter.noto.char_lengths.return_value = [12.0]
        
        # When: Getting width for Japanese character
        width = self.converter.get_char_width("あ", 12.0)
        
        # Then: Should use noto font calculation
        self.assertEqual(width, 12.0,
                        "Japanese character should use noto font calculation")
                        
    def test_calculate_text_width_mixed_script(self):
        """Test text width calculation for mixed ASCII and Japanese text."""
        # Mock fonts
        def mock_char_width(char, size):
            if ord(char) < 128:  # ASCII
                return size * 0.6
            else:  # CJK
                return size
                
        with patch.object(self.converter, 'get_char_width', side_effect=mock_char_width):
            # Given: Mixed script text
            text = "Hello世界"  # 5 ASCII + 2 CJK
            font_size = 12.0
            
            # When: Calculating text width
            total_width = self.converter._calculate_text_width(text, font_size)
            
            # Then: Should account for different character widths
            expected_width = (5 * 12.0 * 0.6) + (2 * 12.0)  # ASCII + CJK
            self.assertEqual(total_width, expected_width,
                           "Mixed script text width should be calculated correctly")


if __name__ == "__main__":
    unittest.main()