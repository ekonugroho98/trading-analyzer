"""
Cache Manager
Membersihkan dan mengelola file cache untuk mencegah pembengkakan storage
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import argparse

logger = logging.getLogger(__name__)


class CacheManager:
    """Manager untuk mengelola file cache"""

    def __init__(self, cache_dir: str = "data_cache", max_age_hours: int = 24):
        """
        Args:
            cache_dir: Directory cache
            max_age_hours: Maksimum umur cache dalam jam (default: 24 jam)
        """
        self.cache_dir = Path(cache_dir)
        self.max_age = timedelta(hours=max_age_hours)

    def clean_old_cache(self, dry_run: bool = False) -> dict:
        """
        Hapus file cache yang lebih lama dari max_age

        Args:
            dry_run: Jika True, hanya tampilkan file yang akan dihapus tanpa menghapus

        Returns:
            dict dengan statistik cleanup
        """
        if not self.cache_dir.exists():
            logger.warning(f"Cache directory not found: {self.cache_dir}")
            return {"deleted": 0, "total_size_mb": 0, "files": []}

        now = datetime.now()
        deleted_files = []
        total_size = 0

        # Cari semua file .csv di cache directory
        for cache_file in self.cache_dir.rglob("*.csv"):
            try:
                # Cek umur file berdasarkan modification time
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age = now - mtime

                if age > self.max_age:
                    file_size = cache_file.stat().st_size
                    total_size += file_size

                    if dry_run:
                        deleted_files.append({
                            "file": str(cache_file),
                            "size_kb": file_size / 1024,
                            "age_hours": age.total_seconds() / 3600
                        })
                    else:
                        cache_file.unlink()
                        deleted_files.append(str(cache_file))
                        logger.info(f"Deleted old cache: {cache_file} (age: {age.total_seconds()/3600:.1f}h)")

            except Exception as e:
                logger.error(f"Error processing {cache_file}: {e}")

        return {
            "deleted": len(deleted_files),
            "total_size_mb": total_size / (1024 * 1024),
            "files": deleted_files
        }

    def clean_duplicate_cache(self, symbol: str, interval: str, exchange: str = "binance", dry_run: bool = False) -> dict:
        """
        Hapus file cache duplikat untuk symbol yang sama, pertahankan yang terbaru

        Args:
            symbol: Symbol trading (contoh: BTCUSDT)
            interval: Timeframe (contoh: 4h)
            exchange: Nama exchange (default: binance)
            dry_run: Jika True, hanya tampilkan tanpa menghapus

        Returns:
            dict dengan statistik cleanup
        """
        exchange_dir = self.cache_dir / exchange
        if not exchange_dir.exists():
            return {"deleted": 0, "kept": 0, "files": []}

        # Pattern: {exchange}_{symbol}_{interval}_*.csv
        pattern = f"{exchange}_{symbol}_{interval}_*.csv"
        matching_files = list(exchange_dir.glob(pattern))

        if len(matching_files) <= 1:
            return {"deleted": 0, "kept": len(matching_files), "files": []}

        # Sort by modification time (terbaru dulu)
        matching_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Keep the newest, delete the rest
        files_to_delete = matching_files[1:]
        kept_file = matching_files[0]

        if dry_run:
            return {
                "deleted": len(files_to_delete),
                "kept": 1,
                "kept_file": str(kept_file),
                "files": [str(f) for f in files_to_delete]
            }

        for f in files_to_delete:
            f.unlink()
            logger.info(f"Deleted duplicate cache: {f}")

        return {
            "deleted": len(files_to_delete),
            "kept": 1,
            "kept_file": str(kept_file),
            "files": [str(f) for f in files_to_delete]
        }

    def get_cache_stats(self) -> dict:
        """Dapatkan statistik cache directory"""
        if not self.cache_dir.exists():
            return {"total_files": 0, "total_size_mb": 0, "by_exchange": {}}

        total_files = 0
        total_size = 0
        by_exchange = {}

        for exchange_dir in self.cache_dir.iterdir():
            if exchange_dir.is_dir():
                exchange_name = exchange_dir.name
                exchange_files = 0
                exchange_size = 0

                for cache_file in exchange_dir.glob("*.csv"):
                    exchange_files += 1
                    exchange_size += cache_file.stat().st_size

                by_exchange[exchange_name] = {
                    "files": exchange_files,
                    "size_mb": exchange_size / (1024 * 1024)
                }

                total_files += exchange_files
                total_size += exchange_size

        return {
            "total_files": total_files,
            "total_size_mb": total_size / (1024 * 1024),
            "by_exchange": by_exchange
        }


def main():
    """CLI untuk cache management"""
    parser = argparse.ArgumentParser(description="Cache Manager for Crypto Trading Analyzer")
    parser.add_argument("--cache-dir", default="data_cache", help="Cache directory path")
    parser.add_argument("--max-age", type=int, default=24, help="Max cache age in hours")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--clean-duplicates", action="store_true", help="Clean duplicate cache files")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    manager = CacheManager(cache_dir=args.cache_dir, max_age_hours=args.max_age)

    # Show stats
    if args.stats or not args.clean_duplicates:
        print("\n" + "="*60)
        print("CACHE STATISTICS")
        print("="*60)
        stats = manager.get_cache_stats()
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Size: {stats['total_size_mb']:.2f} MB")

        for exchange, data in stats['by_exchange'].items():
            print(f"\n{exchange.upper()}:")
            print(f"  Files: {data['files']}")
            print(f"  Size: {data['size_mb']:.2f} MB")
        print("="*60 + "\n")

    # Clean old cache
    if not args.clean_duplicates:
        print(f"Cleaning cache older than {args.max_age} hours...")
        result = manager.clean_old_cache(dry_run=args.dry_run)

        if args.dry_run:
            print(f"\nWould delete {result['deleted']} files ({result['total_size_mb']:.2f} MB)")
            for file_info in result['files'][:10]:  # Show first 10
                print(f"  - {file_info['file']} ({file_info['age_hours']:.1f}h old, {file_info['size_kb']:.1f} KB)")
            if len(result['files']) > 10:
                print(f"  ... and {len(result['files']) - 10} more files")
        else:
            print(f"Deleted {result['deleted']} files ({result['total_size_mb']:.2f} MB)")

    # Clean duplicates
    if args.clean_duplicates:
        print("\nCleaning duplicate cache files...")
        # Find all unique symbol+interval combinations
        from collections import defaultdict
        combinations = defaultdict(set)

        for exchange_dir in Path(args.cache_dir).iterdir():
            if exchange_dir.is_dir():
                for cache_file in exchange_dir.glob("*.csv"):
                    # Parse filename: exchange_symbol_interval_timestamp.csv
                    parts = cache_file.stem.split('_')
                    if len(parts) >= 4:
                        exchange = parts[0]
                        symbol = parts[1]
                        interval = parts[2]
                        combinations[(exchange, interval)].add(symbol)

        deleted_total = 0
        for (exchange, interval), symbols in combinations.items():
            for symbol in symbols:
                result = manager.clean_duplicate_cache(
                    symbol=symbol,
                    interval=interval,
                    exchange=exchange,
                    dry_run=args.dry_run
                )
                deleted_total += result['deleted']

                if args.dry_run and result['deleted'] > 0:
                    print(f"  {exchange}/{symbol}/{interval}: would delete {result['deleted']} duplicates, keep 1")

        if not args.dry_run:
            print(f"Deleted {deleted_total} duplicate files")


if __name__ == "__main__":
    main()
