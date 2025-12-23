from flask import Flask, render_template, request, redirect, url_for, session
import json
from datetime import datetime
import pandas as pd
import re
import json
import random 

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

def get_filter_dates():
    """Hàm lấy khoảng thời gian từ URL hoặc mặc định tháng hiện tại"""
    today = datetime.now()
    # Mặc định: Từ ngày 1 của tháng hiện tại đến hôm nay
    default_from = today.replace(day=1).strftime('%Y-%m-%d')
    default_to = today.strftime('%Y-%m-%d')
    
    from_date = request.args.get('from_date', default_from)
    to_date = request.args.get('to_date', default_to)
    return from_date, to_date

app.jinja_env.globals.update(vnd=vnd, datetime=datetime)

# DASHBOARD
@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    from_date, to_date = get_filter_dates()
    conn = get_connection()
    id_nguoi_dung = session['user_id']

    cau_lenh = """
        SELECT t.*, c.category_name 
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s AND t.date BETWEEN %s AND %s
    """
    bang = pd.read_sql(cau_lenh, conn, params=(id_nguoi_dung, from_date, to_date))

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
            username=session.get('username'),
            from_date=from_date,
            to_date=to_date
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

    # BIỂU ĐỒ TRÒN
    bang_loai = bang[bang['transaction_type'] == 'expense']
    bang_loai = bang_loai.groupby('category_name')['amount'].sum()
    du_lieu_loai = bang_loai.to_dict()

    # BIỂU ĐỒ THÁNG 
    cau_lenh_trend = """
        SELECT date, amount, transaction_type 
        FROM transactions 
        WHERE user_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
    """
    bang_trend = pd.read_sql(cau_lenh_trend, conn, params=(id_nguoi_dung,))
    bang_trend['date'] = pd.to_datetime(bang_trend['date'])
    bang_trend['thang_nam'] = bang_trend['date'].dt.strftime('%m/%Y')
    
    bang_thang = bang_trend.groupby(['thang_nam', 'transaction_type'])['amount'].sum().unstack(fill_value=0)
    bang_thang.index = pd.to_datetime(bang_thang.index, format='%m/%Y')
    bang_thang = bang_thang.sort_index()

    ds_thang = bang_thang.index.strftime('%m/%Y').tolist()
    ds_thu = bang_thang['income'].tolist() if 'income' in bang_thang else [0] * len(ds_thang)
    ds_chi = bang_thang['expense'].tolist() if 'expense' in bang_thang else [0] * len(ds_thang)

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
        username=session.get('username'),
        from_date=from_date,
        to_date=to_date
    )

# =========================
# THU - CHI
# =========================
@app.route('/thu-chi')
def thu_chi():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    from_date, to_date = get_filter_dates()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy lịch sử giao dịch có lọc ngày
    cursor.execute("""
        SELECT t.*, c.category_name 
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s AND t.date BETWEEN %s AND %s
        ORDER BY t.date DESC
    """, (session['user_id'], from_date, to_date))
    danh_sach = cursor.fetchall()

    cursor.execute("SELECT id, category_name FROM categories")
    list_categories = cursor.fetchall()

    tong_thu = sum(float(d['amount']) for d in danh_sach if d['transaction_type'] == 'income')
    tong_chi = sum(float(d['amount']) for d in danh_sach if d['transaction_type'] == 'expense')

    cursor.close()
    conn.close()

    return render_template(
        "income_expense.html",
        page="thu_chi",
        transactions=danh_sach,
        categories=list_categories,  
        income=tong_thu,
        expense=tong_chi,
        balance=tong_thu - tong_chi,
        from_date=from_date,
        to_date=to_date
    )

# =========================
# VAY - NỢ
# =========================
@app.route('/vay-no')
def vay_no():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    from_date, to_date = get_filter_dates()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM debt_loans
        WHERE user_id = %s AND start_date BETWEEN %s AND %s
        ORDER BY start_date DESC
    """, (session['user_id'], from_date, to_date))

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
        net_balance=tong_cho_vay - tong_no,
        from_date=from_date,
        to_date=to_date
    )


@app.route('/add-transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""INSERT INTO transactions (user_id, amount, category_id, description, transaction_type, date)
        VALUES (%s, %s, %s, %s, %s, %s)""", (session['user_id'], request.form['amount'], request.form['category_id'], 
        request.form['description'], request.form['transaction_type'], request.form['date']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('thu_chi'))

@app.route('/add-debt-loan', methods=['POST'])
def add_debt_loan():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    person = request.form.get('person'); loan_type = request.form.get('loan_type')
    total_amount = request.form.get('total_amount', 0); paid_amount = request.form.get('paid_amount', 0)
    description = request.form.get('description', ''); start_date = request.form.get('start_date')
    status = "ĐÃ KẾT THÚC" if float(paid_amount) >= float(total_amount) else "ĐANG NỢ"
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""INSERT INTO debt_loans (user_id, start_date, person, loan_type, total_amount, paid_amount, description, status) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", (session['user_id'], start_date, person, loan_type, total_amount, paid_amount, description, status))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('vay_no'))

@app.route('/edit-transaction/<int:id>', methods=['POST'])
def edit_transaction(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""UPDATE transactions SET amount = %s, category_id = %s, description = %s, transaction_type = %s, date = %s
        WHERE id = %s AND user_id = %s""", (request.form['amount'], request.form['category_id'], request.form['description'],
        request.form['transaction_type'], request.form['date'], id, session['user_id']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('thu_chi'))

@app.route('/edit-debt-loan/<int:id>', methods=['POST'])
def edit_debt_loan(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    person = request.form.get('person'); loan_type = request.form.get('loan_type')
    total_amount = float(request.form.get('total_amount', 0)); paid_amount = float(request.form.get('paid_amount', 0))
    description = request.form.get('description', ''); start_date = request.form.get('start_date')
    status = "ĐÃ KẾT THÚC" if paid_amount >= total_amount else "ĐANG NỢ"
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""UPDATE debt_loans SET start_date = %s, person = %s, loan_type = %s, total_amount = %s, paid_amount = %s, description = %s, status = %s
        WHERE id = %s AND user_id = %s""", (start_date, person, loan_type, total_amount, paid_amount, description, status, id, session['user_id']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('vay_no'))

@app.route('/delete-transaction/<int:id>')
def delete_transaction(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (id, session['user_id']))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('thu_chi'))

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

@app.route('/ai-chat', methods=['POST'])
def ai_chat():
    if 'user_id' not in session:
        return json.dumps({"status": "error", "message": "Yêu cầu đăng nhập hệ thống."})

    data = request.json
    user_msg = data.get('message', '').lower().strip()
    user_id = session['user_id']
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        #CHỨC NĂNG TỔNG KẾT
        if any(word in user_msg for word in ['tổng kết', 'báo cáo', 'hôm nay tiêu gì']):
            cursor.execute("""
                SELECT t.amount, t.transaction_type, c.category_name 
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = %s AND t.date = %s
            """, (user_id, today_str))
            
            rows = cursor.fetchall()
            if not rows:
                reply = f"Hệ thống xác nhận: Ngày {datetime.now().strftime('%d/%m')} chưa phát sinh giao dịch."
            else:
                tong_thu = sum(float(r['amount']) for r in rows if r['transaction_type'] == 'income')
                tong_chi = sum(float(r['amount']) for r in rows if r['transaction_type'] == 'expense')
                reply = (f"BÁO CÁO TÀI CHÍNH {datetime.now().strftime('%d/%m')}\n"
                         f"• Tổng thu: {vnd(tong_thu)}đ\n"
                         f"• Tổng chi: {vnd(tong_chi)}đ\n"
                         "----------------------------")
            return json.dumps({"status": "success", "reply": reply})

        #CHỨC NĂNG NHẬP LIỆU TỰ ĐỘNG
        match_money = re.search(r'(\d+(?:\.\d+)?)\s*(k|000|nghìn|ngàn)?', user_msg)
        if match_money:
            amount_raw = float(match_money.group(1).replace('.', ''))
            suffix = match_money.group(2)
            amount = int(amount_raw * 1000) if suffix in ['k', 'nghìn', 'ngàn'] or amount_raw < 1000 else int(amount_raw)
            description_raw = user_msg.replace(match_money.group(0), '').strip()

            # PHÂN LOẠI VAY NỢ 
            debt_keywords = ['vay', 'mượn', 'nợ']
            if any(word in user_msg for word in debt_keywords):
                if any(w in user_msg for w in ['tôi nợ', 'vay của', 'mượn của', 'nợ của', 'nợ anh', 'nợ chị']):
                    loan_type = 'loan-in'
                    action = "vay nợ"
                else:
                    loan_type = 'loan-out'
                    action = "cho vay"

                words = description_raw.split()
                person = words[0].capitalize() if words else "Đối tác"
                if person.lower() == 'tôi' and len(words) > 1: person = words[1].capitalize()

                sql = """INSERT INTO debt_loans (user_id, start_date, person, loan_type, total_amount, paid_amount, description, status) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (user_id, today_str, person, loan_type, amount, 0, f"AI: {user_msg}", "ĐANG NỢ"))
                reply_msg = f"Hệ thống đã lưu khoản {action}: {person} | Số tiền: {vnd(amount)}đ."

            #PHÂN LOẠI THU CHI 
            else:
                cat_name = "Khác"
                if any(x in user_msg for x in ['ăn', 'uống', 'phở', 'cơm', 'bún', 'cafe', 'trà sữa', 'mì', 'snack']):
                    cat_name = "Ăn uống"
                elif any(x in user_msg for x in ['xăng', 'xe', 'grab', 'be', 'bus', 'taxi']):
                    cat_name = "Di chuyển"
                elif any(x in user_msg for x in ['phim', 'chơi', 'du lịch', 'game', 'netflix', 'karaoke']):
                    cat_name = "Giải trí"
                elif any(x in user_msg for x in ['skincare', 'mỹ phẩm', 'quần áo', 'giày', 'shopee', 'lazada', 'son','mua']):
                    cat_name = "Mua sắm"
                elif any(x in user_msg for x in ['điện', 'nước', 'mạng', 'wifi', 'tiền nhà']):
                    cat_name = "Nhà ở"
                elif any(x in user_msg for x in ['lương', 'thưởng', 'tiền về', 'lãi']):
                    cat_name = "Lương"

                income_keywords = ['thu', 'lương', 'nhận', 'lãi', 'được cho']
                tx_type = 'income' if any(word in user_msg for word in income_keywords) else 'expense'
                
                cursor.execute("SELECT id FROM categories WHERE category_name = %s", (cat_name,))
                res = cursor.fetchone()
                
                sql = """INSERT INTO transactions (user_id, amount, category_id, description, transaction_type, date) 
                         VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (user_id, amount, res['id'] if res else 5, description_raw.capitalize() or "AI nhập", tx_type, today_str))
                reply_msg = f"Ghi nhận thành công: {description_raw.capitalize()} | {vnd(amount)}đ | Mục: {cat_name}."

            conn.commit()
            return json.dumps({"status": "success", "reply": reply_msg})

    except Exception as e:
        return json.dumps({"status": "error", "reply": f"Lỗi hệ thống: {str(e)}"})
    finally:
        cursor.close()
        conn.close()

    return json.dumps({"status": "success", "reply": "Yêu cầu không rõ ràng. Vui lòng nhập số tiền hoặc lệnh 'tổng kết'."})

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8000, debug=True)