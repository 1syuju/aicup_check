import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import inspect, text
import pandas as pd
import qrcode
import io
import base64
from datetime import datetime, timezone, timedelta
import json
import time

LOCAL_TZ = timezone(timedelta(hours=8))
DEBUG_LOG_PATH = os.path.join(os.path.dirname(__file__), 'debug-d610a5.log')


def _debug_log(location, message, data=None, hypothesis_id=''):
    # #region agent log
    try:
        payload = {
            'sessionId': 'd610a5',
            'runId': 'pre-fix',
            'hypothesisId': hypothesis_id,
            'location': location,
            'message': message,
            'data': data or {},
            'timestamp': int(time.time() * 1000),
        }
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # #endregion


def format_local_time(dt, fmt='%H:%M'):
    """將 UTC 或 naive datetime 轉為 GMT+8 顯示。"""
    if not dt:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ).strftime(fmt)

# 寫死Excel名單路徑（Windows）
FIXED_XLSX_PATH = r"C:\\Users\\USER\\Desktop\\python\\aicup2025_1\\guest_final.xlsx"

# 管理員密碼（簡單認證）
ADMIN_PASSWORD = '33urriii'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///checkin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)


@app.template_filter('localtime')
def localtime_filter(dt, fmt='%Y-%m-%d %H:%M:%S'):
    return format_local_time(dt, fmt)


def _clean_excel_value(value):
    """將 Excel 欄位值轉為可用字串（排除 NaN）。"""
    if pd.isna(value):
        return ''
    text = str(value).strip()
    if text.lower() == 'nan':
        return ''
    return text


def _get_first_available_value(row, columns):
    """依欄位候選順序取第一個有值的欄位（容錯欄名空白/換行）。"""
    normalized_to_real = {}
    for real_column in row.index:
        normalized_name = str(real_column).replace('\ufeff', '').replace('\n', '').replace('\r', '').strip()
        normalized_to_real[normalized_name] = real_column

    for column in columns:
        normalized_candidate = str(column).replace('\ufeff', '').replace('\n', '').replace('\r', '').strip()
        real_column = normalized_to_real.get(normalized_candidate)
        if real_column is not None:
            value = _clean_excel_value(row[real_column])
            if value:
                return value
    return ''


def _build_participant_from_row(row):
    """支援 guest_final 與舊版欄位格式的參加者映射。"""
    name = _get_first_available_value(row, ['隊員姓名', '人名中文', '姓名'])
    if not name:
        return None

    organization = _get_first_available_value(
        row, ['隊伍名稱', '校名中文', '組織/學校']
    )
    phone = _get_first_available_value(
        row, ['貴隊伍聯絡代表人手機號碼', '電話']
    )
    email = _get_first_available_value(row, ['Email', '電子郵件'])
    competition_name = _get_first_available_value(
        row, ['競賽', '參加AI CUP 2026競賽', '競賽名稱']
    )
    seat_number = _get_first_available_value(row, ['座號', '座位號碼'])

    return Participant(
        name=name,
        email=email,
        phone=phone,
        organization=organization,
        competition_name=competition_name,
        seat_number=seat_number
    )

# 資料庫模型
class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    organization = db.Column(db.String(200), nullable=True)
    competition_name = db.Column(db.String(200), nullable=True)
    seat_number = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Participant {self.name}>'

class CheckinLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    checkin_method = db.Column(db.String(20), default='manual')  # manual, qr, mobile
    
    participant = db.relationship('Participant', backref=db.backref('checkins', lazy=True))
    
    def __repr__(self):
        return f'<CheckinLog {self.participant.name} at {self.checkin_time}>'


def ensure_participant_schema():
    """若舊資料庫缺少欄位，啟動時自動補齊。"""
    inspector = inspect(db.engine)
    columns = {column['name'] for column in inspector.get_columns('participant')}
    if 'competition_name' not in columns:
        db.session.execute(text("ALTER TABLE participant ADD COLUMN competition_name VARCHAR(200)"))
        db.session.commit()
    if 'seat_number' not in columns:
        db.session.execute(text("ALTER TABLE participant ADD COLUMN seat_number VARCHAR(50)"))
        db.session.commit()

# 建立資料庫表格
with app.app_context():
    try:
        db.create_all()
        ensure_participant_schema()
        print('資料庫表格建立成功')
        
        # 自動匯入參加者資料（如果資料庫是空的）
        try:
            if os.path.exists(FIXED_XLSX_PATH) and db.session.query(Participant).count() == 0:
                df = pd.read_excel(FIXED_XLSX_PATH)
                count = 0
                for _, row in df.iterrows():
                    participant = _build_participant_from_row(row)
                    if participant:
                        db.session.add(participant)
                        count += 1
                db.session.commit()
                print(f'啟動時自動匯入 {count} 筆參加者資料')
        except Exception as e:
            db.session.rollback()
            print(f'啟動時自動匯入失敗: {str(e)}')
            
    except Exception as e:
        print(f'資料庫初始化失敗: {str(e)}')
        print('請檢查 SQL Server 連線設定或使用 SQLite 作為備用')

# 從固定路徑匯入的輔助函式
def import_participants_from_fixed():
    if not os.path.exists(FIXED_XLSX_PATH):
        return 0, f'找不到固定名單檔案: {FIXED_XLSX_PATH}'
    try:
        df = pd.read_excel(FIXED_XLSX_PATH)
        # 清空現有資料
        CheckinLog.query.delete()
        Participant.query.delete()
        
        count = 0
        for _, row in df.iterrows():
            participant = _build_participant_from_row(row)
            if participant:
                db.session.add(participant)
                count += 1
        db.session.commit()
        return count, 'OK'
    except Exception as e:
        db.session.rollback()
        return 0, str(e)

# 直接從固定路徑匯入的路由
@app.route('/import_fixed', methods=['POST', 'GET'])
def import_fixed():
    count, status = import_participants_from_fixed()
    if status != 'OK':
        flash(f'匯入失敗: {status}')
    else:
        flash(f'成功匯入 {count} 筆參加者資料（固定路徑）')
    return redirect(url_for('admin'))

@app.route('/')
def index():
    is_admin = session.get('admin_authenticated', False)
    return render_template('index.html', is_admin=is_admin)

@app.route('/checkin')
def checkin():
    """報到介面 - 給參加者使用"""
    return render_template('checkin.html')


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """管理員登入頁面"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            flash('登入成功！', 'success')
            return redirect(url_for('admin'))
        else:
            flash('密碼錯誤！', 'error')
    return render_template('admin_login.html')


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    flash('已登出', 'info')
    return redirect(url_for('index'))

from flask import abort, request
@app.route('/admin')
def admin():
    # 允許本機存取或透過管理員登入存取
    if request.remote_addr != '127.0.0.1' and not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))
    participants = Participant.query.all()
    total_count = len(participants)
    # 統計已報到人數
    checked_in_count = db.session.query(CheckinLog).distinct(CheckinLog.participant_id).count()
    # 檢查每個參加者的報到狀態
    for participant in participants:
        participant.is_checked_in = db.session.query(CheckinLog).filter(
            CheckinLog.participant_id == participant.id
        ).first() is not None
    return render_template('admin.html', 
                         participants=participants, 
                         total_count=total_count,
                         checked_in_count=checked_in_count)


@app.route('/api/checkin', methods=['POST'])
def api_checkin():
    data = request.get_json()
    name = data.get('name')
    
    if not name:
        return jsonify({'success': False, 'message': '請輸入姓名'}), 400
    
    participant = Participant.query.filter(Participant.name == name).first()
    if not participant:
        return jsonify({'success': False, 'message': '找不到該參加者，請確認姓名'}), 404
    
    # 檢查是否已經報到
    existing_checkin = CheckinLog.query.filter(
        CheckinLog.participant_id == participant.id
    ).first()
    
    if existing_checkin:
        return jsonify({'success': False, 'message': '該參加者已經報到過了'}), 400
    
    # 記錄報到
    checkin_log = CheckinLog(
        participant_id=participant.id,
        checkin_method='manual'
    )
    db.session.add(checkin_log)
    db.session.commit()

    # #region agent log
    _debug_log(
        'app.py:api_checkin',
        'checkin committed',
        {
            'has_checkin_time_attr': hasattr(checkin_log, 'checkin_time'),
            'checkin_time_raw': str(checkin_log.checkin_time) if checkin_log.checkin_time else None,
            'checkin_time_local': format_local_time(checkin_log.checkin_time),
        },
        hypothesis_id='B,C'
    )
    # #endregion

    participant_payload = {
        'name': participant.name,
        'organization': participant.organization or '',
        'competition_name': participant.competition_name or '',
        'seat_number': participant.seat_number or '',
        'checkin_time': format_local_time(checkin_log.checkin_time),
    }

    # #region agent log
    _debug_log(
        'app.py:api_checkin',
        'api response payload',
        {
            'participant_keys': list(participant_payload.keys()),
            'checkin_time_in_payload': participant_payload.get('checkin_time'),
        },
        hypothesis_id='A,D'
    )
    # #endregion

    return jsonify({
        'success': True,
        'message': f'{participant.name} 報到成功！',
        'participant': participant_payload
    })

@app.route('/api/admin_stats', methods=['GET'])
def api_admin_stats():
    """API: 獲取管理後台統計資訊"""
    try:
        participants = Participant.query.all()
        total_count = len(participants)
        checked_in_count = db.session.query(CheckinLog).distinct(CheckinLog.participant_id).count()
        
        # 獲取每個參加者的報到狀態
        participants_data = []
        for participant in participants:
            checkin_record = CheckinLog.query.filter(
                CheckinLog.participant_id == participant.id
            ).first()
            
            participants_data.append({
                'id': participant.id,
                'name': participant.name,
                'email': participant.email,
                'organization': participant.organization or '未填寫',
                'competition_name': participant.competition_name or '未填寫',
                'seat_number': participant.seat_number or '未填寫',
                'is_checked_in': checkin_record is not None,
                'checkin_time': format_local_time(checkin_record.checkin_time, '%Y-%m-%d %H:%M:%S') if checkin_record else None
            })
        
        return jsonify({
            'success': True,
            'total_count': total_count,
            'checked_in_count': checked_in_count,
            'checkin_rate': round(checked_in_count / total_count * 100, 1) if total_count > 0 else 0,
            'participants': participants_data
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def api_search():
    """API: 搜尋參加者"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'message': '請輸入搜尋關鍵字'}), 400
    
    # 搜尋參加者（姓名、Email、組織、競賽名稱）
    participants = Participant.query.filter(
        db.or_(
            Participant.name.contains(query),
            Participant.email.contains(query),
            Participant.organization.contains(query),
            Participant.competition_name.contains(query),
            Participant.seat_number.contains(query)
        )
    ).all()
    
    results = []
    for p in participants:
        # 檢查報到狀態
        checkin_record = CheckinLog.query.filter(
            CheckinLog.participant_id == p.id
        ).first()
        
        results.append({
            'id': p.id,
            'name': p.name,
            'email': p.email,
            'organization': p.organization,
            'competition_name': p.competition_name,
            'seat_number': p.seat_number,
            'checkin_status': checkin_record is not None,
            'checkin_time': format_local_time(checkin_record.checkin_time, '%Y-%m-%d %H:%M:%S') if checkin_record else None
        })
    
    return jsonify({'success': True, 'results': results})

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """上傳Excel檔案並匯入參加者資料"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('沒有選擇檔案')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('沒有選擇檔案')
            return redirect(request.url)
        
        if file and file.filename.endswith('.xlsx'):
            try:
                # 讀取Excel檔案
                df = pd.read_excel(file)
                
                # 清空現有資料
                CheckinLog.query.delete()
                Participant.query.delete()
                
                # 匯入新資料
                count = 0
                for _, row in df.iterrows():
                    participant = _build_participant_from_row(row)
                    if participant:
                        db.session.add(participant)
                        count += 1
                
                db.session.commit()
                flash(f'成功匯入 {count} 筆參加者資料')
                
            except Exception as e:
                flash(f'匯入失敗: {str(e)}')
        
        return redirect(url_for('admin'))
    
    return render_template('upload.html')

@app.route('/qr_display/<int:participant_id>')
def qr_display(participant_id):
    
    participant = Participant.query.get_or_404(participant_id)
    return render_template('qr_display.html', participant=participant)

@app.route('/qr/<int:participant_id>')
def generate_qr(participant_id):
    
    participant = Participant.query.get_or_404(participant_id)
    
    # 生成QR Code內容：直接使用可點擊的完整簽到URL
    checkin_url = url_for('mobile_checkin', participant_id=participant.id, _external=True)
    
    # 生成QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(checkin_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 轉換為base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return render_template('qr_display.html', 
                         participant=participant, 
                         qr_code=img_str)

@app.route('/mobile_checkin/<int:participant_id>')
def mobile_checkin(participant_id):
    """手機報到頁面（透過QR Code掃描進入）"""
    participant = Participant.query.get_or_404(participant_id)
    
    # 檢查是否已經報到
    checkin_record = CheckinLog.query.filter(
        CheckinLog.participant_id == participant.id
    ).first()
    
    already_checked_in = checkin_record is not None
    
    return render_template('mobile_checkin.html', 
                         participant=participant, 
                         already_checked_in=already_checked_in)

@app.route('/api/mobile_checkin/<int:participant_id>', methods=['POST'])
def api_mobile_checkin(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    data = request.get_json(silent=True) or {}
    method = data.get('method', 'mobile')
    if method not in ('mobile', 'qr'):
        method = 'mobile'

    # 檢查是否已經報到
    existing_checkin = CheckinLog.query.filter(
        CheckinLog.participant_id == participant.id
    ).first()
    
    if existing_checkin:
        return jsonify({'success': False, 'message': '該參加者已經報到過了'}), 400
    
    # 記錄報到
    checkin_log = CheckinLog(
        participant_id=participant.id,
        checkin_method=method
    )
    db.session.add(checkin_log)
    db.session.commit()
    
    participant_payload = {
        'name': participant.name,
        'organization': participant.organization or '',
        'competition_name': participant.competition_name or '',
        'seat_number': participant.seat_number or '',
        'checkin_time': format_local_time(checkin_log.checkin_time),
    }

    return jsonify({
        'success': True,
        'message': f'{participant.name} 報到成功！',
        'participant': participant_payload
    })

@app.route('/manual_checkin/<int:participant_id>')
def manual_checkin(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    
    # 檢查是否已經報到
    existing_checkin = CheckinLog.query.filter(
        CheckinLog.participant_id == participant.id
    ).first()
    
    if existing_checkin:
        flash(f'{participant.name} 已經報到過了', 'warning')
    else:
        # 記錄報到
        checkin_log = CheckinLog(
            participant_id=participant.id,
            checkin_method='manual'
        )
        db.session.add(checkin_log)
        db.session.commit()
        flash(f'{participant.name} 報到成功！', 'success')
    
    return redirect(url_for('admin'))

@app.route('/export')
def export_data():
    """匯出報到資料"""
    try:
        # 查詢所有參加者和報到記錄
        participants = Participant.query.all()
        
        # 準備匯出資料
        export_data = []
        for participant in participants:
            checkin_record = CheckinLog.query.filter(
                CheckinLog.participant_id == participant.id
            ).first()
            
            export_data.append({
                '姓名': participant.name,
                'Email': participant.email or '',
                '電話': participant.phone or '',
                '組織/學校': participant.organization or '',
                '競賽名稱': participant.competition_name or '',
                '座號': participant.seat_number or '',
                '報到狀態': '已報到' if checkin_record else '未報到',
                '報到時間': format_local_time(checkin_record.checkin_time, '%Y-%m-%d %H:%M:%S') if checkin_record else '',
                '報到方式': checkin_record.checkin_method if checkin_record else ''
            })
        
        # 建立 DataFrame 並匯出
        df = pd.DataFrame(export_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='報到資料', index=False)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'AI_CUP_2025_報到資料_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        flash(f'匯出失敗: {str(e)}', 'error')
        return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)