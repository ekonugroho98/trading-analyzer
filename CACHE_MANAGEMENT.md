# Cache Management Guide

## Overview

File cache di `data_cache/` digunakan untuk menyimpan data dari exchange (Binance, Bybit) secara temporary untuk mengurangi API calls. Namun, file-file ini bisa terus bertambah jika tidak dikelola.

## Problem

1. **Duplikat**: Setiap kali fetch data, file baru dibuat dengan timestamp berbeda
2. **File lama**: Cache lama tidak otomatis terhapus
3. **Storage bengkak**: Lama-kelamaan bisa memakan banyak space

## Solution: Cache Manager

`cache_manager.py` menyediakan tools untuk mengelola cache files.

### Usage

#### 1. Lihat Statistik Cache
```bash
python cache_manager.py --stats
```
Output:
```
============================================================
CACHE STATISTICS
============================================================
Total Files: 5
Total Size: 0.05 MB

BINANCE:
  Files: 5
  Size: 0.05 MB
============================================================
```

#### 2. Bersihkan Duplikat
```bash
# Cek dulu (dry run)
python cache_manager.py --clean-duplicates --dry-run

# Hapus duplikat (keep newest)
python cache_manager.py --clean-duplicates
```

#### 3. Bersihkan Cache Lama (berdasarkan umur)
```bash
# Default: 24 jam
python cache_manager.py --max-age 24

# Custom: 6 jam
python cache_manager.py --max-age 6

# Dry run dulu
python cache_manager.py --max-age 24 --dry-run
```

#### 4. Gabungan (All-in-one)
```bash
# Bersihkan duplikat + cache lama lebih dari 12 jam
python cache_manager.py --clean-duplicates --max-age 12
```

## Automated Cleanup

### Cron Job (Linux/Mac)

Tambahkan ke crontab (`crontab -e`):
```bash
# Jalankan setiap jam, bersihkan cache lebih dari 6 jam
0 * * * * cd /path/to/trading-analyzer && python cache_manager.py --clean-duplicates --max-age 6
```

### Windows Task Scheduler

Buat scheduled task yang menjalankan:
```cmd
python C:\path\to\trading-analyzer\cache_manager.py --clean-duplicates --max-age 6
```

## Best Practices

1. **Regular Cleanup**: Jalankan cache manager secara regular (daily/hourly)
2. **Dry Run First**: Selalu gunakan `--dry-run` sebelum menghapus
3. **Set Appropriate TTL**: Sesuaikan `--max-age` dengan kebutuhan (default 24 jam)
4. **Monitor Size**: Cek `--stats` secara regular untuk memantau pertumbuhan cache

## Git Ignore

Semua file cache sudah di-ignore di `.gitignore`:
```
data_cache/*.csv
data_cache/*/*.csv
```

Jadi cache files tidak akan ter-commit ke repository.

## Technical Details

### File Naming Convention

Format: `{exchange}_{symbol}_{interval}_{timestamp}.csv`

Example:
- `binance_BTCUSDT_4h_20251231_122131.csv`
- `bybit_ETHUSDT_1h_20251231_003859.csv`

### Cache Logic

1. **Fetching data**: Cek cache dulu, jika ada dan masih fresh, gunakan cache
2. **Saving**: Simpan ke file dengan timestamp baru
3. **Duplicate**: Symbol+interval yang sama akan membuat file baru
4. **Cleanup**: Manual via cache manager atau automated via cron

## Troubleshooting

### Cache tidak terbaca?
Pastikan file ada dan formatnya benar:
```bash
ls -lh data_cache/binance/
```

### Cache manager tidak jalan?
Cek permission dan path:
```bash
python cache_manager.py --stats
```

### Size terus bertambah?
Jalankan cleanup yang lebih agresif:
```bash
python cache_manager.py --clean-duplicates --max-age 1
```
