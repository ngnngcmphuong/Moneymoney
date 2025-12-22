document.addEventListener('DOMContentLoaded', function () {

  // Hàm hỗ trợ để cập nhật trạng thái toggle (Thu/Chi hoặc Cho vay/Vay nợ)
  function updateToggleState(group, type) {
    const buttons = group.querySelectorAll('.toggle-btn');
    const hiddenInput = 
      group.querySelector('input[name="loan_type"]') ||
      group.querySelector('input[name="transaction_type"]');        
    
    buttons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.type === type);
    });

    if (hiddenInput) {
      hiddenInput.value = type;
    }
  }

  // ======================================================
  // 1. Logic cho sidebar toggle (Mở/Đóng menu con)
  // ======================================================
  const parent = document.getElementById('finance-parent');
  const submenu = document.getElementById('finance-submenu');

  if (parent && submenu) {
    const updateHeight = () => {
      submenu.style.height = submenu.classList.contains('open') ? submenu.scrollHeight + "px" : "0";
    };
    parent.addEventListener('click', () => {
      parent.classList.toggle('open');
      submenu.classList.toggle('open');
      updateHeight();
    });
    updateHeight();  // Cập nhật chiều cao ban đầu
  }

  // ======================================================
  // 2. Logic cho modal thêm mới giao dịch (Thu/Chi)
  // ======================================================
  const modal = document.getElementById('transaction-modal');
  const openBtn = document.getElementById('open-transaction-modal');

  if (modal && openBtn) {
    const form = modal.querySelector('form');
    const header = modal.querySelector('.modal-header');

    openBtn.addEventListener('click', () => {
      header.childNodes[0].nodeValue = 'Thêm giao dịch mới';
      form.action = '/add-transaction';
      form.reset();

      const toggleGroup = modal.querySelector('.toggle-group');
      if (toggleGroup) {
        updateToggleState(toggleGroup, 'income');  // Mặc định chọn "Thu"
      }

      modal.style.display = 'flex';
    });

    // Đóng modal khi click nút close hoặc cancel
    modal.querySelectorAll('.modal-close, .btn-cancel').forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        modal.style.display = 'none';
      });
    });

    // Đóng modal khi click bên ngoài
    modal.addEventListener('click', e => {
      if (e.target === modal) {
        modal.style.display = 'none';
      }
    });
  }

  // ======================================================
  // 3. Logic edit giao dịch (Thu/Chi)
  // ======================================================
  document.querySelectorAll('.btn-edit-tx').forEach(btn => {
    btn.addEventListener('click', function () {
      const modal = document.getElementById('transaction-modal');
      const form = modal.querySelector('form');

      modal.querySelector('.modal-header').childNodes[0].nodeValue = "Sửa giao dịch";
      form.action = this.dataset.action;

      form.amount.value = this.dataset.amount;
      form.description.value = this.dataset.desc;
      form.category_id.value = this.dataset.catid;  // Set category_id cho select
      form.date.value = this.dataset.date;

      updateToggleState(modal.querySelector('.toggle-group'), this.dataset.type);
      modal.style.display = 'flex';
    });
  });

  // ======================================================
  // 3b. Logic edit vay/nợ
  // ======================================================
  document.querySelectorAll('.btn-edit-dl').forEach(btn => {
    btn.addEventListener('click', function () {
      const modal = document.getElementById('debt-loan-modal');
      const form = modal.querySelector('form');

      // Cập nhật tiêu đề và action của form
      modal.querySelector('.modal-header').childNodes[0].nodeValue = "Sửa khoản vay/nợ";
      form.action = this.dataset.action;

      // Map dữ liệu từ dataset của button vào form fields
      const dataMap = {
        'person': this.dataset.person,
        'total_amount': this.dataset.total,
        'paid_amount': this.dataset.paid,
        'description': this.dataset.desc,
        'start_date': this.dataset.date
      };

      // Đổ dữ liệu vào các field tương ứng
      Object.keys(dataMap).forEach(key => {
        if (form[key]) {
          form[key].value = dataMap[key];
        }
      });

      // Cập nhật toggle (Cho vay / Vay nợ)
      const toggleGroup = modal.querySelector('.toggle-group');
      if (toggleGroup) {
        updateToggleState(toggleGroup, this.dataset.type);
      }

      modal.style.display = 'flex';
    });
  });

  // ======================================================
  // 4. Logic click vào toggle buttons
  // ======================================================
  document.querySelectorAll('.toggle-group').forEach(group => {
    group.addEventListener('click', e => {
      if (e.target.classList.contains('toggle-btn')) {
        updateToggleState(group, e.target.dataset.type);
      }
    });
  });

  // ======================================================
  // 5. Logic đăng xuất
  // ======================================================
  const logoutBtn = document.querySelector('.btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', e => {
      e.preventDefault();
      if (confirm('Bạn có chắc chắn muốn đăng xuất không?')) {
        window.location.href = '/logout';
      }
    });
  }

  // ======================================================
  // 6. Logic modal thêm mới vay/nợ
  // ======================================================
  const debtModal = document.getElementById('debt-loan-modal');
  const openDebtBtn = document.getElementById('open-debt-loan-modal');

  if (debtModal && openDebtBtn) {
    const form = debtModal.querySelector('form');
    const header = debtModal.querySelector('.modal-header');

    openDebtBtn.addEventListener('click', () => {
      header.childNodes[0].nodeValue = 'Thêm vay/nợ mới';
      form.action = '/add-debt-loan';
      form.reset();

      updateToggleState(
        debtModal.querySelector('.toggle-group'),
        'loan-out'  // Mặc định chọn "Cho vay"
      );

      debtModal.style.display = 'flex';
    });

    // Đóng modal khi click close hoặc cancel
    debtModal.querySelectorAll('.modal-close, .btn-cancel').forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        debtModal.style.display = 'none';
      });
    });

    // Đóng modal khi click bên ngoài
    debtModal.addEventListener('click', e => {
      if (e.target === debtModal) {
        debtModal.style.display = 'none';
      }
    });
  }

});