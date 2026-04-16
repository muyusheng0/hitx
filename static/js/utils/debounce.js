/**
 * 防抖和节流工具
 */

/**
 * 防抖函数 - 在最后一次调用后delay毫秒执行
 * @param {Function} fn - 要执行的函数
 * @param {number} delay - 延迟毫秒数
 * @returns {Function} 包装后的函数
 */
function debounce(fn, delay = 300) {
    let timeoutId = null;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            fn.apply(this, args);
        }, delay);
    };
}

/**
 * 节流函数 - 间隔delay毫秒执行一次
 * @param {Function} fn - 要执行的函数
 * @param {number} delay - 间隔毫秒数
 * @returns {Function} 包装后的函数
 */
function throttle(fn, delay = 300) {
    let lastCall = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastCall >= delay) {
            lastCall = now;
            fn.apply(this, args);
        }
    };
}

// 导出给全局使用
window.debounce = debounce;
window.throttle = throttle;
