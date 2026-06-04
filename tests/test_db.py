import sys
import os
import sqlite3
import json

# 將專案根目錄加入路徑以便匯入 database.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database import (
    init_db, add_node, get_node, update_node, delete_node,
    add_relation, get_forward_relations, auto_backup_db,
    add_action, get_actions, add_category, get_categories,
    add_transaction, get_monthly_summary
)

TEST_DB = os.path.join(project_root, "test_dms.db")

def run_tests():
    print("🚀 開始執行資料庫回歸測試...\n")
    
    # 確保環境乾淨
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    try:
        # ==========================================
        # 1. 基礎初始化測試
        # ==========================================
        print("[測試 1] 建立測試資料庫 Schema")
        init_db(TEST_DB)
        assert os.path.exists(TEST_DB), "資料庫檔案未成功建立"
        print("✅ 通過")
        
        # ==========================================
        # 2. CRUD 基礎邏輯與 JSONB 擴充測試
        # ==========================================
        print("[測試 2] 節點 CRUD 與 JSON 屬性讀寫")
        nid1 = add_node("回歸測試節點 1", "idea", "這是一段測試內文", {"custom_tag": "test_tag"}, TEST_DB)
        assert nid1 > 0, "節點新增失敗"
        
        node = get_node(nid1, TEST_DB)
        assert node["title"] == "回歸測試節點 1", "節點標題讀取錯誤"
        props = json.loads(node["properties"])
        assert props.get("custom_tag") == "test_tag", "JSON 屬性解析錯誤"
        
        update_node(nid1, "已修改節點", "idea", "內文", {"custom_tag": "updated"}, TEST_DB)
        updated_node = get_node(nid1, TEST_DB)
        assert updated_node["title"] == "已修改節點", "節點更新失敗"
        print("✅ 通過")

        # ==========================================
        # 3. SQLite 級聯刪除 (ON DELETE CASCADE) 測試
        # ==========================================
        print("[測試 3] 驗證 relations 表的級聯刪除 (ON DELETE CASCADE)")
        nid2 = add_node("關聯目標節點", "guide", "內容", {}, TEST_DB)
        
        # 建立關聯：nid1 -> nid2
        add_relation(nid1, nid2, "link", TEST_DB)
        fwd = get_forward_relations(nid1, TEST_DB)
        assert len(fwd) == 1, "關聯建立失敗"
        assert fwd[0]["id"] == nid2, "關聯目標錯誤"
        
        # 刪除目標節點 (nid2)
        delete_node(nid2, TEST_DB)
        
        # 驗證關聯是否被資料庫底層自動清除
        fwd_after = get_forward_relations(nid1, TEST_DB)
        assert len(fwd_after) == 0, "級聯刪除失敗：節點已被刪除，但 relations 表中仍存在孤立記錄"
        print("✅ 通過")
        
        # ==========================================
        # 4. auto_backup_db 滾動備份測試
        # ==========================================
        print("[測試 4] 驗證自動備份機制")
        auto_backup_db(TEST_DB, retain_days=90)
        
        backup_dir = os.path.join(project_root, "backups")
        assert os.path.exists(backup_dir), "backups 資料夾未建立"
        
        # 尋找測試資料庫的備份檔
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith("test_dms_backup_")]
        assert len(backup_files) == 1, "備份檔未成功生成"
        print(f"✅ 通過 (生成備份：{backup_files[0]})")
        
        print("\n🎉 所有回歸測試皆已順利通過！")
        
    finally:
        # ==========================================
        # 清理測試環境，嚴禁留下垃圾檔案
        # ==========================================
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
            
        backup_dir = os.path.join(project_root, "backups")
        if os.path.exists(backup_dir):
            for f in os.listdir(backup_dir):
                if f.startswith("test_dms_backup_"):
                    os.remove(os.path.join(backup_dir, f))
            # 若備份資料夾為空，則移除
            try:
                os.rmdir(backup_dir)
            except OSError:
                pass

if __name__ == "__main__":
    run_tests()
