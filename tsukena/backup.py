"""DB のバックアップを取る。`python -m tsukena.backup <保存先のフォルダ>` で実行する。

systemd のタイマーから毎日1回呼ぶ（→ docs/design.md 11、deploy/systemd/）。
API が書き込み中でも壊れない写しを作るため、ファイルのコピーではなく SQLite のバックアップの仕組みを使う。
保存先は同じ機械の中なので、機械の故障には備えられない（→ 残課題 R-2）。
"""

import datetime
import sqlite3
import sys
from pathlib import Path

from .config import load_db_path

# 何日分を残すか
KEEP_DAYS = 30


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("使い方: python -m tsukena.backup <保存先のフォルダ>")
    backup_dir = Path(sys.argv[1])
    backup_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.date.today()
    dest = backup_dir / f"tsukena-{today.isoformat()}.db"
    src = sqlite3.connect(load_db_path())
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    print(f"バックアップを取りました: {dest}")

    # 名前の日付で古いものを消す。ファイルの更新日時はコピーで変わることがあるため使わない
    oldest = today - datetime.timedelta(days=KEEP_DAYS)
    for old in backup_dir.glob("tsukena-*.db"):
        try:
            day = datetime.date.fromisoformat(old.stem.removeprefix("tsukena-"))
        except ValueError:
            continue
        if day < oldest:
            old.unlink()


if __name__ == "__main__":
    main()
