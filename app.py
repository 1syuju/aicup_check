import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import pandas as pd
import qrcode
import io
import base64
from datetime import datetime

# 寫死Excel名單路徑（Windows）
FIXED_XLSX_PATH = r"C:\\Users\\USER\\Desktop\\python\\aicup2025_1\\AI CUP 2025 教育部獎狀總整理.xlsx"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///checkin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

# 資料庫模型
class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    organization = db.Column(db.String(200), nullable=True)
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

# 建立資料庫表格
with app.app_context():
    try:
        db.create_all()
        print('資料庫表格建立成功')
        
        # 自動匯入參加者資料（如果資料庫是空的）
        try:
            if os.path.exists(FIXED_XLSX_PATH) and db.session.query(Participant).count() == 0:
                df = pd.read_excel(FIXED_XLSX_PATH)
                count = 0
                for _, row in df.iterrows():
                    name = str(row.get('人名中文', '')).strip()
                    if name and name != 'nan' and name != 'NaN':
                        participant = Participant(
                            name=name,
                            email='',
                            phone='',
                            organization=str(row.get('校名中文', '')).strip() if '校名中文' in df.columns else ''
                        )
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
            name = str(row.get('人名中文', '')).strip()
            if name and name != 'nan' and name != 'NaN':
                participant = Participant(
                    name=name,
                    email='',
                    phone='',
                    organization=str(row.get('校名中文', '')).strip() if '校名中文' in df.columns else ''
                )
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
    """首頁 - 顯示報到系統選項"""
    return render_template('index.html')

@app.route('/checkin')
def checkin():
    """報到介面 - 給參加者使用"""
    return render_template('checkin.html')

from flask import abort, request
@app.route('/admin')
def admin():
    # 只允許本機存取
    if request.remote_addr != '127.0.0.1':
        abort(403)
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
    
    return jsonify({
        'success': True, 
        'message': f'{participant.name} 報到成功！',
        'participant': {
            'name': participant.name,
            'organization': participant.organization
        }
    })

@app.route('/api/search', methods=['POST'])
def api_search():
    """API: 搜尋參加者"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'message': '請輸入搜尋關鍵字'}), 400
    
    # 搜尋參加者（姓名、Email、組織）
    participants = Participant.query.filter(
        db.or_(
            Participant.name.contains(query),
            Participant.email.contains(query),
            Participant.organization.contains(query)
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
            'checkin_status': checkin_record is not None,
            'checkin_time': checkin_record.checkin_time.strftime('%Y-%m-%d %H:%M:%S') if checkin_record else None
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
                Participant.query.delete()
                CheckinLog.query.delete()
                
                # 匯入新資料
                for _, row in df.iterrows():
                    participant = Participant(
                        name=str(row.get('姓名', '')),
                        email=str(row.get('Email', '')),
                        phone=str(row.get('電話', '')),
                        organization=str(row.get('組織/學校', ''))
                    )
                    db.session.add(participant)
                
                db.session.commit()
                flash(f'成功匯入 {len(df)} 筆參加者資料')
                
            except Exception as e:
                flash(f'匯入失敗: {str(e)}')
        
        return redirect(url_for('admin'))
    
    return render_template('upload.html')

@app.route('/qr_display/<int:participant_id>')
def qr_display(participant_id):
    """顯示參加者的QR Code報到頁面"""
    participant = Participant.query.get_or_404(participant_id)
    return render_template('qr_display.html', participant=participant)

@app.route('/qr/<int:participant_id>')
def generate_qr(participant_id):
    """為特定參加者生成QR Code（保留原有功能）"""
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

@app.route('/qr_scanner')
def qr_scanner():
    """QR Code掃描器頁面"""
    return render_template('qr_scanner.html')

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
    
    # 檢查是否已經報到
    existing_checkin = CheckinLog.query.filter(
        CheckinLog.participant_id == participant.id
    ).first()
    
    if existing_checkin:
        return jsonify({'success': False, 'message': '該參加者已經報到過了'}), 400
    
    # 記錄報到
    checkin_log = CheckinLog(
        participant_id=participant.id,
        checkin_method='mobile'
    )
    db.session.add(checkin_log)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'{participant.name} 報到成功！',
        'participant': {
            'name': participant.name,
            'organization': participant.organization
        }
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
                '報到狀態': '已報到' if checkin_record else '未報到',
                '報到時間': checkin_record.checkin_time.strftime('%Y-%m-%d %H:%M:%S') if checkin_record else '',
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