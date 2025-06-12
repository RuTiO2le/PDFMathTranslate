// Native Messaging Host名
const NATIVE_HOST_NAME = 'com.pdfmathtranslate.nativehost';

// 翻訳処理中のタブを追跡
const processingTabs = new Set();

// デフォルト設定
const DEFAULT_SETTINGS = {
  translationService: 'plamo',
  targetLanguage: 'ja',
  outputFormat: 'dual',
  autoOrganize: false,
  googleDrivePath: '',
  createShortcuts: false,
  abstractAnalysis: false
};

// 現在の設定をキャッシュ
let currentSettings = { ...DEFAULT_SETTINGS };

// 設定を読み込み
async function loadSettings() {
  try {
    const result = await chrome.storage.sync.get(DEFAULT_SETTINGS);
    currentSettings = result;
    console.log('Settings loaded:', currentSettings);
    return currentSettings;
  } catch (error) {
    console.error('Failed to load settings:', error);
    return DEFAULT_SETTINGS;
  }
}

// メッセージリスナー
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Background received message:', message);
  
  if (message.action === 'settingsUpdated') {
    // 設定が更新された場合
    currentSettings = message.settings;
    console.log('Settings updated:', currentSettings);
    sendResponse({ success: true });
    return true;
  }
  
  if (message.action === 'translatePdf') {
    // 重複リクエストをチェック
    const tabId = sender.tab?.id;
    if (tabId && processingTabs.has(tabId)) {
      console.log('🔒 Translation already in progress for tab:', tabId);
      sendResponse({ 
        success: false, 
        error: 'Translation already in progress' 
      });
      return false;
    }
    
    if (tabId) {
      processingTabs.add(tabId);
      console.log('🔓 Started processing for tab:', tabId);
    }
    
    // handleTranslatePdfをPromiseでラップして、完了時にタブIDを削除
    (async () => {
      try {
        await handleTranslatePdf(message, sendResponse);
      } finally {
        if (tabId) {
          processingTabs.delete(tabId);
          console.log('✅ Finished processing for tab:', tabId);
        }
      }
    })();
    
    return true; // 非同期レスポンスを示す
  }
});

// PDF翻訳処理
async function handleTranslatePdf(message, sendResponse) {
  const startTime = Date.now();
  try {
    const { pdfUrl, currentUrl } = message;
    
    console.log('🚀 Starting translation for:', pdfUrl);
    console.log('📊 Translation start time:', new Date().toISOString());
    
    // Native Messaging Hostにリクエストを送信
    const nativeMessage = {
      action: 'translate',
      pdfUrl: pdfUrl,
      sourceUrl: currentUrl,
      options: {
        service: 'plamo',
        language: 'ja'
      }
    };
    
    // Native Hostと通信
    if (!chrome.runtime.sendNativeMessage) {
      console.error('Native messaging not available');
      sendResponse({ 
        success: false, 
        error: 'Native messaging not supported' 
      });
      return;
    }

    console.log('🔄 Sending message to native host:', JSON.stringify(nativeMessage, null, 2));
    
    chrome.runtime.sendNativeMessage(NATIVE_HOST_NAME, nativeMessage, (response) => {
      if (chrome.runtime.lastError) {
        console.error('❌ Native messaging error details:');
        console.error('   Host name:', NATIVE_HOST_NAME);
        console.error('   Error message:', chrome.runtime.lastError.message);
        console.error('   Full error object:', JSON.stringify(chrome.runtime.lastError));
        sendResponse({ 
          success: false, 
          error: `Native messaging failed: ${chrome.runtime.lastError.message}` 
        });
        return;
      }
      
      const elapsedTime = Date.now() - startTime;
      console.log('✅ Native host response received:', JSON.stringify(response, null, 2));
      console.log('⏱️ Total translation time:', `${elapsedTime}ms (${(elapsedTime/1000).toFixed(2)}s)`);
      
      if (response && response.success) {
        console.log('🎉 Translation completed successfully');
        sendResponse({
          success: true,
          translatedUrl: response.url,
          filename: response.filename
        });
      } else {
        console.error('💥 Translation failed:', response ? response.error : 'Unknown error');
        sendResponse({
          success: false,
          error: response ? response.error : 'Unknown error'
        });
      }
    });
    
  } catch (error) {
    console.error('Translation error:', error);
    sendResponse({ 
      success: false, 
      error: error.message 
    });
  }
}

// 拡張機能インストール時の処理
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('PDF Math Translate extension installed/updated:', details.reason);
  
  if (details.reason === 'install') {
    // 初回インストール時の処理
    console.log('First time installation');
    
    // デフォルト設定を保存
    await chrome.storage.sync.set(DEFAULT_SETTINGS);
    console.log('Default settings saved');
    
    // オプションページを開く
    chrome.tabs.create({ url: 'options.html' });
  }
  
  // 設定を読み込み
  await loadSettings();
  
  // コンテキストメニューを作成
  createContextMenus();
});

// コンテキストメニューを作成
function createContextMenus() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'open-settings',
      title: '⚙️ 設定を開く',
      contexts: ['action']
    });
    
    chrome.contextMenus.create({
      id: 'quick-translate-gpt4',
      title: '🚀 GPT-4で翻訳 (クイック)',
      contexts: ['action']
    });
    
    chrome.contextMenus.create({
      id: 'quick-translate-claude',
      title: '🧠 Claudeで翻訳 (クイック)',
      contexts: ['action']
    });
  });
}

// コンテキストメニューのクリック処理
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  switch (info.menuItemId) {
    case 'open-settings':
      chrome.tabs.create({ url: 'options.html' });
      break;
      
    case 'quick-translate-gpt4':
      await quickTranslate(tab, 'openai:gpt-4o');
      break;
      
    case 'quick-translate-claude':
      await quickTranslate(tab, 'anthropic:claude-3-5-sonnet-20241022');
      break;
  }
});

// クイック翻訳機能
async function quickTranslate(tab, service) {
  if (!isPdfUrl(tab.url)) {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'PDF Math Translate',
      message: 'PDFページで拡張機能をご利用ください'
    });
    return;
  }
  
  if (processingTabs.has(tab.id)) {
    console.log('🔒 Translation already in progress for this tab (quick translate)');
    updateStatusBadge(tab.id, '処理中');
    return;
  }
  
  updateIconState(tab.id, 'processing');
  updateStatusBadge(tab.id, 'Quick');
  
  processingTabs.add(tab.id);
  console.log('🔓 Started quick processing for tab:', tab.id, 'with service:', service);
  
  const pdfUrl = getPdfUrlFromTab(tab.url);
  await loadSettings();
  
  const message = {
    action: 'translatePdf',
    pdfUrl: pdfUrl,
    currentUrl: tab.url,
    options: {
      service: service,
      language: currentSettings.targetLanguage,
      outputFormat: currentSettings.outputFormat
    }
  };
  
  handleTranslatePdf(message, (response) => {
    if (response && response.success) {
      updateIconState(tab.id, 'active');
      updateStatusBadge(tab.id, '完了');
      
      if (response.translatedUrl) {
        chrome.tabs.create({ url: response.translatedUrl });
      }
      
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48_active.png',
        title: 'PDF Math Translate',
        message: `翻訳が完了しました (${service.split(':')[0]}): ${response.filename || 'PDF'}`
      });
      
      setTimeout(() => updateStatusBadge(tab.id, ''), 3000);
    } else {
      updateIconState(tab.id, 'active');
      updateStatusBadge(tab.id, 'エラー');
      
      const errorMessage = response && response.error ? response.error : '不明なエラー';
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'PDF Math Translate',
        message: `翻訳に失敗しました: ${errorMessage}`
      });
      
      setTimeout(() => updateStatusBadge(tab.id, ''), 5000);
    }
    
    processingTabs.delete(tab.id);
    console.log('✅ Finished quick processing for tab:', tab.id);
  });
}

// アクションクリック時の処理 - 直接翻訳を開始
chrome.action.onClicked.addListener(async (tab) => {
  console.log('🔵 PDF Math Translate: Extension icon clicked');
  console.log('🔵 Tab URL:', tab.url);
  console.log('🔵 Tab ID:', tab.id);
  console.log('🔵 Currently processing tabs:', Array.from(processingTabs));
  
  // 既に処理中かチェック
  if (processingTabs.has(tab.id)) {
    console.log('🔒 Translation already in progress for this tab (action click)');
    updateStatusBadge(tab.id, '処理中');
    return;
  }
  
  if (isPdfUrl(tab.url)) {
    // アイコンを翻訳中状態に変更
    updateIconState(tab.id, 'processing');
    updateStatusBadge(tab.id, '開始中...');
    
    // タブIDを処理中リストに追加
    processingTabs.add(tab.id);
    console.log('🔓 Started processing for tab:', tab.id, '(action click)');
    
    // PDF URLを取得
    const pdfUrl = getPdfUrlFromTab(tab.url);
    console.log('Starting translation for:', pdfUrl);
    
    // 設定を読み込んで翻訳を開始
    await loadSettings();
    
    const message = {
      action: 'translatePdf',
      pdfUrl: pdfUrl,
      currentUrl: tab.url,
      options: {
        service: currentSettings.translationService,
        language: currentSettings.targetLanguage,
        outputFormat: currentSettings.outputFormat
      }
    };
    
    updateStatusBadge(tab.id, 'DL中');
    
    handleTranslatePdf(message, (response) => {
      if (response && response.success) {
        // 成功 - アイコンを緑に戻す
        updateIconState(tab.id, 'active');
        updateStatusBadge(tab.id, '完了');
        
        console.log('Translation completed successfully:', response.filename);
        
        // 翻訳結果のタブを開く
        if (response.translatedUrl) {
          chrome.tabs.create({ url: response.translatedUrl });
        }
        
        // 通知を表示
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon48_active.png',
          title: 'PDF Math Translate',
          message: `翻訳が完了しました: ${response.filename || 'PDF'}`
        });
        
        // 3秒後にバッジをクリア
        setTimeout(() => updateStatusBadge(tab.id, ''), 3000);
      } else {
        // エラー - アイコンを元に戻す
        updateIconState(tab.id, 'active');
        updateStatusBadge(tab.id, 'エラー');
        
        console.error('Translation failed details:', {
          response: response,
          error: response ? response.error : 'No response received',
          responseType: typeof response,
          responseKeys: response ? Object.keys(response) : 'none'
        });
        
        // Responseを文字列として出力
        console.error('Full response object:', JSON.stringify(response, null, 2));
        
        // エラー通知
        const errorMessage = response && response.error ? response.error : '不明なエラー';
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon48.png',
          title: 'PDF Math Translate',
          message: `翻訳に失敗しました: ${errorMessage}`
        });
        
        // 5秒後にバッジをクリア
        setTimeout(() => updateStatusBadge(tab.id, ''), 5000);
      }
      
      // 処理完了時にタブIDを削除
      processingTabs.delete(tab.id);
      console.log('✅ Finished processing for tab:', tab.id, '(action click)');
    });
  } else {
    // PDFページではない場合の通知
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'PDF Math Translate',
      message: 'PDFページで拡張機能をご利用ください'
    });
  }
});

// タブ更新時の処理
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    // PDFページかどうかをチェック
    if (isPdfUrl(tab.url)) {
      console.log('PDF page detected:', tab.url);
      
      // アイコンをアクティブ状態に変更
      updateIconState(tabId, 'active');
    } else {
      // アイコンを通常状態に変更
      updateIconState(tabId, 'default');
    }
  }
});

// アイコン状態を更新
function updateIconState(tabId, state) {
  const iconPaths = {
    default: {
      "16": "icons/icon16.png",
      "32": "icons/icon32.png", 
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    },
    active: {
      "16": "icons/icon16_active.png",
      "32": "icons/icon32_active.png",
      "48": "icons/icon48_active.png", 
      "128": "icons/icon128_active.png"
    },
    processing: {
      "16": "icons/icon16_processing.png",
      "32": "icons/icon32_processing.png",
      "48": "icons/icon48_processing.png",
      "128": "icons/icon128_processing.png"
    }
  };

  if (iconPaths[state]) {
    chrome.action.setIcon({ tabId: tabId, path: iconPaths[state] });
  }
}

// 状況バッジを更新
function updateStatusBadge(tabId, text) {
  chrome.action.setBadgeText({ tabId: tabId, text: text });
  
  // バッジの色を状況に応じて変更
  if (text.includes('エラー')) {
    chrome.action.setBadgeBackgroundColor({ tabId: tabId, color: '#f44336' });
  } else if (text.includes('完了')) {
    chrome.action.setBadgeBackgroundColor({ tabId: tabId, color: '#4CAF50' });
  } else if (text === '') {
    chrome.action.setBadgeBackgroundColor({ tabId: tabId, color: '#4CAF50' });
  } else {
    chrome.action.setBadgeBackgroundColor({ tabId: tabId, color: '#FF9800' });
  }
}

// タブからPDF URLを取得
function getPdfUrlFromTab(url) {
  // すでにPDF URLの場合
  if (url.includes('.pdf')) {
    return url;
  }
  
  // arXivの場合、PDFリンクを生成
  if (url.includes('arxiv.org')) {
    const match = url.match(/arxiv\.org\/abs\/(.+)/);
    if (match) {
      return `https://arxiv.org/pdf/${match[1]}.pdf`;
    }
    
    if (url.includes('/pdf/')) {
      return url;
    }
  }
  
  return url;
}

// PDF URLかどうかを判定
function isPdfUrl(url) {
  if (!url) return false;
  
  // 直接PDFファイル
  if (url.includes('.pdf')) return true;
  
  // arXivのPDFページ
  if (url.includes('arxiv.org') && (url.includes('/pdf/') || url.includes('.pdf'))) return true;
  
  // その他のPDFビューワー
  if (url.includes('/pdf/') || url.includes('pdfviewer')) return true;
  
  return false;
}

// Downloads API は使用しない（エラーの原因となるため）
console.log('PDF Math Translate: Downloads API monitoring disabled');

// 通知を表示（オプション）
function showTranslationNotification(downloadItem) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: 'PDF Math Translate',
    message: `${downloadItem.filename} をダウンロードしました。翻訳しますか？`,
    buttons: [
      { title: '翻訳する' },
      { title: 'キャンセル' }
    ]
  });
}

// 通知のボタンクリック処理
chrome.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {
  if (buttonIndex === 0) { // 翻訳するボタン
    // 翻訳処理を開始
    console.log('User chose to translate from notification');
  }
  chrome.notifications.clear(notificationId);
});

// エラーハンドリング
chrome.runtime.onSuspend.addListener(() => {
  console.log('Extension is being suspended');
});

chrome.runtime.onStartup.addListener(() => {
  console.log('Extension startup');
});

// デバッグ用のログ
// デバッグ用のテスト関数
function testNativeMessaging() {
  console.log('🧪 Testing native messaging...');
  const testMessage = { action: 'test', message: 'Hello from extension' };
  
  if (!chrome.runtime.sendNativeMessage) {
    console.error('❌ Native messaging API not available');
    return;
  }
  
  chrome.runtime.sendNativeMessage(NATIVE_HOST_NAME, testMessage, (response) => {
    if (chrome.runtime.lastError) {
      console.error('❌ Native messaging test failed:');
      console.error('   Error:', chrome.runtime.lastError.message);
    } else {
      console.log('✅ Native messaging test success:', response);
    }
  });
}

// 初期化完了のログ
console.log('🚀 PDF Math Translate background script loaded');
console.log('🔧 Native host name:', NATIVE_HOST_NAME);

// 5秒後にテスト実行
setTimeout(testNativeMessaging, 5000);