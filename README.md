# Daily Management System (DMS)

這是一個基於 Python 與 Flet 打造的極簡風格本地端個人管理系統，旨在透過單一整合介面掌握個人的財務、行動待辦與知識卡片。

## 🌟 功能模組

- **全局儀表板 (Dashboard)**: 統整所有核心模組的即時狀態概覽。
- **財務概況 (Finance)**: 具備動態標籤 (Chips) 與月度結算的記帳系統。
- **行動中樞 (Action)**: 結合每日習慣打卡與 GTD 待辦清單的執行系統。
- **知識庫 (Zettelkasten)**: 支援動態屬性與雙向連結的卡片盒筆記系統。

## 🛠️ 技術棧

- **Python 3.10+**
- **Flet**: 基於 Flutter 的現代 Python UI 框架。
- **SQLite**: 輕量本地端資料庫，並實作 90 天滾動自動備份防禦機制。

## 🚀 快速啟動

1. **安裝依賴套件**:
   請確認環境已安裝 Flet (建議版本 0.23+)。
   ```bash
   pip install flet
   ```

2. **執行應用程式**:
   直接透過 Python 啟動主程式即可。系統會自動在同目錄初始化 SQLite 資料庫 (`dms.db`) 與備份。
   ```bash
   python main.py
   ```

## 🧪 測試指南

> **注意：** `tests/test_db.py` 是一個「資料庫層回歸測試」，主要驗證 SQLite CRUD 邏輯、級聯刪除機制與自動備份功能，並非完整的 UI 自動化測試。對於 UI 的測試，請參考 `docs/regression_checklist.md` 進行人工查驗。

執行資料庫回歸測試：

**Windows PowerShell**
```powershell
$env:PYTHONIOENCODING="utf8"; python tests/test_db.py
```

**macOS / Linux**
```bash
PYTHONIOENCODING=utf8 python tests/test_db.py
```

## 📂 架構文件
進階開發或了解架構設計，請參閱 [`docs/architecture.md`](docs/architecture.md)。
