"""
view_knowledge.py
-----------------
Zettelkasten 知識庫視圖。

佈局：雙欄
  左欄（固定 280px）
    ├─ 搜尋框
    ├─ [+ 新增卡片] 按鈕
    └─ 節點列表（可捲動）
  右欄（expand）
    ├─ 標題 + 類型下拉
    ├─ 內文（Markdown textarea）
    ├─ JSON 屬性編輯器（動態 Key-Value 列）
    ├─ 關聯連結（正向 + 新增）
    ├─ 反向連結（Backlinks）
    └─ 儲存 / 刪除 按鈕
"""

import flet as ft
import json as json_mod

# 系統屬性常數定義
SYSTEM_PROPERTY_KEYS = {"狀態", "難度", "進度"}
STATUS_OPTIONS = ["草稿", "進行中", "已完成"]
DIFFICULTY_OPTIONS = ["高", "中", "低"]
import os

from theme import (
    BG_DARK, BG_PANEL, BG_SURFACE, BG_HOVER,
    ACCENT, ACCENT_SOFT, SUCCESS, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
)
from database import (
    add_node, get_nodes, get_node, update_node, delete_node,
    add_relation, get_forward_relations, get_backlinks, delete_relation,
)
from components.shared import highlight_error

# ── Node type 設定 ───────────────────────────────────────────────
NODE_META = {
    "idea":      {"icon": "💡", "color": ACCENT,   "label": "💡 Idea"},
    "journal":   {"icon": "📓", "color": SUCCESS,  "label": "📓 Journal"},
    "guide":     {"icon": "📖", "color": WARNING,  "label": "📖 Guide"},
    "reference": {"icon": "🔗", "color": "#9B59B6","label": "🔗 Reference"},
}


def _sec(label: str) -> ft.Text:
    return ft.Text(label, size=11, color=TEXT_SECONDARY, weight=ft.FontWeight.W_600)


def _tf(hint="", multiline=False, min_lines=1, expand=True, value="") -> ft.TextField:
    return ft.TextField(
        hint_text=hint,
        value=value,
        expand=expand,
        multiline=multiline,
        min_lines=min_lines,
        max_lines=None if multiline else 1,
        border_color=BG_SURFACE,
        focused_border_color=ACCENT,
        bgcolor=BG_SURFACE,
        color=TEXT_PRIMARY,
        cursor_color=ACCENT,
        text_size=13,
        border_radius=RADIUS_SM,
        content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM),
    )


# ══════════════════════════════════════════════════════════════════
# Main View Class
# ══════════════════════════════════════════════════════════════════

class _KnowledgeView(ft.Column):
    def __init__(self):
        super().__init__(expand=True, spacing=0)

        # ── 狀態 ──────────────────────────────────────────
        self._selected_id: int | None = None
        self._active_tag_filter: str | None = None
        # kv_pairs: [(key_str, val_str), ...]
        self._kv_pairs: list[tuple[str, str]] = []
        # kv_fields: [(key_TextField, val_TextField), ...]
        self._kv_fields: list[tuple[ft.TextField, ft.TextField]] = []

        # ── 左欄持久控制元件 ──────────────────────────────
        self._search_field = _tf(hint="搜尋節點…", expand=True)
        self._search_field.on_change = self._on_search
        self._tags_row = ft.Row(wrap=True, spacing=4)
        self._nodes_col = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=2,
        )

        # ── 右欄持久控制元件（Editor）────────────────────
        self._title_field = _tf(hint="標題", expand=True)
        self._type_dd = ft.Dropdown(
            width=160,
            value="idea",
            options=[
                ft.dropdown.Option(key=k, text=v["label"])
                for k, v in NODE_META.items()
            ],
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=0),
        )
        self._content_field = _tf(
            hint="內文（支援 Markdown 語法）",
            multiline=True,
            min_lines=10,
            value="",
        )
        # JSON kv section
        self._kv_section = ft.Column(spacing=PAD_SM)

        # Relations
        self._rel_dd = ft.Dropdown(
            expand=True,
            hint_text="選擇要連結的節點…",
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=0),
            options=[],
        )
        self._relations_section = ft.Column(spacing=PAD_SM)
        self._backlinks_section = ft.Column(spacing=PAD_SM)

        # Status / Buttons
        self._status_text = ft.Text("", size=11, color=SUCCESS)
        self._delete_btn = ft.OutlinedButton(
            "刪除卡片",
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            style=ft.ButtonStyle(
                color=DANGER,
                side=ft.BorderSide(1, DANGER),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            ),
            on_click=self._delete_node,
            visible=False,
        )

        self._assemble()
        self._refresh_node_list()
        self._show_empty_editor()

    # ── 靜態骨架 ─────────────────────────────────────────

    def _assemble(self):
        # ── 左欄 ──────────────────────────────────────
        new_btn = ft.ElevatedButton(
            "＋ 新增卡片",
            icon=ft.Icons.ADD,
            bgcolor=ACCENT,
            color=TEXT_PRIMARY,
            height=36,
            style=ft.ButtonStyle(
                elevation=0,
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            ),
            on_click=lambda _: self._show_empty_editor(),
        )

        left_panel = ft.Container(
            width=272,
            bgcolor=BG_PANEL,
            border=ft.border.only(right=ft.BorderSide(1, BG_SURFACE)),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    ft.Container(
                        padding=PAD_MD,
                        content=ft.Column(
                            spacing=PAD_SM,
                            controls=[self._search_field, self._tags_row, new_btn],
                        ),
                    ),
                    ft.Divider(height=1, color=BG_SURFACE),
                    ft.Container(
                        expand=True,
                        content=self._nodes_col,
                    ),
                ],
            ),
        )

        # ── 右欄（Editor）──────────────────────────────
        add_prop_btn = ft.PopupMenuButton(
            content=ft.Row(
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=ACCENT, size=20),
                    ft.Text("＋ 新增屬性", color=ACCENT, weight=ft.FontWeight.W_500),
                ]
            ),
            items=[
                ft.PopupMenuItem(text="狀態", on_click=lambda e: self._add_kv("狀態")),
                ft.PopupMenuItem(text="難度", on_click=lambda e: self._add_kv("難度")),
                ft.PopupMenuItem(text="進度", on_click=lambda e: self._add_kv("進度")),
                ft.PopupMenuItem(text="自由輸入", on_click=lambda e: self._add_kv("")),
            ]
        )
        add_rel_btn = ft.IconButton(
            ft.Icons.LINK,
            icon_color=ACCENT,
            icon_size=20,
            tooltip="新增關聯",
            on_click=self._add_relation,
        )
        save_btn = ft.ElevatedButton(
            "儲存",
            icon=ft.Icons.SAVE_OUTLINED,
            bgcolor=ACCENT,
            color=TEXT_PRIMARY,
            height=40,
            style=ft.ButtonStyle(
                elevation=0,
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            ),
            on_click=self._save_node,
        )

        editor_col = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=PAD_MD,
            controls=[
                ft.Container(height=2),
                # 標題 + 類型
                ft.Row(
                    spacing=PAD_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[self._title_field, self._type_dd],
                ),
                # 內文
                _sec("✏️ 內文"),
                self._content_field,
                # JSON 屬性
                _sec("🗂 JSON 屬性"),
                self._kv_section,
                add_prop_btn,
                ft.Divider(height=1, color=BG_SURFACE),
                # 關聯連結
                _sec("🔗 關聯連結（正向）"),
                self._relations_section,
                ft.Row(
                    spacing=PAD_SM,
                    controls=[self._rel_dd, add_rel_btn],
                ),
                ft.Divider(height=1, color=BG_SURFACE),
                # 反向連結
                _sec("← 反向連結（Backlinks）"),
                self._backlinks_section,
                ft.Divider(height=1, color=BG_SURFACE),
                # 操作按鈕
                ft.Row(
                    spacing=PAD_MD,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[save_btn, self._delete_btn, self._status_text],
                ),
                ft.Container(height=PAD_XL),
            ],
        )

        right_panel = ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=PAD_LG, vertical=PAD_MD),
            content=editor_col,
        )

        # ── 組裝 ──────────────────────────────────────
        header = ft.Container(
            padding=ft.padding.only(
                left=PAD_LG, right=PAD_LG, top=PAD_LG, bottom=PAD_SM
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "知識庫",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Zettelkasten",
                        size=12,
                        color=TEXT_SECONDARY,
                        italic=True,
                    ),
                ],
            ),
        )

        self.controls = [
            header,
            ft.Divider(height=1, color=BG_SURFACE),
            ft.Row(
                expand=True,
                spacing=0,
                controls=[left_panel, right_panel],
            ),
        ]

    # ══════════════════════════════════════════════════════
    # 左欄：節點列表
    # ══════════════════════════════════════════════════════

    def _toggle_tag_filter(self, tag: str):
        if self._active_tag_filter == tag:
            self._active_tag_filter = None
        else:
            self._active_tag_filter = tag
        self._refresh_node_list(self._search_field.value or "")

    def _refresh_node_list(self, search: str = ""):
        nodes = get_nodes(search)
        
        nodes_with_props = []
        all_custom_tags = set()
        
        # 1. 預先取得詳細屬性與收集所有的自訂標籤
        # [註] Dynamic Tag Filter 目前為不修改 database.py 下的前端 MVP 實作；
        # 若資料量增加，未來應新增更有效率的資料查詢函式，避免目前的 N+1 查詢。
        for n in nodes:
            node_full = get_node(n["id"]) or {}
            props_json = node_full.get("properties", "{}")
            
            node_tags = []
            try:
                props = json_mod.loads(props_json or "{}")
            except json_mod.JSONDecodeError:
                props = {}
            if not isinstance(props, dict):
                props = {}
                
            for k, v in props.items():
                if k not in SYSTEM_PROPERTY_KEYS:
                    v_str = str(v).strip()
                    display_text = f"#{k}" if not v_str else f"{k}:{v_str}"
                    node_tags.append(display_text)
                    all_custom_tags.add(display_text)
                
            nodes_with_props.append((n, props_json, node_tags))
            
        # 2. 渲染上方的標籤過濾區 (Tag Filter Row)
        tag_chips = []
        for tag in sorted(list(all_custom_tags)):
            is_active = (self._active_tag_filter == tag)
            bg_color = ACCENT if is_active else BG_SURFACE
            text_color = TEXT_PRIMARY if is_active else TEXT_SECONDARY
            
            tag_chips.append(
                ft.Container(
                    content=ft.Text(tag, size=11, color=text_color, weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.NORMAL),
                    bgcolor=bg_color,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=RADIUS_SM,
                    on_click=lambda e, t=tag: self._toggle_tag_filter(t),
                )
            )
        self._tags_row.controls = tag_chips
        try:
            self._tags_row.update()
        except Exception:
            pass

        # 3. 渲染過濾後的卡片列表
        items: list[ft.Control] = []
        for n, props_json, node_tags in nodes_with_props:
            # 檢查標籤過濾
            if self._active_tag_filter and self._active_tag_filter not in node_tags:
                continue

            meta = NODE_META.get(n["node_type"], NODE_META["idea"])
            is_sel = n["id"] == self._selected_id
            bg = ACCENT_SOFT if is_sel else "transparent"

            items.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=8),
                    border_radius=RADIUS_SM,
                    bgcolor=bg,
                    on_click=lambda e, nid=n["id"]: self._select_node(nid),
                    on_hover=self._list_hover(is_sel),
                    border=ft.border.only(
                        left=ft.BorderSide(3, meta["color"] if is_sel else "transparent")
                    ),
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Row(
                                spacing=PAD_SM,
                                controls=[
                                    ft.Text(meta["icon"], size=13),
                                    ft.Text(
                                        n["title"],
                                        size=13,
                                        color=TEXT_PRIMARY if is_sel else TEXT_SECONDARY,
                                        weight=ft.FontWeight.W_500 if is_sel else ft.FontWeight.NORMAL,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True,
                                    ),
                                ],
                            ),
                            self._build_node_chips(props_json),
                            ft.Text(
                                n["updated_at"][:10],
                                size=10,
                                color=TEXT_DISABLED,
                            ),
                        ],
                    ),
                )
            )

        if not items:
            items = [
                ft.Container(
                    padding=PAD_LG,
                    alignment=ft.alignment.center,
                    content=ft.Text(
                        "尚無節點" if not search and not self._active_tag_filter else "找不到符合的節點",
                        size=12,
                        color=TEXT_DISABLED,
                    ),
                )
            ]

        self._nodes_col.controls = items
        try:
            self._nodes_col.update()
        except Exception:
            pass

    def _build_node_chips(self, props_json: str) -> ft.Control:
        row = ft.Row(spacing=4, wrap=True)
        try:
            props = json_mod.loads(props_json or "{}")
        except json_mod.JSONDecodeError:
            props = {}
        if not isinstance(props, dict):
            props = {}
            
        for k, v in props.items():
            v_str = str(v).strip()
            if k == "狀態":
                if not v_str: continue
                c = SUCCESS if v_str == "已完成" else (WARNING if v_str == "進行中" else TEXT_SECONDARY)
                row.controls.append(ft.Container(ft.Text(v_str, size=10, color=c), bgcolor=BG_SURFACE, padding=ft.padding.symmetric(horizontal=6, vertical=2), border_radius=4))
            elif k == "難度":
                if not v_str: continue
                c = DANGER if v_str == "高" else (WARNING if v_str == "中" else SUCCESS)
                row.controls.append(ft.Container(ft.Text(f"難度:{v_str}", size=10, color=c), bgcolor=BG_SURFACE, padding=ft.padding.symmetric(horizontal=6, vertical=2), border_radius=4))
            elif k == "進度":
                if not v_str: continue
                row.controls.append(ft.Container(ft.Text(f"{v_str}%", size=10, color=ACCENT), bgcolor=BG_SURFACE, padding=ft.padding.symmetric(horizontal=6, vertical=2), border_radius=4))
            else:
                # 自由輸入的標籤或屬性
                if not v_str:
                    content = ft.Text(f"#{k}", size=10, color=TEXT_PRIMARY)
                else:
                    content = ft.Row(
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(f"{k}:", size=10, color=TEXT_PRIMARY),
                            ft.Text(v_str, size=10, color=ACCENT, weight=ft.FontWeight.W_500),
                        ]
                    )
                row.controls.append(ft.Container(content, bgcolor=BG_SURFACE, padding=ft.padding.symmetric(horizontal=6, vertical=2), border_radius=4))
                    
        return row if row.controls else ft.Container(height=0)

    def _list_hover(self, is_sel: bool):
        def on_hover(e: ft.HoverEvent):
            if not is_sel:
                e.control.bgcolor = BG_HOVER if e.data == "true" else "transparent"
                e.control.update()
        return on_hover

    def _on_search(self, e):
        self._refresh_node_list(e.control.value or "")

    # ══════════════════════════════════════════════════════
    # Editor：載入 / 清空
    # ══════════════════════════════════════════════════════

    def _show_empty_editor(self):
        self._selected_id = None
        self._kv_pairs = []
        self._title_field.value = ""
        self._type_dd.value = "idea"
        self._content_field.value = ""
        self._rebuild_kv_ui()
        self._relations_section.controls = []
        self._backlinks_section.controls = [
            ft.Text("儲存後才能查看反向連結", size=11, color=TEXT_DISABLED)
        ]
        self._refresh_rel_dropdown([])
        self._status_text.value = ""
        self._delete_btn.visible = False
        self._refresh_node_list()
        try:
            self._title_field.update()
            self._type_dd.update()
            self._content_field.update()
            self._kv_section.update()
            self._relations_section.update()
            self._backlinks_section.update()
            self._rel_dd.update()
            self._status_text.update()
            self._delete_btn.update()
        except Exception:
            pass

    def _select_node(self, node_id: int):
        self._selected_id = node_id
        node = get_node(node_id)
        if not node:
            return

        # 基本欄位
        self._title_field.value = node["title"]
        self._type_dd.value = node["node_type"]
        self._content_field.value = node["content"] or ""

        self._kv_pairs = []
        try:
            props = json_mod.loads(node["properties"] or "{}")
        except (json_mod.JSONDecodeError, TypeError):
            props = {}
        if not isinstance(props, dict):
            props = {}
            
        for k, v in props.items():
            self._kv_pairs.append((k, str(v)))
        self._rebuild_kv_ui()

        # Relations & Backlinks
        all_nodes = get_nodes()
        self._refresh_rel_dropdown(all_nodes)
        self._refresh_relations_section()
        self._refresh_backlinks_section()

        self._delete_btn.visible = True
        self._status_text.value = ""

        # Refresh list (to highlight selected)
        self._refresh_node_list(self._search_field.value or "")

        try:
            self._title_field.update()
            self._type_dd.update()
            self._content_field.update()
            self._kv_section.update()
            self._relations_section.update()
            self._backlinks_section.update()
            self._rel_dd.update()
            self._status_text.update()
            self._delete_btn.update()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════
    # Editor：JSON 屬性 K-V
    # ══════════════════════════════════════════════════════

    def _sync_kv(self):
        """把目前 UI 欄位的值同步回 _kv_pairs。"""
        self._kv_pairs = []
        for kf, vf in self._kv_fields:
            k = kf.value or ""
            v = vf.value or ""
            self._kv_pairs.append((k, v))

    def _rebuild_kv_ui(self):
        self._kv_fields = []
        rows: list[ft.Control] = []
        for i, (k, v) in enumerate(self._kv_pairs):
            is_typed = k in SYSTEM_PROPERTY_KEYS
            
            kf = ft.TextField(
                value=k,
                hint_text="Key (例如: 標籤)",
                expand=2,
                read_only=is_typed,
                border_color=BG_SURFACE,
                focused_border_color=ACCENT,
                bgcolor=BG_SURFACE,
                color=TEXT_PRIMARY if not is_typed else TEXT_SECONDARY,
                cursor_color=ACCENT,
                text_size=12,
                border_radius=RADIUS_SM,
                content_padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
            )
            
            if k == "狀態":
                vf = ft.Dropdown(
                    value=v or STATUS_OPTIONS[0],
                    options=[ft.dropdown.Option(x) for x in STATUS_OPTIONS],
                    expand=3,
                    bgcolor=BG_SURFACE,
                    color=TEXT_PRIMARY,
                    border_color=BG_SURFACE,
                    focused_border_color=ACCENT,
                    text_size=12,
                    border_radius=RADIUS_SM,
                    content_padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
                )
            elif k == "難度":
                vf = ft.Dropdown(
                    value=v or DIFFICULTY_OPTIONS[1],
                    options=[ft.dropdown.Option(x) for x in DIFFICULTY_OPTIONS],
                    expand=3,
                    bgcolor=BG_SURFACE,
                    color=TEXT_PRIMARY,
                    border_color=BG_SURFACE,
                    focused_border_color=ACCENT,
                    text_size=12,
                    border_radius=RADIUS_SM,
                    content_padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
                )
            elif k == "進度":
                vf = ft.TextField(
                    value=v or "0",
                    hint_text="0~100 (無嚴格驗證)",
                    keyboard_type=ft.KeyboardType.NUMBER,
                    expand=3,
                    border_color=BG_SURFACE,
                    focused_border_color=ACCENT,
                    bgcolor=BG_SURFACE,
                    color=TEXT_PRIMARY,
                    text_size=12,
                    border_radius=RADIUS_SM,
                    content_padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
                )
            else:
                vf = ft.TextField(
                    value=v,
                    hint_text="Value (可留白)",
                    expand=3,
                    border_color=BG_SURFACE,
                    focused_border_color=ACCENT,
                    bgcolor=BG_SURFACE,
                    color=TEXT_PRIMARY,
                    cursor_color=ACCENT,
                    text_size=12,
                    border_radius=RADIUS_SM,
                    content_padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
                )

            self._kv_fields.append((kf, vf))
            rows.append(
                ft.Row(
                    spacing=PAD_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        kf,
                        ft.Text(":", size=12, color=TEXT_SECONDARY),
                        vf,
                        ft.IconButton(
                            ft.Icons.CLOSE_ROUNDED,
                            icon_color=TEXT_DISABLED,
                            icon_size=14,
                            tooltip="移除",
                            on_click=lambda e, idx=i: self._remove_kv(idx),
                        ),
                    ],
                )
            )
        self._kv_section.controls = rows

    def _add_kv(self, key_type: str = ""):
        self._sync_kv()
        self._kv_pairs.append((key_type, ""))
        self._rebuild_kv_ui()
        try:
            self._kv_section.update()
        except Exception:
            pass

    def _remove_kv(self, idx: int):
        self._sync_kv()
        if 0 <= idx < len(self._kv_pairs):
            self._kv_pairs.pop(idx)
        self._rebuild_kv_ui()
        try:
            self._kv_section.update()
        except Exception:
            pass

    def _collect_properties(self) -> dict:
        self._sync_kv()
        return {k: v for k, v in self._kv_pairs if k.strip()}

    # ══════════════════════════════════════════════════════
    # Editor：Relations
    # ══════════════════════════════════════════════════════

    def _refresh_rel_dropdown(self, all_nodes: list[dict]):
        """用所有其他節點更新新增關聯用的 Dropdown。"""
        self._rel_dd.options = [
            ft.dropdown.Option(key=str(n["id"]), text=n["title"])
            for n in all_nodes
            if n["id"] != self._selected_id
        ]
        self._rel_dd.value = None
        try:
            self._rel_dd.update()
        except Exception:
            pass

    def _refresh_relations_section(self):
        if self._selected_id is None:
            self._relations_section.controls = []
            return
        rels = get_forward_relations(self._selected_id)
        rows: list[ft.Control] = []
        for r in rels:
            meta = NODE_META.get(r["node_type"], NODE_META["idea"])
            rows.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
                    bgcolor=BG_SURFACE,
                    border_radius=RADIUS_SM,
                    content=ft.Row(
                        spacing=PAD_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(meta["icon"], size=14),
                            ft.Text(
                                r["title"],
                                expand=True,
                                size=13,
                                color=TEXT_PRIMARY,
                            ),
                            ft.Text(r["rel_type"], size=10, color=TEXT_SECONDARY),
                            ft.IconButton(
                                ft.Icons.LINK_OFF_ROUNDED,
                                icon_color=TEXT_DISABLED,
                                icon_size=14,
                                tooltip="移除連結",
                                on_click=lambda e, tid=r["id"]: self._remove_relation(tid),
                            ),
                        ],
                    ),
                )
            )
        self._relations_section.controls = rows or [
            ft.Text("尚無關聯連結", size=11, color=TEXT_DISABLED)
        ]

    def _refresh_backlinks_section(self):
        if self._selected_id is None:
            self._backlinks_section.controls = []
            return
        blinks = get_backlinks(self._selected_id)
        rows: list[ft.Control] = []
        for b in blinks:
            meta = NODE_META.get(b["node_type"], NODE_META["idea"])
            rows.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
                    bgcolor=BG_SURFACE,
                    border_radius=RADIUS_SM,
                    on_click=lambda e, nid=b["id"]: self._select_node(nid),
                    content=ft.Row(
                        spacing=PAD_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("←", size=12, color=TEXT_SECONDARY),
                            ft.Text(meta["icon"], size=14),
                            ft.Text(
                                b["title"],
                                expand=True,
                                size=13,
                                color=ACCENT,
                            ),
                        ],
                    ),
                )
            )
        self._backlinks_section.controls = rows or [
            ft.Text("尚無反向連結", size=11, color=TEXT_DISABLED)
        ]

    def _add_relation(self, e):
        if self._selected_id is None:
            self._show_status("請先儲存卡片再新增關聯", DANGER)
            return
        target_str = self._rel_dd.value
        if not target_str:
            return
        target_id = int(target_str)
        ok = add_relation(self._selected_id, target_id)
        if ok:
            self._show_status("關聯已新增", SUCCESS)
        else:
            self._show_status("關聯已存在", TEXT_SECONDARY)
        all_nodes = get_nodes()
        self._refresh_rel_dropdown(all_nodes)
        self._refresh_relations_section()
        try:
            self._relations_section.update()
        except Exception:
            pass

    def _remove_relation(self, target_id: int):
        if self._selected_id is None:
            return
        delete_relation(self._selected_id, target_id)
        self._refresh_relations_section()
        try:
            self._relations_section.update()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════
    # Editor：Save / Delete
    # ══════════════════════════════════════════════════════

    def _save_node(self, e):
        title = (self._title_field.value or "").strip()
        if not title:
            highlight_error(self.page, self._title_field)
            return
        self._title_field.error_text = None

        node_type = self._type_dd.value or "idea"
        content   = self._content_field.value or ""
        props     = self._collect_properties()

        if self._selected_id is None:
            # 新增
            new_id = add_node(title, node_type, content, props)
            self._selected_id = new_id
            self._delete_btn.visible = True
            try:
                self._delete_btn.update()
            except Exception:
                pass
            self._show_status("✓ 新卡片已建立", SUCCESS)
        else:
            # 更新
            update_node(self._selected_id, title, node_type, content, props)
            self._show_status("✓ 已儲存", SUCCESS)

        # Refresh list + relations dropdown
        all_nodes = get_nodes()
        self._refresh_rel_dropdown(all_nodes)
        self._refresh_relations_section()
        self._refresh_backlinks_section()
        self._refresh_node_list(self._search_field.value or "")
        try:
            self._title_field.update()
            self._relations_section.update()
            self._backlinks_section.update()
        except Exception:
            pass

    def _delete_node(self, e):
        if self._selected_id is None:
            return
            
        node_id = self._selected_id

        fwd = get_forward_relations(node_id)
        bwd = get_backlinks(node_id)
        
        rel_texts = []
        for r in fwd:
            rel_texts.append(f"🔗 正向關聯：{r['title']}")
        for b in bwd:
            rel_texts.append(f"← 反向連結：{b['title']}")

        if rel_texts:
            content_text = "刪除此卡片將一併解除以下連結：\n\n" + "\n".join(rel_texts) + "\n\n確定要刪除嗎？"
        else:
            content_text = "此卡片目前沒有任何關聯。確定要永久刪除嗎？"

        def close_dlg(e):
            self.page.close(dlg)

        def confirm_delete(e):
            self.page.close(dlg)
            delete_node(node_id)
            self._show_empty_editor()
            self._show_status("", SUCCESS)

        dlg = ft.AlertDialog(
            title=ft.Text("確認刪除？", weight=ft.FontWeight.BOLD),
            content=ft.Text(content_text, size=13, color=TEXT_SECONDARY),
            actions=[
                ft.TextButton("取消", on_click=close_dlg),
                ft.TextButton("確認刪除", on_click=confirm_delete, style=ft.ButtonStyle(color=DANGER)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    # ══════════════════════════════════════════════════════
    # 工具
    # ══════════════════════════════════════════════════════

    def _show_status(self, msg: str, color: str = SUCCESS):
        self._status_text.value = msg
        self._status_text.color = color
        try:
            self._status_text.update()
        except Exception:
            pass


# 工廠函式
def KnowledgeView() -> ft.Control:
    return _KnowledgeView()
