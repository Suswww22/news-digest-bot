# 📰 News Digest Bot：每日 AI 新聞摘要機器人

每天自動爬取多個新聞網站，交給 Claude 挑選重點並寫成繁體中文摘要，再推播到 Discord 或 LINE。

這個專案展示了一條完整的 AI 應用資料管線：**網頁爬蟲 → 資料清理與去重 → LLM 結構化輸出 → 第三方 API 推播 → 排程自動化**。

## 功能

- **爬蟲**：用 RSS 取得新聞清單，再抓原文頁面萃取內文（自動移除導覽列、廣告、script），抓取失敗時退回 RSS 摘要。以多執行緒並行抓取。
- **資料處理**：網址正規化（去除 `utm_*`、`fbclid` 等追蹤參數）、以網址與標題相似度去重、用 SQLite 記錄已推播的新聞，隔天不重複推送。
- **AI 摘要**：一次把當天新聞交給 Claude，用 **JSON Schema 結構化輸出** 拿回「標題、摘要、分類、重要性分數」，程式端再驗證 ID、排序、截斷。英文新聞會自動翻成中文。
- **推播**：Discord Webhook（彩色 embed 卡片，依重要性上色）與 LINE Messaging API（push 或 broadcast），用統一的 `Notifier` 介面，新增平台只要多寫一個類別。
- **自動化**：GitHub Actions 每天台灣時間 08:00 自動執行，金鑰放在 GitHub Secrets。
- **測試**：17 個 pytest 測試，所有網路與 LLM 呼叫都用 mock，CI 不需要金鑰。

## 架構

```
config.yaml ──► fetcher.py ──► processing.py ──► summarizer.py ──► notifiers/
 (新聞來源)     RSS + 原文爬取   去重 / 已推播過濾    Claude 結構化摘要     Discord / LINE
                                     │                                    │
                                 data/sent.db ◄──────── 推播成功後記錄 ───┘
```

| 模組 | 說明 |
|---|---|
| `news_digest_bot/fetcher.py` | RSS 解析、時間窗過濾、原文內文萃取 |
| `news_digest_bot/processing.py` | 網址正規化、去重、`SentStore`（SQLite） |
| `news_digest_bot/summarizer.py` | Prompt 設計、JSON Schema、拒答與截斷處理 |
| `news_digest_bot/formatter.py` | Markdown / 純文字排版 |
| `news_digest_bot/notifiers/` | Discord、LINE 推播 |
| `news_digest_bot/cli.py` | 串起整條流程的指令列入口 |

## 快速開始

```bash
git clone https://github.com/Suswww22/news-digest-bot.git
cd news-digest-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env      # 填入金鑰（.env 不會被提交）
export $(grep -v '^#' .env | xargs)

python -m news_digest_bot --dry-run   # 只印出摘要，不推播
python -m news_digest_bot             # 實際推播
pytest -q                             # 跑測試
```

## 環境變數

| 變數 | 必填 | 說明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude API 金鑰 |
| `CLAUDE_MODEL` | | 預設 `claude-opus-5-5`，可改成其他 Claude 模型 |
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

1. 到 repo 的 **Settings → Secrets and variables → Actions** 新增 `ANTHROPIC_API_KEY`、`DISCORD_WEBHOOK_URL`（或 LINE 的兩個變數）。
2. `.github/workflows/daily-digest.yml` 會每天 UTC 00:00 執行，也可以在 Actions 頁面手動觸發。
3. 每次產生的摘要 Markdown 會上傳為 workflow artifact，已推播紀錄用 Actions cache 保留。

## 設計重點

- **為什麼一次送整批新聞，而不是一則一則摘要？** 讓模型能跨新聞比較重要性、合併同一事件的不同報導，也只需要一次 API 呼叫，成本與延遲都更低。
- **為什麼用結構化輸出？** JSON Schema 保證回傳格式可以直接解析，程式端只需處理商業邏輯（例如模型回傳不存在的 ID 時丟棄），不用寫脆弱的字串解析。
- **Prompt injection 防護**：新聞內文用 XML 標籤包起來，並在系統提示中明確要求忽略內文裡的任何指示。
- **錯誤處理**：單一來源失敗不影響其他來源；模型拒答或輸出被截斷時拋出明確錯誤；推播成功後才寫入已推播紀錄，失敗時隔天會重試。
- **金鑰安全**：所有金鑰只從環境變數讀取，`.env` 已加入 `.gitignore`。

## 可以再延伸的方向

- 依使用者興趣做個人化排序（embedding 相似度）
- 加入向量資料庫，支援「這週 AI 有什麼新聞？」的問答
- 用 FastAPI 做網頁版歷史摘要瀏覽
