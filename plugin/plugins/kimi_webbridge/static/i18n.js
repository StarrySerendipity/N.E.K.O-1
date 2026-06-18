/**
 * 国际化支持模块
 */

const i18n = {
    'zh-CN': {
        app_title: 'Kimi WebBridge',
        connection_status: '连接状态',
        checking: '检查中...',
        refresh: '刷新',
        navigation: '导航',
        go: '前往',
        new_tab: '新标签页',
        actions: '操作',
        snapshot: '快照',
        screenshot: '截图',
        list_tabs: '标签页',
        close_session: '关闭会话',
        execute_js: '执行JS',
        status: '状态',
        results: '结果',
        clear: '清空',
        welcome_message: '欢迎使用 Kimi WebBridge 浏览器自动化插件',
        welcome_hint: '选择操作开始探索网络世界吧~',
        copyright: '© 2026 Kimi WebBridge Plugin for N.E.K.O.',
        footer_hint: '由 Kimi 提供技术支持',
        
        // 状态文本
        status_online: '已连接',
        status_offline: '未连接',
        status_connecting: '连接中...',
        
        // 操作结果
        operation_success: '操作成功',
        operation_failed: '操作失败',
        navigate_success: '导航成功',
        navigate_error: '导航失败',
        click_success: '点击成功',
        click_error: '点击失败',
        fill_success: '填写成功',
        fill_error: '填写失败',
        screenshot_success: '截图成功',
        screenshot_error: '截图失败',
        session_created: '会话已创建',
        session_closed: '会话已关闭',
        daemon_started: '守护进程已启动',
        daemon_stopped: '守护进程已停止',
        webbridge_not_installed: 'Kimi WebBridge未安装',
        invalid_url: '无效的URL',
        selector_required: '需要选择器参数',
        value_required: '需要值参数',
        
        // 按钮文本
        btn_navigate: '导航',
        btn_snapshot: '获取快照',
        btn_screenshot: '截图',
        btn_click: '点击',
        btn_fill: '填写',
        btn_evaluate: '执行',
        btn_close: '关闭',
        btn_clear: '清空',
        
        // 占位符
        placeholder_url: '请输入URL...',
        placeholder_selector: '请输入选择器...',
        placeholder_value: '请输入值...',
        placeholder_js_code: '请输入JavaScript代码...',
        placeholder_session: '会话ID（可选）',
        
        // 确认对话框
        confirm_close_session: '确定要关闭当前会话吗？',
        confirm_clear_results: '确定要清空所有结果吗？',
        
        // 错误消息
        error_network: '网络错误，请检查连接',
        error_timeout: '请求超时',
        error_unknown: '未知错误',
        error_invalid_json: '无效的JSON数据',
        error_missing_params: '缺少必要参数'
    },
    
    'en-US': {
        app_title: 'Kimi WebBridge',
        connection_status: 'Connection Status',
        checking: 'Checking...',
        refresh: 'Refresh',
        navigation: 'Navigation',
        go: 'Go',
        new_tab: 'New Tab',
        actions: 'Actions',
        snapshot: 'Snapshot',
        screenshot: 'Screenshot',
        list_tabs: 'Tabs',
        close_session: 'Close Session',
        execute_js: 'Execute JS',
        status: 'Status',
        results: 'Results',
        clear: 'Clear',
        welcome_message: 'Welcome to Kimi WebBridge Browser Automation Plugin',
        welcome_hint: 'Select an action to start exploring the web~',
        copyright: '© 2026 Kimi WebBridge Plugin for N.E.K.O.',
        footer_hint: 'Powered by Kimi',
        
        status_online: 'Connected',
        status_offline: 'Disconnected',
        status_connecting: 'Connecting...',
        
        operation_success: 'Operation successful',
        operation_failed: 'Operation failed',
        navigate_success: 'Navigation successful',
        navigate_error: 'Navigation failed',
        click_success: 'Click successful',
        click_error: 'Click failed',
        fill_success: 'Fill successful',
        fill_error: 'Fill failed',
        screenshot_success: 'Screenshot successful',
        screenshot_error: 'Screenshot failed',
        session_created: 'Session created',
        session_closed: 'Session closed',
        daemon_started: 'Daemon started',
        daemon_stopped: 'Daemon stopped',
        webbridge_not_installed: 'Kimi WebBridge not installed',
        invalid_url: 'Invalid URL',
        selector_required: 'Selector parameter required',
        value_required: 'Value parameter required',
        
        btn_navigate: 'Navigate',
        btn_snapshot: 'Get Snapshot',
        btn_screenshot: 'Screenshot',
        btn_click: 'Click',
        btn_fill: 'Fill',
        btn_evaluate: 'Execute',
        btn_close: 'Close',
        btn_clear: 'Clear',
        
        placeholder_url: 'Enter URL...',
        placeholder_selector: 'Enter selector...',
        placeholder_value: 'Enter value...',
        placeholder_js_code: 'Enter JavaScript code...',
        placeholder_session: 'Session ID (optional)',
        
        confirm_close_session: 'Are you sure you want to close the current session?',
        confirm_clear_results: 'Are you sure you want to clear all results?',
        
        error_network: 'Network error, please check connection',
        error_timeout: 'Request timeout',
        error_unknown: 'Unknown error',
        error_invalid_json: 'Invalid JSON data',
        error_missing_params: 'Missing required parameters'
    },
    
    'ja-JP': {
        app_title: 'Kimi WebBridge',
        connection_status: '接続状態',
        checking: '確認中...',
        refresh: '更新',
        navigation: 'ナビゲーション',
        go: '移動',
        new_tab: '新しいタブ',
        actions: 'アクション',
        snapshot: 'スナップショット',
        screenshot: 'スクリーンショット',
        list_tabs: 'タブ',
        close_session: 'セッション終了',
        execute_js: 'JS実行',
        status: '状態',
        results: '結果',
        clear: 'クリア',
        welcome_message: 'Kimi WebBridge ブラウザ自動化プラグインへようこそ',
        welcome_hint: 'アクションを選択してネットの世界を探検しましょう~',
        copyright: '© 2026 Kimi WebBridge Plugin for N.E.K.O.',
        footer_hint: 'Kimi による技術サポート',
        
        status_online: '接続済み',
        status_offline: '未接続',
        status_connecting: '接続中...',
        
        operation_success: '操作成功',
        operation_failed: '操作失敗',
        navigate_success: 'ナビゲーション成功',
        navigate_error: 'ナビゲーション失敗',
        click_success: 'クリック成功',
        click_error: 'クリック失敗',
        fill_success: '入力成功',
        fill_error: '入力失敗',
        screenshot_success: 'スクリーンショット成功',
        screenshot_error: 'スクリーンショット失敗',
        session_created: 'セッション作成済み',
        session_closed: 'セッション終了済み',
        daemon_started: 'デーモン起動済み',
        daemon_stopped: 'デーモン停止済み',
        webbridge_not_installed: 'Kimi WebBridge未インストール',
        invalid_url: '無効なURL',
        selector_required: 'セレクターパラメータが必要',
        value_required: '値パラメータが必要',
        
        btn_navigate: 'ナビゲート',
        btn_snapshot: 'スナップショット取得',
        btn_screenshot: 'スクリーンショット',
        btn_click: 'クリック',
        btn_fill: '入力',
        btn_evaluate: '実行',
        btn_close: '終了',
        btn_clear: 'クリア',
        
        placeholder_url: 'URLを入力...',
        placeholder_selector: 'セレクターを入力...',
        placeholder_value: '値を入力...',
        placeholder_js_code: 'JavaScriptコードを入力...',
        placeholder_session: 'セッションID（オプション）',
        
        confirm_close_session: '現在のセッションを終了してもよろしいですか？',
        confirm_clear_results: 'すべての結果をクリアしてもよろしいですか？',
        
        error_network: 'ネットワークエラー、接続を確認してください',
        error_timeout: 'リクエストタイムアウト',
        error_unknown: '不明なエラー',
        error_invalid_json: '無効なJSONデータ',
        error_missing_params: '必須パラメータが不足しています'
    }
};

/**
 * 获取当前语言的翻译文本
 * @param {string} key - 翻译键
 * @param {string} lang - 语言代码
 * @returns {string} 翻译后的文本
 */
function getTranslation(key, lang = 'zh-CN') {
    return i18n[lang]?.[key] || i18n['zh-CN'][key] || key;
}

/**
 * 更新页面中的所有翻译文本
 * @param {string} lang - 语言代码
 */
function updatePageTranslations(lang) {
    // 更新所有带有 data-i18n 属性的元素
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const translation = getTranslation(key, lang);
        if (element.tagName === 'INPUT' && element.type !== 'button') {
            element.placeholder = translation;
        } else {
            element.textContent = translation;
        }
    });
    
    // 更新语言选择器
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
        languageSelect.value = lang;
    }
    
    // 更新HTML语言属性
    document.documentElement.lang = lang;
}

/**
 * 初始化国际化
 */
function initI18n() {
    // 从本地存储获取语言设置
    const savedLang = localStorage.getItem('kimi-webbridge-language') || 'zh-CN';
    
    // 更新页面翻译
    updatePageTranslations(savedLang);
    
    // 设置语言选择器事件
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
        languageSelect.value = savedLang;
        languageSelect.addEventListener('change', function() {
            const newLang = this.value;
            localStorage.setItem('kimi-webbridge-language', newLang);
            updatePageTranslations(newLang);
            
            // 触发自定义事件，通知其他模块语言已更改
            const event = new CustomEvent('languageChanged', { detail: { language: newLang } });
            document.dispatchEvent(event);
        });
    }
    
    return savedLang;
}

/**
 * 格式化时间戳
 * @param {Date} date - 日期对象
 * @returns {string} 格式化后的时间字符串
 */
function formatTimestamp(date = new Date()) {
    return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
}

/**
 * 创建结果项HTML
 * @param {string} type - 结果类型 (success, error, warning, info)
 * @param {string} title - 结果标题
 * @param {string} content - 结果内容
 * @returns {string} HTML字符串
 */
function createResultItemHTML(type, title, content) {
    return `
        <div class="result-item ${type} fade-in">
            <div class="result-header">
                <span class="result-title">${title}</span>
                <span class="result-time">${formatTimestamp()}</span>
            </div>
            <div class="result-content">${content}</div>
        </div>
    `;
}

// 导出函数
window.i18nModule = {
    getTranslation,
    updatePageTranslations,
    initI18n,
    formatTimestamp,
    createResultItemHTML
};