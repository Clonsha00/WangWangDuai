"""
finance_form.py
---------------
財務輸入表單元件。
  - 金額輸入 + 支出/收入切換
  - 智慧分類 Chips（來自 DB） + 新增分類按鈕
  - 備註欄位 + 送出
"""

import flet as ft
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from theme import (
    BG_SURFACE, ACCENT, ACCENT_SOFT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED,
    SUCCESS, DANGER,
    PAD_SM, PAD_MD,
    RADIUS_SM,
)
from database import add_category, delete_category, get_categories, PROTECTED_CATEGORY_NAMES


class FinanceForm(ft.Column):
    """
    Props:
        categories          list[dict]  初始分類清單（來自 DB）
        on_submit_cb        callable    (amount, type_, category_id, description) → None
        on_category_added_cb callable   (new_cat: dict) → None
    """

    def __init__(self, categories: list[dict], on_submit_cb, on_category_added_cb):
        super().__init__(spacing=PAD_MD)
        self.categories = categories
        self.on_submit_cb = on_submit_cb
        self.on_category_added_cb = on_category_added_cb

        # ── 內部狀態 ──────────────────────────────────
        self._selected_cat_id: int | None = None
        self._tx_type: str = "expense"
        self._show_new_cat: bool = False

        # ── 固定控制元件（跨 rebuild 的持久 ref）───────
        self._amount_field = ft.TextField(
            hint_text="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            cursor_color=ACCENT,
            text_size=22,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=10),
        )

        self._desc_field = ft.TextField(
            hint_text="備註（選填）",
            expand=True,
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            cursor_color=ACCENT,
            text_size=13,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM),
        )

        self._new_cat_field = ft.TextField(
            hint_text="輸入新分類名稱",
            expand=True,
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            cursor_color=ACCENT,
            text_size=12,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
        )

        # 動態列（rebuild 時更新 controls 清單）
        self._type_row = ft.Row(spacing=PAD_SM)
        self._chips_row = ft.Row(wrap=True, spacing=PAD_SM, run_spacing=PAD_SM)
        self._new_cat_row = ft.Row(
            visible=False,
            spacing=PAD_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self._new_cat_field,
                ft.IconButton(
                    icon=ft.Icons.CHECK,
                    icon_color=SUCCESS,
                    icon_size=18,
                    on_click=self._confirm_new_cat,
                    tooltip="確認新增",
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=DANGER,
                    icon_size=18,
                    on_click=self._cancel_new_cat,
                    tooltip="取消",
                ),
            ],
        )

        # 初次建立動態元件
        self._rebuild_type_toggle()
        self._rebuild_chips()

        # 組裝 Column.controls
        self.controls = [
            # Row 1：NT$ 標籤 + 金額 + 支出/收入切換
            ft.Row(
                spacing=PAD_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("NT$", size=14, color=TEXT_SECONDARY, weight=ft.FontWeight.W_600),
                    self._amount_field,
                    self._type_row,
                ],
            ),
            # Row 2：分類 Chips
            ft.Column(
                spacing=PAD_SM,
                controls=[
                    ft.Text("分類", size=11, color=TEXT_SECONDARY),
                    self._chips_row,
                    self._new_cat_row,
                ],
            ),
            # Row 3：備註 + 送出
            ft.Row(
                spacing=PAD_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._desc_field,
                    ft.ElevatedButton(
                        text="記帳",
                        icon=ft.Icons.CHECK,
                        bgcolor=ACCENT,
                        color=TEXT_PRIMARY,
                        on_click=self._on_submit,
                        height=44,
                        style=ft.ButtonStyle(
                            elevation=0,
                            shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                        ),
                    ),
                ],
            ),
        ]

    # ── Type Toggle ──────────────────────────────────────────────────

    def _make_type_btn(self, label: str, type_val: str, icon_name) -> ft.Container:
        active = self._tx_type == type_val
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=8),
            bgcolor=ACCENT_SOFT if active else BG_SURFACE,
            border_radius=RADIUS_SM,
            border=ft.border.all(1, ACCENT if active else "transparent"),
            on_click=lambda e, t=type_val: self._set_type(t),
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Icon(icon_name, size=14, color=ACCENT if active else TEXT_SECONDARY),
                    ft.Text(label, size=12, color=TEXT_PRIMARY if active else TEXT_SECONDARY),
                ],
            ),
        )

    def _rebuild_type_toggle(self):
        self._type_row.controls = [
            self._make_type_btn("支出", "expense", ft.Icons.TRENDING_DOWN),
            self._make_type_btn("收入", "income",  ft.Icons.TRENDING_UP),
        ]

    def _set_type(self, type_val: str):
        if self._tx_type == type_val:
            return
        self._tx_type = type_val
        self._rebuild_type_toggle()
        try:
            self._type_row.update()
        except Exception:
            pass

    # ── Category Chips ───────────────────────────────────────────────

    def _rebuild_chips(self):
        chips: list[ft.Control] = []

        for cat in self.categories:
            is_sel = cat["id"] == self._selected_cat_id
            chip_label = ft.Text(
                f"{cat['icon']} {cat['name']}",
                size=12,
                color=TEXT_PRIMARY if is_sel else TEXT_SECONDARY,
            )

            def _make_delete_btn(cid: int, cname: str):
                def _do_delete(e, _cid=cid, _cname=cname):
                    try:
                        delete_category(_cid)
                        # 成功就從資料庫重新讀取，避免狀態不同步
                        self.categories = get_categories()
                        if self._selected_cat_id == _cid:
                            self._selected_cat_id = None
                        self._rebuild_chips()
                        try:
                            self._chips_row.update()
                        except Exception:
                            pass
                    except ValueError as ve:
                        if self.page:
                            self.page.open(ft.SnackBar(
                                ft.Text(f"⚠️ 拒絕删除：{ve}", color=ft.Colors.WHITE),
                                bgcolor=DANGER,
                            ))
                return _do_delete

            is_protected = cat["name"] in PROTECTED_CATEGORY_NAMES

            chips.append(
                ft.Chip(
                    label=chip_label,
                    selected=is_sel,
                    bgcolor=ACCENT_SOFT if is_sel else BG_SURFACE,
                    check_color=ACCENT,
                    padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=4),
                    on_select=lambda e, cid=cat["id"]: self._on_chip_select(cid),
                    # 預設分類不顯示刪除按鈕
                    delete_icon=None if is_protected else ft.Icon(ft.Icons.CLOSE, size=12, color=TEXT_DISABLED),
                    delete_icon_tooltip=None if is_protected else "刪除分類",
                    on_delete=None if is_protected else _make_delete_btn(cat["id"], cat["name"]),
                )
            )

        # 「新增分類」按鈕（用 Container 模擬 Chip 外型，避免 API 歧義）
        chips.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=6),
                bgcolor=BG_SURFACE,
                border_radius=20,
                border=ft.border.all(1, TEXT_DISABLED),
                on_click=self._toggle_new_cat,
                content=ft.Row(
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Icon(ft.Icons.ADD, size=12, color=TEXT_SECONDARY),
                        ft.Text("新增分類", size=12, color=TEXT_SECONDARY),
                    ],
                ),
            )
        )

        self._chips_row.controls = chips

    def _on_chip_select(self, cat_id: int):
        # 點已選中 → 取消；點未選中 → 選中（單選）
        self._selected_cat_id = None if self._selected_cat_id == cat_id else cat_id
        self._rebuild_chips()
        try:
            self._chips_row.update()
        except Exception:
            pass

    # ── New Category ─────────────────────────────────────────────────

    def _toggle_new_cat(self, e):
        self._show_new_cat = not self._show_new_cat
        self._new_cat_row.visible = self._show_new_cat
        try:
            self._new_cat_row.update()
        except Exception:
            pass

    def _confirm_new_cat(self, e):
        name = (self._new_cat_field.value or "").strip()
        if not name:
            return
        cat_id = add_category(name, "🏷️", "#607D8B", "finance")
        new_cat = {"id": cat_id, "name": name, "icon": "🏷️", "color": "#607D8B", "type": "finance"}
        self._new_cat_field.value = ""
        self._show_new_cat = False
        self._new_cat_row.visible = False
        # 通知父層重整分類清單
        self.on_category_added_cb(new_cat)
        try:
            self._new_cat_row.update()
        except Exception:
            pass

    def _cancel_new_cat(self, e):
        self._new_cat_field.value = ""
        self._show_new_cat = False
        self._new_cat_row.visible = False
        try:
            self._new_cat_row.update()
        except Exception:
            pass

    # ── Submit ───────────────────────────────────────────────────────

    def _on_submit(self, e):
        raw = (self._amount_field.value or "").strip().replace(",", "")
        if not raw:
            self._amount_field.error_text = "請輸入金額"
            try:
                self._amount_field.update()
            except Exception:
                pass
            return
        try:
            amount = float(raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            if self.page:
                self.page.open(ft.SnackBar(ft.Text("⚠️ 儲存失敗：金額格式錯誤", color=ft.Colors.WHITE), bgcolor=DANGER))
            return

        # 清除錯誤
        self._amount_field.error_text = None
        try:
            self._amount_field.update()
        except Exception:
            pass

        self.on_submit_cb(
            amount=amount,
            type_=self._tx_type,
            category_id=self._selected_cat_id,
            description=(self._desc_field.value or "").strip(),
        )

    # ── Public API ───────────────────────────────────────────────────

    def reset(self):
        """送出後清空表單回到預設狀態。"""
        self._amount_field.value = ""
        self._amount_field.error_text = None
        self._desc_field.value = ""
        self._selected_cat_id = None
        self._tx_type = "expense"
        self._rebuild_type_toggle()
        self._rebuild_chips()
        try:
            self.update()
        except Exception:
            pass

    def refresh_categories(self, categories: list[dict]):
        """新分類寫入 DB 後，父層呼叫此方法更新 Chips。"""
        self.categories = categories
        self._rebuild_chips()
        try:
            self._chips_row.update()
        except Exception:
            pass
