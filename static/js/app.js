document.addEventListener('DOMContentLoaded', function () {
    console.log("Hệ thống khởi động...");

    // --- HÀM TRỢ GIÚP ---
    function updateToggleState(group, type) {
        if (!group) return;
        const buttons = group.querySelectorAll('.toggle-btn');
        const hiddenInput = group.querySelector('input[name="loan_type"]') || group.querySelector('input[name="transaction_type"]');
        buttons.forEach(btn => btn.classList.toggle('active', btn.dataset.type === type));
        if (hiddenInput) hiddenInput.value = type;
    }

    // --- 1. LOGIC SIDEBAR ---
    const parent = document.getElementById('finance-parent');
    const submenu = document.getElementById('finance-submenu');
    if (parent && submenu) {
        parent.addEventListener('click', () => {
            parent.classList.toggle('open');
            submenu.classList.toggle('open');
            submenu.style.height = submenu.classList.contains('open') ? submenu.scrollHeight + "px" : "0";
        });
    }

    // --- 2. LOGIC MODAL & EDIT (THU CHI) ---
    const txModal = document.getElementById('transaction-modal');
    const openTxBtn = document.getElementById('open-transaction-modal');

    if (txModal) {
        const txForm = txModal.querySelector('form');
        if (openTxBtn) {
            openTxBtn.addEventListener('click', () => {
                txModal.querySelector('.modal-header').childNodes[0].nodeValue = 'Thêm giao dịch mới';
                txForm.action = '/add-transaction';
                txForm.reset();
                updateToggleState(txModal.querySelector('.toggle-group'), 'income');
                txModal.style.display = 'flex';
            });
        }
        document.querySelectorAll('.btn-edit-tx').forEach(btn => {
            btn.addEventListener('click', function () {
                txModal.querySelector('.modal-header').childNodes[0].nodeValue = "Sửa giao dịch";
                txForm.action = this.dataset.action;
                txForm.amount.value = this.dataset.amount;
                txForm.description.value = this.dataset.desc;
                txForm.category_id.value = this.dataset.catid;
                txForm.date.value = this.dataset.date;
                updateToggleState(txModal.querySelector('.toggle-group'), this.dataset.type);
                txModal.style.display = 'flex';
            });
        });
    }

    // --- 3. LOGIC MODAL & EDIT (VAY NỢ) ---
    const dlModal = document.getElementById('debt-loan-modal');
    const openDlBtn = document.getElementById('open-debt-loan-modal');

    if (dlModal) {
        const dlForm = dlModal.querySelector('form');
        if (openDlBtn) {
            openDlBtn.addEventListener('click', () => {
                dlModal.querySelector('.modal-header').childNodes[0].nodeValue = 'Thêm vay/nợ mới';
                dlForm.action = '/add-debt-loan';
                dlForm.reset();
                updateToggleState(dlModal.querySelector('.toggle-group'), 'loan-out');
                dlModal.style.display = 'flex';
            });
        }
        document.querySelectorAll('.btn-edit-dl').forEach(btn => {
            btn.addEventListener('click', function () {
                dlModal.querySelector('.modal-header').childNodes[0].nodeValue = "Sửa khoản vay/nợ";
                dlForm.action = this.dataset.action;
                dlForm.person.value = this.dataset.person;
                dlForm.total_amount.value = this.dataset.total;
                dlForm.paid_amount.value = this.dataset.paid;
                dlForm.description.value = this.dataset.desc;
                dlForm.start_date.value = this.dataset.date;
                updateToggleState(dlModal.querySelector('.toggle-group'), this.dataset.type);
                dlModal.style.display = 'flex';
            });
        });
    }

    // --- 4. ĐÓNG MODAL ---
    document.querySelectorAll('.modal-close, .btn-cancel').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            if (txModal) txModal.style.display = 'none';
            if (dlModal) dlModal.style.display = 'none';
        });
    });

    // --- 5. LOGIC CHATBOT AI ---
    const floatBtn = document.getElementById('ai-float-button');
const chatWin = document.getElementById('ai-chat-window');
const closeChat = document.getElementById('close-chat');
const sendBtn = document.getElementById('btn-ai-send');
const aiInput = document.getElementById('ai-chat-input');
const chatContent = document.getElementById('ai-chat-content');

if (floatBtn && chatWin) {
    floatBtn.onclick = function (e) {
        e.stopPropagation();
        chatWin.classList.toggle('ai-chat-hidden');
    };

    if (closeChat) {
        closeChat.onclick = function (e) {
            e.stopPropagation();
            chatWin.classList.add('ai-chat-hidden');
        };
    }

    async function handleAISend() {
        const text = aiInput.value.trim();
        if (!text) return;

        // Hiển thị tin nhắn của bạn
        chatContent.innerHTML += `
            <div style="text-align:right; margin-bottom:10px;">
                <span style="background:#6366f1; color:white; padding:8px 12px; border-radius:12px; display:inline-block; max-width:80%; word-wrap:break-word;">
                    ${text}
                </span>
            </div>`;
        
        aiInput.value = '';
        chatContent.scrollTop = chatContent.scrollHeight;

        try {
            const response = await fetch('/ai-chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();

            // Hiển thị câu trả lời của AI
            chatContent.innerHTML += `
                <div style="margin-bottom:10px;">
                    <span style="background:#e2e8f0; color:#1e293b; padding:8px 12px; border-radius:12px; display:inline-block; max-width:80%; white-space: pre-line;">
                        ${data.reply}
                    </span>
                </div>`;
            
            chatContent.scrollTop = chatContent.scrollHeight;

            if (data.status === 'success' && !text.includes('tổng kết')) {
                console.log("Dữ liệu đã được lưu thành công vào Database.");
            }

        } catch (e) { 
            console.error("Lỗi kết nối AI:", e);
            chatContent.innerHTML += `<div style="color:red; font-size:12px; margin-bottom:10px;">Lỗi: Không thể kết nối máy chủ.</div>`;
        }
    }

    if (sendBtn) sendBtn.onclick = handleAISend;
    if (aiInput) {
        aiInput.onkeypress = (e) => { 
            if (e.key === 'Enter') {
                e.preventDefault(); 
                handleAISend(); 
            }
        };
    }
}
    // --- 6. TOGGLE & ĐĂNG XUẤT ---
    document.querySelectorAll('.toggle-group').forEach(group => {
        group.addEventListener('click', e => {
            if (e.target.classList.contains('toggle-btn')) updateToggleState(group, e.target.dataset.type);
        });
    });

    const logoutBtn = document.querySelector('.btn-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            if (!confirm('Bạn có chắc chắn muốn đăng xuất?')) e.preventDefault();
            else window.location.href = '/logout';
        });
    }
});