(() => {
  // PDFページかどうかを判定
  function isPdfPage() {
    // Content-Typeをチェック
    const contentType = document.contentType || '';
    if (contentType.includes('application/pdf')) {
      return true;
    }
    
    // URLでPDFを判定
    const url = window.location.href;
    if (url.includes('.pdf') || url.includes('/pdf/')) {
      return true;
    }
    
    // arXivのPDFページを判定
    if (url.includes('arxiv.org') && url.includes('.pdf')) {
      return true;
    }
    
    // PDFビューワーの存在をチェック
    const pdfViewer = document.querySelector('embed[type="application/pdf"], object[type="application/pdf"], iframe[src*=".pdf"]');
    return !!pdfViewer;
  }

  // PDF URLを取得
  function getPdfUrl() {
    const currentUrl = window.location.href;
    
    // すでにPDF URLの場合
    if (currentUrl.includes('.pdf')) {
      return currentUrl;
    }
    
    // arXivの場合、PDFリンクを探す
    if (currentUrl.includes('arxiv.org')) {
      const pdfLink = document.querySelector('a[href*=".pdf"]');
      if (pdfLink) {
        return pdfLink.href;
      }
      
      // arXivのPDF URLパターンを生成
      const match = currentUrl.match(/arxiv\.org\/abs\/(.+)/);
      if (match) {
        return `https://arxiv.org/pdf/${match[1]}.pdf`;
      }
    }
    
    // embed, object, iframeからPDF URLを取得
    const pdfElements = document.querySelectorAll('embed[type="application/pdf"], object[type="application/pdf"], iframe[src*=".pdf"]');
    for (const element of pdfElements) {
      const src = element.src || element.data;
      if (src && src.includes('.pdf')) {
        return new URL(src, window.location.href).href;
      }
    }
    
    return currentUrl;
  }

  // 翻訳ボタンを作成（簡素化版 - 拡張機能アイコンクリックを案内）
  function createTranslateButton() {
    const button = document.createElement('button');
    button.id = 'pdf-translate-btn';
    button.innerHTML = '🔤 拡張機能アイコンをクリックして翻訳';
    button.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      background: #2196F3;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: bold;
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      transition: all 0.3s ease;
      opacity: 0.9;
    `;
    
    button.addEventListener('mouseenter', () => {
      button.style.opacity = '1';
      button.style.transform = 'translateY(-1px)';
    });
    
    button.addEventListener('mouseleave', () => {
      button.style.opacity = '0.9';
      button.style.transform = 'translateY(0)';
    });
    
    // クリック時は拡張機能アイコンを案内
    button.addEventListener('click', () => {
      button.innerHTML = '☝️ 上部の拡張機能アイコンをクリック！';
      button.style.background = '#FF9800';
      setTimeout(() => {
        button.innerHTML = '🔤 拡張機能アイコンをクリックして翻訳';
        button.style.background = '#2196F3';
      }, 3000);
    });
    
    return button;
  }

  // バックグラウンドスクリプトからのメッセージを処理
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'getPdfUrl') {
      const pdfUrl = getPdfUrl();
      sendResponse({ pdfUrl: pdfUrl });
    }
  });

  // 初期化
  function init() {
    if (isPdfPage()) {
      console.log('PDF page detected:', window.location.href);
      // ボタン表示は無効化 - アイコンの色変更のみで十分
    }
  }

  // ページ読み込み完了時に実行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 動的コンテンツの変更を監視
  const observer = new MutationObserver((mutations) => {
    let shouldReinit = false;
    
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList') {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.matches('embed[type="application/pdf"], object[type="application/pdf"], iframe[src*=".pdf"]')) {
              shouldReinit = true;
            }
          }
        });
      }
    });
    
    if (shouldReinit) {
      setTimeout(init, 1000);
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
})();