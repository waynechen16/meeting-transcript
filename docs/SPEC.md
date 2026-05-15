# 即時會議逐字稿系統 — 實作計劃書

**版本**：v1.0
**日期**：2026-05-14
**狀態**：規劃中
**預計交付**：6 週後（V1.0 內部試用版）

---

## 1. 專案概述

### 1.1 背景與動機

會議過程中經常有需要事後追溯的細節（決議、行動項目、技術討論），但人工筆記既費神又容易漏記。市面上工具（Teams Recap、Otter.ai 等）多為雲端服務，敏感會議內容上雲存在合規與商業機密外洩疑慮。

本專案目標是建構一個**完全在本機運行**的即時會議逐字稿工具，所有音訊與文字處理皆不離開使用者裝置。

### 1.2 核心目標

1. 即時擷取系統音訊輸出（瀏覽器與桌面會議軟體皆可）
2. 串流式語音辨識，端到端延遲 < 1.5 秒
3. 同步逐字稿顯示，視覺上區分「已確認」與「處理中」兩段
4. 持久化儲存，支援事後檢索
5. 跨平台桌面應用，可分發給同事使用

### 1.3 非目標（V1.0 不做）

- LLM 摘要生成、行動項目抽取
- 發言者區分（speaker diarization）
- 多會議室並行管理
- 雲端同步與分享
- 即時翻譯

以上規劃於 V2.0 評估，見 §8。

---

## 2. 範圍定義

### 2.1 In Scope

| 功能 | 說明 |
|------|------|
| 系統音訊擷取 | Windows WASAPI loopback；macOS / Linux 為加分項 |
| VAD 切片 | 端點偵測 + 最長窗口 fallback |
| 串流式 STT | 中英混雜會議內容，繁體中文為主 |
| 即時逐字稿渲染 | committed / pending 兩段顯示，自動捲動 |
| 本地存儲 | SQLite，附時間戳，全文可檢索 |
| 桌面應用打包 | Windows 為首要平台，雙擊執行 |
| 基本操作 | 開始 / 暫停 / 結束會議，匯出逐字稿 |

### 2.2 Out of Scope（V1.0）

LLM 摘要、speaker diarization、跨會議搜尋、Teams / Zoom 深度整合、即時翻譯。

---

## 3. 技術選型

| 層 | 選擇 | 備選 | 理由 |
|---|---|---|---|
| 桌面框架 | **Tauri 2.x** | Electron | 安裝檔體積小（< 15 MB）、啟動快、記憶體佔用低 |
| 前端 | React 18 + Vite + TypeScript | Vue | 生態成熟、團隊熟悉度高 |
| Rust 端音訊擷取 | `cpal` + WASAPI loopback | `wasapi-rs` | cpal 跨平台、社群活躍 |
| STT 引擎 | **faster-whisper (large-v3)** | whisper.cpp、FunASR | GPU 加速版 Whisper，中文準確度佳 |
| 串流封裝 | **whisper_streaming** | 自製 | LocalAgreement 演算法，開源成熟 |
| VAD | **Silero VAD** | WebRTC VAD | 準確度高、CPU 即時跑、PyTorch 生態 |
| Sidecar 打包 | PyInstaller | whisper.cpp 單檔 | 從 Python prototype 直接打包，迭代快 |
| 後端框架（POC） | FastAPI + uvicorn | Flask | async 友善、WebSocket 一級支援 |
| 進程間通訊 | WebSocket（POC）→ stdin/stdout（Tauri sidecar） | named pipe | Tauri sidecar 機制原生支援 |
| 存儲 | SQLite + FTS5 | DuckDB | 嵌入式、零維護、FTS5 為 V2 全文檢索預鋪路 |
| Frontend 虛擬捲動 | `react-virtuoso` | `react-window` | 長會議（千段以上）效能保障 |

---

## 4. 系統架構

### 4.1 整體資料流

```
[系統音訊源] → [音訊擷取層] → [VAD 切片] → [串流 STT 引擎]
                                                  │
                                  ┌───────────────┴───────────────┐
                                  ▼                               ▼
                          [即時逐字稿渲染]                   [SQLite 存儲]
                          (committed + pending)              (持久化)
```

### 4.2 同步顯示機制

STT 引擎產出兩種事件：

- `is_final = false`：interim 結果，會隨後續音訊上下文修正
- `is_final = true`：定稿，不再變動

前端維護兩個狀態：

- `committed: Segment[]` — 所有 final 結果累積，append-only
- `pending: string` — 當下最新的 interim，每次更新整段替換

當收到 final 事件：把 pending 內容封裝為一個 `Segment` 推入 committed，pending 清空。

```
時間軸 →

T=1s:  committed: []                              pending: "你好"
T=2s:  committed: []                              pending: "你好世界"
T=3s:  committed: [{ts:"00:03", text:"你好世界，"}]  pending: "今天"
T=4s:  committed: [{ts:"00:03", text:"你好世界，"}]  pending: "今天天氣"
```

視覺上 pending 用半透明 + 斜體呈現，讓使用者一眼分辨「會變」與「不會變」。

### 4.3 桌面 App 部署架構（Phase 2）

```
┌─ Tauri Shell (Rust) ───────────────────────────────────┐
│                                                          │
│  ┌─────────────────┐    IPC (event)    ┌──────────────┐ │
│  │  React Web UI   │ ←────────────────→│  Rust Core   │ │
│  │  (前端顯示)     │                    │              │ │
│  └─────────────────┘                    │  - 音訊擷取  │ │
│                                          │    (WASAPI)  │ │
│                                          │  - SQLite    │ │
│                                          │  - Sidecar   │ │
│                                          │    管理       │ │
│                                          └──────┬───────┘ │
│                                                 │ stdin   │
│                                                 │ stdout  │
│                                          ┌──────▼───────┐ │
│                                          │ Python       │ │
│                                          │ Sidecar      │ │
│                                          │              │ │
│                                          │ - Silero VAD │ │
│                                          │ - Whisper    │ │
│                                          │   (large-v3) │ │
│                                          │ - streaming  │ │
│                                          └──────────────┘ │
└──────────────────────────────────────────────────────────┘
```

整個系統打包後對使用者就是一個雙擊執行的 `.exe`（或 `.app` / `.AppImage`）。

---

## 5. 開發階段

### Phase 1 — Web POC（Week 1–2）

**目標**：驗證 Whisper streaming pipeline 全程跑得通

**任務拆解**

| ID | 任務 | 預估 |
|----|------|------|
| P1-1 | 建立 FastAPI 後端骨架，WebSocket endpoint | 0.5d |
| P1-2 | 串接 faster-whisper + whisper_streaming | 1.5d |
| P1-3 | Silero VAD 整合與 chunking 邏輯 | 1d |
| P1-4 | React 前端骨架（Vite + TS） | 0.5d |
| P1-5 | `getDisplayMedia` 擷取分頁音訊，PCM resample 至 16kHz | 1d |
| P1-6 | WebSocket 雙向資料流，committed / pending 狀態管理 | 1d |
| P1-7 | SQLite schema 與寫入邏輯 | 0.5d |
| P1-8 | UI 自動捲動（含 pause-on-user-scroll） | 0.5d |
| P1-9 | 整合測試與 bug fixing | 2d |

**交付物**：開發機上可運行的 web 版本

**驗收標準**
- 端到端延遲 < 1.5 秒（從說話到字幕出現）
- 清晰會議錄音中文辨識率 ≥ 85%
- 連續運行 60 分鐘不掉、不漏字、不爆記憶體

---

### Phase 2 — Tauri 桌面打包（Week 3–4）

**目標**：把 POC 包成可發送的 Windows 桌面 app

**任務拆解**

| ID | 任務 | 預估 |
|----|------|------|
| P2-1 | Tauri 2.x 專案初始化，前端搬遷 | 0.5d |
| P2-2 | Rust 端音訊擷取（cpal + WASAPI loopback） | 2d |
| P2-3 | Python sidecar PyInstaller 打包 | 1.5d |
| P2-4 | Tauri sidecar 機制整合（stdin/stdout IPC） | 1d |
| P2-5 | 模型檔下載策略（首次啟動下載 + 進度條） | 1d |
| P2-6 | 系統托盤、全域熱鍵（開始 / 停止） | 0.5d |
| P2-7 | 設定頁（模型大小、儲存路徑、語言偏好） | 1d |
| P2-8 | Windows 安裝包（MSI / NSIS）建置 | 1d |
| P2-9 | 程式碼簽署、版本控制 | 0.5d |
| P2-10 | 整合測試與穩定性修正 | 1d |

**交付物**：Windows `.exe` 安裝檔

**驗收標準**
- 安裝包 < 30 MB（不含模型）
- 啟動到 ready < 5 秒
- 在沒有開發環境的乾淨 Windows 11 機器上可正常運行
- 同時擷取 Teams 桌面版與 Edge 中的 Webex 音訊皆成功

---

### Phase 3 — 內部試用與優化（Week 5–6）

**目標**：在真實會議場景中驗證並修補問題

**任務拆解**

| ID | 任務 | 預估 |
|----|------|------|
| P3-1 | 邀請 3–5 位同事試用（含跨部門） | 持續 |
| P3-2 | 蒐集與分類回饋 | 持續 |
| P3-3 | Edge case 處理（多人插話、靜音中斷、長會議記憶體） | 3d |
| P3-4 | 效能調校（chunking 參數、模型大小切換） | 2d |
| P3-5 | 使用者文件撰寫（README、Troubleshooting） | 1d |
| P3-6 | 開發者文件（架構、貢獻指南） | 1d |
| P3-7 | V1.0 正式發版與內部公告 | 0.5d |

**交付物**：V1.0 release，附完整文件

---

## 6. 時程與里程碑

```
Week:        1    2    3    4    5    6
─────────────────────────────────────────
Phase 1:    ████ ████
Phase 2:              ████ ████
Phase 3:                        ████ ████
─────────────────────────────────────────
里程碑:           M1        M2        M3
```

| 里程碑 | 預計完成 | 驗收條件 |
|--------|----------|----------|
| **M1**：POC 跑通 | W2 末 | Web 版本端到端可運作，延遲達標 |
| **M2**：Tauri MVP | W4 末 | 可安裝、可運行於乾淨 Windows |
| **M3**：V1.0 發版 | W6 末 | 試用回饋處理完，文件齊備 |

---

## 7. 風險與緩解

### 7.1 技術風險

**R1：Whisper 對中英混雜的辨識率不足**
- 影響：會議常有 SI/PI、CPO、SerDes 等技術名詞與人名英文夾雜
- 緩解：採 large-v3；建立內部術語詞表，必要時走 initial_prompt 提示
- 備案：評估阿里 FunASR / Paraformer-Streaming（中文場景強）

**R2：WASAPI loopback 權限與相容性**
- 影響：部分公司 IT 政策可能限制低階 audio API；舊版 Windows 行為不一致
- 緩解：早期在實際工作筆電測試；提供 fallback 到 `getDisplayMedia`
- 備案：若 WASAPI 受阻，改用虛擬音訊裝置方案（VB-Cable）

**R3：Python sidecar 啟動延遲**
- 影響：使用者點開 app 後等很久（loading model 可能 5–15 秒）
- 緩解：lazy load 模型；UI 先顯示「初始化中」並 disable 錄音按鈕
- 備案：改用 whisper.cpp（C++ 單檔執行，啟動 < 1 秒），但須重做 streaming wrapper

**R4：模型檔過大不易分發**
- 影響：large-v3 ~3GB，內建會讓安裝包爆量
- 緩解：安裝包不含模型，首次啟動從 HuggingFace 下載並顯示進度
- 備案：預設 medium 模型（1.5GB），允許使用者進階設定升級

**R5：長會議記憶體洩漏**
- 影響：2 小時以上會議可能因為 React state 累積或 sidecar buffer 不清而 OOM
- 緩解：committed 段超過 N 筆轉成虛擬捲動；定期 flush sidecar internal state
- 備案：設定自動分檔（每小時切一個新逐字稿檔）

### 7.2 進度風險

**R6：估時偏樂觀**
- 緩解：每週 retrospective，必要時砍範圍而不延期；Phase 2 的設定頁、全域熱鍵可延後

---

## 8. V2 規劃（不在本計劃範圍）

待 V1.0 內部試用穩定後評估，候選功能依優先序：

1. **LLM 滾動摘要**：每 5 分鐘更新會議摘要、抽取行動項目與待追蹤問題（Claude API 或本地 Qwen2.5）
2. **Speaker diarization**：用 pyannote.audio 區分發言者
3. **時間戳跳轉**：保留壓縮原音檔，點逐字稿任一段跳回該時間點播放
4. **全文檢索**：SQLite FTS5 跨會議搜尋（「上週開會講過 CRDO 那段在哪」）
5. **匯出格式**：PDF / DOCX / SRT 字幕檔
6. **Teams / Zoom plugin**：原生整合會議軟體
7. **macOS / Linux 版**：跨平台覆蓋

---

## 9. 資源需求

### 9.1 人力

- 1 名工程師 full-stack（Python + TS/JS 必備，Rust 加分）
- 投入：6 週 full-time，或 12 週 half-time
- Phase 1–2 約 80% 開發、20% 整合；Phase 3 約 50% 修正、50% 文件與溝通

### 9.2 設備

- **開發機**：建議搭載 NVIDIA GPU（RTX 3060 以上），用於 large-v3 即時性測試
- **測試機**：純 CPU 的 Windows 工作筆電一台，驗證在公司一般機器上跑得動

### 9.3 雲端與服務

- HuggingFace：模型檔 hosting（免費公開模型）
- 程式碼控管：內部 Git 服務
- **不需要雲端 STT 預算**（全本地處理）

---

## 10. 成功指標

V1.0 發版後 1 個月內：

- 內部活躍使用者 ≥ 5 人
- 平均單次會議使用時長 ≥ 30 分鐘
- 使用者滿意度（NPS）≥ 50
- 嚴重 bug 數（影響核心錄音功能）≤ 2

---

## 附錄 A：開源參考實作

| 專案 | 用途 | 連結 |
|------|------|------|
| whisper_streaming | 串流 wrapper（LocalAgreement） | github.com/ufal/whisper_streaming |
| faster-whisper | CTranslate2 加速 Whisper | github.com/SYSTRAN/faster-whisper |
| Whispering | Tauri-based 桌面參考 | github.com/braden-w/whispering |
| Buzz | PyQt-based 桌面參考 | github.com/chidiwilliams/buzz |
| Silero VAD | VAD 引擎 | github.com/snakers4/silero-vad |
| Tauri | 桌面框架 | tauri.app |
| pyannote.audio | speaker diarization（V2 用） | github.com/pyannote/pyannote-audio |

## 附錄 B：開發環境設定（簡要）

- Node.js 20+ LTS
- Rust stable（rustup 安裝）
- Python 3.11+
- ffmpeg（音訊處理用）
- Windows：Visual Studio 2022 Build Tools（含 C++ 工具鏈）
- 建議 IDE：VS Code + rust-analyzer + Python + Tauri extension

## 附錄 C：文件清單（隨開發產出）

- `README.md` — 終端使用者文件
- `DEVELOPMENT.md` — 開發者環境設定與 contribution 指南
- `ARCHITECTURE.md` — 架構詳述與重要決策記錄（ADR）
- `CHANGELOG.md` — 版本歷史
- `TROUBLESHOOTING.md` — 常見問題排查

---

*本計劃書為 living document，隨開發進度更新。每週 retrospective 後依實際進度與發現的問題調整。*
