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