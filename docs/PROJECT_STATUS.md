# 專案狀態 (Project Status)

**當前版本**: `v1.0.0-MVP`
**狀態**: 穩定 (Stable)

## 已實現核心模組

- **雙軌 SQLite 資料庫**: 支援核心正規化查詢與 properties JSON 字串欄位（以 SQLite TEXT 儲存序列化 JSON，模擬 JSONB 彈性），底層支援級聯刪除機制 (ON DELETE CASCADE) 避免孤立連結。
- **Flet SPA 路由**: 不依賴 URL 的單頁面局部刷新與視圖切換機制，達成輕量高效的 UI 體驗。
- **首頁動態儀表板**: 自動匯整各大核心模組摘要，提供即時狀態總覽。
- **財務智慧標籤**: 結合支出/收入切換與自訂分類 Chips，並提供基本的防呆驗證及月度結算功能。
- **行動中樞 (Action Center)**: 實作基於 GTD 的待辦清單 (TODO) 與每日習慣打卡 (Habits) 之雙欄操作中樞。
- **Zettelkasten 知識庫**: 支援 Markdown 內文、動態 Key-Value 屬性綁定，並內建帶有完整防呆警告的雙向連結 (正向關聯與反向連結)。
- **安全與防禦機制**: 內建 90 天滾動式靜默備份 (`auto_backup_db`)，以及在財務表單等關鍵輸入流程加入錯誤攔截與 SnackBar 降級提示。

## 🚀 近期功能升級 (v1.1.0 開發中)

- **知識庫 UI 進化 (Step 9)**：
  - 實作型別化屬性 (Typed Properties)，針對狀態、難度提供 Dropdown，進度提供數字輸入，自由輸入提供高對比顯示（進度欄位目前僅輔助鍵盤，尚未實作嚴格的 0–100 驗證）。
  - 實作動態標籤過濾 (Dynamic Tag Filter)，在左側列表自動萃取自訂 JSON 屬性成為 Chip，點擊即可純前端快速過濾卡片，再次點擊可取消，且支援與關鍵字搜尋疊加。
  - 大幅優化 JSON 解析機制，壞軌 JSON、空值、或非字典格式皆不再導致 UI 崩潰。
  - 本階段全程**未修改** `database.py` 與資料庫 schema，嚴守資料庫底層邊界，並已通過自動化回歸測試 (`tests/test_db.py`)。

- **財務模組升級與資料防護 (Step 10)**：
  - **資料來源 (10-A)**：`database.py` 新增專屬圓餅圖的 `get_monthly_expense_by_category()` 查詢，自動過濾 `amount <= 0` 的零值與異常值，且保證 `income` 收入不混入支出圖表。
  - **視覺化進化 (10-B)**：於 `view_finance.py` 新增隱藏式 Toggle 實心 PieChart。圖表預設隱藏，展開後以 `badge` 與 `legend` 呈現分類百分比，並將 `< 1%` 之微小分類完美合併至「其他」。無支出時具備優雅的 Empty State 佔位提示。最終設計為求穩定與效能，從 Canvas Leader Lines 收斂為 Toggle 實心 PieChart。
  - **安全刪除機制 (10-C)**：實作分類的雙層防護刪除機制。`database.py` 引入 `PROTECTED_CATEGORY_NAMES` 保護預設分類，並阻擋刪除已有歷史帳務的分類；UI 層 (`finance_form.py`) 會自動隱藏受保護分類的刪除按鈕，並於刪除失敗時透過 SnackBar 給予使用者反饋，刪除成功則即時重讀資料庫維持狀態同步。本階段完全未修改資料庫 schema 或新增資料表。

- **財務導航重構與獨立借款系統 (Step 11)**：
  - **資料庫擴充 (11-A)**：新增 `debts` 資料表，實作 `add_debt`、`mark_debt_settled`、`delete_debt` 與各類查詢 (`get_pending_debts`、`get_settled_debts`、`get_debt_summary_by_person`、`get_all_debt_persons`)。確保 `settled_at` migration 完美整合進 `init_db()`。
  - **導航重構 (11-B)**：Sidebar 財務管理改為 `ft.ExpansionTile`，新增 `finance`、`finance/stats`、`finance/debts` 三個內部 SPA 路由。
  - **視圖拆分與實作 (11-C)**：`FinanceView` 拆分為 Overview / Stats / Debts 三個子視圖。借款管理使用 `ft.Tabs` 劃分待處理清單、對象總計、歷史紀錄。借款金額輸入框使用 `input_filter` 搭配後端 `try/except ValueError` 進行雙層防呆。

## 已知限制

- **單機本地端架構**: 目前專案設計純為本地運行 (Local-first)，無提供後端 API 或雲端資料庫自動同步功能。
- **無權限與多用戶管理**: 系統預設為個人私有使用，未實作任何帳號登入、角色驗證或加密保護機制。
- **分類保護以名稱判斷**: `PROTECTED_CATEGORY_NAMES` 目前純以分類名稱判斷（這是在不改動現有 schema 下的取捨，配合 DB `INSERT OR IGNORE` 維持唯一性）。
- **圓餅圖標籤對齊**: 分類超過 8 個時 PieChart badge 可能靠近或重疊，目前 MVP 階段以圖例列 (legend) 輔助辨識。圖表使用固定高度，極窄視窗下可能被截斷。

## 未來藍圖 (Roadmap)

> 以下為後續可規劃方向，不代表目前 MVP 已實作，也不應由 Coding Agent 在未經規劃與審查前直接開工。

- **視覺 Theme 深度客製化**: 提供使用者自訂調色盤、字體及深淺色主題切換選項。 *(狀態：可規劃，需另開 Step。)*
- **AI Agent 自然語言解析**: 預留整合介面，未來可串接 LLM，允許使用者以自然語言輸入「幫我記一筆中餐花費 150 元」來直接寫入資料庫或進行複雜查詢。 *(狀態：暫緩，需另行設計資料安全與寫入權限。)*
- **更豐富的數據視覺化**: 引入圓餅圖、長條圖等圖表元件，增強財務與習慣打卡的回顧體驗。 *(狀態：可規劃，建議先從財務月度統計開始。)*
