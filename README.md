# 📰 News Digest Bot：每日 AI 新聞摘要機器人

每天自動爬取多個新聞網站，交給 LLM（**Gemini 或 Claude**，可自由切換）挑選重點並寫成繁體中文摘要，再推播到 Discord 或 LINE。

這個專案展示了一條完整的 AI 應用資料管線：**網頁爬蟲 → 資料清理與去重 → LLM 結構化輸出 → 第三方 API 推播 → 排程自動化**。

## 功能

- **爬蟲**：用 RSS 取得新聞清單，再抓原文頁面萃取內文（自動移除導覽列、廣告、script），抓取失敗時退回 RSS 摘要。以多執行緒並行抓取。
- **資料處理**：網址正規化（去除 `utm_*`、`fbclid` 等追蹤參數）、以網址與標題相似度去重、用 SQLite 記錄已推播的新聞，隔天不重複推送。
- **AI 摘要**：支援 Google Gemini（有免費額度）與 Anthropic Claude 兩家 LLM，用環境變數切換。一次把當天新聞交給模型，用 **JSON Schema 結構化輸出** 拿回「標題、摘要、分類、重要性分數」，程式端再驗證 ID、排序、截斷。英文新聞會自動翻成中文。
- **推播**：Discord Webhook（彩色 embed 卡片，依重要性上色）與 LINE Messaging API（push 或 broadcast），用統一的 `Notifier` 介面，新增平台只要多寫一個類別。
- **自動化**：GitHub Actions 每天台灣時間 08:00 自動執行，金鑰放在 GitHub Secrets。
- **測試**：23 個 pytest 測試，所有網路與 LLM 呼叫都用 mock，CI 不需要金鑰。

## 架構

```
config.yaml ──► fetcher.py ──► processing.py ──► summarizer.py ──► notifiers/
 (新聞來源)     RSS + 原文爬取   去重 / 已推播過濾    Gemini / Claude 摘要   Discord / LINE
                                     │                                    │
                                 data/sent.db ◄──────── 推播成功後記錄 ───┘
```

| 模組 | 說明 |
|---|---|
| `news_digest_bot/fetcher.py` | RSS 解析、時間窗過濾、原文內文萃取 |
| `news_digest_bot/processing.py` | 網址正規化、去重、`SentStore`（SQLite） |
| `news_digest_bot/summarizer.py` | Prompt 設計、共用 JSON Schema、Gemini / Claude 兩種 provider、拒答與截斷處理 |
| `news_digest_bot/formatter.py` | Markdown / 純文字排版 |
| `news_digest_bot/notifiers/` | Discord、LINE 推播 |
| `news_digest_bot/cli.py` | 串起整條流程的指令列入口 |

## 快速開始（Windows PowerShell）

1. 到 [Google AI Studio](https://aistudio.google.com/apikey) 免費申請 Gemini API 金鑰。
2. 在 PowerShell 執行：

```powershell
cd E:\Claude作品集\news-digest-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # 若出現「無法載入」，先執行：Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements-dev.txt

$env:GEMINI_API_KEY = "貼上你的金鑰"     # 只在這個視窗有效
python -m news_digest_bot --dry-run     # 只印出摘要，不推播

$env:DISCORD_WEBHOOK_URL = "你的 Webhook 網址"
python -m news_digest_bot               # 實際推播到 Discord
pytest -q                               # 跑測試（不需要金鑰）
```

想讓金鑰永久保存，可以改用 `setx GEMINI_API_KEY "金鑰"`，然後重開 PowerShell。

macOS / Linux 的話，把 `.\.venv\Scripts\Activate.ps1` 換成 `source .venv/bin/activate`，`$env:X = "..."` 換成 `export X="..."` 即可。

## 環境變數

| 變數 | 必填 | 說明 |
|---|---|---|
| `GEMINI_API_KEY` | 二擇一 | Gemini API 金鑰（Google AI Studio 免費申請） |
| `ANTHROPIC_API_KEY` | 二擇一 | Claude API 金鑰 |
| `LLM_PROVIDER` | | `gemini` 或 `claude`；不填時只要有 `GEMINI_API_KEY` 且沒有 Claude 金鑰，就自動用 Gemini |
| `GEMINI_MODEL` | | 預設 `gemini-flash-latest` |
| `CLAUDE_MODEL` | | 預設 `claude-opus-5-5` |
| `DISCORD_WEBHOOK_URL` | 用 Discord 時 | 頻道設定 → 整合 → Webhook |
| `LINE_CHANNEL_ACCESS_TOKEN` | 用 LINE 時 | LINE Developers 建立 Messaging API channel 取得 |
| `LINE_TO` | | 指定 user / group ID 就 push，留空則 broadcast 給所有好友 |

> LINE Notify 已於 2025 年 3 月停止服務，因此本專案使用 LINE Messaging API。

## 設定新聞來源

編輯 `config.yaml`，任何提供 RSS 的網站都能加入：

```yaml
sources:
  - name: iThome
    url: https://www.ithome.com.tw/rss
    category_hint: 科技
```

其他可調整項目：時間窗（`lookback_hours`）、每個來源最多幾則、最終推播幾則、是否抓全文、推播管道。

## 部署到 GitHub Actions

> workflow 檔放在 `deploy/github-actions/`。GitHub 只會執行 repo 根目錄 `.github/workflows/` 裡的檔案，請把它們複製過去；若這個資料夾在作品集 repo 的子目錄，記得在步驟裡加上 `working-directory: news-digest-bot`。

1. 到 repo 的 **Settings → Secrets and variables → Actions** 新增 `GEMINI_API_KEY`（或 `ANTHROPIC_API_KEY`）、`DISCORD_WEBHOOK_URL`（或 LINE 的兩個變數）。
2. `.github/workflows/daily-digest.yml` 會每天 UTC 00:00 執行，也可以在 Actions 頁面手動觸發。
3. 每次產生的摘要 Markdown 會上傳為 workflow artifact，已推播紀錄用 Actions cache 保留。

## 設計重點

- **為什麼一次送整批新聞，而不是一則一則摘要？** 讓模型能跨新聞比較重要性、合併同一事件的不同報導，也只需要一次 API 呼叫，成本與延遲都更低。
- **為什麼同時支援兩家 LLM？** 兩家共用同一份 prompt 與 JSON Schema，只有呼叫 API 的那一層不同，換模型不必動其他程式；Gemini 有免費額度適合個人每日使用，Claude 則可作為品質比較。
- **為什麼用結構化輸出？** JSON Schema 保證回傳格式可以直接解析，程式端只需處理商業邏輯（例如模型回傳不存在的 ID 時丟棄），不用寫脆弱的字串解析。
- **Prompt injection 防護**：新聞內文用 XML 標籤包起來，並在系統提示中明確要求忽略內文裡的任何指示。
- **錯誤處理**：單一來源失敗不影響其他來源；模型拒答或輸出被截斷時拋出明確錯誤；推播成功後才寫入已推播紀錄，失敗時隔天會重試。
- **金鑰安全**：所有金鑰只從環境變數讀取，`.env` 已加入 `.gitignore`。

## 可以再延伸的方向

- 依使用者興趣做個人化排序（embedding 相似度）
- 加入向量資料庫，支援「這週 AI 有什麼新聞？」的問答
- 用 FastAPI 做網頁版歷史摘要瀏覽
