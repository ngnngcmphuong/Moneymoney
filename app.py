from flask import Flask, render_template, request, redirect, url_for, session
import json
from datetime import datetime
import pandas as pd

from auth import auth
from db import get_connection

# =========================
# KHỞI TẠO APP
# =========================
app = Flask(__name__)
app.secret_key = "super_secret_key_for_moneytrack_app"  # Nên thay bằng secret key an toàn hơn trong production
app.register_blueprint(auth)

# =========================
# HÀM HỖ TRỢ
# =========================
def vnd(tien):
    try:
        return f"{abs(float(tien or 0)):,.0f}".replace(",", ".")
    except:
        return "0"

app.jinja_env.globals.update(vnd=vnd, datetime=datetime)

# =========================
# DASHBOARD
# =========================
@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    id_nguoi_dung = session['user_id']

    # Sử dụng JOIN để lấy category_name thay vì category_id
    cau_lenh = """
        SELECT t.*, c.category_name 
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
    """
    bang = pd.read_sql(cau_lenh, conn, params=(id_nguoi_dung,))

    if bang.empty:
        conn.close()
        return render_template(
            'dashboard.html',
            page='dashboard',
            kpi_data={"income": 0, "expense": 0, "balance": 0, "saving_pct": 0},
            monthly_labels_json=json.dumps([]),
            monthly_income_json=json.dumps([]),
            monthly_expense_json=json.dumps([]),
            category_labels_json=json.dumps([]),
            category_values_json=json.dumps([]),
            username=session.get('username')
        )

    bang['amount'] = bang['amount'].astype(float)
    bang['date'] = pd.to_datetime(bang['date'])

    tong_thu = bang[bang['transaction_type'] == 'income']['amount'].sum()
    tong_chi = bang[bang['transaction_type'] == 'expense']['amount'].sum()
    so_du = tong_thu - tong_chi

    if tong_thu > 0:
        phan_tram_tiet_kiem = (so_du / tong_thu) * 100
    else:
        phan_tram_tiet_kiem = 0

    # BIỂU ĐỒ TRÒN: Group by 'category_name' (nhờ JOIN)
    bang_loai = bang[bang['transaction_type'] == 'expense']
    bang_loai = bang_loai.groupby('category_name')['amount'].sum()
    du_lieu_loai = bang_loai.to_dict()

    # BIỂU ĐỒ THÁNG
    bang['thang_nam'] = bang['date'].dt.strftime('%m/%Y')
    bang_thang = bang.groupby(
        ['thang_nam', 'transaction_type']
    )['amount'].sum().unstack(fill_value=0)

    bang_thang.index = pd.to_datetime(bang_thang.index, format='%m/%Y')
    bang_thang = bang_thang.sort_index()

    ds_thang = bang_thang.index.strftime('%m/%Y').tolist()

    if 'income' in bang_thang:
        ds_thu = bang_thang['income'].tolist()
    else:
        ds_thu = [0] * len(ds_thang)

    if 'expense' in bang_thang:
        ds_chi = bang_thang['expense'].tolist()
    else:
        ds_chi = [0] * len(ds_thang)

    conn.close()

    return render_template(
        'dashboard.html',
        page='dashboard',
        kpi_data={
            "income": float(tong_thu),
            "expense": float(tong_chi),
            "balance": float(so_du),
            "saving_pct": float(phan_tram_tiet_kiem)
        },
        monthly_labels_json=json.dumps(ds_thang),
        monthly_income_json=json.dumps(ds_thu),
        monthly_expense_json=json.dumps(ds_chi),
        category_labels_json=json.dumps(list(du_lieu_loai.keys())),
        category_values_json=json.dumps(list(du_lieu_loai.values())),
        username=session.get('username')
    )

# =========================
# THU - CHI
# =========================
@app.route('/thu-chi')
def thu_chi():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Lấy lịch sử giao dịch (JOIN với categories để hiện tên)
    cursor.execute("""
        SELECT t.*, c.category_name 
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.date DESC
    """, (session['user_id'],))
    danh_sach = cursor.fetchall()

    # 2. LẤY DANH SÁCH DANH MỤC CHO MODAL
    cursor.execute("SELECT id, category_name FROM categories")
    list_categories = cursor.fetchall()

    tong_thu = 0
    tong_chi = 0

    for dong in danh_sach:
        if dong['transaction_type'] == 'income':
            tong_thu += float(dong['amount'])
        elif dong['transaction_type'] == 'expense':
            tong_chi += float(dong['amount'])

    cursor.close()
    conn.close()

    return render_template(
        "income_expense.html",
        page="thu_chi",
        transactions=danh_sach,
        categories=list_categories,  # Truyền biến này vào HTML cho dropdown
        income=tong_thu,
        expense=tong_chi,
        balance=tong_thu - tong_chi
    )

# =========================
# VAY - NỢ
# =========================
@app.route('/vay-no')
def vay_no():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM debt_loans
        WHERE user_id = %s
        ORDER BY start_date DESC
    """, (session['user_id'],))

    danh_sach = cursor.fetchall()

    tong_cho_vay = 0
    tong_no = 0

    for dong in danh_sach:
        con_lai = float(dong['total_amount']) - float(dong['paid_amount'])
        if dong['loan_type'] == 'loan-out':
            tong_cho_vay += con_lai
        else:
            tong_no += con_lai

    cursor.close()
    conn.close()

    return render_template(
        "debt_loan.html",
        page="vay_no",
        debt_loan_items=danh_sach,
        total_loan=tong_cho_vay,
        total_debt=tong_no,
        net_balance=tong_cho_vay - tong_no
    )

# =========================
# THÊM / SỬA / XÓA
# =========================
@app.route('/add-transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions
        (user_id, amount, category_id, description, transaction_type, date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        session['user_id'],
        request.form['amount'],
        request.form['category_id'],  # Khớp với name trong <select> HTML
        request.form['description'],
        request.form['transaction_type'],
        request.form['date']
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('thu_chi'))

@app.route('/add-debt-loan', methods=['POST'])
def add_debt_loan():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Lấy đúng tên trường 'person' từ form
    person = request.form.get('person') 
    loan_type = request.form.get('loan_type')
    total_amount = request.form.get('total_amount', 0)
    paid_amount = request.form.get('paid_amount', 0)
    description = request.form.get('description', '')
    start_date = request.form.get('start_date')
    
    # Tự động tính status dựa trên số tiền
    status = "ĐÃ KẾT THÚC" if float(paid_amount) >= float(total_amount) else "ĐANG NỢ"

    conn = get_connection()
    cursor = conn.cursor()
    # Câu lệnh SQL phải dùng đúng tên cột 'person'
    sql = """INSERT INTO debt_loans 
             (user_id, start_date, person, loan_type, total_amount, paid_amount, description, status) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    cursor.execute(sql, (session['user_id'], start_date, person, loan_type, total_amount, paid_amount, description, status))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('vay_no'))

@app.route('/edit-transaction/<int:id>', methods=['POST'])
def edit_transaction(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE transactions
        SET amount = %s,
            category_id = %s,
            description = %s,
            transaction_type = %s,
            date = %s
        WHERE id = %s AND user_id = %s
    """, (
        request.form['amount'],
        request.form['category_id'],
        request.form['description'],
        request.form['transaction_type'],
        request.form['date'],
        id,
        session['user_id']
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('thu_chi'))

@app.route('/edit-debt-loan/<int:id>', methods=['POST'])
def edit_debt_loan(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 1. Lấy dữ liệu từ form bằng 'person' thay vì 'name'
    person = request.form.get('person')
    loan_type = request.form.get('loan_type')
    total_amount = float(request.form.get('total_amount', 0))
    paid_amount = float(request.form.get('paid_amount', 0))
    description = request.form.get('description', '')
    start_date = request.form.get('start_date')

    # 2. Logic tính toán Status tự động
    status = "ĐÃ KẾT THÚC" if paid_amount >= total_amount else "ĐANG NỢ"

    conn = get_connection()
    cursor = conn.cursor()
    # 3. Câu lệnh SQL UPDATE chính xác với tên cột 'person'
    sql = """
        UPDATE debt_loans 
        SET start_date = %s, 
            person = %s, 
            loan_type = %s, 
            total_amount = %s, 
            paid_amount = %s, 
            description = %s, 
            status = %s
        WHERE id = %s AND user_id = %s
    """
    params = (start_date, person, loan_type, total_amount, paid_amount, description, status, id, session['user_id'])
    cursor.execute(sql, params)
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('vay_no')) 

@app.route('/delete-transaction/<int:id>')
def delete_transaction(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM transactions WHERE id = %s AND user_id = %s",
        (id, session['user_id'])
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('thu_chi'))

@app.route('/delete-debt-loan/<int:id>')
def delete_debt_loan(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM debt_loans WHERE id = %s AND user_id = %s",
        (id, session['user_id'])
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('vay_no'))

# =========================
# ĐĂNG XUẤT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# =========================
# CHẠY SERVER
# =========================
if __name__ == '__main__':
    app.run(debug=True)  # Tắt debug trong production