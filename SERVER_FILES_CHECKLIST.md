# Server Deployment Files Checklist

## ✅ File yang PERLU di-Upload Manual

### 1. **.env** (WAJIB - Wajib Dibuat Manual)
Ini adalah SATU-SATUNYA file yang wajib Anda buat manual di server.

```bash
# Di server, setelah clone repository:
cd /opt/crypto-trading-analyzer
cp .env.example .env
nano .env

# Isi dengan credentials Anda:
TELEGRAM_BOT_TOKEN=your_bot_token_here
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

**Cara dapat credentials:**
- **Telegram Bot Token**: Chat @BotFather di Telegram, kirim `/newbot`
- **Binance API Key**: Login ke Binance, buka API Management
- **DeepSeek API Key**: Daftar di https://platform.deepseek.com/

---

## ❌ File yang TIDAK PERLU di-Upload (Auto-Generated)

File-file ini akan otomatis dibuat oleh script `deploy.sh` atau saat aplikasi jalan:

### 1. Database Files
```
- *.db, *.sqlite, *.sqlite3
- /var/lib/crypto-trading-analyzer/trading_bot.db (auto-created)
```

### 2. Log Files
```
- *.log
- /opt/crypto-trading-analyzer/logs/*.log (auto-created)
```

### 3. Cache Files
```
- data_cache/*.csv
- __pycache__/
- *.pyc
```

### 4. Python Virtual Environment
```
- venv/ (auto-created oleh deploy.sh)
```

### 5. Session Files
```
- *.session (Telegram session files)
```

---

## 📋 Cara Deploy yang Benar

### Option 1: Automated Deploy (RECOMMENDED)

```bash
# Di server, jalankan satu command ini:
bash <(curl -s https://raw.githubusercontent.com/ekonugroho98/trading-analyzer/main/deploy.sh)
```

Script ini akan:
- ✅ Clone repository dari GitHub
- ✅ Create virtual environment
- ✅ Install semua dependencies
- ✅ Initialize database
- ✅ Create systemd service
- ✅ Start service

**Anda hanya perlu:**
1. Edit `.env` file dengan credentials Anda
2. Test bot di Telegram

---

### Option 2: Manual Deploy

Jika mau deploy manual:

```bash
# 1. Clone repository
cd /opt
sudo mkdir crypto-trading-analyzer
sudo chown $USER:$USER crypto-trading-analyzer
cd crypto-trading-analyzer
git clone https://github.com/ekonugroho98/trading-analyzer.git .

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env FILE (SATU-SATUNYA file manual)
cp .env.example .env
nano .env
# Isi dengan credentials Anda

# 5. Initialize database
python3 -c "from tg_bot.database import Database; db = Database(); db.init_db()"

# 6. Start service
sudo systemctl start crypto-trading-bot
```

---

## 🎯 Summary

### Yang PERLU Anda lakukan:
1. **Clone repository** (via `git clone` atau `deploy.sh`)
2. **Buat file `.env`** dengan credentials Anda
3. **Jalankan bot**

### Yang TIDAK PERLU:
- ❌ Upload `*.db` files (auto-created)
- ❌ Upload `*.log` files (auto-created)
- ❌ Upload `data_cache/` folder (auto-created)
- ❌ Upload `venv/` folder (auto-created)
- ❌ Upload `__pycache__/` folder (auto-created)

---

## 🔒 Security Best Practices

### JANGAN PERNAH upload ke server:
- ❌ Local `.env` dari development machine (create baru di server)
- ❌ Local database files
- ❌ Local log files
- ❌ Local cache files

### SELALU lakukan di server:
- ✅ Create fresh `.env` from `.env.example`
- ✅ Let application create fresh database
- ✅ Start with clean state

---

## 📝 Quick Command Reference

```bash
# Setelah deploy, check status:
sudo systemctl status crypto-trading-bot

# View logs:
sudo journalctl -u crypto-trading-bot -f

# Restart service:
sudo systemctl restart crypto-trading-bot

# Edit .env jika perlu:
nano /opt/crypto-trading-analyzer/.env
sudo systemctl restart crypto-trading-bot
```

---

## ✅ Deployment Checklist

Sebelum deploy ke server:
- [ ] Anda punya akses SSH ke server
- [ ] Python 3.8+ sudah terinstall di server
- [ ] Anda sudah punya Telegram Bot Token
- [ ] Anda sudah punya Binance API Key & Secret
- [ ] Anda sudah punya DeepSeek API Key

Saat deploy:
- [ ] Clone repository atau run `deploy.sh`
- [ ] Create `.env` file dengan credentials
- [ ] Database berhasil di-initialize
- [ ] Service berhasil di-start
- [ ] Bot merespon `/start` command di Telegram

---

**Bottom Line:** Hanya **.env** file yang perlu Anda buat manual. Semua file lain akan otomatis di-handle oleh script deployment atau aplikasi.
