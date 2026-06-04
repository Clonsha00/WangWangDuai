"""
sidebar.py
----------
左側固定 Sidebar 導覽列。
回傳一個 ft.Container，並透過 on_navigate callback 通知 main.py 切換視圖。
"""

import flet as ft
from theme import (
    BG_PANEL, BG_HOVER, BG_SURFACE,
    ACCENT, ACCENT_SOFT,
    TEXT_PRIMARY, TEXT_SECONDARY,
    SIDEBAR_WIDTH, PAD_MD, PAD_SM, PAD_LG,
    RADIUS_MD,
)

# ── 導覽項目定義 ─────────────────────────────────────
NAV_ITEMS = [
    {"route": "home",      "icon": ft.Icons.HOME_OUTLINED, "label": "首頁"},
    {
        "type": "expansion",
        "icon": ft.Icons.CHECK_CIRCLE_OUTLINE,
        "label": "⚡ 行動管理",
        "children": [
            {"route": "action",   "label": "⚡ 行動中樞"},
            {"route": "calendar", "label": "📅 拖曳排程"},
        ]
    },
    {
        "type": "expansion",
        "icon": ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
        "label": "💰 財務管理",
        "children": [
            {"route": "finance",       "label": "📝 記帳總覽"},
            {"route": "finance/stats", "label": "📊 統計分析"},
            {"route": "finance/debts", "label": "💸 借款管理"},
        ]
    },
    {"route": "knowledge", "icon": ft.Icons.LIGHTBULB_OUTLINE,    "label": "知識"},
]


class Sidebar(ft.Column):
    """
    Sidebar 是一個 ft.Column，內含 Logo、Nav Items、底部設定。
    active_route: 目前選中的 route 字串。
    on_navigate: 點擊 nav item 時的 callback(route: str)。
    """

    def __init__(self, active_route: str, on_navigate):
        super().__init__(spacing=0, width=SIDEBAR_WIDTH)
        self.active_route = active_route
        self.on_navigate = on_navigate
        self._build()

    # ── 內部構建 ──────────────────────────────────────

    def _build(self):
        self.controls = [
            self._logo_section(),
            ft.Divider(height=1, color=BG_SURFACE),
            self._nav_section(),
            ft.Container(expand=True),  # 彈性空間把底部按鈕推下去
            ft.Divider(height=1, color=BG_SURFACE),
            self._bottom_section(),
        ]

    def _logo_section(self) -> ft.Container:
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_LG),
            content=ft.Row(
                spacing=PAD_SM,
                controls=[
                    ft.Container(
                        width=32, height=32,
                        border_radius=RADIUS_MD,
                        bgcolor=ACCENT,
                        alignment=ft.alignment.center,
                        content=ft.Text("D", size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ),
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text("Daily", size=13, weight=ft.FontWeight.W_700, color=TEXT_PRIMARY),
                            ft.Text("Management", size=10, color=TEXT_SECONDARY),
                        ],
                    ),
                ],
            ),
        )

    def _nav_section(self) -> ft.Column:
        items = []
        for n in NAV_ITEMS:
            if n.get("type") == "expansion":
                items.append(self._nav_expansion(n))
            else:
                items.append(self._nav_item(n))
        return ft.Column(
            spacing=2,
            controls=items,
            scroll=None,
        )

    def _nav_expansion(self, nav: dict) -> ft.ExpansionTile:
        is_active = any(child["route"] == self.active_route for child in nav["children"])
        
        children_controls = []
        for child in nav["children"]:
            child_is_active = child["route"] == self.active_route
            bg = ACCENT_SOFT if child_is_active else "transparent"
            text_color = TEXT_PRIMARY if child_is_active else TEXT_SECONDARY
            weight = ft.FontWeight.W_600 if child_is_active else ft.FontWeight.NORMAL
            
            def on_click(_e, route=child["route"]):
                self.on_navigate(route)

            indicator = ft.Container(
                width=3,
                height=36,
                border_radius=ft.border_radius.only(top_right=4, bottom_right=4),
                bgcolor=ACCENT if child_is_active else "transparent",
            )
            
            child_control = ft.Container(
                height=40,
                border_radius=ft.border_radius.only(top_right=RADIUS_MD, bottom_right=RADIUS_MD),
                bgcolor=bg,
                on_click=on_click,
                on_hover=self._make_hover_handler(child_is_active),
                content=ft.Row(
                    spacing=0,
                    controls=[
                        indicator,
                        ft.Container(
                            expand=True,
                            padding=ft.padding.only(left=PAD_LG, right=PAD_MD),
                            content=ft.Text(child["label"], size=13, color=text_color, weight=weight),
                        ),
                    ],
                ),
            )
            children_controls.append(child_control)

        return ft.ExpansionTile(
            title=ft.Row(
                spacing=PAD_SM,
                controls=[
                    ft.Icon(nav["icon"], color=TEXT_PRIMARY if is_active else TEXT_SECONDARY, size=18),
                    ft.Text(nav["label"], size=13, color=TEXT_PRIMARY if is_active else TEXT_SECONDARY, weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL),
                ]
            ),
            initially_expanded=is_active,
            controls=children_controls,
            controls_padding=0,
            shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
            collapsed_shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
        )

    def _nav_item(self, nav: dict) -> ft.Container:
        is_active = nav["route"] == self.active_route
        bg = ACCENT_SOFT if is_active else "transparent"
        icon_color = ACCENT if is_active else TEXT_SECONDARY
        text_color = TEXT_PRIMARY if is_active else TEXT_SECONDARY
        weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL

        def on_click(_e, route=nav["route"]):
            self.on_navigate(route)

        # 左側選中指示條
        indicator = ft.Container(
            width=3,
            height=36,
            border_radius=ft.border_radius.only(top_right=4, bottom_right=4),
            bgcolor=ACCENT if is_active else "transparent",
        )

        return ft.Container(
            height=44,
            border_radius=ft.border_radius.only(top_right=RADIUS_MD, bottom_right=RADIUS_MD),
            bgcolor=bg,
            on_click=on_click,
            on_hover=self._make_hover_handler(is_active),
            content=ft.Row(
                spacing=0,
                controls=[
                    indicator,
                    ft.Container(
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=PAD_MD - 3),
                        content=ft.Row(
                            spacing=PAD_SM,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(nav["icon"], color=icon_color, size=18),
                                ft.Text(nav["label"], size=13, color=text_color, weight=weight),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def _make_hover_handler(self, is_active: bool):
        def on_hover(e: ft.HoverEvent):
            if not is_active:
                e.control.bgcolor = BG_HOVER if e.data == "true" else "transparent"
                e.control.update()
        return on_hover

    def _bottom_section(self) -> ft.Container:
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_MD),
            content=ft.Row(
                spacing=PAD_SM,
                controls=[
                    ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=TEXT_SECONDARY, size=16),
                    ft.Text("設定", size=12, color=TEXT_SECONDARY),
                ],
            ),
        )

    # ── 外部呼叫：更新選中狀態 ────────────────────────

    def update_active(self, route: str):
        self.active_route = route
        self._build()
        self.update()
