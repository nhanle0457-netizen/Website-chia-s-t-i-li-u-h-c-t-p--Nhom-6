import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Doc

app = Flask(__name__)

app.secret_key = 'mat_khau_session_sieu_bao_mat_cua_ban'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# lưu trữ file và tạo thư mục tự động nếu chưa có
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Trang chủ: Truy vấn dữ liệu dựa trên quyền hạn (Admin vs User)"""
    search = request.args.get('search', '')
    user_name = session.get('username')
    is_admin = session.get('role') == 'admin'   
    query = Doc.query
    
    # Logic lọc: Nếu không phải admin, chỉ thấy tài liệu đã duyệt HOẶC tài liệu của chính mình
    if not is_admin:
        query = query.filter((Doc.status == 'approved') | (Doc.username == user_name))   
    # Logic tìm kiếm: Tìm kiếm không phân biệt hoa thường theo tiêu đề hoặc mô tả
    if search:
        search_filter = f'%{search}%'
        query = query.filter(Doc.title.ilike(search_filter) | Doc.description.ilike(search_filter))       
    docs = query.order_by(Doc.id.desc()).all()
    return render_template('index.html', docs=docs, search=search)

@app.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    """Admin duyệt bài: Cập nhật trạng thái trong DB"""
    if session.get('role') == 'admin':
        doc = Doc.query.get_or_404(id) 
        doc.status = 'approved'
        db.session.commit() 
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        action = request.form['action']       
        
        if action == 'register':
            if not User.query.filter_by(username=username).first():
                role = 'admin' if username.lower() == 'admin' else 'user'
                hashed_password = generate_password_hash(password)
                new_user = User(username=username, password=hashed_password, role=role)
                db.session.add(new_user)
                db.session.commit()
                flash('Đăng ký tài khoản thành công! Vui lòng đăng nhập.', 'success')
                return redirect(url_for('login')) # Chuyển về trang đăng nhập
            else:
                flash('Tên người dùng đã tồn tại!', 'danger')        
        else: # action == 'login'
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                session['username'], session['role'] = user.username, user.role
                return redirect(url_for('index'))
            else:
                flash('Sai tên đăng nhập hoặc mật khẩu!', 'danger')
                
    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Tải file lên server an toàn và lưu thông tin vào DB"""
    if 'username' not in session: 
        return redirect(url_for('login'))        
    if request.method == 'POST':
        file = request.files['file']
        if file and request.form['title']:
            # BẢO MẬT: Chuyển tên file về dạng an toàn (tránh lỗi kí tự đặc biệt, tấn công path traversal)
            safe_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_filename))            
            is_admin = session.get('role') == 'admin'
            status = 'approved' if is_admin else 'pending'           
            new_doc = Doc(title=request.form['title'], description=request.form['description'], 
                          filename=safe_filename, username=session['username'], status=status)
            db.session.add(new_doc)
            db.session.commit()            
            if not is_admin:
                flash('Tài liệu của bạn đã được đăng và đang chờ Admin duyệt!', 'success')
            else:
                flash('Tài liệu đã được đăng thành công', 'success')           
            return redirect(url_for('index'))
    return render_template('upload.html', doc=None)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Sửa thông tin tài liệu (Chủ sở hữu HOẶC Admin đều được sửa)"""
    doc = Doc.query.get_or_404(id)
    if doc.username != session.get('username') and session.get('role') != 'admin': 
        return redirect(url_for('index'))            
    if request.method == 'POST':
        doc.title = request.form['title']
        doc.description = request.form['description']
        if session.get('role') != 'admin':
            doc.status = 'pending'
        db.session.commit()
        flash('Đã cập nhật tài liệu!', 'success')
        return redirect(url_for('index'))       
    return render_template('upload.html', doc=doc)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """Xóa file vật lý trên ổ cứng và xóa bản ghi trong DB"""
    doc = Doc.query.get_or_404(id)
    if doc.username == session.get('username') or session.get('role') == 'admin':
        try: 
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], doc.filename))
        except: 
            pass  # Bỏ qua nếu file vật lý không tìm thấy
        db.session.delete(doc)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download(filename):
    """Kiểm tra quyền hạn trước khi cho phép tải file xuống"""
    doc = Doc.query.filter_by(filename=filename).first_or_404()
    if doc.status == 'approved' or doc.username == session.get('username') or session.get('role') == 'admin':
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Đăng xuất, xóa toàn bộ thông tin phiên làm việc"""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
