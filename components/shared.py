import flet as ft
from theme import TEXT_SECONDARY, BG_PANEL, BG_SURFACE, RADIUS_LG, PAD_MD, TEXT_PRIMARY, ACCENT, DANGER

def section_title(text: str) -> ft.Text:
    return ft.Text(text, size=12, color=TEXT_SECONDARY, weight=ft.FontWeight.W_600)

def card(content: ft.Control, padding=PAD_MD) -> ft.Container:
    return ft.Container(
        padding=padding,
        bgcolor=BG_PANEL,
        border_radius=RADIUS_LG,
        border=ft.border.all(1, BG_SURFACE),
        content=content,
    )

def show_toast(page: ft.Page, message: str, color: str = ACCENT):
    if not page:
        return
    page.overlay.append(
        ft.SnackBar(
            content=ft.Text(message, color=TEXT_PRIMARY),
            bgcolor=color,
            duration=2000,
            open=True
        )
    )
    page.update()

def confirm_delete_dialog(page: ft.Page, title: str, on_confirm: callable):
    if not page:
        return
        
    def _confirm(e):
        page.close(dialog)
        on_confirm()
        
    dialog = ft.AlertDialog(
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        bgcolor=BG_PANEL,
        content=ft.Text("確定要刪除嗎？此操作無法復原。", size=13, color=TEXT_SECONDARY),
        actions=[
            ft.TextButton("取消", on_click=lambda e: page.close(dialog)),
            ft.TextButton("刪除", on_click=_confirm, style=ft.ButtonStyle(color=DANGER))
        ]
    )
    page.open(dialog)

def highlight_error(page: ft.Page, control: ft.Control):
    if not page or not control: return
    import time
    import threading
    original_color = getattr(control, "border_color", None)
    
    def _animate():
        control.border_color = DANGER
        try: control.update()
        except: pass
        time.sleep(0.5)
        control.border_color = original_color
        try: control.update()
        except: pass

    threading.Thread(target=_animate, daemon=True).start()

