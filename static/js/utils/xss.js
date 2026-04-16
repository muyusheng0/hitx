/**
 * XSS防护工具
 * 用于转义HTML特殊字符，防止XSS攻击
 */

const HTML_ESCAPE_MAP = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '`': '&#x60;',
    '=': '&#x3D;'
};

function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"'`=]/g, char => HTML_ESCAPE_MAP[char] || char);
}

// 导出给全局使用
window.escapeHtml = escapeHtml;
