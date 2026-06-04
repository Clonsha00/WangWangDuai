import flet as ft
from theme import (
    BG_PANEL, BG_SURFACE, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED, PAD_MD, PAD_SM
)
from database import get_categories, add_category, delete_category

TAG_PALETTE = ["#E74C3C", "#E67E22", "#F1C40F", "#2ECC71", "#3498DB", "#9B59B6", "#34495E", "#95A5A6"]

def open_tag_manager(page: ft.Page, on_refresh_cb: callable):
    if not page: return
    
    selected_color = [TAG_PALETTE[0]]
    
    def refresh_manager_list():
        tags = get_categories(type_filter="action")
        def delete_tag(tid):
            try:
                delete_category(tid)
                refresh_manager_list()
                on_refresh_cb()
            except Exception as ex:
                print("Delete tag error:", ex)
                
        list_col.controls = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row([
                        ft.Container(width=12, height=12, border_radius=6, bgcolor=t["color"]),
                        ft.Text(t["name"], size=13, color=TEXT_PRIMARY)
                    ]),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14, icon_color=TEXT_DISABLED, on_click=lambda e, tid=t["id"]: delete_tag(tid))
                ]
            ) for t in tags
        ]
        try: list_col.update()
        except: pass
        
    def build_palette():
        def set_color(c):
            selected_color[0] = c
            palette_row.controls = build_palette().controls
            palette_row.update()
        return ft.Row(
            spacing=8,
            controls=[
                ft.Container(
                    width=24, height=24, border_radius=12, bgcolor=c,
                    border=ft.border.all(2, TEXT_PRIMARY) if selected_color[0] == c else None,
                    on_click=lambda e, c=c: set_color(c)
                ) for c in TAG_PALETTE
            ]
        )
        
    def on_add_tag(e):
        name = tag_name_field.value.strip()
        if name:
            add_category(name, icon="🏷️", color=selected_color[0], type_="action")
            tag_name_field.value = ""
            tag_name_field.update()
            refresh_manager_list()
            on_refresh_cb()
            
    list_col = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    tag_name_field = ft.TextField(
        hint_text="新標籤名稱...", expand=True, text_size=13, 
        border_color=BG_SURFACE, focused_border_color=ACCENT, bgcolor=BG_SURFACE,
        content_padding=ft.padding.symmetric(horizontal=PAD_MD, vertical=PAD_SM),
        on_submit=on_add_tag
    )
    palette_row = build_palette()
    
    dialog = ft.AlertDialog(
        title=ft.Text("管理標籤", size=16, weight=ft.FontWeight.BOLD),
        bgcolor=BG_PANEL,
        content=ft.Container(
            width=300, height=400,
            content=ft.Column([
                ft.Text("新增標籤", size=12, color=TEXT_SECONDARY),
                ft.Row([tag_name_field, ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=ACCENT, on_click=on_add_tag)]),
                palette_row,
                ft.Divider(height=20, color=BG_SURFACE),
                ft.Text("現有標籤", size=12, color=TEXT_SECONDARY),
                list_col
            ])
        ),
        actions=[ft.TextButton("關閉", on_click=lambda e: page.close(dialog))]
    )
    page.open(dialog)
    refresh_manager_list()
