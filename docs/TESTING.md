# テスト・デバッグ手法

プロジェクトのテストおよびデバッグに関するドキュメントです。

## PDF生成機能のレイアウト確認

`reportlab` を用いて生成されるPDF（運用連絡票）のレイアウトを検証・修正するための手順です。

### 1. デバッグ用PDFの生成
サンプルの固定データを使用してPDFを生成し、`media/debug_pdf/latest.pdf` に保存するスクリプトを用意しています。

```bash
# Dockerコンテナ内で実行
docker-compose exec web python scripts/debug_pdf.py
```

### 2. ブラウザでの確認
生成されたPDFは、開発サーバー経由でブラウザから直接閲覧可能です。

*   URL: [http://localhost:8084/media/debug_pdf/latest.pdf](http://localhost:8084/media/debug_pdf/latest.pdf)

### 3. データ内容の変更
`scripts/debug_pdf.py` 内の `test_data` 辞書を修正することで、異なるパターン（施設数、チャンネル選択、文字数の増減など）でのレイアウト崩れを確認できます。

## 自動テスト (Playwright)

UIの動作確認には Playwright を使用します。

(今後、E2Eテストの実装が進んだらここに追記します)
