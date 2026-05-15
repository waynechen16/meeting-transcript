# Phase 1 任務分解

每個任務都是一個獨立的 Claude Code session。**先 plan，後 implement**。
完成一個任務後 commit，然後開新 session 做下一個。

進入下一個任務前 Claude Code 不需要記得上一個任務的細節 — 所有重要 context 都在程式碼、CLAUDE.md、與 PHASE1_TASKS.md 裡。

---

## 工作模式建議

### Session 開始時
1. `claude` 啟動
2. 開頭說明要做的任務 ID（例如「來做 P1-3」）
3. 切到 plan mode（`/plan` 或 `claude --plan`）
4. 請 Claude 讀 @docs/PHASE1_TASKS.md 中的該任務描述、相關現有程式碼，寫一份 plan 到 `PLAN.md`
5. Review plan，必要時請 Claude 修改

### Implement 階段
1. 切到 implement mode
2. 請 Claude 照 plan 實作
3. 跑 `just test`（或該任務的特定驗證腳本）
4. 修補問題直到通過驗收標準

### Commit
1. `just lint` + `just fmt`
2. 確認 git diff 沒有意外檔案
3. Conventional commit，訊息引用任務 ID（例如 `feat(sidecar): integrate Silero VAD (P1-3)`）

---

## 任務清單

### P1-1：FastAPI 後端骨架與 WebSocket endpoint
**子系統**：`sidecar/`
**預估**：0.5 day

**做什麼**
- `sidecar/main.py`：FastAPI app，一個 `/stream` WebSocket endpoint
- WebSocket 收 PCM 音訊 chunk（client 推送）；先用 echo / mock 文字回傳驗證雙向通訊
- 不串 Whisper，僅建立通道與資料 schema

**Plan 階段要釐清**
- WebSocket 訊息格式（client → server：PCM 二進位 + metadata；server → client：JSON）
- 錯誤處理（連線斷掉、payload 過大）

**驗收**
- `just test-sidecar` 通過
- 手動：用 `wscat` 或 `websocat` 連線、推 dummy bytes、收到 echo

---

### P1-2：faster-whisper + whisper_streaming 串接
**子系統**：`sidecar/`
**預估**：1.5 day
**前置**：P1-1

**做什麼**
- 安裝 faster-whisper、下載 large-v3 到本機（不入 git）
- `sidecar/stt.py`：包裝 whisper_streaming 的 `OnlineASRProcessor`
- `scripts/verify_stt.py`：吃一個 sample WAV，輸出 streaming 結果到 stdout（人眼可看是否合理）
- 把 STT 串到 WebSocket：收 PCM → 餵給 streaming processor → 推結果回 client

**Plan 階段要釐清**
- 取樣率、bit depth、channel 數的轉換（client 來的格式 vs Whisper 要的 16kHz mono float32）
- chunk size 設定（whisper_streaming 預設 vs 我們會議場景的最佳值）
- interim / final 事件的判定（whisper_streaming 的 `process_iter()` 回傳結構）

**驗收**
- `just verify-stt` 對 `tests/fixtures/sample_meeting.wav` 跑出合理逐字稿
- 端到端延遲 < 2s（這個任務先放寬，後續調優）

---

### P1-3：Silero VAD 整合與 chunking
**子系統**：`sidecar/`
**預估**：1 day
**前置**：P1-2

**做什麼**
- `sidecar/vad.py`：包 Silero VAD，輸入連續 PCM、輸出端點時間
- 在 STT 前加一層 VAD chunker：偵測到句末靜音切片、最長 15s fallback
- 處理「持續靜音」狀態（不要送空 chunk 給 STT 浪費計算）

**Plan 階段要釐清**
- VAD 與 Whisper 的取樣率對齊（兩者都是 16kHz，OK）
- 切片邊界處理（不要切在字中間）
- 與 whisper_streaming 內建的切片邏輯誰負責什麼（whisper_streaming 自己也有 voice activity 機制，要決定保留哪個）

**驗收**
- `just verify-stt` 結果不變或更好
- 純靜音輸入 30 秒，不會產出任何 STT 結果
- CPU 使用率：VAD 不超過單核 20%

---

### P1-4：React 前端骨架
**子系統**：`frontend/`
**預估**：0.5 day

**做什麼**
- Vite + React 18 + TS 專案初始化
- 基本 layout：標題列、逐字稿區、控制列（開始/停止鈕）
- 用 mock data 驗證 committed/pending 兩段顯示樣式

**Plan 階段要釐清**
- 狀態管理用什麼（純 useState、Zustand、還是 Redux Toolkit）— 推薦從 useState 開始
- CSS 方案（Tailwind / CSS Modules / styled-components）

**驗收**
- `npm run dev` 跑起來
- mock data 下，pending 區視覺上明顯與 committed 不同（半透明 + 斜體）

---

### P1-5：音訊擷取（getDisplayMedia + Web Audio API）
**子系統**：`frontend/`
**預估**：1 day
**前置**：P1-4

**做什麼**
- 「開始」按鈕觸發 `navigator.mediaDevices.getDisplayMedia({ audio: true })`
- Web Audio API 連到 `AudioContext`
- 用 `AudioWorklet` 把 audio resample 到 16kHz mono Float32
- 透過 WebSocket 推到後端（每 100ms 一個 buffer）

**Plan 階段要釐清**
- AudioWorklet vs ScriptProcessorNode（推薦 AudioWorklet，後者已 deprecated）
- 二進位資料格式（Float32 vs Int16 PCM；建議 Int16 省頻寬）
- WebSocket 重連策略

**驗收**
- 開分頁播一段 podcast，後端能收到合理的音訊資料（用 wave file 寫出來檢查）

---

### P1-6：committed/pending 雙段狀態管理與顯示
**子系統**：`frontend/`
**預估**：1 day
**前置**：P1-5

**做什麼**
- WebSocket 收到 `is_final=true` → append 到 `committed`
- 收到 `is_final=false` → 取代 `pending`
- 列表渲染、時間戳格式化
- pending 區的視覺差異（已在 P1-4 預備）

**Plan 階段要釐清**
- 時間戳是用 server 時間（從 sidecar 來）還是 client 接收時間 — 推薦 sidecar，校準到音訊起點
- committed 段的 key 策略（用 segment id）

**驗收**
- 串接 P1-3 之後的後端，講話即時看到字
- 端到端延遲 < 1.5s（清楚的單人講話）

---

### P1-7：SQLite 存儲
**子系統**：`sidecar/`（Phase 1）→ `src-tauri/`（Phase 2 會搬）
**預估**：0.5 day
**前置**：P1-2

**做什麼**
- Schema：`segments(id INTEGER PK, session_id TEXT, started_at REAL, ended_at REAL, text TEXT)`
- 每個 final segment 寫入；async 寫入不阻塞 STT
- FTS5 虛擬表（為 V2 鋪路）

**Plan 階段要釐清**
- session 怎麼劃（一次「開始-停止」一個 session？跨重啟怎麼處理？）
- async I/O 用 `aiosqlite` 還是 `asyncio.to_thread` 包同步 sqlite3

**驗收**
- 連續錄 5 分鐘，DB 內 segment 數與前端顯示一致
- session 表正確記錄起訖時間

---

### P1-8：UI 自動捲動（含 pause-on-user-scroll）
**子系統**：`frontend/`
**預估**：0.5 day
**前置**：P1-6

**做什麼**
- 新內容進來時 scroll to bottom
- 偵測使用者手動捲動（scroll event + 比對位置），暫停 auto-scroll
- 回到底部時恢復 auto-scroll
- 顯示「有新內容」提示（如果暫停中）

**Plan 階段要釐清**
- 判斷「在底部」的閾值（容差 ~50px）
- Smooth scroll vs instant scroll

**驗收**
- 持續錄音時自動捲到底
- 手動往上捲後不會被搶走捲軸
- 點「跳到底」按鈕能立刻回到底部並恢復自動

---

### P1-9：整合測試與穩定性修正
**預估**：2 days
**前置**：所有以上

**做什麼**
- 端到端整合測試（用真實會議錄音）
- 1 小時連續錄音壓力測試
- 記憶體洩漏檢查
- bug fixing

**驗收**：見 SPEC.md §5 Phase 1 驗收標準

---

## Phase 1 整體驗收（M1 里程碑）

- [ ] 端到端延遲 < 1.5 秒
- [ ] 清晰會議音訊中文辨識率 ≥ 85%
- [ ] 連續運行 60 分鐘不掉、不漏字、記憶體穩定
- [ ] 所有測試通過
- [ ] 文件：每個子系統 CLAUDE.md 完整、README 可讓新人 30 分鐘跑起來
