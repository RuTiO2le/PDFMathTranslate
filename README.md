# PDF Math Translate Chrome Extension

📄→🌏 PDFを日本語に翻訳してブラウザで表示するChrome拡張機能

![Extension Demo](https://img.shields.io/badge/status-ready-brightgreen)
![Chrome](https://img.shields.io/badge/Chrome-Extension-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ 特徴

- 🎯 **ワンクリック翻訳**: 拡張機能アイコンをクリックするだけで翻訳開始
- 🎨 **動的アイコン**: PDF検出時にアイコンの色が変わり、翻訳可能状態を視覚的に表示
- 📚 **arXiv対応**: 学術論文の翻訳に最適化
- 🔄 **複数サービス**: Plamo、OpenAI GPT-4など複数の翻訳サービス対応
- 🌐 **ブラウザ表示**: 翻訳結果を新しいタブで即座に表示
- ⚡ **翻訳キャッシュ**: 翻訳済みファイルの自動再利用で高速化
- 🔒 **重複防止**: 同一タブでの重複処理を自動防止
- 👥 **複数プロファイル対応**: 異なるChromeプロファイル間での共有利用
- 🎮 **リアルタイム進捗**: 翻訳中の状態をバッジとアイコンで表示

## 🎨 アイコン状態

| 状態 | 色 | 説明 |
|------|----|----|
| グレー | 🔘 | 通常状態 |
| 緑 | 🟢 | PDFページ検出（翻訳可能） |
| オレンジ | 🟠 | 翻訳中 |

## インストール方法

### 1. Native Messaging Hostの設定

```bash
# Chrome用のNative Messaging Host設定ファイルを配置
sudo mkdir -p /Library/Google/Chrome/NativeMessagingHosts/
sudo cp com.pdfmathtranslate.nativehost.json /Library/Google/Chrome/NativeMessagingHosts/

# 拡張機能IDを設定ファイルに追加する必要があります（後述）
```

### 2. Chrome拡張機能のインストール

1. Chromeで `chrome://extensions/` を開く
2. 「デベロッパーモード」を有効にする
3. 「パッケージ化されていない拡張機能を読み込む」をクリック
4. `chrome-extension` フォルダを選択
5. 拡張機能IDをコピーする

### 3. Native Messaging Host設定ファイルの更新

**重要**: 拡張機能IDを確認してNative Host設定を更新してください。

```bash
# 現在設定済みのExtension ID: ofkepkmomlelebfcghpgjfbngenhbhbh
# 新しいプロファイルで異なるIDが表示された場合は以下の手順で追加:

# 1. 現在の設定を確認
cat /Library/Google/Chrome/NativeMessagingHosts/com.pdfmathtranslate.nativehost.json

# 2. 新しいIDを追加（複数プロファイル対応）
sudo nano /Library/Google/Chrome/NativeMessagingHosts/com.pdfmathtranslate.nativehost.json

# allowed_origins に新しいIDを追加:
# "allowed_origins": [
#   "chrome-extension://ofkepkmomlelebfcghpgjfbngenhbhbh/",
#   "chrome-extension://新しいプロファイルのID/"
# ]
```

**Extension IDの確認方法**:
1. `chrome://extensions/` を開く
2. 「PDF Math Translate」拡張機能のIDをコピー
3. 上記設定ファイルに追加

## 📖 使い方

1. **arXivなどのPDFページを開く**
2. **拡張機能アイコンが緑色に変わることを確認**
3. **アイコンをクリック** （翻訳が自動開始）
4. **翻訳中はアイコンがオレンジ色に変わる**
5. **完了すると通知が表示され、新しいタブで翻訳結果が開く**

## 🌐 対応サイト

- ✅ [arXiv.org](https://arxiv.org) - 学術論文アーカイブ
- ✅ 直接PDFファイルのURL
- ✅ PDFビューワーページ
- ✅ その他のPDF表示サイト

## 🛠️ 技術仕様

### ファイル構成

```
pdf-math-translate-extension/
├── manifest.json                   # 拡張機能の設定
├── background.js                   # バックグラウンド処理
├── content.js                      # PDF検出とページ注入
├── pdf2zh_native_host.py          # Native Messaging Host
├── com.pdfmathtranslate.nativehost.json  # Native Host設定
├── icons/                          # 3状態のアイコン
│   ├── icon*.png                  # 通常時（グレー）
│   ├── icon*_active.png           # PDF検出時（緑）
│   └── icon*_processing.png       # 翻訳中（オレンジ）
└── README.md
```

### 権限

- `activeTab`: 現在のタブにアクセス
- `nativeMessaging`: Python Hostとの通信
- `storage`: 設定の保存
- `notifications`: 翻訳完了通知

## トラブルシューティング

### PDFが検出されない場合
- ページを再読み込みしてください
- URLにPDFが含まれているか確認してください
- 拡張機能のアイコンが緑色に変わらない場合は対応サイトではない可能性があります

### 翻訳が失敗する場合
- **Extension ID確認**: `chrome://extensions/` でIDが設定ファイルと一致するか確認
- **Native Host設定**: `cat /Library/Google/Chrome/NativeMessagingHosts/com.pdfmathtranslate.nativehost.json`
- **ログ確認**: `/tmp/pdf2zh_native_host.log` で詳細エラーを確認
- **pdf2zh動作確認**: コマンドラインでpdf2zhが動作するか確認

### 権限エラーが発生する場合
- `pdf2zh_native_host.py` に実行権限があるか確認: `chmod +x pdf2zh_native_host.py`
- Native Messaging Host設定ファイルのパスが正しいか確認
- システム設定ファイルが最新か確認: `sudo cp com.pdfmathtranslate.nativehost.json /Library/Google/Chrome/NativeMessagingHosts/`

### 複数プロファイルで動作しない場合
- 各プロファイルのExtension IDを確認し、Native Host設定の`allowed_origins`に全て追加されているか確認
- Extension IDは通常プロファイルごとに異なります

### "Access to the specified native messaging host is forbidden"エラー
- Extension IDが設定ファイルに正しく記載されているか確認
- 設定ファイルをシステムディレクトリに正しくコピーしているか確認

## 開発者向け

### デバッグ

1. Chrome DevToolsでバックグラウンドページを開く
2. Console でログを確認
3. Native Messaging Hostのログは `/tmp/pdf2zh_native_host.log` で確認

### カスタマイズ

- 翻訳サービスを追加: `popup.html` の `serviceSelect` オプションを編集
- 対応サイトを追加: `manifest.json` の `content_scripts.matches` を編集
- UIのカスタマイズ: `popup.html` と `popup.js` を編集

## ライセンス

このプロジェクトのライセンスに従います。