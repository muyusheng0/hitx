/**
 * 用户状态管理模块
 * 统一管理用户状态，消除多数据源导致的同步问题
 */

const UserStore = {
    _state: null,
    _listeners: [],

    /**
     * 获取当前状态
     */
    getState() {
        return this._state;
    },

    /**
     * 设置状态
     */
    setState(user) {
        this._state = user;
        if (user) {
            // 同步到localStorage
            try {
                localStorage.setItem('jlu8_current_user', JSON.stringify(user));
            } catch (e) {
                console.error('Failed to save to localStorage:', e);
            }
        } else {
            localStorage.removeItem('jlu8_current_user');
        }
        this._notify();
    },

    /**
     * 清除状态
     */
    clearState() {
        this._state = null;
        localStorage.removeItem('jlu8_current_user');
        this._notify();
    },

    /**
     * 初始化，从localStorage恢复状态
     */
    init() {
        try {
            const saved = localStorage.getItem('jlu8_current_user');
            if (saved) {
                this._state = JSON.parse(saved);
            }
        } catch (e) {
            console.error('Failed to load from localStorage:', e);
            this._state = null;
        }
        return this._state;
    },

    /**
     * 订阅状态变化
     */
    subscribe(callback) {
        this._listeners.push(callback);
        return () => {
            this._listeners = this._listeners.filter(cb => cb !== callback);
        };
    },

    /**
     * 通知所有监听器
     */
    _notify() {
        this._listeners.forEach(cb => {
            try {
                cb(this._state);
            } catch (e) {
                console.error('State listener error:', e);
            }
        });
    }
};

// 导出到全局
window.UserStore = UserStore;
