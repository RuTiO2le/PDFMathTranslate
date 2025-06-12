/**
 * PDF Math Translate Options Page
 * 拡張機能の設定を管理
 */

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

// DOM要素の取得
const elements = {
    translationService: document.getElementById('translationService'),
    targetLanguage: document.getElementById('targetLanguage'),
    outputFormat: document.getElementById('outputFormat'),
    autoOrganize: document.getElementById('autoOrganize'),
    googleDrivePath: document.getElementById('googleDrivePath'),
    createShortcuts: document.getElementById('createShortcuts'),
    abstractAnalysis: document.getElementById('abstractAnalysis'),
    saveButton: document.getElementById('saveButton'),
    status: document.getElementById('status')
};

/**
 * 設定を読み込む
 */
async function loadSettings() {
    try {
        const result = await chrome.storage.sync.get(DEFAULT_SETTINGS);
        
        // フォーム要素に設定値を反映
        elements.translationService.value = result.translationService;
        elements.targetLanguage.value = result.targetLanguage;
        elements.outputFormat.value = result.outputFormat;
        elements.autoOrganize.checked = result.autoOrganize;
        elements.googleDrivePath.value = result.googleDrivePath;
        elements.createShortcuts.checked = result.createShortcuts;
        elements.abstractAnalysis.checked = result.abstractAnalysis;
        
        console.log('Settings loaded:', result);
    } catch (error) {
        console.error('Failed to load settings:', error);
        showStatus('設定の読み込みに失敗しました', 'error');
    }
}

/**
 * 設定を保存する
 */
async function saveSettings() {
    try {
        const settings = {
            translationService: elements.translationService.value,
            targetLanguage: elements.targetLanguage.value,
            outputFormat: elements.outputFormat.value,
            autoOrganize: elements.autoOrganize.checked,
            googleDrivePath: elements.googleDrivePath.value,
            createShortcuts: elements.createShortcuts.checked,
            abstractAnalysis: elements.abstractAnalysis.checked
        };
        
        await chrome.storage.sync.set(settings);
        
        console.log('Settings saved:', settings);
        showStatus('設定を保存しました', 'success');
        
        // バックグラウンドスクリプトに設定変更を通知
        try {
            await chrome.runtime.sendMessage({
                action: 'settingsUpdated',
                settings: settings
            });
        } catch (error) {
            console.log('Background script notification failed (this is normal if background is inactive)');
        }
        
    } catch (error) {
        console.error('Failed to save settings:', error);
        showStatus('設定の保存に失敗しました', 'error');
    }
}

/**
 * ステータスメッセージを表示
 */
function showStatus(message, type = 'success') {
    elements.status.textContent = message;
    elements.status.className = `status ${type}`;
    elements.status.style.display = 'block';
    
    // 3秒後に非表示
    setTimeout(() => {
        elements.status.style.display = 'none';
    }, 3000);
}

/**
 * 翻訳サービスの説明を更新
 */
function updateServiceDescription() {
    const service = elements.translationService.value;
    const descriptions = {
        'plamo': 'Plamo AIは日本語に最適化されており、学術論文の翻訳に適しています。',
        'openai:gpt-4o': 'OpenAI GPT-4oは最新の大規模言語モデルで、高品質な翻訳を提供します。',
        'openai:gpt-4o-mini': 'OpenAI GPT-4o Miniは軽量版で、高速かつ経済的です。',
        'openai:gpt-4-turbo': 'OpenAI GPT-4 Turboは高速で正確な翻訳を提供します。',
        'anthropic:claude-3-5-sonnet-20241022': 'Claude 3.5 Sonnetは理解力が高く、複雑な文書の翻訳に優れています。',
        'anthropic:claude-3-5-haiku-20241022': 'Claude 3.5 Haikuは高速で効率的な翻訳を提供します。',
        'google:gemini-1.5-pro': 'Google Gemini 1.5 Proは多言語対応で高品質な翻訳が可能です。',
        'google:gemini-1.5-flash': 'Google Gemini 1.5 Flashは高速処理に優れています。'
    };
    
    const description = elements.translationService.parentElement.querySelector('.description');
    if (description && descriptions[service]) {
        description.textContent = descriptions[service];
    }
}

/**
 * フォームバリデーション
 */
function validateForm() {
    let isValid = true;
    
    // Google Driveパスの検証（将来機能）
    const drivePath = elements.googleDrivePath.value.trim();
    if (drivePath && !drivePath.startsWith('/')) {
        showStatus('Google Driveパスは絶対パスで入力してください', 'error');
        isValid = false;
    }
    
    return isValid;
}

/**
 * 設定のエクスポート
 */
async function exportSettings() {
    try {
        const settings = await chrome.storage.sync.get();
        const dataStr = JSON.stringify(settings, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'pdf-math-translate-settings.json';
        link.click();
        
        URL.revokeObjectURL(url);
        showStatus('設定をエクスポートしました', 'success');
    } catch (error) {
        console.error('Export failed:', error);
        showStatus('エクスポートに失敗しました', 'error');
    }
}

/**
 * 設定のインポート
 */
function importSettings(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const settings = JSON.parse(e.target.result);
            await chrome.storage.sync.set(settings);
            await loadSettings();
            showStatus('設定をインポートしました', 'success');
        } catch (error) {
            console.error('Import failed:', error);
            showStatus('インポートに失敗しました', 'error');
        }
    };
    reader.readAsText(file);
}

// イベントリスナーの設定
document.addEventListener('DOMContentLoaded', () => {
    // 設定を読み込み
    loadSettings();
    
    // 保存ボタンのイベント
    elements.saveButton.addEventListener('click', async () => {
        if (validateForm()) {
            await saveSettings();
        }
    });
    
    // 翻訳サービス変更時の説明更新
    elements.translationService.addEventListener('change', updateServiceDescription);
    
    // キーボードショートカット
    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {
            event.preventDefault();
            if (validateForm()) {
                saveSettings();
            }
        }
    });
    
    // 初期説明を設定
    updateServiceDescription();
});

// 設定変更の監視
chrome.storage.onChanged.addListener((changes, namespace) => {
    console.log('Settings changed:', changes);
    if (namespace === 'sync') {
        // 他のタブで設定が変更された場合に反映
        loadSettings();
    }
});