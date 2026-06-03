from flask_sqlalchemy import SQLAlchemy

# Khởi tạo đối tượng db độc lập để tránh lỗi vòng lặp import (circular import)
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Lưu mật khẩu đã mã hóa (hash)
    role = db.Column(db.String(20), default='user')       # Phân quyền: user hoặc admin

class Doc(db.Model):
    __tablename__ = 'docs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(200))                  # Lưu tên file an toàn sau khi upload
    username = db.Column(db.String(80))                   # Người sở hữu tài liệu user ỏ admin
    status = db.Column(db.String(20), default='pending')  # Trạng thái: pending/approved
