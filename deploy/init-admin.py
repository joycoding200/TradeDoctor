#!/usr/bin/env python3
"""
TradeDoctor — 管理员账户初始化/更新脚本

用法：
    # 通过环境变量（推荐，不会出现在进程列表中）
    ADMIN_PASSWORD=YourPassword python ../deploy/init-admin.py --email admin@example.com

    # 或交互式输入（不在终端回显）
    python ../deploy/init-admin.py --email admin@example.com

    # 更新已有管理员密码
    python ../deploy/init-admin.py --email admin@example.com --update

功能：
    1. 检查数据库连接
    2. 检查管理员是否已存在
    3. 不存在则创建（is_admin=True）
    4. --update 则更新密码
"""
import argparse
import getpass
import sys
import os

# 确保能导入 app 模块
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, os.path.abspath(backend_dir))

from app.database import SessionLocal
from app.models.user import User
from app.auth.jwt import hash_password


def main():
    parser = argparse.ArgumentParser(description='创建或更新管理员账户')
    parser.add_argument('--email', required=True, help='管理员邮箱（登录用）')
    parser.add_argument('--nickname', default='管理员', help='昵称（默认：管理员）')
    parser.add_argument('--update', action='store_true', help='更新已有管理员密码')
    args = parser.parse_args()

    # 密码：优先从环境变量读取（不在进程列表中暴露），否则交互式输入
    password = os.environ.get('ADMIN_PASSWORD')
    if password:
        print('从环境变量 ADMIN_PASSWORD 读取密码')
    else:
        password = getpass.getpass('管理员密码（输入时不回显）：')

    # 密码强度校验（与注册接口一致）
    if len(password) < 8:
        print('错误：密码至少 8 位')
        sys.exit(1)
    if not any(c.isalpha() for c in password):
        print('错误：密码必须包含字母')
        sys.exit(1)
    if not any(c.isdigit() for c in password):
        print('错误：密码必须包含数字')
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            User.email == args.email, User.is_admin == True
        ).first()

        if existing and not args.update:
            print(f'管理员 {args.email} 已存在（ID: {existing.id}）')
            print('如需更新密码，加 --update 参数')
            sys.exit(0)

        if existing and args.update:
            existing.password_hash = hash_password(password)
            db.commit()
            print(f'管理员密码已更新：{args.email}')
        else:
            # 检查邮箱是否被普通用户占用
            email_user = db.query(User).filter(User.email == args.email).first()
            if email_user:
                print(f'错误：邮箱 {args.email} 已被普通用户占用')
                print('请使用其他邮箱，或先删除该用户')
                sys.exit(1)

            admin = User(
                email=args.email,
                nickname=args.nickname,
                is_admin=True,
                password_hash=hash_password(password),
            )
            db.add(admin)
            db.commit()
            print(f'管理员创建成功：{args.email}（ID: {admin.id}）')

        print('可用此账号在前端 Admin 页面登录')

    except Exception as e:
        print(f'错误：{e}')
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
