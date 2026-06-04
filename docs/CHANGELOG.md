# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project loosely follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) during MVP development.

## [1.1.0] - 2026-05-26

### Added
- **[Step 9] 知識庫新增 Typed Properties (屬性 UI 型別化)**
  - 支援「狀態 / 難度 / 進度 / 自由輸入」。
  - 狀態與難度改用 Dropdown 選單。
  - 進度目前使用數字鍵盤提示，尚未做嚴格 0–100 驗證。
- **[Step 9] 知識庫新增 Dynamic Tag Filter (動態標籤過濾)**
  - 自訂 properties tag 會在左側列表上方自動萃取並顯示為可點擊的 Chip。
  - 點擊 tag 可快速過濾列表卡片，再次點擊可取消過濾。
  - tag filter 可與原有的關鍵字搜尋框完美疊加運作。
- **[Step 10-A] 完善財務圓餅圖資料來源**
  - `database.py` 新增 `get_monthly_expense_by_category()`。
  - 只統計本月 `expense`，且 `amount <= 0` 的異常或零值皆不納入。
  - 回傳分類名稱、icon、color、total。本輪未修改 schema。
- **[Step 10-B] 財務視圖新增隱藏式 Toggle 實心 PieChart**
  - 圖表預設隱藏，可透過按鈕展開/收起。
  - 最終設計從 Canvas Leader Lines 收斂為 Toggle 實心 PieChart + badge + legend。
  - 佔比 `< 1%` 的分類會自動合併至「其他」區塊。
  - 無本月支出時顯示 Empty State 佔位提示。
- **[Step 10-C] 分類安全刪除機制 (雙層防護)**
  - `database.py` 新增 `PROTECTED_CATEGORY_NAMES`，預設分類不可刪除（目前以分類名稱判斷）。
  - `database.py` 新增 `delete_category()`，有歷史帳務的分類不可刪除，無歷史帳務的自訂分類可以刪除。
  - `finance_form.py` 的分類 Chip 新增安全刪除 UI，受保護分類不顯示刪除按鈕。
  - 刪除失敗時顯示 SnackBar，刪除成功後重新 `get_categories()` 同步 UI 狀態。
- **[Step 11-A] 擴充借款資料庫與統計邏輯**
  - `database.py` 新增 `debts` 資料表。
  - 新增 API：`add_debt`、`mark_debt_settled`、`delete_debt`。
  - 新增 API：`get_pending_debts`、`get_settled_debts`、`get_debt_summary_by_person`、`get_all_debt_persons`。
  - `settled_at` migration 邏輯已完美整合進 `init_db()`。
- **[Step 11-B] 左側導航與路由重構**
  - `sidebar.py` 財務管理改為 `ft.ExpansionTile`。
  - 註冊並處理 `finance`、`finance/stats`、`finance/debts` 三個內部路由 (維持內部 SPA 機制)。
- **[Step 11-C] 重構財務視窗與實作借款介面**
  - `FinanceView` 主入口解耦，拆分為 `Overview` / `Stats` / `Debts` 三個子視圖。
  - 借款管理實作獨立三頁籤 Tabs：待處理清單、對象總計、歷史紀錄。
  - 借款金額輸入框實作 `input_filter` + `try/except ValueError` 雙層防呆。

### Fixed / Improved
- **[Step 9] 強化的資料健壯性**：優化 JSON 解析機制，壞 JSON / 空 properties / 非 dict properties 均不會造成 UI 崩潰。
- **[Step 9] 架構穩定性**：本輪開發嚴守邊界，未修改 `database.py`、未修改資料庫 schema，且所有變更皆已通過 `python tests/test_db.py` 回歸測試。

## [1.0.0-MVP] - 2026-05-26

### Added
- 建立 `database.py` 實作 SQLite 雙軌 Schema (正規化 + JSONB)。
- 建立 Flet SPA 基礎路由與 `theme.py` 全域樣式。
- 實作財務模組 (智慧標籤、收支統計)。
- 實作行動中樞 (習慣打卡、待辦清單與季度目標雙欄佈局)。
- 實作知識庫 (Markdown 編輯、動態 JSON 屬性、正反向關聯連結)。
- 實作首頁儀表板 (各模組數據動態卡片)。
- 建立 `tests/test_db.py` 自動化測試與架構文件。

### Security / Defense
- 實作 90 天靜默滾動備份機制 (`auto_backup_db`)。
- 啟用 SQLite `ON DELETE CASCADE` 外鍵約束避免幽靈連結。
- 實作前端表單防呆 (金額型別驗證) 與刪除警告對話框 (AlertDialog)。
