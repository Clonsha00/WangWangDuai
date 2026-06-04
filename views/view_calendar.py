"""
view_calendar.py
--------------
拖曳排程視圖
佈局：左 7 (日曆主視圖) : 右 3 (Inbox 收件匣)
支援拖曳排程 (Drag and Drop)
"""

import flet as ft
from datetime import date, timedelta
import calendar
import os

from theme import (
    BG_DARK, BG_PANEL, BG_SURFACE,
    ACCENT, ACCENT_SOFT, SUCCESS, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
)
from database import (
    add_action, get_actions, update_action_status, delete_action,
    update_todo_due_date, get_categories, add_category, delete_category
)
from components.shared import section_title, card, confirm_delete_dialog, show_toast
from components.tag_manager import open_tag_manager

class _CalendarView(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)

        self._current_date = date.today()
        self._view_year = self._current_date.year
        self._view_month = self._current_date.month

        # 動態區塊容器
        self._calendar_container = ft.Container(expand=True)
        self._inbox_col = ft.Column(spacing=PAD_SM, scroll=ft.ScrollMode.AUTO, expand=True)

        self._selected_inbox_tag = None
        self._inbox_tags_row = ft.Row(spacing=PAD_SM, scroll=ft.ScrollMode.AUTO)

        # 新增未排程任務輸入框
        self._todo_field = ft.TextField(
            hint_text="新增未排程任務，按 Enter...",
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            cursor_color=ACCENT,
            text_size=13,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM),
            on_submit=self._add_inbox_todo,
            suffix=ft.IconButton(
                ft.Icons.ADD_CIRCLE_OUTLINE,
                icon_color=ACCENT,
                icon_size=18,
                on_click=self._add_inbox_todo,
                tooltip="新增",
            ),
        )

        self._assemble()
        self._refresh_all()

    def _assemble(self):
        self._month_label = ft.Text(
            f"{self._view_year} 年 {self._view_month} 月",
            size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY
        )
        header = ft.Container(
            padding=ft.padding.only(left=PAD_LG, right=PAD_LG, top=PAD_LG, bottom=PAD_SM),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row([
                        ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=self._prev_month),
                        self._month_label,
                        ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=self._next_month),
                        ft.ElevatedButton("回到今天", height=32, bgcolor=BG_SURFACE, color=TEXT_SECONDARY, on_click=self._go_today)
                    ]),
                    ft.Row([
                        ft.ElevatedButton("🏷️ 標籤管理", height=32, bgcolor=BG_SURFACE, color=TEXT_PRIMARY, on_click=lambda e: open_tag_manager(self.page, lambda: (self._refresh_tag_selector(), self._refresh_all()))),
                        ft.Text("拖曳排程", size=14, color=TEXT_SECONDARY),
                    ])
                ],
            ),
        )

        divider = ft.Divider(height=1, color=BG_SURFACE)

        left_col = ft.Container(
            expand=7,
            padding=PAD_LG,
            content=self._calendar_container
        )

        right_col = ft.Container(
            expand=3,
            padding=ft.padding.only(top=PAD_LG, right=PAD_LG, bottom=PAD_LG, left=0),
            content=card(
                ft.Column(
                    expand=True,
                    spacing=PAD_MD,
                    controls=[
                        section_title("📥 Inbox (未排程)"),
                        self._todo_field,
                        self._inbox_tags_row,
                        self._inbox_col,
                    ],
                )
            ),
        )

        body = ft.Row(
            expand=True,
            spacing=0,
            controls=[
                left_col,
                ft.VerticalDivider(width=1, color=BG_SURFACE),
                right_col,
            ],
        )

        self.controls = [header, divider, body]

    # ════════════════════════════════════════════════════════════════
    # 控制與刷新
    # ════════════════════════════════════════════════════════════════
    def _prev_month(self, e):
        d = date(self._view_year, self._view_month, 1) - timedelta(days=1)
        self._view_year = d.year
        self._view_month = d.month
        self._refresh_all()

    def _next_month(self, e):
        days_in_month = calendar.monthrange(self._view_year, self._view_month)[1]
        d = date(self._view_year, self._view_month, days_in_month) + timedelta(days=1)
        self._view_year = d.year
        self._view_month = d.month
        self._refresh_all()

    def _go_today(self, e):
        self._view_year = self._current_date.year
        self._view_month = self._current_date.month
        self._refresh_all()

    def _refresh_tag_selector(self):
        tags = get_categories(type_filter="action")
        def on_click(tid):
            self._selected_inbox_tag = tid if self._selected_inbox_tag != tid else None
            self._refresh_tag_selector()
            
        self._inbox_tags_row.controls = [
            ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=t["color"] if self._selected_inbox_tag == t["id"] else BG_SURFACE,
                border_radius=RADIUS_SM,
                border=ft.border.all(1, t["color"]),
                on_click=lambda e, tid=t["id"]: on_click(tid),
                content=ft.Text(t["name"], size=11, color=BG_DARK if self._selected_inbox_tag == t["id"] else t["color"])
            ) for t in tags
        ]
        try: self._inbox_tags_row.update()
        except Exception as ex: print('[WARN]', ex)

    def _refresh_all(self):
        self._current_date = date.today()
        self._month_label.value = f"{self._view_year} 年 {self._view_month} 月"
        all_tasks = get_actions(priority=2)
        
        self._render_calendar(all_tasks)
        self._render_inbox(all_tasks)
        self._refresh_tag_selector()
        
        try:
            self.update()
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════════
    # Inbox 渲染與邏輯
    # ════════════════════════════════════════════════════════════════
    def _add_inbox_todo(self, e):
        title = (self._todo_field.value or "").strip()
        if not title: return
        add_action(title, priority=2, due_date=None, category_id=self._selected_inbox_tag)
        self._todo_field.value = ""
        self._selected_inbox_tag = None
        self._refresh_all()
        show_toast(self.page, f"新增排程：{title}")

    def _delete_task(self, task_id):
        confirm_delete_dialog(self.page, "刪除排程", lambda: (delete_action(task_id), self._refresh_all(), show_toast(self.page, "已刪除")))

    def _toggle_task(self, task_id, current_done):
        update_action_status(task_id, "todo" if current_done else "done")
        self._refresh_all()

    def _on_inbox_accept(self, e):
        src_control = e.page.get_control(e.src_id)
        task_id = src_control.data
        update_todo_due_date(task_id, None)
        self._refresh_all()

    def _render_inbox(self, all_tasks):
        inbox_tasks = [t for t in all_tasks if t["due_date"] is None and t["status"] != "done"]
        controls = []
        for task in inbox_tasks:
            draggable_card = ft.Draggable(
                group="task",
                data=task["id"],
                content=ft.Container(
                    padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=6),
                    border_radius=RADIUS_SM,
                    bgcolor=BG_SURFACE,
                    margin=ft.margin.only(bottom=PAD_SM),
                    border=ft.border.all(1, "transparent"),
                    content=ft.Row(
                        spacing=4,
                        controls=[
                            ft.Icon(ft.Icons.DRAG_INDICATOR, size=14, color=TEXT_DISABLED),
                            ft.Checkbox(value=task["status"] == "done", on_change=lambda e, tid=task["id"]: self._toggle_task(tid, not e.control.value)),
                            ft.Text(task["title"], size=13, color=TEXT_PRIMARY, expand=True),
                            *( [ft.Container(bgcolor=task["category_color"], border_radius=4, padding=ft.padding.symmetric(horizontal=4, vertical=2), content=ft.Text(task["category_name"], size=9, color=BG_DARK, weight=ft.FontWeight.W_600))] if task.get("category_color") else [] ),
                            ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_size=12, icon_color=TEXT_DISABLED, on_click=lambda e, tid=task["id"]: self._delete_task(tid))
                        ]
                    )
                ),
                content_feedback=ft.Container(
                    padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=8),
                    border_radius=RADIUS_SM, bgcolor=ACCENT_SOFT, border=ft.border.all(1, ACCENT),
                    content=ft.Text(task["title"], size=13, color=TEXT_PRIMARY)
                )
            )
            controls.append(draggable_card)
            
        if not controls: controls.append(ft.Text("目前沒有未排程的任務 🎉", size=12, color=TEXT_DISABLED))
            
        inbox_target = ft.DragTarget(group="task", content=ft.Column(spacing=PAD_SM, controls=controls, expand=True), on_will_accept=lambda e: True, on_accept=self._on_inbox_accept)
        self._inbox_col.controls = [inbox_target]

    # ════════════════════════════════════════════════════════════════
    # 日曆主視圖渲染
    # ════════════════════════════════════════════════════════════════
    def _render_calendar(self, all_tasks):
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(self._view_year, self._view_month)
        
        while len(month_days) < 6:
            last_day = month_days[-1][-1]
            next_week = [last_day + timedelta(days=i) for i in range(1, 8)]
            month_days.append(next_week)
            
        
        tasks_by_date = {}
        for t in all_tasks:
            if t["due_date"]: tasks_by_date.setdefault(t["due_date"], []).append(t)
                
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        header_row = ft.Row(
            spacing=PAD_SM,
            controls=[
                ft.Container(expand=True, alignment=ft.alignment.center, content=ft.Text(wd, size=12, color=TEXT_SECONDARY, weight=ft.FontWeight.W_600)) for wd in weekdays
            ]
        )
        
        grid = ft.Column(expand=True, spacing=PAD_SM)
        for week in month_days:
            week_row = ft.Row(expand=True, spacing=PAD_SM)
            for day in week:
                is_current_month = (day.month == self._view_month)
                is_today = (day == self._current_date)
                date_str = day.isoformat()
                day_tasks = tasks_by_date.get(date_str, [])
                week_row.controls.append(self._build_calendar_cell(day, is_current_month, is_today, date_str, day_tasks))
            grid.controls.append(week_row)
            
        self._calendar_container.content = ft.Column(expand=True, spacing=PAD_MD, controls=[header_row, grid])

    def _build_calendar_cell(self, day, is_current_month, is_today, date_str, day_tasks):
        bg_color = BG_PANEL if is_current_month else BG_DARK
        border_color = ACCENT if is_today else BG_SURFACE
        
        task_chips = [self._build_task_chip(t) for t in day_tasks]

        cell_content = ft.Container(
            expand=True,
            bgcolor=bg_color,
            border_radius=RADIUS_SM,
            border=ft.border.all(1, border_color),
            padding=PAD_SM,
            alignment=ft.alignment.top_left,
            on_click=lambda e, d=date_str: self._open_day_dialog(d),
            content=ft.Column(
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text(str(day.day), size=12, color=TEXT_PRIMARY if is_current_month else TEXT_DISABLED, weight=ft.FontWeight.W_600 if is_today else ft.FontWeight.NORMAL),
                    *task_chips
                ]
            )
        )
        
        def on_will_accept(e, c_bg=bg_color):
            e.control.content.bgcolor = ACCENT_SOFT
            e.control.update()
            return True

        def on_leave(e, c_bg=bg_color):
            e.control.content.bgcolor = c_bg
            e.control.update()

        def on_accept(e, target_date=date_str, c_bg=bg_color):
            e.control.content.bgcolor = c_bg
            src_control = e.page.get_control(e.src_id)
            task_id = src_control.data
            update_todo_due_date(task_id, target_date)
            self._refresh_all()

        return ft.Container(
            expand=True,
            content=ft.DragTarget(
                group="task",
                content=cell_content,
                on_will_accept=on_will_accept,
                on_leave=on_leave,
                on_accept=on_accept
            )
        )

    def _build_task_chip(self, task):
        done = task["status"] == "done"
        
        bg = SUCCESS if done else (task.get("category_color") or BG_SURFACE)
        text_color = BG_DARK if done or task.get("category_color") else TEXT_PRIMARY
        
        return ft.Draggable(
            group="task",
            data=task["id"],
            content=ft.Container(
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
                bgcolor=bg,
                border_radius=4,
                margin=ft.margin.only(bottom=2),
                content=ft.Row(
                    spacing=4,
                    controls=[
                        ft.GestureDetector(
                            on_tap=lambda e, tid=task["id"], d=done: self._toggle_task(tid, d),
                            content=ft.Icon(ft.Icons.CHECK_CIRCLE if done else ft.Icons.RADIO_BUTTON_UNCHECKED, size=12, color=text_color)
                        ),
                        ft.Text(
                            task["title"], size=10, color=text_color, style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None,
                            expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS
                        ),
                        ft.GestureDetector(
                            on_tap=lambda e, tid=task["id"]: self._delete_task(tid),
                            content=ft.Icon(ft.Icons.CLOSE_ROUNDED, size=10, color=text_color)
                        )
                    ]
                )
            ),
            content_feedback=ft.Container(
                padding=ft.padding.all(6), bgcolor=ACCENT_SOFT, border_radius=4, border=ft.border.all(1, ACCENT),
                content=ft.Text(task["title"], size=10, color=TEXT_PRIMARY)
            )
        )

    # ════════════════════════════════════════════════════════════════
    # 當日彈出視窗
    # ════════════════════════════════════════════════════════════════
    def _open_day_dialog(self, date_str):
        if not self.page: return
        
        dialog_selected_tag = [None]
        tags = get_categories(type_filter="action")
        
        def build_dialog_tags():
            def set_tag(tid):
                dialog_selected_tag[0] = tid if dialog_selected_tag[0] != tid else None
                tag_row.controls = build_dialog_tags().controls
                tag_row.update()
            return ft.Row(
                spacing=PAD_SM, scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        bgcolor=t["color"] if dialog_selected_tag[0] == t["id"] else BG_SURFACE,
                        border_radius=RADIUS_SM, border=ft.border.all(1, t["color"]),
                        on_click=lambda e, tid=t["id"]: set_tag(tid),
                        content=ft.Text(t["name"], size=11, color=BG_DARK if dialog_selected_tag[0] == t["id"] else t["color"])
                    ) for t in tags
                ]
            )

        tag_row = build_dialog_tags()
            
        def refresh_dialog_content():
            all_tasks = get_actions(priority=2)
            day_tasks = [t for t in all_tasks if t["due_date"] == date_str]
            controls = [self._build_dialog_task_row(t, refresh_dialog_content) for t in day_tasks]
            if not controls: controls.append(ft.Text("無待辦事項 🎉", size=13, color=TEXT_DISABLED))
            dialog_col.controls = controls
            dialog_col.update()
            self._refresh_all()
            
        def on_add(e):
            title = add_field.value.strip()
            if title:
                add_action(title, priority=2, due_date=date_str, category_id=dialog_selected_tag[0])
                add_field.value = ""
                dialog_selected_tag[0] = None
                tag_row.controls = build_dialog_tags().controls
                refresh_dialog_content()
                add_field.update()
                tag_row.update()
                
        add_field = ft.TextField(
            hint_text="新增待辦...", expand=True, border_color=BG_SURFACE, focused_border_color=ACCENT,
            bgcolor=BG_SURFACE, color=TEXT_PRIMARY, cursor_color=ACCENT, text_size=13,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM), on_submit=on_add
        )
        dialog_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=4)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"排程 - {date_str}", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            bgcolor=BG_PANEL, shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
            content=ft.Container(
                width=400, height=450,
                content=ft.Column([
                    ft.Row([add_field, ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=ACCENT, on_click=on_add)]),
                    tag_row,
                    ft.Divider(height=1, color=BG_SURFACE),
                    dialog_col
                ])
            ),
            actions=[ft.TextButton("關閉", on_click=lambda e: self.page.close(dialog))]
        )
        self.page.open(dialog)
        refresh_dialog_content()

    def _build_dialog_task_row(self, task, refresh_cb):
        done = task["status"] == "done"
        def toggle(e):
            update_action_status(task["id"], "done" if e.control.value else "todo")
            refresh_cb()
        def delete(e):
            confirm_delete_dialog(self.page, "刪除待辦", lambda: (delete_action(task["id"]), refresh_cb(), show_toast(self.page, "已刪除")))
            
        title_style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None
        
        row_content = [
            ft.Checkbox(value=done, active_color=ACCENT, check_color=TEXT_PRIMARY, on_change=toggle),
            ft.Text(task["title"], expand=True, size=13, style=title_style, color=TEXT_PRIMARY),
        ]
        
        if task.get("category_color"):
            row_content.append(ft.Container(
                bgcolor=task["category_color"], border_radius=4, padding=ft.padding.symmetric(horizontal=4, vertical=2),
                content=ft.Text(task["category_name"], size=9, color=BG_DARK, weight=ft.FontWeight.W_600)
            ))
            
        row_content.append(ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_color=TEXT_DISABLED, icon_size=14, on_click=delete))

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=6),
            border_radius=RADIUS_SM, bgcolor=BG_SURFACE, opacity=0.6 if done else 1.0,
            content=ft.Row(row_content)
        )

def CalendarView() -> ft.Control:
    return _CalendarView()
