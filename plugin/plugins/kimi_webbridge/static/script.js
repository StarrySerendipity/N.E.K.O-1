/**
 * Kimi WebBridge 浏览器自动化插件 - 前端交互逻辑
 * 注意：此UI仅用于查看状态和手动操作。LLM调用插件通过IPC机制，不经过此UI。
 */

class KimiWebBridgeUI {
    constructor() {
        this.sessionId = 'webbridge-session';
        this.init();
    }

    init() {
        this.bindEvents();
        // 启动时显示就绪状态（插件已加载即表示可用）
        this.showReady();
    }

    bindEvents() {
        const navigateBtn = document.getElementById('navigateBtn');
        const snapshotBtn = document.getElementById('snapshotBtn');
        const screenshotBtn = document.getElementById('screenshotBtn');
        const listTabsBtn = document.getElementById('listTabsBtn');
        const closeSessionBtn = document.getElementById('closeSessionBtn');
        const evaluateBtn = document.getElementById('evaluateBtn');
        const clearResultsBtn = document.getElementById('clearResultsBtn');
        const urlInput = document.getElementById('urlInput');

        if (navigateBtn) navigateBtn.addEventListener('click', () => this.handleNavigate());
        if (snapshotBtn) snapshotBtn.addEventListener('click', () => this.addResult('info', '快照', '请通过对话让猫娘执行snapshot操作'));
        if (screenshotBtn) screenshotBtn.addEventListener('click', () => this.addResult('info', '截图', '请通过对话让猫娘执行screenshot操作'));
        if (listTabsBtn) listTabsBtn.addEventListener('click', () => this.addResult('info', '标签页', '请通过对话让猫娘执行list_tabs操作'));
        if (closeSessionBtn) closeSessionBtn.addEventListener('click', () => this.addResult('info', '关闭会话', '请通过对话让猫娘执行close_session操作'));
        if (evaluateBtn) evaluateBtn.addEventListener('click', () => this.addResult('info', '执行JS', '请通过对话让猫娘执行evaluate操作'));
        if (clearResultsBtn) clearResultsBtn.addEventListener('click', () => this.clearResults());
        if (urlInput) urlInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') this.handleNavigate(); });
    }

    showReady() {
        const statusIndicator = document.getElementById('statusIndicator');
        if (statusIndicator) {
            const statusDot = statusIndicator.querySelector('.status-dot');
            const statusText = statusIndicator.querySelector('.status-text');
            if (statusDot) statusDot.className = 'status-dot online';
            if (statusText) statusText.textContent = '已就绪 - 请通过对话使用浏览器自动化';
        }
    }

    handleNavigate() {
        const urlInput = document.getElementById('urlInput');
        const url = urlInput ? urlInput.value.trim() : '';
        if (!url) {
            this.addResult('warning', '请输入URL', '请在输入框中输入要导航的URL');
            return;
        }
        this.addResult('info', '导航请求', `请对猫娘说：帮我用浏览器打开 ${url}`);
        if (urlInput) urlInput.value = '';
    }

    clearResults() {
        const resultsContainer = document.getElementById('resultsContainer');
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="welcome-message"><p>结果区域已清空</p></div>';
        }
    }

    addResult(type, title, content) {
        const resultsContainer = document.getElementById('resultsContainer');
        if (!resultsContainer) return;
        const welcomeMessage = resultsContainer.querySelector('.welcome-message');
        if (welcomeMessage) welcomeMessage.remove();
        const colors = { success: '#10b981', error: '#ef4444', warning: '#f59e0b', info: '#3b82f6' };
        const color = colors[type] || '#6b7280';
        const html = `<div style="border-left:3px solid ${color};padding:8px 12px;margin-bottom:8px;background:rgba(255,255,255,0.05);border-radius:4px;">
            <strong style="color:${color};">${title}</strong>
            <p style="margin:4px 0 0;color:#ccc;font-size:13px;">${content}</p>
        </div>`;
        resultsContainer.insertAdjacentHTML('afterbegin', html);
        resultsContainer.scrollTop = 0;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.kimiWebBridgeUI = new KimiWebBridgeUI();
});
