"""
view_finance.py
---------------
財務主視圖，依據 route 分為三個子視圖：
  - _FinanceOverviewView: 記帳總覽
  - _FinanceStatsView: 統計分析
  - _FinanceDebtsView: 借款管理
"""

import flet as ft
from datetime import date
import os

from theme import (
    BG_DARK, BG_PANEL, BG_SURFACE,
    ACCENT, ACCENT_SOFT, SUCCESS, DANGER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
)
from database import (
    get_categories, add_transaction,
    get_transactions, delete_transaction, get_monthly_summary,
    get_monthly_expense_by_category,
    add_debt, mark_debt_settled, delete_debt, delete_debts_by_person,
    get_pending_debts, get_settled_debts, get_debt_summary_by_person,
    get_all_debt_persons
)
from components.finance_form import FinanceForm
from components.shared import confirm_delete_dialog, show_toast, highlight_error

# ── 1. 記帳總覽 ──────────────────────────────────────────

class _FinanceOverviewView(ft.Column):
    def __init__(self, on_navigate_cb):
        super().__init__(spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
        self.on_navigate_cb = on_navigate_cb
        self._month = date.today().strftime("%Y-%m")
        self._categories = get_categories()

        self._summary_col = ft.Column(spacing=0)
        self._list_col = ft.Column(spacing=0)

        self._month_label = ft.Text(
            self._fmt_month(),
            size=13,
            color=TEXT_PRIMARY,
            weight=ft.FontWeight.W_500,
        )

        self._form = FinanceForm(
            categories=self._categories,
            on_submit_cb=self._handle_submit,
            on_category_added_cb=self._handle_new_category,
        )

        self._assemble()
        self._populate_data()

    def _fmt_month(self) -> str:
        y, m = self._month.split("-")
        return f"{y}年{int(m):02d}月"

    def _assemble(self):
        # 捷徑按鈕
        shortcuts = ft.Row(
            spacing=PAD_SM,
            alignment=ft.MainAxisAlignment.END,
            controls=[
                ft.ElevatedButton(
                    "📊 統計分析",
                    bgcolor=ACCENT_SOFT,
                    color=ACCENT,
                    height=36,
                    on_click=lambda e: self.on_navigate_cb("finance/stats") if self.on_navigate_cb else None,
                    style=ft.ButtonStyle(elevation=0, shape=ft.RoundedRectangleBorder(radius=RADIUS_SM)),
                ),
                ft.ElevatedButton(
                    "💸 借款管理",
                    bgcolor=ACCENT_SOFT,
                    color=ACCENT,
                    height=36,
                    on_click=lambda e: self.on_navigate_cb("finance/debts") if self.on_navigate_cb else None,
                    style=ft.ButtonStyle(elevation=0, shape=ft.RoundedRectangleBorder(radius=RADIUS_SM)),
                ),
            ]
        )

        self.controls = [
            ft.Container(
                padding=ft.padding.only(left=PAD_LG, right=PAD_LG, top=PAD_LG, bottom=PAD_SM),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("財務管理", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        shortcuts,
                    ],
                ),
            ),
            ft.Container(
                padding=ft.padding.only(left=PAD_LG, right=PAD_LG, bottom=PAD_SM),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, icon_color=TEXT_SECONDARY, icon_size=20, on_click=self._prev_month),
                        self._month_label,
                        ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, icon_color=TEXT_SECONDARY, icon_size=20, on_click=self._next_month),
                    ],
                ),
            ),
            ft.Container(
                margin=ft.margin.symmetric(horizontal=PAD_LG),
                padding=PAD_MD,
                bgcolor=BG_PANEL,
                border_radius=RADIUS_LG,
                border=ft.border.all(1, BG_SURFACE),
                content=self._form,
            ),
            ft.Container(height=PAD_MD),
            ft.Container(padding=ft.padding.symmetric(horizontal=PAD_LG), content=self._summary_col),
            ft.Container(height=PAD_MD),
            ft.Container(padding=ft.padding.symmetric(horizontal=PAD_LG), content=self._list_col),
            ft.Container(height=PAD_XL),
        ]

    def _populate_data(self):
        self._refresh_summary()
        self._refresh_list()

    def _refresh_summary(self):
        summary = get_monthly_summary(self._month)
        
        def card(label: str, amount: float, color: str) -> ft.Container:
            return ft.Container(
                expand=True, padding=PAD_MD, bgcolor=BG_PANEL, border_radius=RADIUS_MD, border=ft.border.all(1, BG_SURFACE),
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(label, size=11, color=TEXT_SECONDARY),
                        ft.Text(f"NT$ {abs(amount):,.0f}", size=18, weight=ft.FontWeight.BOLD, color=color),
                    ],
                ),
            )

        net_color = SUCCESS if summary["net"] >= 0 else DANGER
        self._summary_col.controls = [
            ft.Row(
                spacing=PAD_SM,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    card("本月收入", summary["income"], SUCCESS),
                    card("本月支出", summary["expense"], DANGER),
                    card("淨餘", summary["net"], net_color),
                ],
            )
        ]

    def _refresh_list(self):
        txs = get_transactions(month=self._month)
        def tx_row(tx: dict) -> ft.Container:
            icon = tx.get("category_icon") or "─"
            cat_name = tx.get("category_name") or "未分類"
            cat_color = tx.get("category_color") or TEXT_SECONDARY
            is_inc = tx["type"] == "income"
            color = SUCCESS if is_inc else DANGER
            sign = "+" if is_inc else "−"

            return ft.Container(
                padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=10),
                border_radius=RADIUS_MD, bgcolor=BG_PANEL,
                border=ft.border.only(left=ft.BorderSide(3, cat_color)),
                margin=ft.margin.only(bottom=PAD_SM),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=PAD_MD, expand=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(width=36, height=36, border_radius=RADIUS_SM, bgcolor=BG_SURFACE, alignment=ft.alignment.center, content=ft.Text(icon, size=18)),
                                ft.Column(spacing=2, expand=True, controls=[
                                    ft.Text(cat_name, size=13, color=TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                                    ft.Text(tx.get("description") or "─", size=11, color=TEXT_SECONDARY),
                                ]),
                            ],
                        ),
                        ft.Row(
                            spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END, controls=[
                                    ft.Text(f"{sign} NT$ {tx['amount']:,.0f}", size=14, weight=ft.FontWeight.W_600, color=color),
                                    ft.Text(tx["date"], size=10, color=TEXT_SECONDARY),
                                ]),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=TEXT_DISABLED, icon_size=16, tooltip="刪除", on_click=lambda e, tid=tx["id"]: self._delete_tx(tid)),
                            ],
                        ),
                    ],
                ),
            )

        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("本月明細", size=13, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                ft.Text(f"{len(txs)} 筆", size=11, color=TEXT_DISABLED),
            ],
        )

        if txs:
            self._list_col.controls = [header, ft.Container(height=PAD_SM), *[tx_row(t) for t in txs]]
        else:
            self._list_col.controls = [header, ft.Container(padding=ft.padding.all(PAD_XL), alignment=ft.alignment.center, content=ft.Text("本月尚無記錄，新增第一筆吧 ✦", size=13, color=TEXT_DISABLED))]

    def _refresh_all(self):
        self._refresh_summary()
        self._refresh_list()
        try:
            self._summary_col.update()
            self._list_col.update()
        except Exception:
            pass

    def _handle_submit(self, amount: float, type_: str, category_id: int | None, description: str):
        if not amount or amount <= 0:
            highlight_error(self.page, self._form.amount_field)
            return
            
        add_transaction(amount=amount, type_=type_, category_id=category_id, description=description)
        self._form.reset()
        self._refresh_all()
        show_toast(self.page, "記帳成功")
        try: self._form.amount_field.focus()
        except Exception: pass

    def _handle_new_category(self, _cat: dict):
        self._categories = get_categories()
        self._form.refresh_categories(self._categories)

    def _delete_tx(self, tx_id: int):
        confirm_delete_dialog(self.page, "刪除帳務", lambda: (delete_transaction(tx_id), self._refresh_all(), show_toast(self.page, "已刪除")))

    def _prev_month(self, e):
        y, m = map(int, self._month.split("-"))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        self._month = f"{y:04d}-{m:02d}"
        self._month_label.value = self._fmt_month()
        try: self._month_label.update()
        except Exception as ex: print('[WARN]', ex)
        self._refresh_all()

    def _next_month(self, e):
        y, m = map(int, self._month.split("-"))
        m += 1
        if m == 13:
            m, y = 1, y + 1
        self._month = f"{y:04d}-{m:02d}"
        self._month_label.value = self._fmt_month()
        try: self._month_label.update()
        except Exception as ex: print('[WARN]', ex)
        self._refresh_all()


# ── 2. 統計分析 ──────────────────────────────────────────

class _FinanceStatsView(ft.Column):
    def __init__(self, on_navigate_cb):
        super().__init__(spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
        self.on_navigate_cb = on_navigate_cb
        self._month = date.today().strftime("%Y-%m")
        
        self._month_label = ft.Text(self._fmt_month(), size=13, color=TEXT_PRIMARY, weight=ft.FontWeight.W_500)
        self._chart_container = ft.Container(expand=True)
        self._assemble()
        self._refresh_chart()

    def _fmt_month(self) -> str:
        y, m = self._month.split("-")
        return f"{y}年{int(m):02d}月"

    def _assemble(self):
        self.controls = [
            ft.Container(
                padding=ft.padding.only(left=PAD_LG, right=PAD_LG, top=PAD_LG, bottom=PAD_SM),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=PAD_SM, controls=[
                            ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, icon_color=TEXT_SECONDARY, on_click=lambda e: self.on_navigate_cb("finance") if self.on_navigate_cb else None),
                            ft.Text("統計分析", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ]),
                        ft.Row(
                            spacing=0,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, icon_color=TEXT_SECONDARY, on_click=self._prev_month),
                                self._month_label,
                                ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, icon_color=TEXT_SECONDARY, on_click=self._next_month),
                            ],
                        ),
                    ],
                ),
            ),
            ft.Container(padding=ft.padding.all(PAD_LG), expand=True, content=self._chart_container),
        ]

    def _prev_month(self, e):
        y, m = map(int, self._month.split("-"))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        self._month = f"{y:04d}-{m:02d}"
        self._month_label.value = self._fmt_month()
        self._refresh_chart()

    def _next_month(self, e):
        y, m = map(int, self._month.split("-"))
        m += 1
        if m == 13:
            m, y = 1, y + 1
        self._month = f"{y:04d}-{m:02d}"
        self._month_label.value = self._fmt_month()
        self._refresh_chart()

    def _refresh_chart(self):
        cats = get_monthly_expense_by_category(self._month)
        if cats:
            total = sum(c["total"] for c in cats)
            main_cats = []
            other_total = 0.0
            other_color = TEXT_SECONDARY
            for c in cats:
                if (c["total"] / total) < 0.03 or c["category_name"] == "其他":
                    other_total += c["total"]
                    if c["category_name"] == "其他":
                        other_color = c["color"]
                else:
                    main_cats.append(c)
            if other_total > 0:
                main_cats.append({"category_name": "其他", "color": other_color, "total": other_total})

            legend_rows = []
            for c in main_cats:
                pct = c["total"] / total
                legend_rows.append(
                    ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(width=10, height=10, border_radius=2, bgcolor=c["color"]),
                            ft.Text(f"{c['category_name']}", size=11, color=TEXT_SECONDARY, expand=True),
                            ft.Text(f"{pct:.0%}  NT${c['total']:,.0f}", size=11, color=TEXT_PRIMARY),
                        ],
                    )
                )

            pie_sections = [
                ft.PieChartSection(
                    value=c["total"],
                    color=c["color"],
                    badge=ft.Text(
                        f"{c['category_name']}\n{c['total']/total:.0%}",
                        size=10, color=TEXT_PRIMARY, text_align=ft.TextAlign.CENTER,
                    ) if (c["total"]/total) >= 0.04 else None,
                    badge_position=1.4,
                    radius=120,
                )
                for c in main_cats
            ]

            pie_chart = ft.PieChart(
                sections=pie_sections,
                sections_space=2,
                center_space_radius=0,
                expand=True,
            )

            self._chart_container.content = ft.Row(
                expand=True,
                controls=[
                    ft.Container(expand=2, content=pie_chart, padding=ft.padding.all(PAD_LG)),
                    ft.Container(
                        expand=1,
                        padding=PAD_LG,
                        bgcolor=BG_PANEL,
                        border_radius=RADIUS_LG,
                        border=ft.border.all(1, BG_SURFACE),
                        content=ft.Column(spacing=10, controls=[ft.Text("分類佔比", size=14, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY), *legend_rows]),
                    )
                ]
            )
        else:
            self._chart_container.content = ft.Container(
                alignment=ft.alignment.center,
                content=ft.Column(
                    spacing=8, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.PIE_CHART_OUTLINE_ROUNDED, size=60, color=TEXT_DISABLED),
                        ft.Text("本月尚無支出資料", size=16, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                        ft.Text("新增支出後將顯示分類圓餅圖", size=13, color=TEXT_DISABLED),
                    ],
                ),
            )
        try:
            self._month_label.update()
            self._chart_container.update()
        except Exception:
            pass


# ── 3. 借款管理 ──────────────────────────────────────────

class _FinanceDebtsView(ft.Column):
    def __init__(self, on_navigate_cb):
        super().__init__(spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
        self.on_navigate_cb = on_navigate_cb

        # Form fields
        self._person_input = ft.TextField(label="對象名稱", expand=1, text_size=13, content_padding=PAD_SM, bgcolor=BG_DARK, border_color=BG_SURFACE)
        self._amount_input = ft.TextField(
            label="金額", expand=1, text_size=13, content_padding=PAD_SM, bgcolor=BG_DARK, border_color=BG_SURFACE, 
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9.]", replacement_string="")
        )
        def _on_date_change(e):
            if e.control.value:
                self._date_btn.text = e.control.value.isoformat()
                self._date_btn.update()
                
        self._date_picker = ft.DatePicker(on_change=_on_date_change)
        self._date_btn = ft.ElevatedButton(
            text=date.today().isoformat(),
            icon=ft.Icons.CALENDAR_MONTH,
            bgcolor=BG_DARK,
            color=TEXT_PRIMARY,
            on_click=lambda e: self.page.open(self._date_picker) if self.page else None
        )
        self._type_dropdown = ft.Dropdown(
            label="類別", expand=1, text_size=13, content_padding=PAD_SM, bgcolor=BG_DARK, border_color=BG_SURFACE,
            options=[ft.dropdown.Option("lend", "借出 (別人欠我)"), ft.dropdown.Option("borrow", "借入 (我欠別人)")],
            value="lend"
        )
        self._notes_input = ft.TextField(label="備註 (選填)", expand=1, text_size=13, content_padding=PAD_SM, bgcolor=BG_DARK, border_color=BG_SURFACE)
        
        # 快選清單 (Chips)
        self._person_chips_row = ft.Row(spacing=PAD_SM, wrap=True)

        # Tab contents
        self._tab_pending = ft.Column(spacing=PAD_SM, scroll=ft.ScrollMode.AUTO)
        self._tab_summary = ft.Column(spacing=PAD_SM, scroll=ft.ScrollMode.AUTO)
        self._tab_settled = ft.Column(spacing=PAD_SM, scroll=ft.ScrollMode.AUTO)

        self._tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="待處理清單",
                    content=ft.Container(padding=ft.padding.only(top=PAD_LG), content=self._tab_pending)
                ),
                ft.Tab(
                    text="對象總計",
                    content=ft.Container(padding=ft.padding.only(top=PAD_LG), content=self._tab_summary)
                ),
                ft.Tab(
                    text="歷史紀錄",
                    content=ft.Container(padding=ft.padding.only(top=PAD_LG), content=self._tab_settled)
                ),
            ],
            expand=True,
        )

        self._assemble()
        self._refresh_all()

    def _assemble(self):
        form_row = ft.Container(
            padding=PAD_MD,
            bgcolor=BG_PANEL,
            border_radius=RADIUS_LG,
            border=ft.border.all(1, BG_SURFACE),
            content=ft.Column(
                spacing=PAD_MD,
                controls=[
                    ft.Text("新增借款", size=14, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
                    ft.Row(spacing=PAD_SM, controls=[self._person_input, self._amount_input, self._date_btn]),
                    self._person_chips_row,
                    ft.Row(spacing=PAD_SM, controls=[self._type_dropdown, self._notes_input]),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.ElevatedButton("新增", bgcolor=ACCENT_SOFT, color=ACCENT, on_click=self._handle_add)
                        ]
                    )
                ]
            )
        )

        self.controls = [
            ft.Container(
                padding=ft.padding.only(left=PAD_LG, right=PAD_LG, top=PAD_LG, bottom=PAD_SM),
                content=ft.Row(
                    spacing=PAD_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, icon_color=TEXT_SECONDARY, on_click=lambda e: self.on_navigate_cb("finance") if self.on_navigate_cb else None),
                        ft.Text("借款管理", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ],
                ),
            ),
            ft.Container(padding=ft.padding.symmetric(horizontal=PAD_LG), content=form_row),
            ft.Container(padding=ft.padding.symmetric(horizontal=PAD_LG), expand=True, content=self._tabs),
        ]

    def _handle_add(self, e):
        person = self._person_input.value or ""
        amount_str = self._amount_input.value or "0"
        type_ = self._type_dropdown.value
        date_val = self._date_btn.text
        notes = self._notes_input.value or ""
        try:
            amount = float(amount_str)
            if amount <= 0: raise ValueError("Amount must be positive")
        except ValueError:
            highlight_error(self.page, self._amount_input)
            return
            
        try:
            add_debt(person, amount, type_, date_str=date_val, notes=notes)

            # 清空輸入
            self._amount_input.value = ""
            self._notes_input.value = ""

            try:
                self._amount_input.update()
                self._notes_input.update()
                self._amount_input.focus()
            except Exception:
                pass
                
            self._refresh_all()
            show_toast(self.page, "已新增借款記錄")
        except Exception as ex:
            if self.page:
                self.page.open(ft.SnackBar(ft.Text(f"錯誤: {ex}"), bgcolor=DANGER))

    def _handle_settle(self, debt_id: int):
        mark_debt_settled(debt_id)
        self._refresh_all()
        show_toast(self.page, "借款已結清")

    def _delete_debt(self, debt_id: int):
        confirm_delete_dialog(self.page, "刪除借款紀錄", lambda: (delete_debt(debt_id), self._refresh_all(), show_toast(self.page, "已刪除")))

    def _delete_all_person_debts(self, person: str):
        confirm_delete_dialog(self.page, f"刪除與 {person} 的所有借款紀錄", lambda: (delete_debts_by_person(person), self._refresh_all(), show_toast(self.page, f"已清除 {person} 的所有紀錄")))

    def _refresh_all(self):
        # 快選清單 (Chips)
        def _fill_person(e, p):
            self._person_input.value = p
            try: self._person_input.update()
            except Exception as ex: print('[WARN]', ex)
            
        all_persons = get_all_debt_persons()
        self._person_chips_row.controls = [
            ft.Chip(
                label=ft.Text(p, size=11), 
                bgcolor=BG_SURFACE, 
                on_click=lambda e, pp=p: _fill_person(e, pp)
            ) for p in all_persons
        ]
        
        # Pending
        pending = get_pending_debts()
        self._tab_pending.controls = []
        if not pending:
            self._tab_pending.controls.append(ft.Text("沒有待處理的借款", color=TEXT_DISABLED))
        for d in pending:
            is_lend = d["type"] == "lend"
            color = SUCCESS if is_lend else DANGER
            icon = ft.Icons.ARROW_OUTWARD if is_lend else ft.Icons.CALL_RECEIVED
            self._tab_pending.controls.append(
                ft.Container(
                    padding=PAD_MD, bgcolor=BG_PANEL, border_radius=RADIUS_MD, border=ft.border.only(left=ft.BorderSide(3, color)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(spacing=PAD_MD, controls=[
                                ft.Icon(icon, color=color),
                                ft.Column(spacing=2, controls=[
                                    ft.Text(d["person"], size=14, weight=ft.FontWeight.W_600),
                                    ft.Text(d["date"] + (" - " + d["notes"] if d["notes"] else ""), size=11, color=TEXT_SECONDARY)
                                ])
                            ]),
                            ft.Row(spacing=PAD_MD, controls=[
                                ft.Text(f"NT$ {d['amount']:,.0f}", size=15, weight=ft.FontWeight.BOLD, color=color),
                                ft.ElevatedButton("✅ 結清", on_click=lambda e, did=d["id"]: self._handle_settle(did), bgcolor=BG_SURFACE, color=TEXT_PRIMARY, height=30)
                            ])
                        ]
                    )
                )
            )

        # Summary
        summary = get_debt_summary_by_person()
        self._tab_summary.controls = []
        if not summary:
            self._tab_summary.controls.append(ft.Text("目前沒有未結清對象", color=TEXT_DISABLED))
        for s in summary:
            net = s["net_amount"]
            color = SUCCESS if net > 0 else DANGER
            label = "對方欠我" if net > 0 else "我欠對方"
            self._tab_summary.controls.append(
                ft.Container(
                    padding=PAD_MD, bgcolor=BG_PANEL, border_radius=RADIUS_MD, border=ft.border.all(1, BG_SURFACE),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(s["person"], size=15, weight=ft.FontWeight.W_600),
                            ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=PAD_MD, controls=[
                                ft.Column(horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2, controls=[
                                    ft.Text(label, size=11, color=TEXT_SECONDARY),
                                    ft.Text(f"NT$ {abs(net):,.0f}", size=16, weight=ft.FontWeight.BOLD, color=color),
                                ]),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=TEXT_DISABLED, on_click=lambda e, pp=s["person"]: self._delete_all_person_debts(pp), tooltip="刪除此對象所有款項")
                            ])
                        ]
                    )
                )
            )

        # Settled
        settled = get_settled_debts()
        self._tab_settled.controls = []
        if not settled:
            self._tab_settled.controls.append(ft.Text("沒有已結清的歷史紀錄", color=TEXT_DISABLED))
        for d in settled:
            is_lend = d["type"] == "lend"
            type_label = "借出" if is_lend else "借入"
            self._tab_settled.controls.append(
                ft.Container(
                    padding=PAD_MD, bgcolor=BG_PANEL, border_radius=RADIUS_MD, border=ft.border.all(1, BG_SURFACE),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(spacing=2, controls=[
                                ft.Text(f"{d['person']} ({type_label})", size=13, weight=ft.FontWeight.W_500, color=TEXT_SECONDARY),
                                ft.Text(f"結清於: {d.get('settled_at') or '未知'}", size=11, color=TEXT_DISABLED)
                            ]),
                            ft.Row(spacing=PAD_MD, controls=[
                                ft.Text(f"NT$ {d['amount']:,.0f}", size=14, color=TEXT_DISABLED, style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH)),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=TEXT_DISABLED, on_click=lambda e, did=d["id"]: self._delete_debt(did), tooltip="直接刪除")
                            ])
                        ]
                    )
                )
            )

        try:
            self._person_chips_row.update()
            self._tab_pending.update()
            self._tab_summary.update()
            self._tab_settled.update()
        except Exception:
            pass


# ── 4. 工廠函式 ──────────────────────────────────────────

def FinanceView(route: str = "finance", on_navigate_cb=None) -> ft.Control:
    if route == "finance/stats":
        return _FinanceStatsView(on_navigate_cb)
    elif route == "finance/debts":
        return _FinanceDebtsView(on_navigate_cb)
    else:
        return _FinanceOverviewView(on_navigate_cb)

