#!/usr/bin/env python
"""Djangoの管理タスク用コマンドラインユーティリティ。"""

import os
import sys


def main():
    """管理タスクを実行する。"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            'Djangoをインポートできませんでした。インストールされているか、'
            'PYTHONPATH環境変数で利用可能であることを確認してください。'
            '仮想環境を有効にし忘れていませんか？'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
