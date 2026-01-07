#!/usr/bin/env python3
"""
Script untuk menambahkan admin ke bot trading.
Usage: python add_admin.py <CHAT_ID> [@username]
"""

import sys
from tg_bot.database import db

def add_admin(chat_id: int, username: str = None):
    """Tambah user sebagai admin

    Args:
        chat_id: Chat ID Telegram user (required)
        username: Username Telegram (optional, can be None)
    """
    try:
        # Tambah user jika belum ada (username sekarang optional)
        db.add_user(chat_id, username=username)

        # Set tier ke admin
        db.set_user_tier(chat_id, 'admin')

        # Verifikasi
        user = db.get_user(chat_id)
        tier = db.get_user_tier(chat_id)

        print(f"✅ Berhasil menambahkan admin!")
        print(f"   Chat ID: {chat_id}")
        if username:
            print(f"   Username: @{username}")
        print(f"   Tier: {tier}")
        print(f"   Role: {user.get('role', 'user')}")

        # Cek apakah benar-benar admin
        if db.is_admin(chat_id):
            print(f"   Status: ✅ Admin access confirmed")
        else:
            print(f"   Status: ❌ Warning - is_admin() returns False")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_admin.py <CHAT_ID> [@username]")
        print("\nExample:")
        print("  python add_admin.py 123456789")
        print("  python add_admin.py 123456789 @username")
        print("\nCara mendapatkan Chat ID:")
        print("  1. Chat dengan @userinfobot di Telegram")
        print("  2. Bot akan memberikan Chat ID Anda")
        sys.exit(1)

    try:
        chat_id = int(sys.argv[1])
        username = sys.argv[2] if len(sys.argv) > 2 else None

        # Remove @ from username if present
        if username and username.startswith('@'):
            username = username[1:]

        if add_admin(chat_id, username):
            print("\n✅ Admin berhasil ditambahkan!")
            print(f"\nSekarang user {chat_id} bisa menggunakan command admin:")
            print("  /users - List semua users")
            print("  /promote - Promote user ke admin")
            print("  /set_tier - Set tier user")
            print("  /grant_feature - Grant feature access")
            print("  /revoke_feature - Revoke feature access")
            print("  /stats - Bot statistics")
            print("  /broadcast - Broadcast message")
        else:
            sys.exit(1)

    except ValueError:
        print("❌ Error: Chat ID harus berupa angka")
        sys.exit(1)
