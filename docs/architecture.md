# Daily Management System (DMS) 系統架構文件

本文件描述了 DMS 的內部運作機制與技術選型，作為 Step 8 階段的架構基準與後續 AI 接手參考文件。

## 📁 目錄結構

```text
daily_management_system/
├── README.md              # 專案介紹與啟動指南
├── main.py                # 應用程式進入點與 SPA 路由中樞
├── database.py            # SQLite 雙軌架構層與自動備份邏輯
├── theme.py               # 設計系統 (Design Tokens)
├── components/            # 可複用共用元件
│   ├── sidebar.py         # 包含選中指示與路由切換的導覽列
│   └── finance_form.py    # 處理防呆與狀態的獨立財務表單
├── views/                 # 各大模組的主要視圖
│   ├── view_home.py       # 全局儀表板
│   ├── view_finance.py    # 財務管理模組
│   ├── view_action.py     # 行動中樞 (GTD + 習慣)
│   └── view_knowledge.py  # 知識庫 (Zettelkasten)
└── tests/
    └── test_db.py         # 回歸測試腳本
```

## 🗄️ SQLite 雙軌 Schema 設計

為兼顧關聯式資料庫的高效查詢與 NoSQL 的無 Schema 擴充彈性，DMS 採用了「雙軌設計」。

1. **核心正規化欄位**：
   - 負責查詢、排序與關聯。例如 `transactions.amount`、`knowledge_nodes.title`。
2. **`properties` (JSON 字串)**：
   - 作為 JSONB 的替代方案。在不需要複雜 SQL 查詢，但需要頻繁新增動態屬性（如筆記自訂 Tag、額外備註）時，統一序列化存入此欄位。

### 外鍵與級聯刪除 (Cascading Delete)
資料庫連線預設開啟 `PRAGMA foreign_keys = ON;`。
在設計知識庫雙向連結 (`relations` 表) 時，特別配置了 `ON DELETE CASCADE`。當 `knowledge_nodes` 中的主節點被刪除時，依賴它的任何正向或反向連結，皆由 SQLite 底層自動且安全地清理，免除前端繁雜的手動維護邏輯。

## 🧭 Flet SPA 路由與局部更新策略

DMS 不依賴 Flet 內建基於 URL 的路由系統，而是實作了效能最佳化的**視圖替換機制**。

### 路由運作流程：
1. **初始化**：`main.py` 建立左側 `Sidebar` 與右側 `view_container` (負責裝載主視圖)。
2. **跳轉觸發**：當使用者點擊 Sidebar 或儀表板卡片時，呼叫 `on_navigate(route)`。
3. **無縫替換與子路由分發**：
   - 檢查是否與當前路由相同（若相同則直接 Return，節省效能）。
   - 針對有子模組的路由（例如 `/finance` 開頭），透過工廠函式 `get_view()` 委託給該模組的主入口（如 `FinanceView`）進行內部再派發。
   - `FinanceView` 會將路由進一步拆分為 `_FinanceOverviewView`、`_FinanceStatsView` 與 `_FinanceDebtsView` 三個獨立子類別，維持單一檔案但職責分離的乾淨架構。
   - `Sidebar` 內部重繪活躍選中提示，同時 `view_container.content` 被賦予新的 View。

### 局部更新 (Partial Update)
在複雜視圖（如知識庫編輯器）中，我們堅守「局部更新」的設計原則。
* **避免 `page.update()` 濫用**：每個輸入框、每一列清單（`ft.Column`）皆為獨立控制元件。
* **精準更新**：當新增一個分類 Chip 時，僅呼叫 `self._chips_row.update()`，而非讓整個表單或視圖重新渲染，大幅提升操作流暢度並減少閃爍。
