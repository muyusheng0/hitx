/**
 * 吉大通信八班 同学录网站 - JavaScript
 * 版本: 20260407-001
 */

console.log('[VERSION] main.js v20260407-007');

// ==================== 全局状态 ====================
const state = {
    verified: false,
    currentStudent: null,
    pendingUploadFile: null  // 待上传的文件
};

// ==================== 用户状态 ====================
function updateUserStatusUI(verified, student) {
    const userStatus = document.getElementById('userStatus');
    if (!userStatus) return;

    if (verified && student) {
        const adminBadge = student.is_admin ? '<span style="background: var(--secondary); color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; margin-left: 4px;">管理员</span>' : '';
        userStatus.innerHTML = `
            <div class="user-logged" onclick="window.location.href='/about'" style="cursor: pointer;">
                <span>欢迎，</span>
                <span class="user-name">${escapeHtml(student.name)}</span>${adminBadge}
            </div>
        `;
    } else {
        userStatus.innerHTML = `
            <span class="user-login" onclick="showVerifyModal()">登录</span>
        `;
    }
}

// ==================== 验证与编辑 ====================
async function checkVerifyStatus() {
    try {
        const res = await fetch('/api/check_verify', { credentials: 'same-origin' });
        const data = await res.json();
        if (data.verified) {
            state.verified = true;
            state.currentStudent = data.student;
            window.currentUser = data.student;  // 直接使用完整的学生对象，包含 avatar
            showEditButton();
            updateUserStatusUI(true, data.student);
            updateVerifyUI(true);
            updateMessageInputUI(true);
            loadNotificationCount();
            // 触发登录成功事件
            window.dispatchEvent(new CustomEvent('userLoginSuccess', { detail: window.currentUser }));
            // 检查是否需要设置密码（所有用户）
            if (!data.student.login_password_set) {
                checkAndShowPasswordPrompt();
            }
        } else {
            window.currentUser = null;
            updateUserStatusUI(false);
            updateMessageInputUI(false);
        }
    } catch (e) {
        console.error('Check verify failed:', e);
        window.currentUser = null;
        updateUserStatusUI(false);
        updateMessageInputUI(false);
    }
}

// 检查并显示设置密码提示
async function checkAndShowPasswordPrompt() {
    try {
        // 只有密码未设置时才提示
        if (window.currentUser && window.currentUser.login_password_set) {
            return;
        }
        const res = await fetch('/api/user/get_password_prompt', { credentials: 'same-origin' });
        const data = await res.json();
        if (data.success && !data.no_prompt) {
            showPasswordPromptModal();
        }
    } catch (e) {
        console.error('检查密码提示失败:', e);
    }
}

// 显示设置密码提示弹窗
function showPasswordPromptModal() {
    const modal = document.getElementById('passwordPromptModal');
    if (!modal) {
        // 创建弹窗
        const modalHtml = `
        <div class="modal-overlay" id="passwordPromptModal">
            <div class="modal">
                <div class="modal-header">
                    <h3 class="modal-title">设置登录密码</h3>
                    <button class="modal-close" onclick="closePasswordPromptModal()">✕</button>
                </div>
                <div style="padding: 1rem; text-align: center;">
                    <p style="margin-bottom: 1rem; color: var(--text);">设置登录密码后，可用于身份验证等场景。</p>
                    <input type="password" id="promptNewPasswordInput" placeholder="请输入密码" style="width: 100%; padding: 0.8rem; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 0.5rem; box-sizing: border-box;">
                    <input type="password" id="promptConfirmPasswordInput" placeholder="请确认密码" style="width: 100%; padding: 0.8rem; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 0.5rem; box-sizing: border-box;">
                    <label style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; margin-bottom: 1rem; cursor: pointer;">
                        <input type="checkbox" id="noPasswordPromptCheck">
                        <span style="color: var(--text-light); font-size: 0.9rem;">不再提示设置密码</span>
                    </label>
                    <p id="promptPasswordError" style="color: #e74c3c; margin-bottom: 0.5rem;"></p>
                    <div style="display: flex; gap: 0.5rem; justify-content: center;">
                        <button onclick="submitPasswordPrompt()" style="background: var(--secondary); color: white; border: none; padding: 0.6rem 1.5rem; border-radius: 8px; cursor: pointer;">确定</button>
                        <button onclick="closePasswordPromptModal()" style="background: var(--bg-dark); color: var(--text); border: none; padding: 0.6rem 1.5rem; border-radius: 8px; cursor: pointer;">稍后</button>
                    </div>
                </div>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    document.getElementById('passwordPromptModal').classList.add('active');
}

function closePasswordPromptModal() {
    const modal = document.getElementById('passwordPromptModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

async function submitPasswordPrompt() {
    const newPwd = document.getElementById('promptNewPasswordInput').value;
    const confirmPwd = document.getElementById('promptConfirmPasswordInput').value;
    const noPrompt = document.getElementById('noPasswordPromptCheck').checked;
    const errorEl = document.getElementById('promptPasswordError');

    if (!newPwd) {
        errorEl.textContent = '请输入密码';
        return;
    }
    if (newPwd !== confirmPwd) {
        errorEl.textContent = '两次密码不一致';
        return;
    }

    try {
        const res = await fetch('/api/user/set_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ password: newPwd })
        });
        const data = await res.json();
        if (data.success) {
            // 如果勾选了不再提示，保存设置
            if (noPrompt) {
                await fetch('/api/user/set_password_prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ no_prompt: true })
                });
            }
            closePasswordPromptModal();
            if (window.currentUser) {
                window.currentUser.login_password_set = true;
                localStorage.setItem('currentUser', JSON.stringify(window.currentUser));
            }
        } else {
            errorEl.textContent = data.message || '设置失败';
        }
    } catch (e) {
        errorEl.textContent = '设置失败';
    }
}

function updateVerifyUI(verified) {
    const verifyBtns = document.querySelectorAll('.verify-required');
    verifyBtns.forEach(btn => {
        btn.style.display = verified ? '' : 'none';
    });
}

function updateMessageInputUI(verified) {
    const loginPrompt = document.getElementById('messageLoginPrompt');
    const messageForm = document.getElementById('messageForm');
    const aiImageGenBox = document.getElementById('aiImageGenBox');
    console.log('[updateMessageInputUI] called with:', verified);
    console.log('[updateMessageInputUI] elements:', { loginPrompt, messageForm, aiImageGenBox });
    if (loginPrompt && messageForm) {
        if (verified) {
            loginPrompt.style.display = 'none';
            messageForm.style.display = 'block';
            if (aiImageGenBox) aiImageGenBox.style.display = 'block';
            // 更新头像显示 - 使用真实头像
            const avatar = document.getElementById('msgComposeAvatar');
            if (avatar && window.currentUser) {
                const avatarUrl = window.currentUser.avatar;
                if (avatarUrl) {
                    avatar.textContent = '';
                    avatar.style.backgroundImage = `url(${avatarUrl})`;
                    avatar.style.backgroundSize = 'cover';
                    avatar.style.backgroundPosition = 'center';
                } else {
                    avatar.textContent = window.currentUser.name[0];
                    avatar.style.backgroundImage = 'none';
                }
            }
            console.log('[updateMessageInputUI] UI updated to logged in state');
        } else {
            loginPrompt.style.display = '';
            messageForm.style.display = 'none';
            if (aiImageGenBox) aiImageGenBox.style.display = 'none';
            console.log('[updateMessageInputUI] UI updated to logged out state');
        }
    } else {
        console.log('[updateMessageInputUI] elements not found on this page');
    }
}

function showVerifyModal() {
    console.log('showVerifyModal called');
    const overlay = document.getElementById('verifyModal');
    console.log('verifyModal overlay:', overlay);
    if (overlay) {
        overlay.classList.add('active');
        console.log('Modal should now be visible');
        // 打开时刷新验证码
        refreshCaptcha();
    } else {
        console.log('ERROR: verifyModal not found in DOM');
    }
}

function closeVerifyModal() {
    const overlay = document.getElementById('verifyModal');
    if (overlay) overlay.classList.remove('active');
    // 清除密码输入
    const passwordInput = document.getElementById('verifyLoginPassword');
    if (passwordInput) passwordInput.value = '';
    const passwordGroup = document.getElementById('loginPasswordGroup');
    if (passwordGroup) passwordGroup.style.display = 'none';
    const errorEl = document.getElementById('verifyError');
    if (errorEl) errorEl.textContent = '';
}

async function refreshCaptcha() {
    try {
        const res = await fetch('/api/captcha', { credentials: 'same-origin' });
        const data = await res.json();
        const captchaEl = document.getElementById('captchaQuestion');
        if (captchaEl) {
            captchaEl.textContent = data.captcha;
        }
    } catch (e) {
        console.error('Failed to load captcha:', e);
    }
}

async function checkPasswordRequired() {
    const name = document.getElementById('verifyName')?.value.trim();
    const passwordGroup = document.getElementById('loginPasswordGroup');

    if (!name || !passwordGroup) return;

    // 先获取学号
    const studentId = document.getElementById('verifyStudentId')?.value.trim();
    if (!studentId) {
        // 学号还没填，先不显示密码框
        return;
    }

    try {
        const res = await fetch('/api/check_user_login_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ name, student_id: studentId })
        });
        const data = await res.json();
        if (data.has_password) {
            passwordGroup.style.display = 'block';
        } else {
            passwordGroup.style.display = 'none';
        }
    } catch (e) {
        console.error('检查密码状态失败:', e);
    }
}

async function submitVerify(e) {
    e.preventDefault();

    const name = document.getElementById('verifyName').value.trim();
    const studentId = document.getElementById('verifyStudentId').value.trim();
    const captcha = document.getElementById('verifyCaptcha').value.trim();
    const loginPassword = document.getElementById('verifyLoginPassword').value.trim();
    const errorEl = document.getElementById('verifyError');
    const passwordGroup = document.getElementById('loginPasswordGroup');

    if (!name || !studentId) {
        errorEl.textContent = '请填写姓名和学号';
        return;
    }

    if (!captcha) {
        errorEl.textContent = '请填写验证码';
        return;
    }

    // 如果密码框可见但没有输入，且不是密码错误的情况
    if (passwordGroup && passwordGroup.style.display !== 'none' && !loginPassword) {
        errorEl.textContent = '请输入登录密码';
        return;
    }

    try {
        const res = await fetch('/api/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ name, student_id: studentId, captcha, login_password: loginPassword })
        });

        const data = await res.json();

        if (data.success) {
            console.log('登录API成功，等待会话建立...');
            // 先关闭登录弹窗
            closeVerifyModal();
            // 清除密码
            if (document.getElementById('verifyLoginPassword')) {
                document.getElementById('verifyLoginPassword').value = '';
            }
            if (passwordGroup) {
                passwordGroup.style.display = 'none';
            }
            // 短暂延迟确保会话cookie已设置
            await new Promise(r => setTimeout(r, 100));
            // 获取完整用户信息（包括is_admin）
            try {
                const verifyRes = await fetch('/api/check_verify', { credentials: 'same-origin' });
                const verifyData = await verifyRes.json();
                console.log('check_verify返回:', verifyData);
                if (verifyData.verified) {
                    console.log('验证成功，设置用户状态...');
                    state.verified = true;
                    state.currentStudent = verifyData.student;
                    window.currentUser = verifyData.student;
                    showEditButton();
                    updateUserStatusUI(true, verifyData.student);
                    updateVerifyUI(true);
                    updateMessageInputUI(true);
                    // 触发登录成功事件
                    window.dispatchEvent(new CustomEvent('userLoginSuccess', { detail: window.currentUser }));
                    if (typeof loadStudentData === 'function') {
                        loadStudentData();
                    }
                    if (typeof loadNotifications === 'function') {
                        loadNotifications();
                    }
                    // 直接更新"我的"页面的 UI（不刷新页面）
                    const unloggedView = document.getElementById('unloggedView');
                    const loggedView = document.getElementById('loggedView');
                    if (unloggedView) unloggedView.style.display = 'none';
                    if (loggedView) {
                        loggedView.style.display = 'block';
                        const nameEl = document.getElementById('profileName');
                        const idEl = document.getElementById('profileId');
                        const avatarEl = document.getElementById('profileAvatarInitial');
                        if (nameEl && verifyData.student) nameEl.textContent = verifyData.student.name || '未设置';
                        if (idEl && verifyData.student) idEl.textContent = '学号：' + (verifyData.student.id || '未设置');
                        if (avatarEl && verifyData.student) avatarEl.textContent = (verifyData.student.name || '?')[0];
                    }
                    console.log('登录成功完成');
                } else {
                    console.log('验证失败: verifyData.verified is false');
                    alert('登录成功但获取用户信息失败，请刷新页面');
                }
            } catch (e) {
                console.error('获取用户信息失败:', e);
                alert('登录成功但获取用户信息失败，请刷新页面');
            }
        } else if (data.prompt === '请输入登录密码') {
            // 需要显示密码输入框
            errorEl.textContent = '';
            passwordGroup.style.display = 'block';
            document.getElementById('verifyLoginPassword').focus();
        } else {
            errorEl.textContent = data.message;
        }
    } catch (e) {
        errorEl.textContent = '验证失败，请稍后重试';
    }
}

function logout() {
    if (!confirm('确定要退出登录吗？')) return;
    fetch('/api/logout').then(() => {
        state.verified = false;
        state.currentStudent = null;
        window.currentUser = null;
        localStorage.removeItem('currentUser');
        localStorage.removeItem('rememberedLogin');
        hideEditButton();
        updateUserStatusUI(false);
        updateVerifyUI(false);
        updateMessageInputUI(false);
    }).then(() => {
        window.location.reload();
    });
}

function showEditButton() {
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.style.display = 'flex';
    });
}

function hideEditButton() {
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.style.display = 'none';
    });
}

// ==================== 留言板 ====================
async function loadMessages() {
    try {
        const res = await fetch('/api/lyb');
        const messages = await res.json();
        renderMessages(messages);
    } catch (e) {
        console.error('Load messages failed:', e);
    }
}

function renderMessages(messages) {
    const container = document.getElementById('messageList');
    if (!container) return;

    if (messages.length === 0) {
        container.innerHTML = '<div class="empty-message">还没有留言，来写第一条吧~</div>';
        return;
    }

    container.innerHTML = messages.map(msg => `
        <div class="message-item slide-in">
            <div class="message-nickname">${escapeHtml(msg.nickname)}</div>
            <div class="message-content">${escapeHtml(msg.content)}</div>
            <div class="message-time">${msg.time}</div>
        </div>
    `).join('');
}

async function deleteMessage(msgId) {
    if (!confirm('确定要删除这条留言吗？')) return;

    try {
        const res = await fetch('/api/delete_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ id: msgId })
        });
        const data = await res.json();

        if (data.success) {
            const msgEl = document.getElementById('msg-' + msgId);
            if (msgEl) {
                msgEl.remove();
            }
            alert('删除成功');
        } else {
            alert(data.message || '删除失败');
        }
    } catch (e) {
        alert('删除失败，请稍后重试');
    }
}

function updateDeleteButtonsVisibility() {
    if (!state.verified || !window.currentUser) {
        document.querySelectorAll('.delete-msg-btn').forEach(btn => btn.style.display = 'none');
        return;
    }

    const currentName = window.currentUser.name;
    const isAdmin = window.currentUser.is_admin;
    document.querySelectorAll('.envelope-card[data-nickname]').forEach(item => {
        const author = item.dataset.nickname;
        if (author === currentName || isAdmin) {
            item.querySelector('.delete-msg-btn').style.display = 'block';
        } else {
            item.querySelector('.delete-msg-btn').style.display = 'none';
        }
    });
}

async function submitMessage(e) {
    e.preventDefault();

    console.log('submitMessage called, state.verified:', state.verified);

    if (!state.verified) {
        console.log('Not verified, showing verify modal');
        showVerifyModal();
        return;
    }

    const nickname = document.getElementById('msgNickname')?.value?.trim() || (window.currentUser?.name || '匿名同学');
    const content = document.getElementById('msgContent')?.value?.trim();
    const imageInput = document.getElementById('msgImage');
    let imageUrl = '';
    const submitBtn = e.target.querySelector('.submit-btn');

    // 检查是否有AI生成的图片
    if (e.target.dataset.aiImage) {
        imageUrl = e.target.dataset.aiImage;
    }

    console.log('Submitting message:', { nickname, content });

    if (!content) {
        alert('请输入留言内容');
        return;
    }

    if (content.length > 500) {
        alert('留言内容过长');
        return;
    }

    // 如果有图片先上传（带进度）
    if (imageInput && imageInput.files[0]) {
        const progressEl = document.getElementById('msgImageUploadProgress');
        if (progressEl) {
            progressEl.style.display = 'block';
            progressEl.classList.remove('upload-error');
            showUploadProgress(progressEl, 0);
        }

        const formData = new FormData();
        formData.append('file', imageInput.files[0]);

        // 禁用提交按钮
        if (submitBtn) submitBtn.disabled = true;

        try {
            await new Promise((resolve, reject) => {
                uploadWithProgress('/api/upload_image', formData,
                    (percent) => {
                        if (progressEl) showUploadProgress(progressEl, percent);
                    },
                    (uploadData) => {
                        if (uploadData.success) {
                            imageUrl = uploadData.url;
                            resolve();
                        } else {
                            reject(new Error(uploadData.message || '上传失败'));
                        }
                    },
                    (err) => {
                        reject(new Error(err));
                    }
                );
            });
        } catch (uploadErr) {
            if (progressEl) {
                showUploadError(progressEl, uploadErr.message);
            }
            if (submitBtn) submitBtn.disabled = false;
            if (uploadErr.message === '请先验证身份') {
                alert('登录已过期，请重新登录');
                showVerifyModal();
            } else {
                alert('图片上传失败: ' + uploadErr.message);
            }
            return;
        }
    }

    try {
        console.log('Sending API request to /api/add_message');
        const res = await fetch('/api/add_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ nickname, content, image: imageUrl })
        });

        console.log('Response status:', res.status);
        const data = await res.json();
        console.log('Response data:', data);

        if (data.success) {
            document.getElementById('msgContent').value = '';
            document.getElementById('charCount').textContent = '0/500';
            document.getElementById('msgImage').value = '';
            document.getElementById('msgImagePreview').style.display = 'none';
            const progressEl = document.getElementById('msgImageUploadProgress');
            if (progressEl) progressEl.style.display = 'none';

            const container = document.getElementById('messageList');
            const emptyMsg = container.querySelector('.empty-message');
            if (emptyMsg) emptyMsg.remove();

            const msgId = data.message.id;
            const newMsg = document.createElement('div');
            newMsg.className = 'envelope-card open';
            newMsg.id = `msg-${msgId}`;
            newMsg.dataset.nickname = data.message.nickname;
            newMsg.dataset.msgId = msgId;
            newMsg.onclick = function() { toggleEnvelope(this); };
            newMsg.innerHTML = `
                <div class="envelope-body">
                    <div class="envelope-flap"></div>
                    <div class="wax-seal"></div>
                    <div class="postmark">
                        <div class="postmark-date">${data.message.time.substring(0, 7)}</div>
                    </div>
                    <div class="letter-content">
                        <div class="letter-header">
                            <div class="letter-avatar" style="display: flex; align-items: center; justify-content: center; font-family: 'ZCOOL XiaoWei', serif; font-size: 1.2rem; color: var(--primary);">${escapeHtml(data.message.nickname[0])}</div>
                            <div class="letter-info">
                                <div class="letter-nickname">${escapeHtml(data.message.nickname)}</div>
                                <div class="letter-time">${data.message.time}</div>
                            </div>
                        </div>
                        <div class="letter-text">${escapeHtml(data.message.content)}</div>
                        ${data.message.image ? `<div class="letter-image"><img src="${data.message.image}" onclick="showLightbox(this.src)"></div>` : ''}
                        <div class="letter-signature">${escapeHtml(data.message.nickname)}</div>
                        <div class="letter-actions">
                            <button class="letter-like-btn" onclick="event.stopPropagation(); toggleLike(${msgId})" data-liked="false">
                                <span class="like-icon">🤍</span>
                                <span class="like-count">0</span>
                            </button>
                            <button class="letter-comment-btn" onclick="event.stopPropagation(); toggleComments(${msgId})">
                                <span>💬</span>
                                <span class="comment-count">0</span>
                            </button>
                            <button class="delete-msg-btn" onclick="event.stopPropagation(); deleteMessage(${msgId})" style="display: none; background: none; border: 1px solid #d4a574; border-radius: 20px; padding: 6px 12px; cursor: pointer;">🗑️</button>
                        </div>
                        <div class="letter-comments" id="comments-${msgId}" style="display: block;">
                            <div class="comments-list" id="comments-list-${msgId}"></div>
                            <div class="comment-input-area" id="comment-input-${msgId}" style="display: flex; gap: 8px; margin-top: 10px;">
                                <input type="text" class="comment-input" placeholder="写下你的评论..." onkeypress="handleCommentKeypress(event, ${msgId})" style="flex: 1; padding: 8px 12px; border: 1px solid #d4a574; border-radius: 20px; font-size: 0.85rem;">
                                <button class="comment-submit-btn" onclick="submitComment(${msgId})" style="padding: 8px 16px; background: var(--secondary); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 0.85rem;">发送</button>
                            </div>
                        </div>
                    </div>
                    <div class="expand-hint">点击收起</div>
                </div>
            `;
            container.insertBefore(newMsg, container.firstChild);
            updateDeleteButtonsVisibility();
            alert('留言发表成功！');
        } else {
            console.log('API returned success: false, message:', data.message);
            alert(data.message || '提交失败，请稍后重试');
        }
    } catch (e) {
        console.error('Submit message error:', e);
        alert('提交失败，请稍后重试');
    }
}

async function submitTextMessage() {
    if (!state.verified) {
        showVerifyModal();
        return;
    }

    const nickname = window.currentUser?.name || '匿名同学';
    const content = document.getElementById('msgContent')?.value?.trim();
    const imageInput = document.getElementById('msgImage');
    let imageUrl = '';
    const msgForm = document.getElementById('messageForm');
    const submitBtn = document.querySelector('.msg-submit-btn');

    // 检查是否有AI生成的图片
    if (msgForm && msgForm.dataset.aiImage) {
        imageUrl = msgForm.dataset.aiImage;
    }

    if (!content) {
        alert('请输入留言内容');
        return;
    }

    if (content.length > 500) {
        alert('留言内容过长');
        return;
    }

    // 如果有图片先上传（带进度）
    if (!imageUrl && imageInput && imageInput.files[0]) {
        const progressEl = document.getElementById('msgImageUploadProgress');
        if (progressEl) {
            progressEl.style.display = 'block';
            showUploadProgress(progressEl, 0);
        }

        const formData = new FormData();
        formData.append('file', imageInput.files[0]);

        if (submitBtn) submitBtn.disabled = true;

        try {
            await new Promise((resolve, reject) => {
                uploadWithProgress('/api/upload_image', formData,
                    (percent) => {
                        if (progressEl) showUploadProgress(progressEl, percent);
                    },
                    (uploadData) => {
                        if (uploadData.success) {
                            imageUrl = uploadData.url;
                            resolve();
                        } else {
                            reject(new Error(uploadData.message || '上传失败'));
                        }
                    },
                    (err) => {
                        reject(new Error(err));
                    }
                );
            });
        } catch (uploadErr) {
            if (progressEl) progressEl.style.display = 'none';
            if (submitBtn) submitBtn.disabled = false;
            if (uploadErr.message === '请先验证身份') {
                alert('登录已过期，请重新登录');
                showVerifyModal();
            } else {
                alert('图片上传失败: ' + uploadErr.message);
            }
            return;
        }
    }

    try {
        const res = await fetch('/api/add_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ nickname, content, image: imageUrl })
        });

        const data = await res.json();

        if (data.success) {
            document.getElementById('msgContent').value = '';
            document.getElementById('charCount').textContent = '0';
            document.getElementById('msgImage').value = '';
            document.getElementById('msgImagePreview').style.display = 'none';
            document.getElementById('msgImageUploadProgress').style.display = 'none';
            msgForm.dataset.aiImage = '';

            const container = document.getElementById('messageList');
            if (container.querySelector('.empty-message')) {
                container.querySelector('.empty-message').remove();
            }

            const msgId = data.message.id;
            const newMsg = document.createElement('div');
            newMsg.className = 'envelope-card open';
            newMsg.id = `msg-${msgId}`;
            newMsg.dataset.nickname = data.message.nickname;
            newMsg.dataset.msgId = msgId;
            newMsg.onclick = function() { toggleEnvelope(this); };
            newMsg.innerHTML = `
                <div class="envelope-body">
                    <div class="envelope-flap"></div>
                    <div class="wax-seal"></div>
                    <div class="postmark">
                        <div class="postmark-date">${data.message.time.substring(0, 7)}</div>
                    </div>
                    <div class="letter-content">
                        <div class="letter-header">
                            <div class="letter-avatar" style="display: flex; align-items: center; justify-content: center; font-family: 'ZCOOL XiaoWei', serif; font-size: 1.2rem; color: var(--primary);">${escapeHtml(data.message.nickname[0])}</div>
                            <div class="letter-info">
                                <div class="letter-nickname">${escapeHtml(data.message.nickname)}</div>
                                <div class="letter-time">${data.message.time}</div>
                            </div>
                        </div>
                        <div class="letter-text">${escapeHtml(data.message.content)}</div>
                        ${data.message.image ? `<div class="letter-image"><img src="${data.message.image}" onclick="showLightbox(this.src)"></div>` : ''}
                        <div class="letter-signature">${escapeHtml(data.message.nickname)}</div>
                        <div class="letter-actions">
                            <button class="letter-like-btn" onclick="event.stopPropagation(); toggleLike(${msgId})" data-liked="false">
                                <span class="like-icon">🤍</span>
                                <span class="like-count">0</span>
                            </button>
                            <button class="letter-comment-btn" onclick="event.stopPropagation(); toggleComments(${msgId})">
                                <span>💬</span>
                                <span class="comment-count">0</span>
                            </button>
                            <button class="delete-msg-btn" onclick="event.stopPropagation(); deleteMessage(${msgId})" style="display: none; background: none; border: 1px solid #d4a574; border-radius: 20px; padding: 6px 12px; cursor: pointer;">🗑️</button>
                        </div>
                        <div class="letter-comments" id="comments-${msgId}" style="display: block;">
                            <div class="comments-list" id="comments-list-${msgId}"></div>
                            <div class="comment-input-area" id="comment-input-${msgId}" style="display: flex; gap: 8px; margin-top: 10px;">
                                <input type="text" class="comment-input" placeholder="写下你的评论..." onkeypress="handleCommentKeypress(event, ${msgId})" style="flex: 1; padding: 8px 12px; border: 1px solid #d4a574; border-radius: 20px; font-size: 0.85rem;">
                                <button class="comment-submit-btn" onclick="submitComment(${msgId})" style="padding: 8px 16px; background: var(--secondary); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 0.85rem;">发送</button>
                            </div>
                        </div>
                    </div>
                    <div class="expand-hint">点击收起</div>
                </div>
            `;
            container.insertBefore(newMsg, container.firstChild);
            updateDeleteButtonsVisibility();
        } else {
            alert(data.message || '提交失败，请稍后重试');
        }
    } catch (e) {
        console.error('Submit message error:', e);
        alert('提交失败，请稍后重试');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

// 监听留言内容字数变化
document.addEventListener('DOMContentLoaded', function() {
    const msgContent = document.getElementById('msgContent');
    if (msgContent) {
        msgContent.addEventListener('input', function() {
            const charCount = document.getElementById('charCount');
            if (charCount) {
                charCount.textContent = this.value.length;
            }
        });
    }
});

function previewMessageImage(input) {
    const preview = document.getElementById('msgImagePreview');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        preview.style.display = 'none';
    }
}

// ==================== AI 图片生成 ====================
let aiGeneratedImageUrl = null;
let aiRefImageBase64 = null;

function toggleAiImageGen() {
    const content = document.getElementById('aiImageGenContent');
    const toggle = document.getElementById('aiImageGenToggle');
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = '▲';
    } else {
        content.style.display = 'none';
        toggle.textContent = '▼';
    }
}

function previewAiRefImage(input) {
    const preview = document.getElementById('aiImgRefPreview');
    aiRefImageBase64 = null;
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
            // 保存base64用于API调用
            aiRefImageBase64 = e.target.result.split(',')[1];
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        preview.style.display = 'none';
    }
}

async function generateAiImage() {
    const prompt = document.getElementById('aiImgPrompt').value.trim();
    if (!prompt) {
        alert('请输入图片描述');
        return;
    }

    const btn = document.getElementById('aiImgGenBtn');
    const progress = document.getElementById('aiImgProgress');
    const preview = document.getElementById('aiImgPreview');

    btn.disabled = true;
    progress.style.display = 'block';
    preview.style.display = 'none';

    // 模拟进度
    let progressValue = 0;
    const progressBar = document.getElementById('aiImgProgressBar');
    const progressInterval = setInterval(() => {
        progressValue += Math.random() * 15;
        if (progressValue > 90) progressValue = 90;
        progressBar.style.width = progressValue + '%';
    }, 500);

    try {
        const res = await fetch('/api/ai_image/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({
                prompt: prompt,
                ref_image: aiRefImageBase64 || '',
                aspect_ratio: document.getElementById('aiImgAspect').value
            })
        });
        const data = await res.json();

        clearInterval(progressInterval);
        progressBar.style.width = '100%';

        if (data.success) {
            aiGeneratedImageUrl = data.url;
            document.getElementById('aiImgPreviewImg').src = aiGeneratedImageUrl;
            preview.style.display = 'block';
            document.getElementById('aiImgInsertBtn').disabled = false;
        } else {
            alert(data.message || '生成失败');
        }
    } catch (e) {
        clearInterval(progressInterval);
        alert('生成失败，请稍后重试');
        console.error(e);
    } finally {
        btn.disabled = false;
        setTimeout(() => {
            progress.style.display = 'none';
            progressBar.style.width = '0%';
        }, 1000);
    }
}

function insertAiImageToMsg() {
    if (!aiGeneratedImageUrl) return;
    // 将AI生成的图片URL设置到留言表单的图片输入
    const imgPreview = document.getElementById('msgImagePreview');
    imgPreview.src = aiGeneratedImageUrl;
    imgPreview.style.display = 'block';
    // 标记这是AI生成的图片，提交时特殊处理
    const msgForm = document.getElementById('messageForm');
    msgForm.dataset.aiImage = aiGeneratedImageUrl;
    // 清空AI生成区域
    cancelAiImage();
    alert('图片已插入留言，请补充留言内容后发送');
}

function cancelAiImage() {
    aiGeneratedImageUrl = null;
    aiRefImageBase64 = null;
    document.getElementById('aiImgPrompt').value = '';
    document.getElementById('aiImgRef').value = '';
    document.getElementById('aiImgRefPreview').style.display = 'none';
    document.getElementById('aiImgPreview').style.display = 'none';
    document.getElementById('aiImgInsertBtn').disabled = true;
    document.getElementById('aiImgProgress').style.display = 'none';
    document.getElementById('aiImgProgressBar').style.width = '0%';
}

// ==================== 省份城市联动 ====================
// 城市到省份的映射
const CITY_TO_PROVINCE = {
    '北京': 'beijing', '上海': 'shanghai', '天津': 'tianjin', '重庆': 'chongqing',
    '南京': 'jiangsu', '苏州': 'jiangsu', '无锡': 'jiangsu', '常州': 'jiangsu', '南通': 'jiangsu', '扬州': 'jiangsu', '徐州': 'jiangsu', '盐城': 'jiangsu',
    '杭州': 'zhejiang', '宁波': 'zhejiang', '温州': 'zhejiang', '嘉兴': 'zhejiang', '湖州': 'zhejiang', '绍兴': 'zhejiang', '金华': 'zhejiang', '台州': 'zhejiang',
    '广州': 'guangdong', '深圳': 'guangdong', '珠海': 'guangdong', '东莞': 'guangdong', '佛山': 'guangdong', '中山': 'guangdong', '惠州': 'guangdong', '汕头': 'guangdong',
    '成都': 'sichuan', '绵阳': 'sichuan', '德阳': 'sichuan', '南充': 'sichuan', '宜宾': 'sichuan', '自贡': 'sichuan', '攀枝花': 'sichuan',
    '武汉': 'hubei', '襄阳': 'hubei', '宜昌': 'hubei', '黄石': 'hubei', '十堰': 'hubei', '荆州': 'hubei', '荆门': 'hubei',
    '长沙': 'hunan', '株洲': 'hunan', '湘潭': 'hunan', '衡阳': 'hunan', '岳阳': 'hunan', '常德': 'hunan', '张家界': 'hunan',
    '郑州': 'henan', '洛阳': 'henan', '开封': 'henan', '南阳': 'henan', '新乡': 'henan', '安阳': 'henan',
    '济南': 'shandong', '青岛': 'shandong', '烟台': 'shandong', '威海': 'shandong', '潍坊': 'shandong', '淄博': 'shandong', '临沂': 'shandong',
    '石家庄': 'hebei', '保定': 'hebei', '唐山': 'hebei', '邯郸': 'hebei', '秦皇岛': 'hebei', '沧州': 'hebei',
    '西安': 'shaanxi', '咸阳': 'shaanxi', '宝鸡': 'shaanxi', '渭南': 'shaanxi', '延安': 'shaanxi',
    '沈阳': 'liaoning', '大连': 'liaoning', '鞍山': 'liaoning', '抚顺': 'liaoning', '锦州': 'liaoning', '丹东': 'liaoning',
    '长春': 'jilin', '吉林': 'jilin', '四平': 'jilin', '辽源': 'jilin', '通化': 'jilin',
    '哈尔滨': 'heilongjiang', '大庆': 'heilongjiang', '齐齐哈尔': 'heilongjiang', '牡丹江': 'heilongjiang',
    '福州': 'fujian', '厦门': 'fujian', '泉州': 'fujian', '漳州': 'fujian', '莆田': 'fujian',
    '南昌': 'jiangxi', '赣州': 'jiangxi', '九江': 'jiangxi', '宜春': 'jiangxi', '上饶': 'jiangxi',
    '昆明': 'yunnan', '曲靖': 'yunnan', '玉溪': 'yunnan', '大理': 'yunnan',
    '贵阳': 'guizhou', '遵义': 'guizhou', '安顺': 'guizhou', '六盘水': 'guizhou',
    '南宁': 'guangxi', '桂林': 'guangxi', '柳州': 'guangxi', '北海': 'guangxi', '梧州': 'guangxi',
    '合肥': 'anhui', '芜湖': 'anhui', '蚌埠': 'anhui', '淮南': 'anhui', '马鞍山': 'anhui',
    '太原': 'shanxi', '大同': 'shanxi', '运城': 'shanxi', '临汾': 'shanxi',
    '兰州': 'gansu', '天水': 'gansu', '白银': 'gansu', '酒泉': 'gansu',
    '乌鲁木齐': 'xinjiang', '克拉玛依': 'xinjiang', '石河子': 'xinjiang',
    '呼和浩特': 'neimenggu', '包头': 'neimenggu', '鄂尔多斯': 'neimenggu',
    '拉萨': 'xizang',
    '海口': 'hainan', '三亚': 'hainan',
    '台北': 'taiwan', '高雄': 'taiwan', '台中': 'taiwan'
};

function onProvinceChange() {
    // 用户选择省份后，不需要自动清空城市
    // 可以在这里添加其他联动逻辑
}

function autoDetectProvince() {
    const cityInput = document.getElementById('cityInput');
    const provinceSelect = document.getElementById('hometownSelect');
    if (!cityInput || !provinceSelect) return;

    const city = cityInput.value.trim();
    if (city && CITY_TO_PROVINCE[city]) {
        provinceSelect.value = CITY_TO_PROVINCE[city];
    }
}

// ==================== 通讯录编辑 ====================
async function loadStudentData() {
    if (!state.verified) return;

    try {
        const res = await fetch('/api/get_student');
        const data = await res.json();

        if (data.success) {
            state.currentStudent = data.student;

            // 更新全局用户对象，确保showLoggedView能获取完整数据
            window.currentUser = data.student;

            const form = document.getElementById('editForm');
            if (form) {
                const nameEl = document.getElementById('editStudentName');
                const idEl = document.getElementById('editStudentId');
                if (nameEl) nameEl.textContent = data.student.name;
                if (idEl) idEl.textContent = '学号: ' + data.student.id;

                form.querySelector('[name="phone"]').value = data.student.phone || '';
                form.querySelector('[name="hometown"]').value = data.student.hometown || '';
                form.querySelector('[name="city"]').value = data.student.city || '';
                form.querySelector('[name="district"]').value = data.student.district || '';
                form.querySelector('[name="note"]').value = data.student.note || '';
                form.querySelector('[name="custom_intro"]').value = data.student.custom_intro || '';
                form.querySelector('[name="hobby"]').value = data.student.hobby || '';
                form.querySelector('[name="dream"]').value = data.student.dream || '';
                form.querySelector('[name="industry"]').value = data.student.industry || '';
                form.querySelector('[name="company"]').value = data.student.company || '';
                form.querySelector('[name="weibo"]').value = data.student.weibo || '';
                form.querySelector('[name="xiaohongshu"]').value = data.student.xiaohongshu || '';
                form.querySelector('[name="douyin"]').value = data.student.douyin || '';

                // 更新头像预览
                const avatarPreview = document.getElementById('editAvatarPreview');
                const avatarInitial = document.getElementById('avatarInitial');
                if (data.student.avatar) {
                    if (avatarPreview) {
                        avatarPreview.innerHTML = `<img src="${data.student.avatar}" alt="avatar">`;
                    }
                } else {
                    if (avatarInitial) avatarInitial.textContent = data.student.name ? data.student.name[0] : '?';
                }
            }

            // 重新触发showLoggedView更新"我的"页面显示
            if (typeof showLoggedView === 'function') {
                showLoggedView(data.student);
            }
        }
    } catch (e) {
        console.error('Load student data failed:', e);
    }
}

function handleAvatarUpload(fileOrEvent) {
    let file;
    if (fileOrEvent && fileOrEvent.target) {
        file = fileOrEvent.target.files[0];
    } else {
        file = fileOrEvent;
    }
    if (!file) return;

    const progressEl = document.getElementById('avatarUploadProgress');
    if (progressEl) {
        progressEl.style.display = 'block';
        progressEl.classList.remove('upload-error');
        showUploadProgress(progressEl, 0);
    }

    const formData = new FormData();
    formData.append('file', file);

    uploadWithProgress('/api/upload_avatar', formData,
        (percent) => {
            if (progressEl) showUploadProgress(progressEl, percent);
        },
        (data) => {
            if (data.success) {
                if (progressEl) showUploadProgress(progressEl, 100);
                const avatarPreview = document.getElementById('editAvatarPreview');
                if (avatarPreview) {
                    avatarPreview.innerHTML = `<img src="${data.url}" alt="avatar" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                }
                const avatarInitial = document.getElementById('editAvatarInitial');
                if (avatarInitial) avatarInitial.textContent = '';
                setTimeout(() => {
                    alert('头像上传成功！');
                }, 300);
            } else {
                if (progressEl) {
                    showUploadError(progressEl, data.message || '上传失败');
                } else {
                    alert(data.message || '上传失败');
                }
            }
        },
        (err) => {
            if (progressEl) {
                showUploadError(progressEl, err);
            } else {
                alert('上传失败，请稍后重试');
            }
        }
    );
}

function showEditModal(studentId) {
    if (!state.verified) {
        showVerifyModal();
        return;
    }

    const modal = document.getElementById('editModal');
    if (modal) {
        modal.classList.add('active');
        loadStudentData();
    }
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) modal.classList.remove('active');
}

async function submitEdit(e) {
    e.preventDefault();

    const form = e.target;
    const phone = form.phone.value.trim();
    const hometown = form.hometown ? form.hometown.value.trim() : '';
    const city = form.city.value.trim();
    const district = form.district.value.trim();
    const note = form.note.value.trim();
    const custom_intro = form.custom_intro.value.trim();
    const hobby = form.hobby.value.trim();
    const dream = form.dream.value.trim();
    const industry = form.industry ? form.industry.value.trim() : '';
    const company = form.company ? form.company.value.trim() : '';
    const weibo = form.weibo ? form.weibo.value.trim() : '';
    const xiaohongshu = form.xiaohongshu ? form.xiaohongshu.value.trim() : '';
    const douyin = form.douyin ? form.douyin.value.trim() : '';

    try {
        const res = await fetch('/api/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, hometown, city, district, note, custom_intro, hobby, dream, industry, company, weibo, xiaohongshu, douyin })
        });

        const data = await res.json();

        if (data.success) {
            alert('更新成功！');
            closeEditModal();
            window.location.reload();
        } else {
            alert(data.message || '更新失败');
        }
    } catch (e) {
        alert('更新失败，请稍后重试');
    }
}

// ==================== 图片上传（带进度） ====================
function uploadWithProgress(url, formData, onProgress, onSuccess, onError) {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress(percent);
        }
    });

    xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            try {
                const data = JSON.parse(xhr.responseText);
                onSuccess(data);
            } catch (e) {
                onError('解析响应失败');
            }
        } else {
            onError('上传失败: ' + xhr.status);
        }
    });

    xhr.addEventListener('error', () => {
        onError('网络错误，请检查连接');
    });

    xhr.addEventListener('timeout', () => {
        onError('上传超时，请重试');
    });

    xhr.open('POST', url);
    xhr.withCredentials = true;
    xhr.send(formData);
}

function showUploadProgress(progressEl, percent) {
    const bar = progressEl.querySelector('.upload-progress-bar');
    const text = progressEl.querySelector('.upload-progress-text');
    if (bar) bar.style.width = percent + '%';
    if (text) text.textContent = percent + '%';
}

function showUploadError(progressEl, message) {
    const text = progressEl.querySelector('.upload-progress-text');
    if (text) text.textContent = message;
    progressEl.classList.add('upload-error');
}

// ==================== 图片上传 ====================
function showUploadModal() {
    if (!state.verified) {
        showVerifyModal();
        return;
    }

    const modal = document.getElementById('uploadModal');
    if (modal) modal.classList.add('active');
}

function closeUploadModal() {
    const modal = document.getElementById('uploadModal');
    if (modal) modal.classList.remove('active');
    // 清除待上传的文件
    state.pendingUploadFile = null;
}

function handleImageUpload(file) {
    if (!file) return;

    const yearSelect = document.getElementById('photoYear');
    const year = yearSelect ? yearSelect.value : '';

    if (!year) {
        // 年份未选择，保存文件等待用户选择年份
        state.pendingUploadFile = file;
        alert('请选择照片年份，选择后将自动上传');
        return;
    }

    // 年份已选择，直接上传
    doUpload(file, year);
}

function doUpload(file, year) {
    const progressEl = document.getElementById('uploadProgress');
    if (!progressEl) return;

    progressEl.style.display = 'block';
    progressEl.classList.remove('upload-error');
    showUploadProgress(progressEl, 0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('year', year);

    uploadWithProgress('/api/upload_image', formData,
        (percent) => {
            showUploadProgress(progressEl, percent);
        },
        (data) => {
            if (data.success) {
                state.pendingUploadFile = null;
                showUploadProgress(progressEl, 100);
                setTimeout(() => {
                    alert('上传成功！');
                    closeUploadModal();
                    window.location.reload();
                }, 300);
            } else {
                showUploadError(progressEl, data.message || '上传失败');
            }
        },
        (err) => {
            showUploadError(progressEl, err);
        }
    );
}

// 监听年份选择变化，自动上传待上传的文件
document.addEventListener('DOMContentLoaded', () => {
    const yearSelect = document.getElementById('photoYear');
    if (yearSelect) {
        yearSelect.addEventListener('change', function() {
            if (state.pendingUploadFile && this.value) {
                doUpload(state.pendingUploadFile, this.value);
            }
        });
    }
});

// ==================== 视频 ====================
function showVideoModal(url, title) {
    // 暂停背景音乐
    if (state.audio && !state.audio.paused) {
        sessionStorage.setItem('audioWasPlaying', 'true');
        state.audio.pause();
    } else {
        sessionStorage.setItem('audioWasPlaying', 'false');
    }

    const modal = document.getElementById('videoModal');
    if (modal) {
        if (url.startsWith('/static/')) {
            modal.innerHTML = `
                <button class="video-modal-close" onclick="closeVideoModal()">✕</button>
                <div class="video-modal-content" style="background: #000; display: flex; align-items: center; justify-content: center;">
                    <video controls autoplay style="max-width: 100%; max-height: 80vh;">
                        <source src="${url}" type="video/mp4">
                        您的浏览器不支持视频播放
                    </video>
                </div>
            `;
        } else {
            let embedUrl = url;
            if (url.includes('v.youku.com')) {
                const match = url.match(/id_(\w+)\.html/);
                if (match) {
                    embedUrl = `https://player.youku.com/embed/${match[1]}`;
                }
            } else if (url.includes('v.qq.com')) {
                embedUrl = url.replace('v.qq.com/x/page/', 'v.qq.com/iframe/player.html?vid=');
            } else if (url.includes('bilibili.com')) {
                embedUrl = url.replace('bilibili.com/video/', 'player.bilibili.com/player.html?bvid=');
            }
            modal.innerHTML = `
                <button class="video-modal-close" onclick="closeVideoModal()">✕</button>
                <div class="video-modal-content">
                    <iframe src="${embedUrl}" allowfullscreen></iframe>
                </div>
            `;
        }
        modal.classList.add('active');
    }
}

function closeVideoModal() {
    // 恢复背景音乐（如果之前在播放）
    const wasPlaying = sessionStorage.getItem('audioWasPlaying') === 'true';
    if (wasPlaying && state.audio && state.audio.paused) {
        state.audio.play().catch(() => {});
    }

    const modal = document.getElementById('videoModal');
    if (modal) {
        modal.classList.remove('active');
        modal.innerHTML = `
            <button class="video-modal-close" onclick="closeVideoModal()">✕</button>
            <div class="video-modal-content">
                <iframe allowfullscreen></iframe>
            </div>
        `;
    }
}

function showAddVideoModal() {
    if (!state.verified) {
        showVerifyModal();
        return;
    }

    const modal = document.getElementById('addVideoModal');
    if (modal) modal.classList.add('active');
}

function closeAddVideoModal() {
    const modal = document.getElementById('addVideoModal');
    if (modal) modal.classList.remove('active');
}

async function submitVideo(e) {
    e.preventDefault();

    const title = document.getElementById('videoTitle').value.trim();
    const url = document.getElementById('videoUrl').value.trim();

    if (!title || !url) {
        alert('请填写标题和链接');
        return;
    }

    try {
        const res = await fetch('/api/add_video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, url })
        });

        const data = await res.json();

        if (data.success) {
            alert('添加成功！');
            closeAddVideoModal();
            document.getElementById('videoTitle').value = '';
            document.getElementById('videoUrl').value = '';
            window.location.reload();
        } else {
            alert(data.message || '添加失败');
        }
    } catch (e) {
        alert('添加失败，请稍后重试');
    }
}

// ==================== 最新动态轮播 ====================
let activityCurrentPage = 0;
let activityPageSize = 1;
let activityAutoScrollInterval = null;
let activityAutoScrollPaused = false;
let activityResumeTimer = null;

function getActivityPageSize() {
    return 1;
}

function pauseActivityAutoScroll() {
    if (activityAutoScrollPaused) return;
    activityAutoScrollPaused = true;
    if (activityAutoScrollInterval) {
        clearInterval(activityAutoScrollInterval);
        activityAutoScrollInterval = null;
    }
}

function resumeActivityAutoScroll() {
    if (!activityAutoScrollPaused) return;
    activityAutoScrollPaused = false;
    const carousel = document.getElementById('activityCarousel');
    if (!carousel) return;
    const items = carousel.querySelectorAll('.carousel-item');
    const totalPages = Math.ceil(items.length / activityPageSize);
    if (totalPages > 1) {
        activityAutoScrollInterval = setInterval(() => {
            if (totalPages > 1) {
                activityCurrentPage = (activityCurrentPage + 1) % totalPages;
                goToActivityPage(activityCurrentPage);
            }
        }, 4000);
    }
}

function scheduleResumeActivityAutoScroll() {
    if (activityResumeTimer) {
        clearTimeout(activityResumeTimer);
    }
    pauseActivityAutoScroll();
    activityResumeTimer = setTimeout(() => {
        resumeActivityAutoScroll();
        activityResumeTimer = null;
    }, 10000); // 10秒后恢复
}

function initActivityCarousel() {
    const carousel = document.getElementById('activityCarousel');
    const dotsContainer = document.getElementById('activityDots');
    if (!carousel || !dotsContainer) return;

    activityPageSize = getActivityPageSize();
    activityCurrentPage = 0;
    activityAutoScrollPaused = false;

    const items = carousel.querySelectorAll('.carousel-item');
    const totalPages = Math.ceil(items.length / activityPageSize);

    // Create dots
    dotsContainer.innerHTML = '';
    for (let i = 0; i < totalPages; i++) {
        const dot = document.createElement('span');
        dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
        dot.onclick = () => {
            goToActivityPage(i);
            scheduleResumeActivityAutoScroll();
        };
        dotsContainer.appendChild(dot);
    }

    // Clear existing interval
    if (activityAutoScrollInterval) {
        clearInterval(activityAutoScrollInterval);
    }

    // Auto-scroll every 4 seconds
    activityAutoScrollInterval = setInterval(() => {
        if (totalPages > 1) {
            activityCurrentPage = (activityCurrentPage + 1) % totalPages;
            goToActivityPage(activityCurrentPage);
        }
    }, 4000);

    // 用户滑动/拖动时暂停
    let touchStartX = 0;
    let touchEndX = 0;

    carousel.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        pauseActivityAutoScroll();
    }, { passive: true });

    carousel.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        // 只有在滑动距离较大时才暂停
        if (Math.abs(touchEndX - touchStartX) > 30) {
            scheduleResumeActivityAutoScroll();
        } else {
            resumeActivityAutoScroll();
        }
    }, { passive: true });

    // 鼠标拖动也暂停
    let mouseDown = false;
    let mouseStartX = 0;

    carousel.addEventListener('mousedown', (e) => {
        mouseDown = true;
        mouseStartX = e.clientX;
        pauseActivityAutoScroll();
    });

    carousel.addEventListener('mouseup', (e) => {
        if (mouseDown) {
            mouseDown = false;
            if (Math.abs(e.clientX - mouseStartX) > 30) {
                scheduleResumeActivityAutoScroll();
            } else {
                resumeActivityAutoScroll();
            }
        }
    });

    carousel.addEventListener('mouseleave', (e) => {
        if (mouseDown) {
            mouseDown = false;
            scheduleResumeActivityAutoScroll();
        }
    });
}

function goToActivityPage(page) {
    const carousel = document.getElementById('activityCarousel');
    const dots = document.querySelectorAll('#activityDots .carousel-dot');
    if (!carousel) return;

    activityPageSize = getActivityPageSize();
    const items = carousel.querySelectorAll('.carousel-item');
    const totalPages = Math.ceil(items.length / activityPageSize);
    activityCurrentPage = page;

    // Use scrollLeft for smooth scrolling
    const itemWidth = items[0]?.offsetWidth || 0;
    const scrollAmount = page * activityPageSize * itemWidth;
    carousel.scrollTo({ left: scrollAmount, behavior: 'smooth' });

    dots.forEach((dot, i) => {
        dot.classList.toggle('active', i === page);
    });
}

function scrollActivity(direction) {
    const carousel = document.getElementById('activityCarousel');
    if (!carousel) return;

    activityPageSize = getActivityPageSize();
    const items = carousel.querySelectorAll('.carousel-item');
    const totalPages = Math.ceil(items.length / activityPageSize);

    activityCurrentPage = (activityCurrentPage + direction + totalPages) % totalPages;
    goToActivityPage(activityCurrentPage);
    scheduleResumeActivityAutoScroll();
}

function handleActivityClick(element) {
    const type = element.dataset.type;
    const actor = element.dataset.actor;

    if (type === 'profile_update') {
        // 跳转到通讯录，并滚动到该同学卡片
        window.location.href = '/txl#student-' + encodeURIComponent(actor);
    } else if (type === 'message') {
        // 跳转到留言板，并滚动到该留言
        window.location.href = '/lyb#msg-' + element.dataset.msgId;
    } else if (type === 'photo') {
        // 跳转到媒体栏目，并显示该图片灯箱
        const imgUrl = element.dataset.imgUrl;
        window.location.href = '/media#img-' + encodeURIComponent(element.dataset.imgName);
    } else if (type === 'video') {
        // 跳转到媒体栏目
        window.location.href = '/media';
    } else if (type === 'voice_shout') {
        // 跳转到通讯录，并滚动到被喊话人的卡片
        const targetName = element.dataset.targetName;
        if (targetName) {
            window.location.href = '/txl#student-' + encodeURIComponent(targetName);
        } else {
            window.location.href = '/txl';
        }
    }
}

function copyPhone(phone) {
    // 创建临时输入框来复制
    const input = document.createElement('input');
    input.value = phone;
    input.style.position = 'fixed';
    input.style.opacity = '0';
    input.style.zIndex = '-9999';
    document.body.appendChild(input);
    input.select();
    input.setSelectionRange(0, 99999);

    let success = false;
    try {
        success = document.execCommand('copy');
    } catch (e) {
        success = false;
    }
    document.body.removeChild(input);

    // 显示Toast提示
    showToast(success ? '电话号码已复制' : '复制失败，请长按复制');
}

function showToast(message) {
    // 移除已存在的toast
    const existingToast = document.querySelector('.copy-toast');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = 'copy-toast';
    toast.textContent = message;
    toast.style.cssText = 'position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.8);color:#fff;padding:10px 20px;border-radius:20px;font-size:14px;z-index:9999;opacity:0;transition:opacity 0.3s';
    document.body.appendChild(toast);

    // 动画效果
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// ==================== 灯箱 ====================
function showLightbox(src) {
    const lightbox = document.getElementById('lightbox');
    const img = document.getElementById('lightboxImg');

    if (lightbox && img) {
        img.src = src;
        lightbox.classList.add('active');
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (lightbox) lightbox.classList.remove('active');
}

// ==================== 搜索 ====================
function filterStudents(query) {
    const cards = document.querySelectorAll('.student-card');
    const lowerQuery = query.toLowerCase();

    cards.forEach(card => {
        const name = card.dataset.name || '';
        const hometown = card.dataset.hometown || '';

        const match = name.toLowerCase().includes(lowerQuery) ||
                     hometown.toLowerCase().includes(lowerQuery);

        card.style.display = match ? '' : 'none';
    });
}

// ==================== 工具函数 ====================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 移动端导航 ====================
function toggleMobileNav() {
    const navLinks = document.getElementById('navLinks');
    const toggle = document.getElementById('navToggleBtn');

    if (navLinks && toggle) {
        navLinks.classList.toggle('active');
        toggle.classList.toggle('active');
        console.log('Toggle nav:', navLinks.classList.contains('active'));
    }
}

// 页面加载后绑定事件
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('navToggleBtn');
    if (toggle) {
        toggle.addEventListener('click', toggleMobileNav);
        console.log('Nav toggle button event listener added');
    }
});

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    checkVerifyStatus().then(() => {
        updateDeleteButtonsVisibility();
    });
    initActivityCarousel();

    const navToggle = document.querySelector('.nav-toggle');
    if (navToggle) {
        navToggle.addEventListener('click', toggleMobileNav);
    }

    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterStudents(e.target.value);
        });
    }

    const msgContent = document.getElementById('msgContent');
    const charCount = document.getElementById('charCount');
    if (msgContent && charCount) {
        msgContent.addEventListener('input', () => {
            charCount.textContent = `${msgContent.value.length}/500`;
        });
    }

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active, .lightbox.active, .video-modal.active').forEach(el => {
                el.classList.remove('active');
            });
        }
    });

    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.classList.add('page-enter');
        requestAnimationFrame(() => {
            mainContent.classList.add('page-enter-active');
        });
    }

    // 初始化最新动态滚动
    initActivityScroll();

    // Hash导航：滚动到指定元素
    handleHashNavigation();
});

// Hash导航处理
function handleHashNavigation() {
    const hash = window.location.hash;
    if (!hash) return;

    const targetId = hash.substring(1); // 去掉#号
    const targetEl = document.getElementById(targetId);

    if (targetEl) {
        // 延迟一下确保页面已完全渲染
        setTimeout(() => {
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // 高亮显示一下
            targetEl.classList.add('highlight');
            setTimeout(() => targetEl.classList.remove('highlight'), 2000);

            // 如果是图片元素，显示灯箱
            if (targetId.startsWith('img-') && typeof showLightbox === 'function') {
                const imgEl = targetEl.querySelector('img');
                if (imgEl) {
                    showLightbox(imgEl.src);
                }
            }
        }, 100);
    }
}

// ==================== 最新动态滚动 ====================
let currentActivityPage = 0;
const ACTIVITIES_PER_PAGE = 5;
let activityScrollInterval = null;

function initActivityScroll() {
    const wrapper = document.getElementById('activityScrollWrapper');
    const content = document.getElementById('activityScrollContent');
    const indicators = document.getElementById('activityIndicators');

    if (!wrapper || !content) return;

    const items = content.querySelectorAll('.message-item');
    const totalPages = Math.ceil(items.length / ACTIVITIES_PER_PAGE);

    if (totalPages <= 1) {
        if (indicators) indicators.style.display = 'none';
        return;
    }

    // 设置wrapper高度为5条的高度
    const itemHeight = items[0] ? items[0].offsetHeight + 16 : 80; // 包含margin
    wrapper.style.maxHeight = (itemHeight * ACTIVITIES_PER_PAGE) + 'px';

    // 创建指示器
    if (indicators) {
        indicators.innerHTML = '';
        for (let i = 0; i < totalPages; i++) {
            const dot = document.createElement('div');
            dot.className = 'activity-indicator' + (i === 0 ? ' active' : '');
            dot.onclick = () => scrollToActivityPage(i);
            indicators.appendChild(dot);
        }
    }

    // 自动滚动
    if (activityScrollInterval) clearInterval(activityScrollInterval);
    activityScrollInterval = setInterval(() => {
        currentActivityPage = (currentActivityPage + 1) % totalPages;
        scrollToActivityPage(currentActivityPage);
    }, 3000);
}

function scrollToActivityPage(page) {
    const content = document.getElementById('activityScrollContent');
    const indicators = document.getElementById('activityIndicators');
    if (!content) return;

    const items = content.querySelectorAll('.message-item');
    if (items.length === 0) return;

    const itemHeight = items[0].offsetHeight + 16;
    const offset = page * ACTIVITIES_PER_PAGE * itemHeight;
    content.style.transform = `translateY(-${offset}px)`;

    // 更新指示器
    if (indicators) {
        const dots = indicators.querySelectorAll('.activity-indicator');
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === page);
        });
    }

    currentActivityPage = page;
}

// ==================== 通知系统 ====================
async function loadNotificationCount() {
    console.log('[DEBUG] loadNotificationCount 被调用');
    if (!window.currentUser) {
        console.log('[DEBUG] loadNotificationCount: window.currentUser为空');
        return;
    }

    try {
        const res = await fetch('/api/notifications/count', { credentials: 'same-origin' });
        const data = await res.json();
        console.log('[DEBUG] loadNotificationCount 返回:', data);
        const tabBadge = document.getElementById('tabNotificationBadge');
        if (tabBadge) {
            if (data.count > 0) {
                tabBadge.textContent = data.count > 99 ? '99+' : data.count;
                tabBadge.style.display = 'flex';
            } else {
                tabBadge.style.display = 'none';
            }
        }
    } catch (err) {
        console.error('[DEBUG] loadNotificationCount error:', err);
    }
}

async function loadNotifications() {
    console.log('[DEBUG] loadNotifications 被调用');
    // 先检查登录状态
    try {
        const verifyRes = await fetch('/api/check_verify', { credentials: 'same-origin' });
        const verifyData = await verifyRes.json();
        if (!verifyData.verified) {
            const aboutList = document.getElementById('notificationListAbout');
            if (aboutList) {
                aboutList.innerHTML = '<p style="color: var(--text-light); text-align: center; padding: 1rem;">请先登录</p>';
            }
            return;
        }

        const res = await fetch('/api/notifications', { credentials: 'same-origin' });
        const data = await res.json();
        try {
            const list = document.getElementById('notificationList');
            if (list) {
                renderNotificationList(list, data.notifications || [], 1);
            }

            const aboutList = document.getElementById('notificationListAbout');
            if (aboutList) {
                renderNotificationList(aboutList, data.notifications || [], 1);
            }
        } catch (e) {
            console.error('[DEBUG] renderNotificationList error:', e);
            const aboutList = document.getElementById('notificationListAbout');
            if (aboutList) {
                aboutList.innerHTML = '<p style="color: var(--text-light); text-align: center; padding: 1rem;">通知加载失败</p>';
            }
        }
    } catch (err) {
        console.error('[DEBUG] loadNotifications error:', err);
        const aboutList = document.getElementById('notificationListAbout');
        if (aboutList) {
            aboutList.innerHTML = '<p style="color: var(--text-light); text-align: center; padding: 1rem;">通知加载失败</p>';
        }
    }
}

const NOTIFICATION_PAGE_SIZE = 3;
let notificationCurrentPage = 1;
let notificationAllUnread = [];

function renderNotificationList(listElement, notifications, page) {
    if (!listElement) return;

    // 只显示未读通知
    notificationAllUnread = (notifications || []).filter(n => !n.is_read);

    if (notificationAllUnread.length > 0) {
        // 分页计算
        const start = (page - 1) * NOTIFICATION_PAGE_SIZE;
        const end = start + NOTIFICATION_PAGE_SIZE;
        const pageNotifications = notificationAllUnread.slice(start, end);
        const totalPages = Math.ceil(notificationAllUnread.length / NOTIFICATION_PAGE_SIZE);

        listElement.innerHTML = pageNotifications.map(n => {
            const icon = getNotificationIcon(n.type);
            const time = formatNotificationTime(n.created_time);
            const refId = typeof n.ref_id === 'string' ? `'${n.ref_id}'` : n.ref_id;
            return `
                <div class="notification-item unread" data-notif-id="${n.id}" onclick="handleNotificationClick(${n.id}, '${n.type}', ${refId}, '${n.target_name || ''}', '${n.media_type || ''}')">
                    <div class="notification-item-icon notification-type-${n.type}">${icon}</div>
                    <div class="notification-item-content">
                        <div class="notification-item-text">${escapeHtml(n.content)}</div>
                        <div class="notification-item-time">${time}</div>
                    </div>
                </div>
            `;
        }).join('');

        // 渲染分页控件
        const pagination = document.getElementById('notificationPagination');
        if (pagination) {
            if (totalPages > 1) {
                pagination.style.display = 'flex';
                let paginationHtml = '';
                if (page > 1) {
                    paginationHtml += `<button onclick="goToNotificationPage(${page - 1})" style="background: var(--bg-dark); border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer;">上一页</button>`;
                }
                paginationHtml += `<span style="padding: 0.4rem 0.8rem; color: var(--text-light); font-size: 0.85rem;">${page}/${totalPages}</span>`;
                if (page < totalPages) {
                    paginationHtml += `<button onclick="goToNotificationPage(${page + 1})" style="background: var(--bg-dark); border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer;">下一页</button>`;
                }
                pagination.innerHTML = paginationHtml;
            } else {
                pagination.style.display = 'none';
            }
        }

        // 显示"全部已读"按钮
        const actions = document.getElementById('notificationActions');
        if (actions) actions.style.display = 'flex';
    } else {
        listElement.innerHTML = '<div class="notification-empty">暂无未读通知</div>';
        const pagination = document.getElementById('notificationPagination');
        if (pagination) pagination.style.display = 'none';
        const actions = document.getElementById('notificationActions');
        if (actions) actions.style.display = 'none';
    }
}

function goToNotificationPage(page) {
    notificationCurrentPage = page;
    const aboutList = document.getElementById('notificationListAbout');
    if (aboutList) {
        renderNotificationList(aboutList, notificationAllUnread, page);
    }
}

function getNotificationIcon(type) {
    const icons = {
        'comment': '💬',
        'like': '❤️',
        'voice_shout': '🎤'
    };
    return icons[type] || '🔔';
}

function formatNotificationTime(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr.replace(/\./g, '-'));
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return timeStr.substring(0, 10);
}

function toggleNotificationDropdown() {
    const dropdown = document.getElementById('notificationDropdown');
    if (!dropdown) return;

    dropdown.classList.toggle('active');

    if (dropdown.classList.contains('active')) {
        loadNotifications();
    }
}

function handleNotificationClick(notifId, type, refId, targetName, mediaType) {
    // 标记为已读
    markNotificationRead(notifId);

    // 根据类型跳转到对应页面
    if (type === 'comment') {
        // 跳转到留言板
        window.location.href = '/lyb#msg-' + refId;
    } else if (type === 'like') {
        if (mediaType === 'photo' || mediaType === 'video') {
            // 跳转到媒体相册对应标签页
            window.location.href = '/media?highlight=' + encodeURIComponent(refId);
        } else {
            // 跳转到留言板
            window.location.href = '/lyb#msg-' + refId;
        }
    } else if (type === 'voice_shout') {
        // 跳转到通讯录自己的卡片，并传递锚点参数
        if (targetName) {
            window.location.href = '/txl?highlight=' + encodeURIComponent(targetName) + '#student-' + encodeURIComponent(targetName);
        } else {
            window.location.href = '/txl';
        }
    }

    // 关闭下拉
    const dropdown = document.getElementById('notificationDropdown');
    if (dropdown) dropdown.classList.remove('active');
}

function markNotificationRead(notifId) {
    fetch('/api/notifications/mark_read', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: notifId })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            loadNotificationCount();
            // 更新UI
            const item = document.querySelector(`.notification-item[data-notif-id="${notifId}"]`);
            if (item) item.classList.remove('unread');
        }
    });
}

function markAllNotificationsRead() {
    fetch('/api/notifications/mark_read', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ all: true })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            loadNotificationCount();
            // 重新加载通知列表
            loadNotifications();
        }
    });
}

// 点击外部关闭通知下拉
document.addEventListener('click', (e) => {
    const container = document.getElementById('notificationContainer');
    const dropdown = document.getElementById('notificationDropdown');
    if (container && dropdown && !container.contains(e.target)) {
        dropdown.classList.remove('active');
    }
});

// 导出给全局使用
window.showVerifyModal = showVerifyModal;
window.closeVerifyModal = closeVerifyModal;
window.submitVerify = submitVerify;
window.logout = logout;
window.showEditModal = showEditModal;
window.closeEditModal = closeEditModal;
window.submitEdit = submitEdit;
window.submitMessage = submitMessage;
window.showUploadModal = showUploadModal;
window.closeUploadModal = closeUploadModal;
window.handleImageUpload = handleImageUpload;
window.handleAvatarUpload = handleAvatarUpload;
window.updateMessageInputUI = updateMessageInputUI;
window.showVideoModal = showVideoModal;
window.closeVideoModal = closeVideoModal;
window.showAddVideoModal = showAddVideoModal;
window.closeAddVideoModal = closeAddVideoModal;
window.submitVideo = submitVideo;
window.showLightbox = showLightbox;
window.closeLightbox = closeLightbox;
window.filterStudents = filterStudents;
window.toggleMobileNav = toggleMobileNav;
window.previewMessageImage = previewMessageImage;
window.onProvinceChange = onProvinceChange;
window.autoDetectProvince = autoDetectProvince;
window.copyPhone = copyPhone;
window.handleActivityClick = handleActivityClick;
window.handleHashNavigation = handleHashNavigation;
window.deleteMessage = deleteMessage;
window.updateDeleteButtonsVisibility = updateDeleteButtonsVisibility;
window.toggleNotificationDropdown = toggleNotificationDropdown;
window.markAllNotificationsRead = markAllNotificationsRead;
window.handleNotificationClick = handleNotificationClick;

// ==================== 返回顶部功能 ====================
let backToTopVisible = false;

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleScroll() {
    const backToTopBtn = document.getElementById('backToTopBtn');
    const pageEndMsg = document.getElementById('pageEndMessage');
    if (!backToTopBtn) return;

    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight;
    const clientHeight = document.documentElement.clientHeight;

    // 显示/隐藏返回顶部按钮
    if (scrollTop > 300) {
        backToTopBtn.classList.add('visible');
    } else {
        backToTopBtn.classList.remove('visible');
    }

    // 显示/隐藏页面底部提示
    if (pageEndMsg) {
        if (scrollTop + clientHeight >= scrollHeight - 50) {
            pageEndMsg.classList.add('visible');
        } else {
            pageEndMsg.classList.remove('visible');
        }
    }
}

window.scrollToTop = scrollToTop;

// 监听滚动事件
window.addEventListener('scroll', handleScroll);

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    handleScroll();
});
