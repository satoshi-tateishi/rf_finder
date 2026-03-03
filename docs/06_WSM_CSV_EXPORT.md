# WSM用CSVエクスポート機能の調査と実装計画

Sennheiser Wireless Systems Manager (WSM) で周波数除外/許可リストとして読み込める、セミコロン区切りのCSVエクスポート機能についての調査結果と実装計画です。

## 1. WSM CSV 形式の概要

- **ファイル形式**: CSV (セミコロン `;` 区切り)
- **文字エンコーディング**: UTF-8
- **改行コード**: `
` (LF)
- **ヘッダー**: `name;type;frequency;tolerance;minfrequency;maxfrequency;priority;squelchlevel`

## 2. フィールド詳細

| フィールド | 説明 | 値の決定ルール |
| :--- | :--- | :--- |
| `name` | チャンネル名 | `TV 13` 〜 `TV 53` |
| `type` | ゾーン種別 | `2`: 許可 (Included) - ユーザーが選択したCH<br>`3`: 除外 (Excluded) - それ以外のCH |
| `frequency` | 代表周波数 | `0` (範囲指定のため不要) |
| `tolerance` | 許容誤差 | `0` (範囲指定のため不要) |
| `minfrequency` | 開始周波数 (kHz) | チャンネルの開始周波数。ガードバンド適用により±1000調整。 |
| `maxfrequency` | 終了周波数 (kHz) | チャンネルの終了周波数。ガードバンド適用により±1000調整。 |
| `priority` | 優先度 | `2`: 選択したCH<br>`4`: それ以外 |
| `squelchlevel` | スケルチ | `5` (固定値) |

## 3. 業務ロジック (ガードバンド計算)

隣接するチャンネルの空き状況（施設マスタでの `○` の有無）が切り替わる境界において、1MHz (1000kHz) のガードバンドを設定し、シームレスな連結を維持します。

### 基本ルール
- **ch13の下限 (470MHz)**: ガードバンドを設定しない。
- **ch53の上限 (714MHz)**: ガードバンドを設定しない。
- **境界の調整**:
  - 現在の ch が「空き」で、前の ch が「空きでない」場合: `min_f` を +1000kHz する。
  - 現在の ch が「空きでない」で、前の ch が「空き」の場合: `min_f` を -1000kHz する。
  - 現在の ch が「空き」で、次の ch が「空きでない」場合: `max_f` を -1000kHz する。
  - 現在の ch が「空きでない」で、次の ch が「空き」の場合: `max_f` を +1000kHz する。

※このロジックにより、利用可能な帯域が 1MHz 狭まり、その分が「除外帯域」として扱われるようになります。

### 追加除外帯域 (Blocked)
ch53 より上の A 帯域外を明示的に除外するため、以下の行を末尾に追加します。
- `Blocked;3;0;0;714000;798000;4;5`

## 4. 実装内容 (rf_finder)

### 4.1 バックエンド
1. **Service層**: `apps/adjustments/services/wsm_service.py`
   - `Facility` と選択チャンネルリストを元に CSV 文字列を生成。
   - 隣接チャンネルの空き状況に基づくガードバンド（1MHz）の自動計算ロジックを内包。
2. **View層**: `apps/adjustments/views.py` の `export_wsm`
   - JSON リクエストを受け取り、生成された CSV を `HttpResponse` で返却。
   - ファイル名は `wsm_{施設名}_{YYYYMMDD}.csv` 形式。

### 4.2 フロントエンド
1. **API連携**: `static/js/api.js` に `exportWSM` メソッドを追加。
2. **UI制御**: `static/js/ui-controller.js`
   - 各施設のチャンネル選択グリッド上部に「WSM CSV」ボタンを配置。
   - **動的制御**: チャンネルが 1 つも選択されていない場合はボタンを無効化（グレーアウト）。選択されると有効化。
   - `handleExportWSM` 関数により、非同期でのファイル生成と自動ダウンロードを実行。

## 5. テストと品質
- `apps/adjustments/tests/test_wsm_service.py` により、ガードバンド計算と CSV 形式の正当性を自動検証済み。
- `ruff` によるコード整形を適用。
