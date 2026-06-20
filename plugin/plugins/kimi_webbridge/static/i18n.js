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
        error_missing_params: '缺少必要参数',
        
        // 教程页面
        tutorial_title: 'Kimi WebBridge 使用教程',
        tutorial_subtitle: '让猫娘拥有控制你浏览器的魔法 ✨',
        step1_title: '安装 Kimi WebBridge 守护进程',
        step1_desc: '在 PowerShell 中运行以下命令，一键安装守护进程：',
        step1_tip: '安装完成后，守护进程会自动配置好，无需额外设置。',
        step2_title: '安装浏览器扩展',
        step2_desc: '在你的 Chrome 或 Edge 浏览器中安装 Kimi WebBridge 扩展：',
        step2_check1: '打开浏览器扩展商店，搜索 "Kimi WebBridge"',
        step2_check2: '点击"添加到浏览器"安装扩展',
        step2_check3: '安装后扩展会自动连接到本地守护进程',
        step2_tip: '扩展图标显示绿色表示已连接，红色表示未连接。',
        step3_title: '启动守护进程',
        step3_desc: '守护进程会在插件启动时自动尝试启动。你也可以手动启动：',
        step3_tip: '守护进程启动后会监听 127.0.0.1:10086 端口。',
        step4_title: '开始使用',
        step4_desc: '一切就绪！现在你可以对猫娘说：',
        step4_desc2: '猫娘会自动：',
        step4_check1: '调用 navigate 打开B站',
        step4_check2: '调用 snapshot 获取页面结构',
        step4_check3: '调用 fill 在搜索框输入关键词',
        step4_check4: '调用 click 点击搜索按钮',
        step5_title: '可用工具一览',
        step5_desc: '猫娘拥有以下浏览器操作能力：',
        step5_check1: 'navigate - 导航到指定URL',
        step5_check2: 'snapshot - 获取页面结构快照',
        step5_check3: 'click - 点击页面元素',
        step5_check4: 'fill - 填写表单输入框',
        step5_check5: 'screenshot - 页面截图',
        step5_check6: 'evaluate - 执行JavaScript代码',
        step5_check7: 'upload - 上传文件',
        step5_check8: 'list_tabs / find_tab / close_tab - 标签页管理',
        faq_title: '常见问题',
        faq_q1: 'Q: 猫娘打开的页面和我看到的不一样？',
        faq_a1: 'A: Kimi WebBridge 控制的是你的真实浏览器，页面应该完全一致。如果不一样，请检查扩展是否已连接。',
        faq_q2: 'Q: 操作失败提示"守护进程无响应"？',
        faq_a2: 'A: 请确保浏览器扩展已安装并启用，扩展图标显示绿色连接状态。',
        faq_q3: 'Q: 支持哪些浏览器？',
        faq_a3: 'A: 支持 Chrome 和 Edge 浏览器。',
        footer_text: '用 ♥ 为 N.E.K.O 猫娘打造',
        back_to_main: '← 返回主界面',
        tutorial_link: '📖 查看使用教程'
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
        error_missing_params: 'Missing required parameters',
        
        // Tutorial
        tutorial_title: 'Kimi WebBridge Tutorial',
        tutorial_subtitle: 'Give your catgirl the magic to control your browser ✨',
        step1_title: 'Install Kimi WebBridge Daemon',
        step1_desc: 'Run the following command in PowerShell to install the daemon:',
        step1_tip: 'After installation, the daemon is automatically configured.',
        step2_title: 'Install Browser Extension',
        step2_desc: 'Install the Kimi WebBridge extension in Chrome or Edge:',
        step2_check1: 'Open browser extension store, search "Kimi WebBridge"',
        step2_check2: 'Click "Add to Browser" to install',
        step2_check3: 'Extension auto-connects to local daemon after installation',
        step2_tip: 'Green icon = connected, Red icon = disconnected.',
        step3_title: 'Start the Daemon',
        step3_desc: 'The daemon auto-starts with the plugin. You can also start it manually:',
        step3_tip: 'Daemon listens on 127.0.0.1:10086 after starting.',
        step4_title: 'Start Using',
        step4_desc: 'All set! Now you can tell your catgirl:',
        step4_desc2: 'The catgirl will automatically:',
        step4_check1: 'Call navigate to open Bilibili',
        step4_check2: 'Call snapshot to read page structure',
        step4_check3: 'Call fill to type in the search box',
        step4_check4: 'Call click to press the search button',
        step5_title: 'Available Tools',
        step5_desc: 'Your catgirl has these browser abilities:',
        step5_check1: 'navigate - Navigate to a URL',
        step5_check2: 'snapshot - Get page structure snapshot',
        step5_check3: 'click - Click a page element',
        step5_check4: 'fill - Fill form input',
        step5_check5: 'screenshot - Take page screenshot',
        step5_check6: 'evaluate - Execute JavaScript code',
        step5_check7: 'upload - Upload files',
        step5_check8: 'list_tabs / find_tab / close_tab - Tab management',
        faq_title: 'FAQ',
        faq_q1: 'Q: Page looks different from what I see?',
        faq_a1: 'A: Kimi WebBridge controls your real browser. Pages should be identical. Check if extension is connected.',
        faq_q2: 'Q: "Daemon not responding" error?',
        faq_a2: 'A: Ensure browser extension is installed, enabled, and shows green connected status.',
        faq_q3: 'Q: Which browsers are supported?',
        faq_a3: 'A: Chrome and Edge browsers are supported.',
        footer_text: 'Made with ♥ for N.E.K.O catgirl',
        back_to_main: '← Back to Main',
        tutorial_link: '📖 View Tutorial'
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
        error_missing_params: '必須パラメータが不足しています',
        
        // チュートリアル
        tutorial_title: 'Kimi WebBridge チュートリアル',
        tutorial_subtitle: 'ネコ娘にブラウザ操作の魔法を与えましょう ✨',
        step1_title: 'Kimi WebBridge デーモンをインストール',
        step1_desc: 'PowerShellで以下のコマンドを実行してデーモンをインストール：',
        step1_tip: 'インストール後、デーモンは自動的に設定されます。',
        step2_title: 'ブラウザ拡張をインストール',
        step2_desc: 'ChromeまたはEdgeでKimi WebBridge拡張をインストール：',
        step2_check1: 'ブラウザ拡張ストアで「Kimi WebBridge」を検索',
        step2_check2: '「ブラウザに追加」をクリックしてインストール',
        step2_check3: 'インストール後、拡張は自動的にローカルデーモンに接続',
        step2_tip: '緑アイコン=接続済み、赤アイコン=未接続。',
        step3_title: 'デーモンを起動',
        step3_desc: 'デーモンはプラグイン起動時に自動的に起動します。手動で起動することもできます：',
        step3_tip: 'デーモン起動後、127.0.0.1:10086でリッスンします。',
        step4_title: '使い始める',
        step4_desc: '準備完了！猫娘にこう言ってみて：',
        step4_desc2: '猫娘は自動的に：',
        step4_check1: 'navigateを呼び出してBilibiliを開く',
        step4_check2: 'snapshotを呼び出してページ構造を読む',
        step4_check3: 'fillを呼び出して検索ボックスに入力',
        step4_check4: 'clickを呼び出して検索ボタンを押す',
        step5_title: '利用可能なツール',
        step5_desc: '猫娘は以下のブラウザ操作能力を持っています：',
        step5_check1: 'navigate - URLに移動',
        step5_check2: 'snapshot - ページ構造のスナップショット取得',
        step5_check3: 'click - ページ要素をクリック',
        step5_check4: 'fill - フォーム入力',
        step5_check5: 'screenshot - ページスクリーンショット',
        step5_check6: 'evaluate - JavaScriptコード実行',
        step5_check7: 'upload - ファイルアップロード',
        step5_check8: 'list_tabs / find_tab / close_tab - タブ管理',
        faq_title: 'よくある質問',
        faq_q1: 'Q: 猫娘が開いたページが自分が見ているものと違う？',
        faq_a1: 'A: Kimi WebBridgeはあなたの実際のブラウザを操作します。ページは完全に一致するはずです。拡張が接続されているか確認してください。',
        faq_q2: 'Q: 「デーモンが応答しない」エラー？',
        faq_a2: 'A: ブラウザ拡張がインストール・有効化され、緑色の接続状態を表示しているか確認してください。',
        faq_q3: 'Q: サポートされているブラウザは？',
        faq_a3: 'A: ChromeとEdgeブラウザをサポートしています。',
        footer_text: 'N.E.K.O 猫娘のために ♥ を込めて',
        back_to_main: '← メインに戻る',
        tutorial_link: '📖 チュートリアルを見る'
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