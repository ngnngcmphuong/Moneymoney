from flask import Flask, render_template, request, redirect, url_for, session
import json
from datetime import datetime
import pandas as pd
import warnings

# Tắt cảnh báo UserWarning của pandas
warnings.filterwarnings("ignore", category=UserWarning)

from auth import auth
from db import get_connection

# =========================
# KHỞI TẠO APP
# =========================
app = Flask(__name__)
app.secret_key = "super_secret_key_for_moneytrack_app"  
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
# DASHBOARD (Cập nhật chức năng Lọc)
# =========================
@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    id_nguoi_dung = session['user_id']

    # 1. Lấy ngày từ form lọc trong dashboard.html
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    # 2. Xây dựng câu lệnh SQL lọc theo thời gian
    cau_lenh = """
        SELECT t.*, c.category_name 
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
    """
    params = [id_nguoi_dung]

    if from_date:
        cau_lenh += " AND t.date >= %s"
        params.append(from_date)
    if to_date:
        cau_lenh += " AND t.date <= %s"
        params.append(to_date)

    # 3. Đọc dữ liệu bằng pandas với tham số lọc
    bang = pd.read_sql(cau_lenh, conn, params=params)

    if bang.empty:
        conn.close()
        return render_template('dashboard.html', page='dashboard', 
                             from_date=from_date, to_date=to_date, # Truyền lại ngày để giữ giá trị ô nhập
                             kpi_data={"income": 0, "expense": 0, "balance": 0, "saving_pct": 0},
                             monthly_labels_json="[]", monthly_income_json="[]", monthly_expense_json="[]",
                             category_labels_json="[]", category_values_json="[]", username=session.get('username'))

    # Xử lý dữ liệu hiển thị biểu đồ
    bang['amount'] = bang['amount'].astype(float)
    bang['date'] = pd.to_datetime(bang['date'])
    
    tong_thu = bang[bang['transaction_type'] == 'income']['amount'].sum()
    tong_chi = bang[bang['transaction_type'] == 'expense']['amount'].sum()
    so_du = tong_thu - tong_chi
    phan_tram_tiet_kiem = (so_du / tong_thu * 100) if tong_thu > 0 else 0

    # Thống kê theo tháng cho biểu đồ đường
    bang['month'] = bang['date'].dt.strftime('%m/%Y')
    thong_ke_thang = bang.groupby(['month', 'transaction_type'])['amount'].sum().unstack(fill_value=0)
    ds_thang = thong_ke_thang.index.tolist()
    ds_thu = thong_ke_thang.get('income', pd.Series([0]*len(ds_thang))).tolist()
    ds_chi = thong_ke_thang.get('expense', pd.Series([0]*len(ds_thang))).tolist()

    # Thống kê theo danh mục cho biểu đồ tròn
    du_lieu_loai = bang[bang['transaction_type'] == 'expense'].groupby('category_name')['amount'].sum().to_dict()

    conn.close()

    return render_template('dashboard.html', 
        page='dashboard', 
        from_date=from_date, 
        to_date=to_date,
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
# QUẢN LÝ THU CHI
# =========================
@app.route('/thu-chi')
def thu_chi():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT t.*, c.category_name FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE t.user_id = %s ORDER BY t.date DESC", (session['user_id'],))
    txs = cursor.fetchall()
    cursor.execute("SELECT * FROM categories")
    cats = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('thu_chi.html', page='thu_chi', transactions=txs, categories=cats)

@app.route('/add-transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    data = request.form
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (user_id, amount, category_id, description, transaction_type, date) VALUES (%s, %s, %s, %s, %s, %s)",
                 (session['user_id'], data['amount'], data['category_id'], data['description'], data['transaction_type'], data['date']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('thu_chi'))

@app.route('/edit-transaction/<int:id>', methods=['POST'])
def edit_transaction(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    data = request.form
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET amount=%s, category_id=%s, description=%s, transaction_type=%s, date=%s WHERE id=%s AND user_id=%s",
                 (data['amount'], data['category_id'], data['description'], data['transaction_type'], data['date'], id, session['user_id']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('thu_chi'))

@app.route('/delete-transaction/<int:id>')
def delete_transaction(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (id, session['user_id']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('thu_chi'))

# =========================
# QUẢN LÝ VAY NỢ
# =========================
@app.route('/vay-no')
def vay_no():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM debt_loans WHERE user_id = %s ORDER BY start_date DESC", (session['user_id'],))
    items = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('vay_no.html', page='vay_no', debt_loans=items)

@app.route('/add-debt-loan', methods=['POST'])
def add_debt_loan():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    d = request.form
    status = "ĐÃ KẾT THÚC" if float(d['paid_amount']) >= float(d['total_amount']) else "ĐANG NỢ"
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO debt_loans (user_id, person, loan_type, total_amount, paid_amount, description, start_date, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                 (session['user_id'], d['person'], d['loan_type'], d['total_amount'], d['paid_amount'], d['description'], d['start_date'], status))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('vay_no'))

@app.route('/edit-debt-loan/<int:id>', methods=['POST'])
def edit_debt_loan(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    d = request.form
    status = "ĐÃ KẾT THÚC" if float(d['paid_amount']) >= float(d['total_amount']) else "ĐANG NỢ"
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE debt_loans SET start_date=%s, person=%s, loan_type=%s, total_amount=%s, paid_amount=%s, description=%s, status=%s WHERE id=%s AND user_id=%s",
                 (d['start_date'], d['person'], d['loan_type'], d['total_amount'], d['paid_amount'], d['description'], status, id, session['user_id']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('vay_no'))

@app.route('/delete-debt-loan/<int:id>')
def delete_debt_loan(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM debt_loans WHERE id = %s AND user_id = %s", (id, session['user_id']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('vay_no'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)