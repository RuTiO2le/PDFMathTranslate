# Google Drive統合論文管理システム 実装計画

## 🎯 概要

本文書は、現在動作中のPDF Math Translate Chrome Extensionに影響を与えることなく、Google Drive統合論文管理システムを段階的に実装するための詳細計画です。

## ⚠️ 重要な制約

- **現在の拡張機能の機能を維持**: 既存の翻訳機能は一切変更しない
- **段階的実装**: 新機能は独立したモジュールとして実装
- **後方互換性**: 既存のワークフローを破綻させない
- **オプトイン方式**: Google Drive機能は設定で有効化

## 🏗️ システムアーキテクチャ

### ディレクトリ構造
```
Google Drive/Research_Papers/
├── papers/                          # 実際のPDFファイル（一箇所集中）
├── metadata/
│   ├── papers_index.json           # 論文管理用JSON
│   └── categories_config.json      # ディレクトリ管理用JSON
└── shortcuts/                      # ショートカットによる分類
    ├── ML_AI/
    ├── NLP/
    └── Computer_Vision/
```

### データ構造

#### papers_index.json
```json
{
  "papers": {
    "2506.06751": {
      "arxiv_id": "2506.06751",
      "title": "Large Language Models for Mathematical Reasoning",
      "abstract": "In this paper, we investigate...",
      "authors": ["John Doe", "Jane Smith"],
      "arxiv_url": "https://arxiv.org/abs/2506.06751",
      "local_file": "papers/2506.06751-dual.pdf",
      "drive_file_id": "1ABC...XYZ",
      "llm_tags": ["mathematics", "reasoning", "transformer"],
      "confidence_scores": {
        "ML_AI": 0.85,
        "Mathematics": 0.92,
        "NLP": 0.73
      },
      "primary_category": "Mathematics",
      "secondary_categories": ["ML_AI", "NLP"],
      "shortcut_paths": [
        "shortcuts/Mathematics/Reasoning/2506.06751-dual.pdf",
        "shortcuts/ML_AI/LLM/2506.06751-dual.pdf"
      ],
      "translation_info": {
        "service": "anthropic:claude-3-5-sonnet-20241022",
        "target_language": "ja",
        "format": "dual",
        "translated_at": "2025-06-12T10:30:00Z"
      },
      "metadata": {
        "added_at": "2025-06-12T10:25:00Z",
        "last_updated": "2025-06-12T10:35:00Z",
        "source": "arxiv_api",
        "abstract_source": "arxiv_api"
      }
    }
  },
  "statistics": {
    "total_papers": 1247,
    "last_updated": "2025-06-12T10:35:00Z",
    "categories_count": {
      "ML_AI": 456,
      "NLP": 332,
      "Computer_Vision": 287,
      "Mathematics": 172
    }
  }
}
```

#### categories_config.json
```json
{
  "version": "2.0",
  "last_updated": "2025-06-12T10:00:00Z",
  "categories": {
    "ML_AI": {
      "name": "機械学習・AI",
      "keywords": ["machine learning", "deep learning", "neural network", "AI"],
      "subcategories": {
        "Deep_Learning": {
          "keywords": ["deep learning", "neural network", "CNN", "RNN"]
        },
        "Reinforcement_Learning": {
          "keywords": ["reinforcement learning", "RL", "policy", "reward"]
        },
        "LLM": {
          "keywords": ["large language model", "transformer", "GPT", "BERT"]
        }
      }
    },
    "NLP": {
      "name": "自然言語処理",
      "keywords": ["natural language", "text", "language model", "NLP"],
      "subcategories": {
        "Text_Generation": {
          "keywords": ["text generation", "language generation"]
        },
        "Machine_Translation": {
          "keywords": ["translation", "machine translation", "MT"]
        }
      }
    }
  },
  "classification_rules": {
    "confidence_threshold": 0.7,
    "multi_category_limit": 3,
    "primary_category_min_confidence": 0.8
  }
}
```

## 📋 実装マイルストーン

### Phase 1: 基盤モジュール開発 (Week 1-2)
**目標**: 既存機能に影響しない独立したライブラリを作成

#### 1.1 AbstractExtractor モジュール
**ファイル**: `pdf2zh/abstract_extractor.py`

```python
#!/usr/bin/env python3
"""
Abstract抽出モジュール
arXiv API → PDF抽出の2段階フォールバック
"""

import arxiv
import pdfplumber
import re
import os
from typing import Optional, Dict, Any
from pathlib import Path

class AbstractExtractor:
    def __init__(self):
        self.arxiv_client = arxiv.Client()
    
    def extract_abstract(self, identifier: str, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        arXiv ID/PDF パスからAbstractとメタデータを抽出
        
        Args:
            identifier: arXiv ID (例: "2506.06751")
            pdf_path: PDFファイルパス（フォールバック用）
            
        Returns:
            Dict containing title, abstract, authors, etc.
        """
        # Step 1: arXiv APIで試行
        if self.is_arxiv_id(identifier):
            try:
                return self.extract_from_arxiv(identifier)
            except Exception as e:
                print(f"arXiv API failed: {e}")
        
        # Step 2: PDFから抽出（フォールバック）
        if pdf_path and os.path.exists(pdf_path):
            return self.extract_from_pdf(pdf_path)
        
        raise Exception("No valid source for abstract extraction")
    
    def is_arxiv_id(self, identifier: str) -> bool:
        """arXiv IDかどうかを判定"""
        # arXiv ID pattern: YYMM.NNNNN
        pattern = r'^\d{4}\.\d{4,5}$'
        return bool(re.match(pattern, identifier))
    
    def extract_from_arxiv(self, arxiv_id: str) -> Dict[str, Any]:
        """arXiv APIから情報取得"""
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(self.arxiv_client.results(search))
        
        if not results:
            raise Exception(f"Paper not found: {arxiv_id}")
        
        paper = results[0]
        return {
            "title": paper.title,
            "abstract": paper.summary,
            "authors": [author.name for author in paper.authors],
            "arxiv_url": paper.entry_id,
            "published": paper.published.isoformat(),
            "source": "arxiv_api"
        }
    
    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """PDFからAbstract抽出"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                # Abstract部分を正規表現で抽出
                abstract_pattern = r'(?i)abstract[:\s]*\n?(.*?)(?=\n\s*(?:introduction|keywords|1\.|i\.|background))'
                match = re.search(abstract_pattern, text, re.DOTALL)
                
                if match:
                    abstract = match.group(1).strip()
                    title = self.extract_title_from_pdf(text)
                    
                    return {
                        "title": title,
                        "abstract": abstract,
                        "authors": [],  # PDF解析で著者抽出は複雑
                        "source": "pdf_extraction"
                    }
        except Exception as e:
            print(f"PDF extraction failed: {e}")
        
        raise Exception("Could not extract abstract from PDF")
    
    def extract_title_from_pdf(self, text: str) -> str:
        """PDFからタイトル抽出（簡易版）"""
        lines = text.split('\n')
        # 通常、最初の数行がタイトル
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 10 and not line.lower().startswith(('abstract', 'author', 'introduction')):
                return line
        return "Unknown Title"
```

#### 1.2 DriveManager モジュール
**ファイル**: `pdf2zh/drive_manager.py`

```python
#!/usr/bin/env python3
"""
Google Drive管理モジュール
ショートカット作成、ファイルアップロード、フォルダ管理
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

class DriveManager:
    def __init__(self, credentials_path: str, base_folder_name: str = "Research_Papers"):
        self.credentials_path = credentials_path
        self.base_folder_name = base_folder_name
        self.service = None
        self.base_folder_id = None
        self._initialize()
    
    def _initialize(self):
        """Google Drive API初期化"""
        try:
            self.service = self._authenticate()
            self.base_folder_id = self._get_or_create_base_folder()
            print(f"Google Drive initialized. Base folder ID: {self.base_folder_id}")
        except Exception as e:
            print(f"Google Drive initialization failed: {e}")
            self.service = None
    
    def _authenticate(self):
        """Google Drive API認証"""
        creds = None
        token_path = self.credentials_path.replace('.json', '_token.json')
        
        # 既存のトークンファイルをロード
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path)
        
        # 認証が無効な場合は再認証
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("Invalid credentials. Please re-authenticate.")
        
        return build('drive', 'v3', credentials=creds)
    
    def _get_or_create_base_folder(self) -> str:
        """ベースフォルダを取得または作成"""
        # 既存フォルダを検索
        results = self.service.files().list(
            q=f"name='{self.base_folder_name}' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            return folders[0]['id']
        
        # フォルダが存在しない場合は作成
        folder_metadata = {
            'name': self.base_folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
    
    def upload_to_papers_folder(self, file_path: str, metadata: Dict[str, Any]) -> str:
        """papers/フォルダにファイルをアップロード"""
        papers_folder_id = self._get_or_create_subfolder('papers')
        
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [papers_folder_id]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return file.get('id')
    
    def create_shortcut(self, target_file_id: str, parent_folder_id: str, name: str) -> str:
        """Google Driveショートカット作成"""
        shortcut_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.shortcut',
            'shortcutDetails': {
                'targetId': target_file_id
            },
            'parents': [parent_folder_id]
        }
        
        shortcut = self.service.files().create(
            body=shortcut_metadata,
            fields='id,shortcutDetails'
        ).execute()
        
        return shortcut.get('id')
    
    def _get_or_create_subfolder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """サブフォルダを取得または作成"""
        if parent_id is None:
            parent_id = self.base_folder_id
        
        # 既存フォルダを検索
        results = self.service.files().list(
            q=f"name='{folder_name}' and parents in '{parent_id}' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            return folders[0]['id']
        
        # フォルダ作成
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = self.service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
    
    def is_available(self) -> bool:
        """Google Drive機能が利用可能かチェック"""
        return self.service is not None
```

#### 1.3 LLMClassifier モジュール
**ファイル**: `pdf2zh/llm_classifier.py`

```python
#!/usr/bin/env python3
"""
LLM論文分類モジュール
Claude/GPTを使用した論文の自動分類
"""

import json
import re
from typing import Dict, Any, List
from pdf2zh.translator import get_translator  # 既存の翻訳機能を活用

class LLMClassifier:
    def __init__(self, categories_config: Dict[str, Any], service: str = "anthropic:claude-3-5-sonnet-20241022"):
        self.categories = categories_config['categories']
        self.rules = categories_config['classification_rules']
        self.service = service
    
    def classify_paper(self, title: str, abstract: str) -> Dict[str, Any]:
        """LLMを使用して論文を分類"""
        
        category_list = list(self.categories.keys())
        category_descriptions = {
            name: f"{config['name']}: {', '.join(config['keywords'][:5])}"
            for name, config in self.categories.items()
        }
        
        prompt = f"""以下の論文を適切なカテゴリに分類してください：

タイトル: {title}

Abstract: {abstract}

利用可能なカテゴリ:
{json.dumps(category_descriptions, ensure_ascii=False, indent=2)}

以下の形式でJSONで回答してください：
{{
    "primary_category": "最も適切なカテゴリ名",
    "confidence_scores": {{"カテゴリ1": 0.85, "カテゴリ2": 0.23}},
    "llm_tags": ["タグ1", "タグ2", "タグ3"],
    "reasoning": "分類の理由（1-2文）"
}}

注意: JSONの形式を厳密に守って回答してください。"""
        
        try:
            # 既存の翻訳機能を活用してLLM API呼び出し
            translator = get_translator(self.service)
            response = translator.translate(prompt)
            
            # JSON部分を抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return self._validate_classification(result)
            else:
                raise Exception("Could not extract JSON from LLM response")
                
        except Exception as e:
            print(f"LLM classification failed: {e}")
            return self._fallback_classification(title, abstract)
    
    def _validate_classification(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """分類結果の妥当性チェック"""
        # 必須フィールドの確認
        required_fields = ['primary_category', 'confidence_scores', 'llm_tags']
        for field in required_fields:
            if field not in result:
                raise Exception(f"Missing required field: {field}")
        
        # プライマリカテゴリの妥当性チェック
        if result['primary_category'] not in self.categories:
            raise Exception(f"Invalid primary category: {result['primary_category']}")
        
        # 信頼度スコアの正規化
        confidence_scores = result['confidence_scores']
        total_confidence = sum(confidence_scores.values())
        if total_confidence > 0:
            result['confidence_scores'] = {
                k: v / total_confidence for k, v in confidence_scores.items()
            }
        
        return result
    
    def _fallback_classification(self, title: str, abstract: str) -> Dict[str, Any]:
        """LLM分類失敗時のフォールバック（キーワードベース）"""
        text = f"{title} {abstract}".lower()
        scores = {}
        
        for category, config in self.categories.items():
            score = 0
            for keyword in config['keywords']:
                if keyword.lower() in text:
                    score += 1
            scores[category] = score / len(config['keywords'])
        
        primary_category = max(scores, key=scores.get) if scores else list(self.categories.keys())[0]
        
        return {
            'primary_category': primary_category,
            'confidence_scores': scores,
            'llm_tags': [],
            'reasoning': 'Fallback keyword-based classification'
        }
```

### Phase 2: 設定システム拡張 (Week 3)
**目標**: 既存設定に Google Drive オプションを追加

#### 2.1 options.html の拡張
**既存の options.html の Google Drive セクションを有効化**

```html
<!-- Google Drive連携設定 -->
<div class="section" id="gdrive-section">
    <h2>☁️ Google Drive 連携</h2>
    
    <div class="checkbox-group">
        <input type="checkbox" id="enableGoogleDrive">
        <label for="enableGoogleDrive">Google Drive 自動整理を有効にする</label>
    </div>
    <div class="description">翻訳完了後、自動的にGoogle Driveに保存し、分類します。</div>
    
    <div class="form-group gdrive-options" style="display: none;">
        <label for="googleDrivePath">Google Drive パス</label>
        <input type="text" id="googleDrivePath" 
               placeholder="Research_Papers">
        <div class="description">Google Driveに作成するフォルダ名を指定してください。</div>
    </div>
    
    <div class="form-group gdrive-options" style="display: none;">
        <label for="classificationThreshold">分類信頼度閾値</label>
        <input type="range" id="classificationThreshold" 
               min="50" max="95" value="70">
        <span id="thresholdValue">70%</span>
        <div class="description">自動分類の信頼度閾値。低いほど多くのカテゴリに分類されます。</div>
    </div>
    
    <div class="credentials-section gdrive-options" style="display: none;">
        <h3>🔐 認証設定</h3>
        <button id="authenticateGDrive" class="auth-button">Google Drive認証</button>
        <div id="authStatus" class="auth-status"></div>
    </div>
</div>
```

#### 2.2 options.js の拡張
```javascript
// Google Drive設定の追加
const EXTENDED_DEFAULT_SETTINGS = {
    ...DEFAULT_SETTINGS,
    enableGoogleDrive: false,
    googleDrivePath: 'Research_Papers',
    classificationThreshold: 70,
    gdriveCredentials: null
};

// Google Drive有効化チェックボックスの処理
elements.enableGoogleDrive.addEventListener('change', (e) => {
    const gdriveOptions = document.querySelectorAll('.gdrive-options');
    gdriveOptions.forEach(option => {
        option.style.display = e.target.checked ? 'block' : 'none';
    });
});

// 認証ボタンの処理
elements.authenticateGDrive.addEventListener('click', async () => {
    try {
        // Native Hostに認証リクエストを送信
        const response = await chrome.runtime.sendMessage({
            action: 'authenticateGoogleDrive'
        });
        
        if (response.success) {
            elements.authStatus.textContent = '✅ 認証成功';
            elements.authStatus.className = 'auth-status success';
        } else {
            throw new Error(response.error);
        }
    } catch (error) {
        elements.authStatus.textContent = `❌ 認証失敗: ${error.message}`;
        elements.authStatus.className = 'auth-status error';
    }
});
```

### Phase 3: Native Host拡張 (Week 4)
**目標**: 既存の翻訳機能を維持しつつ、Google Drive機能を追加

#### 3.1 pdf2zh_native_host.py の拡張
```python
# 既存のNativeMessagingHostクラスに以下のメソッドを追加

class NativeMessagingHost:
    def __init__(self):
        # 既存の初期化
        self.base_dir = Path(__file__).parent
        self.translated_dir = Path("/Users/ytakeda/codes/PDFMathTranslate/translated_pdf")
        self.translated_dir.mkdir(exist_ok=True)
        self.server_port = None
        
        # Google Drive関連の初期化（オプション）
        self.drive_manager = None
        self.abstract_extractor = None
        self.llm_classifier = None
        self._load_gdrive_components()
    
    def _load_gdrive_components(self):
        """Google Drive関連コンポーネントの遅延読み込み"""
        try:
            from pdf2zh.drive_manager import DriveManager
            from pdf2zh.abstract_extractor import AbstractExtractor
            from pdf2zh.llm_classifier import LLMClassifier
            
            # 設定ファイルから Google Drive 設定を読み込み
            settings = self._load_extension_settings()
            
            if settings.get('enableGoogleDrive', False):
                credentials_path = os.path.join(self.base_dir, 'gdrive_credentials.json')
                if os.path.exists(credentials_path):
                    self.drive_manager = DriveManager(credentials_path, settings.get('googleDrivePath', 'Research_Papers'))
                    self.abstract_extractor = AbstractExtractor()
                    
                    # カテゴリ設定を読み込み
                    categories_config = self._load_categories_config()
                    if categories_config:
                        self.llm_classifier = LLMClassifier(categories_config)
                
        except ImportError as e:
            logger.info(f"Google Drive components not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize Google Drive components: {e}")
    
    def _load_extension_settings(self) -> Dict[str, Any]:
        """Chrome拡張機能の設定を読み込み（可能な場合）"""
        # 実装は後で詳細化
        return {}
    
    def _load_categories_config(self) -> Optional[Dict[str, Any]]:
        """カテゴリ設定を読み込み"""
        config_path = self.base_dir / 'categories_config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def handle_translate_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """翻訳リクエストを処理（Google Drive統合版）"""
        try:
            # 既存の翻訳処理は完全に維持
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
                # PDF翻訳（既存機能）
                translated_path = self.translate_pdf(pdf_path, service, language, output_format)
                filename = os.path.basename(translated_path)
                
                # サーバー起動（既存機能）
                server_url = self.start_server(translated_path)
                
                # Google Drive統合処理（新機能、オプション）
                gdrive_url = None
                classification_info = None
                
                if self.drive_manager and self.drive_manager.is_available():
                    try:
                        gdrive_url, classification_info = self._process_google_drive_integration(
                            pdf_url, translated_path, service, language, output_format
                        )
                    except Exception as e:
                        logger.warning(f"Google Drive integration failed: {e}")
                
                # レスポンス構築（既存のレスポンス形式を維持）
                response = {
                    'success': True,
                    'url': server_url,
                    'filename': filename,
                    'message': 'Translation completed successfully'
                }
                
                # Google Drive情報を追加（オプション）
                if gdrive_url:
                    response['gdrive_url'] = gdrive_url
                if classification_info:
                    response['classification'] = classification_info
                
                return response
                
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
    
    def _process_google_drive_integration(self, pdf_url: str, translated_path: str, 
                                        service: str, language: str, output_format: str) -> tuple:
        """Google Drive統合処理"""
        try:
            # arXiv IDを抽出
            arxiv_id = self._extract_arxiv_id(pdf_url)
            
            # Abstract取得
            metadata = self.abstract_extractor.extract_abstract(arxiv_id, translated_path)
            
            # LLM分類
            if self.llm_classifier:
                classification = self.llm_classifier.classify_paper(
                    metadata.get('title', ''), 
                    metadata.get('abstract', '')
                )
                metadata.update(classification)
            
            # 翻訳情報を追加
            metadata['translation_info'] = {
                'service': service,
                'target_language': language,
                'format': output_format,
                'translated_at': datetime.now().isoformat()
            }
            
            # Google Driveにアップロード
            file_id = self.drive_manager.upload_to_papers_folder(translated_path, metadata)
            metadata['drive_file_id'] = file_id
            
            # ショートカット作成
            self._create_category_shortcuts(file_id, metadata)
            
            # メタデータ保存
            self._save_paper_metadata(arxiv_id, metadata)
            
            gdrive_url = f"https://drive.google.com/file/d/{file_id}/view"
            classification_info = {
                'primary_category': metadata.get('primary_category'),
                'confidence': metadata.get('confidence_scores', {})
            }
            
            return gdrive_url, classification_info
            
        except Exception as e:
            logger.error(f"Google Drive integration error: {e}")
            raise
    
    def _extract_arxiv_id(self, url: str) -> str:
        """URLからarXiv IDを抽出"""
        # arXiv URL pattern matching
        patterns = [
            r'arxiv\.org/abs/(\d{4}\.\d{4,5})',
            r'arxiv\.org/pdf/(\d{4}\.\d{4,5})',
            r'(\d{4}\.\d{4,5})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # フォールバック: ファイル名から抽出
        filename = os.path.basename(url)
        match = re.search(r'(\d{4}\.\d{4,5})', filename)
        if match:
            return match.group(1)
        
        return ""
```

### Phase 4: 既存ファイル移行ツール (Week 5-6)
**目標**: 既存のPDFファイルを新システムに移行

#### 4.1 Migration Tool
**ファイル**: `tools/migrate_existing_papers.py`

```python
#!/usr/bin/env python3
"""
既存PDF論文の移行ツール
ローカル・Google Drive の既存ファイルを新システムに統合
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from pdf2zh.drive_manager import DriveManager
from pdf2zh.abstract_extractor import AbstractExtractor
from pdf2zh.llm_classifier import LLMClassifier

class PaperMigrator:
    def __init__(self, local_dir: str, drive_credentials_path: str):
        self.local_dir = Path(local_dir)
        self.drive_manager = DriveManager(drive_credentials_path)
        self.abstract_extractor = AbstractExtractor()
        self.llm_classifier = None
        self.processed_papers = []
        self.error_log = []
    
    def inventory_existing_files(self) -> List[Dict[str, Any]]:
        """既存ファイルの棚卸し"""
        print("📋 Inventorying existing files...")
        inventory = []
        
        # ローカルファイルを検索
        local_files = list(self.local_dir.glob("*-dual.pdf")) + list(self.local_dir.glob("*-mono.pdf"))
        
        for local_file in local_files:
            arxiv_id = self._extract_arxiv_id_from_filename(local_file.name)
            
            inventory.append({
                "arxiv_id": arxiv_id,
                "local_path": str(local_file),
                "filename": local_file.name,
                "size": local_file.stat().st_size,
                "needs_processing": True
            })
        
        print(f"📊 Found {len(inventory)} local files")
        return inventory
    
    def migrate_batch(self, inventory: List[Dict[str, Any]], batch_size: int = 10) -> None:
        """バッチ単位でファイル移行"""
        print(f"🚀 Starting migration of {len(inventory)} files...")
        
        for i in range(0, len(inventory), batch_size):
            batch = inventory[i:i+batch_size]
            print(f"\n📦 Processing batch {i//batch_size + 1}/{(len(inventory)-1)//batch_size + 1}")
            
            for item in batch:
                try:
                    self._migrate_single_paper(item)
                    self.processed_papers.append(item)
                    print(f"✅ {item['arxiv_id']}")
                    
                except Exception as e:
                    error_info = {
                        'arxiv_id': item['arxiv_id'],
                        'error': str(e),
                        'file': item['local_path']
                    }
                    self.error_log.append(error_info)
                    print(f"❌ {item['arxiv_id']}: {e}")
        
        self._generate_migration_report()
    
    def _migrate_single_paper(self, item: Dict[str, Any]) -> None:
        """単一論文の移行処理"""
        arxiv_id = item['arxiv_id']
        local_path = item['local_path']
        
        # 1. Abstract取得
        try:
            metadata = self.abstract_extractor.extract_abstract(arxiv_id, local_path)
        except:
            # Abstract取得失敗時は基本情報のみ
            metadata = {
                'title': f"Paper {arxiv_id}",
                'abstract': '',
                'authors': [],
                'source': 'migration'
            }
        
        # 2. LLM分類（オプション）
        if self.llm_classifier and metadata.get('abstract'):
            try:
                classification = self.llm_classifier.classify_paper(
                    metadata['title'], metadata['abstract']
                )
                metadata.update(classification)
            except:
                metadata.update({
                    'primary_category': 'Others',
                    'confidence_scores': {},
                    'llm_tags': []
                })
        
        # 3. Google Driveアップロード
        file_id = self.drive_manager.upload_to_papers_folder(local_path, metadata)
        metadata['drive_file_id'] = file_id
        
        # 4. ショートカット作成
        if metadata.get('primary_category'):
            self._create_migration_shortcuts(file_id, metadata)
        
        # 5. メタデータ保存
        self._save_paper_metadata(arxiv_id, metadata)
    
    def _generate_migration_report(self) -> None:
        """移行レポート生成"""
        report = {
            'migration_date': datetime.now().isoformat(),
            'total_files': len(self.processed_papers) + len(self.error_log),
            'successful': len(self.processed_papers),
            'failed': len(self.error_log),
            'processed_papers': self.processed_papers,
            'errors': self.error_log
        }
        
        report_path = self.local_dir / 'migration_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 Migration Report:")
        print(f"   ✅ Successful: {report['successful']}")
        print(f"   ❌ Failed: {report['failed']}")
        print(f"   📄 Report saved: {report_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python migrate_existing_papers.py <local_dir> <credentials_path>")
        sys.exit(1)
    
    migrator = PaperMigrator(sys.argv[1], sys.argv[2])
    inventory = migrator.inventory_existing_files()
    migrator.migrate_batch(inventory)
```

### Phase 5: テストとデプロイ (Week 7-8)

#### 5.1 単体テストの作成
**ファイル**: `test/test_google_drive_integration.py`

```python
#!/usr/bin/env python3
"""
Google Drive統合機能のテスト
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pdf2zh.abstract_extractor import AbstractExtractor
from pdf2zh.llm_classifier import LLMClassifier
from pdf2zh.drive_manager import DriveManager

class TestAbstractExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = AbstractExtractor()
    
    def test_arxiv_id_detection(self):
        """arXiv ID検出のテスト"""
        self.assertTrue(self.extractor.is_arxiv_id("2506.06751"))
        self.assertTrue(self.extractor.is_arxiv_id("1234.5678"))
        self.assertFalse(self.extractor.is_arxiv_id("invalid"))
    
    @patch('arxiv.Client')
    def test_arxiv_extraction(self, mock_client):
        """arXiv API抽出のテスト"""
        # Mock設定
        mock_paper = Mock()
        mock_paper.title = "Test Paper"
        mock_paper.summary = "Test abstract"
        mock_paper.authors = [Mock(name="John Doe")]
        mock_paper.entry_id = "https://arxiv.org/abs/2506.06751"
        mock_paper.published = Mock()
        mock_paper.published.isoformat.return_value = "2025-06-12T10:00:00Z"
        
        mock_client.return_value.results.return_value = [mock_paper]
        
        result = self.extractor.extract_from_arxiv("2506.06751")
        
        self.assertEqual(result['title'], "Test Paper")
        self.assertEqual(result['abstract'], "Test abstract")
        self.assertEqual(result['source'], "arxiv_api")

class TestLLMClassifier(unittest.TestCase):
    def setUp(self):
        categories_config = {
            'categories': {
                'ML_AI': {
                    'name': '機械学習・AI',
                    'keywords': ['machine learning', 'deep learning']
                }
            },
            'classification_rules': {
                'confidence_threshold': 0.7
            }
        }
        self.classifier = LLMClassifier(categories_config)
    
    def test_fallback_classification(self):
        """フォールバック分類のテスト"""
        result = self.classifier._fallback_classification(
            "Deep Learning for NLP", 
            "This paper presents a deep learning approach..."
        )
        
        self.assertIn('primary_category', result)
        self.assertIn('confidence_scores', result)

if __name__ == '__main__':
    unittest.main()
```

## 🚀 デプロイメント戦略

### 段階的ロールアウト

1. **Phase 1-2**: 基盤モジュールのローカル開発・テスト
2. **Phase 3**: 設定画面での Google Drive オプション追加（デフォルト無効）
3. **Phase 4**: Native Host でのオプション機能統合
4. **Phase 5**: 既存ファイル移行ツールの提供
5. **Phase 6**: 本格運用開始

### リスク軽減策

- **機能フラグ**: 全ての新機能は設定で無効化可能
- **例外処理**: Google Drive機能の失敗は既存機能に影響しない
- **バックアップ**: 移行前に既存データの完全バックアップ
- **段階的移行**: 小規模テストから本格移行へ

## 📋 必要な準備作業

### 開発環境

```bash
# 必要なPythonライブラリのインストール
pip install arxiv pdfplumber google-api-python-client google-auth

# Google Drive API認証設定
# 1. Google Cloud Consoleでプロジェクト作成
# 2. Drive API有効化
# 3. OAuth2認証情報ダウンロード
```

### 設定ファイル

1. **Google Drive API認証**: `gdrive_credentials.json`
2. **カテゴリ設定**: `categories_config.json`
3. **拡張機能設定**: Chrome storage sync

## ⚠️ 重要な注意事項

- **現在の拡張機能は一切変更しない**: 新機能はオプションとして追加
- **データ損失防止**: 移行前に必ずバックアップを作成
- **段階的テスト**: 小規模テストから開始し、問題がないことを確認
- **ユーザー同意**: Google Drive機能は明示的に有効化が必要

---

**この実装計画は、現在の PDF Math Translate Chrome Extension の機能を完全に保持しつつ、新しい Google Drive 統合機能を段階的に追加するための詳細ガイドです。各フェーズは独立して実装可能で、既存の翻訳ワークフローに影響を与えません。**