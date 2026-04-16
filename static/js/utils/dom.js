/**
 * DOM操作优化工具
 * 提供DOM缓存和便捷查询
 */

/**
 * DOM元素缓存，避免重复查询
 */
const DOMCache = {
    _cache: new Map(),

    /**
     * 获取元素（带缓存）
     */
    get(id) {
        if (this._cache.has(id)) {
            return this._cache.get(id);
        }
        const el = document.getElementById(id);
        if (el) {
            this._cache.set(id, el);
        }
        return el;
    },

    /**
     * 批量获取元素
     */
    getAll(...ids) {
        return ids.map(id => this.get(id));
    },

    /**
     * 设置文本内容（安全转义）
     */
    setText(id, text) {
        const el = this.get(id);
        if (el) {
            el.textContent = text || '-';
        }
    },

    /**
     * 设置输入值
     */
    setValue(id, value) {
        const el = this.get(id);
        if (el) {
            el.value = value || '';
        }
    },

    /**
     * 显示元素
     */
    show(id) {
        const el = this.get(id);
        if (el) el.style.display = '';
    },

    /**
     * 隐藏元素
     */
    hide(id) {
        const el = this.get(id);
        if (el) el.style.display = 'none';
    },

    /**
     * 清除缓存
     */
    clear() {
        this._cache.clear();
    }
};

/**
 * 批量更新DOM（使用DocumentFragment减少重绘）
 */
function batchUpdateDOM(updates) {
    // updates: [{id, method, args}, ...]
    updates.forEach(({id, method, args}) => {
        const el = DOMCache.get(id);
        if (el && typeof el[method] === 'function') {
            el[method].apply(el, args);
        }
    });
}

// 导出给全局使用
window.DOMCache = DOMCache;
window.batchUpdateDOM = batchUpdateDOM;
