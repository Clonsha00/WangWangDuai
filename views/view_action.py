"""
view_action.py
--------------
行動中樞視圖（Action Center MVP）
佈局：左側 (Habits + GTD Todos) / 右側 (Quarterly Goals)
"""

import flet as ft
from datetime import date, timedelta
import os

from theme import (
    BG_DARK, BG_PANEL, BG_SURFACE, BG_HOVER,
    ACCENT, ACCENT_SOFT, SUCCESS, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
)
from database import (
    get_habits, get_habit_log_today, toggle_habit_log, add_habit, delete_habit,
    add_action, get_actions, update_action_status, delete_action,
    get_categories, add_category, delete_category
)
from components.shared import section_title, card, confirm_delete_dialog, show_toast, highlight_error
from components.tag_manager import open_tag_manager

class _ActionView(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        
        self._habits_col  = ft.Column(spacing=PAD_SM)
        self._todo_col    = ft.Column(spacing=PAD_SM)
        self._goals_col   = ft.Column(spacing=PAD_SM)
        
        self._habit_progress = ft.ProgressBar(value=0, color=SUCCESS, bgcolor=BG_SURFACE)
        self._habit_progress_text = ft.Text("0%", size=11, color=TEXT_SECONDARY)
        
        self._todo_date = None
        self._todo_date_label = ft.Text("無", size=11, color=TEXT_SECONDARY)
        self._todo_date_btn = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            icon_color=TEXT_SECONDARY,
            icon_size=18,
            tooltip="設定日期",
            on_click=lambda e: self.page.open(self._todo_date_picker) if self.page else None
        )
        self._todo_date_chip_today = ft.TextButton("今天", height=24, style=ft.ButtonStyle(padding=0), on_click=lambda e: self._set_todo_date(date.today().isoformat()))
        self._todo_date_chip_tmrw = ft.TextButton("明天", height=24, style=ft.ButtonStyle(padding=0), on_click=lambda e: self._set_todo_date((date.today() + timedelta(days=1)).isoformat()))
        
        self._todo_date_picker = ft.DatePicker(
            on_change=self._on_todo_date_change
        )
        
        # Tags state
        self._selected_todo_tag = None
        self._selected_goal_tag = None
        self._todo_tags_row = ft.Row(spacing=PAD_SM, scroll=ft.ScrollMode.AUTO)
        self._goal_tags_row = ft.Row(spacing=PAD_SM, scroll=ft.ScrollMode.AUTO)

        # 習慣輸入框
        self._habit_field = ft.TextField(
            hint_text="新增每日習慣...",
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            cursor_color=ACCENT,
            text_size=13,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM),
            on_submit=self._add_habit,
            suffix=ft.IconButton(
                ft.Icons.ADD_CIRCLE_OUTLINE,
                icon_color=ACCENT,
                icon_size=18,
                on_click=self._add_habit,
                tooltip="新增",
            ),
        )
        
        # 待辦輸入框
        self._todo_field = ft.TextField(
            hint_text="新增待辦事項，按 Enter 送出…",
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            cursor_color=ACCENT,
            text_size=13,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM),
            on_submit=self._add_todo,
            suffix=ft.IconButton(
                ft.Icons.ADD_CIRCLE_OUTLINE,
                icon_color=ACCENT,
                icon_size=18,
                on_click=self._add_todo,
                tooltip="新增",
            ),
        )

        # 季度目標輸入框
        self._goal_field = ft.TextField(
            hint_text="新增季度目標 (P1)...",
            border_color=BG_SURFACE,
            focused_border_color=ACCENT,
            bgcolor=BG_SURFACE,
            color=TEXT_PRIMARY,
            cursor_color=ACCENT,
            text_size=13,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM),
            on_submit=self._add_goal,
            suffix=ft.IconButton(
                ft.Icons.ADD_CIRCLE_OUTLINE,
                icon_color=ACCENT,
                icon_size=18,
                on_click=self._add_goal,
                tooltip="新增",
            ),
        )

        self._assemble()
        self._populate_all()

    def _set_todo_date(self, date_str: str):
        self._todo_date = date_str
        self._todo_date_label.value = date_str or "無"
        self._todo_date_label.update()
        
    def _on_todo_date_change(self, e):
        if e.control.value:
            self._set_todo_date(e.control.value.isoformat())
        else:
            self._set_todo_date(None)

    def _assemble(self):
        self._date_label = ft.Text(date.today().isoformat(), size=12, color=TEXT_SECONDARY)
        
        header = ft.Container(
            padding=ft.padding.only(left=PAD_LG, right=PAD_LG, top=PAD_LG, bottom=PAD_SM),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("行動中樞", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Row([
                        ft.ElevatedButton("🏷️ 標籤管理", height=32, bgcolor=BG_SURFACE, color=TEXT_PRIMARY, on_click=lambda e: open_tag_manager(self.page, lambda: (self._refresh_tag_selectors(), self._refresh_todos(), self._refresh_goals()))),
                        self._date_label,
                    ])
                ],
            ),
        )

        divider = ft.Divider(height=1, color=BG_SURFACE)

        left_col = ft.Container(
            expand=7,
            padding=PAD_LG,
            content=ft.Column(
                expand=True,
                spacing=PAD_LG,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    card(
                        ft.Column(
                            spacing=PAD_MD,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        section_title("☐ 今日習慣 (Habits)"),
                                        self._habit_progress_text
                                    ]
                                ),
                                self._habit_progress,
                                self._habit_field,
                                self._habits_col,
                            ],
                        )
                    ),
                    card(
                        ft.Column(
                            spacing=PAD_MD,
                            controls=[
                                section_title("☐ 今日待辦"),
                                ft.Row(
                                    spacing=PAD_SM,
                                    controls=[
                                        ft.Container(self._todo_field, expand=True),
                                        ft.Row([self._todo_date_chip_today, self._todo_date_chip_tmrw, self._todo_date_btn, self._todo_date_label])
                                    ]
                                ),
                                self._todo_tags_row,
                                self._todo_col,
                            ],
                        )
                    ),
                ],
            ),
        )

        right_col = ft.Container(
            expand=3,
            padding=ft.padding.only(top=PAD_LG, right=PAD_LG, bottom=PAD_LG, left=0),
            content=card(
                ft.Column(
                    spacing=PAD_MD,
                    controls=[
                        section_title("🎯 季度目標 (P1)"),
                        self._goal_field,
                        self._goal_tags_row,
                        self._goals_col,
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

    def _populate_all(self):
        self._refresh_habits()
        self._refresh_todos()
        self._refresh_goals()
        self._refresh_tag_selectors()

    # --- Tags ---
    def _refresh_tag_selectors(self):
        tags = get_categories(type_filter="action")
        
        def make_chip(tag, is_selected, is_todo):
            return ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=tag["color"] if is_selected else BG_SURFACE,
                border_radius=RADIUS_SM,
                border=ft.border.all(1, tag["color"]),
                on_click=lambda e: self._toggle_tag_selection(tag["id"], is_todo),
                content=ft.Text(tag["name"], size=11, color=BG_DARK if is_selected else tag["color"])
            )

        self._todo_tags_row.controls = [make_chip(t, self._selected_todo_tag == t["id"], True) for t in tags]
        self._goal_tags_row.controls = [make_chip(t, self._selected_goal_tag == t["id"], False) for t in tags]
        
        try:
            self._todo_tags_row.update()
            self._goal_tags_row.update()
        except Exception:
            pass

    def _toggle_tag_selection(self, tag_id, is_todo):
        if is_todo:
            self._selected_todo_tag = tag_id if self._selected_todo_tag != tag_id else None
        else:
            self._selected_goal_tag = tag_id if self._selected_goal_tag != tag_id else None
        self._refresh_tag_selectors()


    # --- Habits ---
    def _add_habit(self, e):
        name = (self._habit_field.value or "").strip()
        if not name:
            highlight_error(self.page, self._habit_field)
            return
        try:
            add_habit(name)
            self._habit_field.value = ""
            self._refresh_habits()
            self._habit_field.update()
            self._habit_field.focus()
            show_toast(self.page, f"已新增習慣：{name}")
        except Exception as ex: print('[WARN]', ex)

    def _delete_habit(self, habit_id):
        def _do_delete():
            delete_habit(habit_id)
            self._refresh_habits()
            show_toast(self.page, "習慣已刪除")
        confirm_delete_dialog(self.page, "刪除習慣", _do_delete)

    def _refresh_habits(self):
        habits = get_habits()
        today_log = get_habit_log_today()
        completed_count = sum(1 for h in habits if today_log.get(h["id"], False))
        
        controls = [self._habit_row(h, today_log.get(h["id"], False)) for h in habits]
        if not controls:
            controls.append(ft.Text("尚未設定習慣", size=13, color=TEXT_DISABLED))
            progress = 0
        else:
            progress = completed_count / len(habits)
        
        self._habit_progress.value = progress
        self._habit_progress_text.value = f"{int(progress * 100)}%"
        self._habits_col.controls = controls
        try:
            self._habits_col.update()
            self._habit_progress.update()
            self._habit_progress_text.update()
        except Exception as ex: print('[WARN]', ex)

    def _habit_row(self, habit: dict, done: bool) -> ft.Control:
        def on_change(e):
            toggle_habit_log(habit["id"], e.control.value)
            self._refresh_habits()
        def on_hover(e):
            e.control.bgcolor = BG_HOVER if e.data == "true" else (SUCCESS if done else BG_SURFACE)
            e.control.update()

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=6),
            border_radius=RADIUS_SM,
            bgcolor=SUCCESS if done else BG_SURFACE,
            opacity=0.6 if done else 1.0,
            on_hover=on_hover,
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Checkbox(value=done, active_color=SUCCESS, check_color=BG_SURFACE if done else TEXT_PRIMARY, fill_color="transparent" if not done else None, on_change=on_change),
                    ft.Text(habit["name"], expand=True, size=13, color=BG_DARK if done else TEXT_PRIMARY, style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14, icon_color=TEXT_DISABLED, on_click=lambda e: self._delete_habit(habit["id"]))
                ],
            ),
        )

    # --- Todos ---
    def _refresh_todos(self):
        self._date_label.value = date.today().isoformat()
        try: self._date_label.update()
        except Exception as ex: print('[WARN]', ex)
        all_todos = get_actions(priority=2)
        today_str = date.today().isoformat()
        
        todos = []
        for t in all_todos:
            if t["status"] != "done":
                todos.append(t)
            else:
                updated_at = t.get("updated_at", "")
                if updated_at.startswith(today_str):
                    todos.append(t)

        controls = [self._todo_row(t, t["status"] == "done") for t in todos]
        if not controls:
            controls.append(ft.Text("無待辦事項 🎉", size=13, color=TEXT_DISABLED))
        
        self._todo_col.controls = controls
        try:
            self._todo_col.update()
        except Exception as ex: print('[WARN]', ex)

    def _todo_row(self, task: dict, done: bool) -> ft.Control:
        def on_change(e):
            update_action_status(task["id"], "done" if e.control.value else "todo")
            self._refresh_todos()
        def on_delete(e):
            confirm_delete_dialog(self.page, "刪除待辦", lambda: (delete_action(task["id"]), self._refresh_todos(), show_toast(self.page, "已刪除")))
        def on_hover(e):
            e.control.bgcolor = BG_HOVER if e.data == "true" else BG_SURFACE
            e.control.update()

        title_style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None
        is_overdue = False
        if not done and task.get("due_date"):
            if task["due_date"] < date.today().isoformat():
                is_overdue = True
                
        date_color = DANGER if is_overdue else TEXT_DISABLED
        
        row_content = [
            ft.Checkbox(value=done, active_color=ACCENT, check_color=TEXT_PRIMARY, on_change=on_change),
            ft.Text(task["title"], size=13, style=title_style, color=TEXT_PRIMARY, expand=True),
        ]
        
        if task.get("category_color"):
            row_content.append(ft.Container(
                bgcolor=task["category_color"], border_radius=4, padding=ft.padding.symmetric(horizontal=4, vertical=2),
                content=ft.Text(task["category_name"], size=9, color=BG_DARK, weight=ft.FontWeight.W_600)
            ))

        if task.get("due_date"):
            row_content.append(ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=12, color=date_color), ft.Text(task["due_date"], size=11, color=date_color)], spacing=2))

        row_content.append(ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_color=TEXT_DISABLED, icon_size=14, on_click=on_delete))

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=6),
            border_radius=RADIUS_SM, bgcolor=BG_SURFACE, opacity=0.6 if done else 1.0, on_hover=on_hover,
            content=ft.Row(spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=row_content),
        )

    def _add_todo(self, e):
        title = (self._todo_field.value or "").strip()
        if not title:
            highlight_error(self.page, self._todo_field)
            return
        add_action(title, priority=2, due_date=self._todo_date, category_id=self._selected_todo_tag)
        
        self._todo_field.value = ""
        self._set_todo_date(None)
        self._todo_date_btn.icon_color = TEXT_SECONDARY
        self._todo_date_btn.tooltip = "設定日期"
        self._selected_todo_tag = None
        
        self._refresh_todos()
        self._refresh_tag_selectors()
        try:
            self._todo_field.update()
            self._todo_field.focus()
            self._todo_date_btn.update()
        except Exception as ex: print('[WARN]', ex)
        show_toast(self.page, f"新增待辦：{title}")

    # --- Goals ---
    def _add_goal(self, e):
        title = (self._goal_field.value or "").strip()
        if not title:
            highlight_error(self.page, self._goal_field)
            return
        add_action(title, priority=1, due_date=None, category_id=self._selected_goal_tag)
        self._goal_field.value = ""
        self._selected_goal_tag = None
        self._refresh_goals()
        self._refresh_tag_selectors()
        try:
            self._goal_field.update()
            self._goal_field.focus()
        except Exception as ex: print('[WARN]', ex)
        show_toast(self.page, f"新增目標：{title}")

    def _refresh_goals(self):
        all_goals = get_actions(priority=1)
        today_str = date.today().isoformat()
        goals = []
        for g in all_goals:
            if g["status"] != "done":
                goals.append(g)
            else:
                updated_at = g.get("updated_at", "")
                if updated_at.startswith(today_str):
                    goals.append(g)

        controls = [self._goal_row(g, g["status"] == "done") for g in goals]
        if not controls: controls.append(ft.Text("無季度目標", size=13, color=TEXT_DISABLED))
        self._goals_col.controls = controls
        try: self._goals_col.update()
        except Exception as ex: print('[WARN]', ex)

    def _goal_row(self, goal: dict, done: bool) -> ft.Control:
        def on_change(e):
            update_action_status(goal["id"], "done" if e.control.value else "todo")
            self._refresh_goals()
        def on_hover(e):
            e.control.bgcolor = BG_HOVER if e.data == "true" else BG_DARK
            e.control.update()
        def on_delete(e):
            confirm_delete_dialog(self.page, "刪除季度目標", lambda: (delete_action(goal["id"]), self._refresh_goals(), show_toast(self.page, "已刪除")))

        title_style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None
        
        row_content = [
            ft.Checkbox(value=done, active_color=SUCCESS, check_color=BG_DARK, on_change=on_change),
            ft.Text(goal["title"], expand=True, size=13, style=title_style),
        ]
        
        if goal.get("category_color"):
            row_content.append(ft.Container(
                bgcolor=goal["category_color"], border_radius=4, padding=ft.padding.symmetric(horizontal=4, vertical=2),
                content=ft.Text(goal["category_name"], size=9, color=BG_DARK, weight=ft.FontWeight.W_600)
            ))

        row_content.append(ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14, icon_color=TEXT_DISABLED, on_click=on_delete))

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=PAD_SM, vertical=8),
            border_radius=RADIUS_SM, bgcolor=BG_DARK, border=ft.border.all(1, BG_SURFACE),
            opacity=0.6 if done else 1.0, on_hover=on_hover,
            content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=row_content),
        )

def ActionView() -> ft.Control:
    return _ActionView()
