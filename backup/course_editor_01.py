"""3E Car Simulator - fullscreen, responsive course editor."""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
COURSE_DIR = ROOT / "saved_courses"
# Logical course size. The editor scales this whole map to the available display area.
CANVAS_W = 1600
CANVAS_H = 900
BG = "#27613b"
ROAD = "#4b4e52"
BORDER = "#d5d5cd"
GRID = "#39764d"


class CourseEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("3E Car Simulator - 最大マップ コースエディター")
        self.root.minsize(1050, 650)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", self._leave_fullscreen)
        self.root.bind("<F11>", self._toggle_fullscreen)

        self.points: list[tuple[float, float]] = []
        self.road_width = tk.IntVar(value=90)
        self.course_name = tk.StringVar(value="My Course")
        self.mode = tk.StringVar(value="points")
        self.selected_index: int | None = None
        self.dragging = False
        self.drawing = False
        self.status = tk.StringVar(value="キャンバスをクリックして、コースの中心線を順番に作成してください。")
        self.saved_course_names: list[str] = []
        self.selected_saved = tk.StringVar()

        self._build_ui()
        self._refresh_saved_courses()
        self.root.after(150, self.redraw)

    def _leave_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", False)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass

    def _toggle_fullscreen(self, _event=None):
        current = self.root.attributes("-fullscreen")
        is_fullscreen = str(current).lower() in ("1", "true", "yes")
        self.root.attributes("-fullscreen", not is_fullscreen)

    def _view(self):
        """Return scale and offsets to fit the complete logical map in the canvas."""
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        scale = min(width / CANVAS_W, height / CANVAS_H)
        offset_x = (width - CANVAS_W * scale) / 2
        offset_y = (height - CANVAS_H * scale) / 2
        return scale, offset_x, offset_y

    def _to_view(self, x: float, y: float, view):
        scale, offset_x, offset_y = view
        return offset_x + x * scale, offset_y + y * scale

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=8)
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            outer,
            width=CANVAS_W,
            height=CANVAS_H,
            background=BG,
            highlightthickness=1,
            highlightbackground="#777777",
            cursor="crosshair",
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

        panel = ttk.Frame(outer, width=275, padding=(12, 0, 0, 0))
        panel.pack(side="left", fill="y")
        panel.pack_propagate(False)

        ttk.Label(panel, text="最大マップ コースエディター", font=("Yu Gothic UI", 15, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            panel,
            text="1600×900の広いマップです。画面サイズに合わせて全体を表示します。Escで全画面解除、F11で切り替えできます。",
            wraplength=250,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(panel, text="作成方法", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w")
        mode_frame = ttk.Frame(panel)
        mode_frame.pack(fill="x", pady=(4, 8))
        ttk.Radiobutton(mode_frame, text="点を配置", value="points", variable=self.mode, command=self._mode_changed).pack(side="left")
        ttk.Radiobutton(mode_frame, text="ペンで描く", value="pen", variable=self.mode, command=self._mode_changed).pack(side="left", padx=(8, 0))

        ttk.Label(panel, text="道路幅", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w", pady=(4, 0))
        width_row = ttk.Frame(panel)
        width_row.pack(fill="x")
        self.width_value = ttk.Label(width_row, text="90 px")
        self.width_value.pack(side="right")
        self.width_scale = ttk.Scale(panel, from_=45, to=180, orient="horizontal", command=self._width_changed)
        self.width_scale.set(90)
        self.width_scale.pack(fill="x", pady=(2, 8))

        ttk.Separator(panel).pack(fill="x", pady=7)
        ttk.Label(panel, text="コース名", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w")
        ttk.Entry(panel, textvariable=self.course_name).pack(fill="x", pady=(4, 8))

        action_row = ttk.Frame(panel)
        action_row.pack(fill="x", pady=(0, 7))
        ttk.Button(action_row, text="1つ戻す", command=self.undo).pack(side="left", fill="x", expand=True)
        ttk.Button(action_row, text="全消去", command=self.clear).pack(side="left", fill="x", expand=True, padx=(6, 0))
        ttk.Button(panel, text="保存", command=self.save_course).pack(fill="x", pady=3)
        ttk.Button(panel, text="保存してシミュレーター起動", command=self.save_and_run).pack(fill="x", pady=3)

        ttk.Separator(panel).pack(fill="x", pady=8)
        ttk.Label(panel, text="保存したコースを開く", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w")
        self.saved_combo = ttk.Combobox(panel, textvariable=self.selected_saved, state="readonly")
        self.saved_combo.pack(fill="x", pady=(4, 5))
        ttk.Button(panel, text="選択したコースを読み込む", command=self.load_selected).pack(fill="x")

        ttk.Separator(panel).pack(fill="x", pady=8)
        help_text = (
            "【点を配置】\n左クリック：点を追加\n点をドラッグ：位置を変更\n\n"
            "【ペンで描く】\n左ボタンを押したままドラッグ\n\n"
            "【コース作成のコツ】\n・点を増やすと滑らかになります\n"
            "・始点と終点は近づけます\n・道路幅は後から変更できます\n"
            "・コースは閉じたループになります\n\n"
            "Esc：全画面解除 / F11：全画面切替"
        )
        ttk.Label(panel, text=help_text, justify="left", wraplength=250).pack(anchor="w")
        ttk.Separator(panel).pack(fill="x", pady=8)
        ttk.Label(panel, textvariable=self.status, wraplength=250, foreground="#245b9a").pack(anchor="w")

    def _mode_changed(self) -> None:
        self.selected_index = None
        self.status.set("点をクリックして追加" if self.mode.get() == "points" else "左ボタンを押したまま、コースを描いてください")
        self.redraw()

    def _width_changed(self, value: str) -> None:
        self.road_width.set(int(float(value)))
        self.width_value.configure(text=f"{self.road_width.get()} px")
        self.redraw()

    def _canvas_xy(self, event) -> tuple[float, float]:
        scale, offset_x, offset_y = self._view()
        x = (float(event.x) - offset_x) / scale
        y = (float(event.y) - offset_y) / scale
        return (
            max(4.0, min(CANVAS_W - 4.0, x)),
            max(4.0, min(CANVAS_H - 4.0, y)),
        )

    def _nearest_point(self, x: float, y: float) -> int | None:
        if not self.points:
            return None
        index = min(range(len(self.points)), key=lambda i: math.hypot(self.points[i][0] - x, self.points[i][1] - y))
        px, py = self.points[index]
        return index if math.hypot(px - x, py - y) <= 20 else None

    def _on_press(self, event) -> None:
        x, y = self._canvas_xy(event)
        if self.mode.get() == "points":
            index = self._nearest_point(x, y)
            if index is not None:
                self.selected_index = index
                self.dragging = True
            else:
                self.points.append((x, y))
                self.selected_index = len(self.points) - 1
                self.dragging = True
                self.status.set(f"点を {len(self.points)} 個配置しました。")
        else:
            self.points = [(x, y)]
            self.drawing = True
            self.status.set("描画中です。始点の近くまで戻ってからマウスを離してください。")
        self.redraw()

    def _on_drag(self, event) -> None:
        x, y = self._canvas_xy(event)
        if self.mode.get() == "points" and self.dragging and self.selected_index is not None:
            self.points[self.selected_index] = (x, y)
            self.redraw()
        elif self.mode.get() == "pen" and self.drawing:
            if not self.points or math.hypot(self.points[-1][0] - x, self.points[-1][1] - y) >= 5:
                self.points.append((x, y))
                self.redraw()

    def _on_release(self, _event) -> None:
        self.dragging = False
        self.drawing = False
        if self.points:
            self.status.set(f"中心線の点が {len(self.points)} 個あります。道路幅を調整して保存できます。")

    def undo(self) -> None:
        if self.points:
            self.points.pop()
            self.status.set("最後の点を削除しました。")
            self.redraw()

    def clear(self) -> None:
        if self.points and not messagebox.askyesno("確認", "描いたコースをすべて消去しますか？"):
            return
        self.points.clear()
        self.status.set("キャンバスを消去しました。")
        self.redraw()

    def redraw(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        view = self._view()
        scale, offset_x, offset_y = view
        left, top = offset_x, offset_y
        right = offset_x + CANVAS_W * scale
        bottom = offset_y + CANVAS_H * scale
        self.canvas.create_rectangle(left, top, right, bottom, fill=BG, outline="")

        grid_step = 50
        for x in range(0, CANVAS_W + 1, grid_step):
            vx, _ = self._to_view(x, 0, view)
            self.canvas.create_line(vx, top, vx, bottom, fill=GRID, width=max(1, scale))
        for y in range(0, CANVAS_H + 1, grid_step):
            _, vy = self._to_view(0, y, view)
            self.canvas.create_line(left, vy, right, vy, fill=GRID, width=max(1, scale))

        if not self.points:
            self.canvas.create_text((left + right) / 2, (top + bottom) / 2, text="ここにコースを描いてください", fill="#dce8dc", font=("Yu Gothic UI", max(12, int(20 * scale))))
            return

        view_points = [self._to_view(x, y, view) for x, y in self.points]
        coords = [value for point in view_points for value in point]
        road_width = max(4, round(self.road_width.get() * scale))
        border_width = road_width + max(2, round(14 * scale))
        closed = len(self.points) >= 3
        if len(self.points) >= 2:
            draw_coords = coords + list(view_points[0]) if closed else coords
            self.canvas.create_line(*draw_coords, fill=BORDER, width=border_width, capstyle="round", joinstyle="round")
            self.canvas.create_line(*draw_coords, fill=ROAD, width=road_width, capstyle="round", joinstyle="round")
            radius_border = border_width / 2
            radius_road = road_width / 2
            for px, py in view_points:
                self.canvas.create_oval(px-radius_border, py-radius_border, px+radius_border, py+radius_border, fill=BORDER, outline=BORDER)
                self.canvas.create_oval(px-radius_road, py-radius_road, px+radius_road, py+radius_road, fill=ROAD, outline=ROAD)
            self.canvas.create_line(*draw_coords, fill="#d5c36f", width=max(1, round(2 * scale)), dash=(max(2, round(12 * scale)), max(2, round(12 * scale))))

        for i, (px, py) in enumerate(view_points):
            radius = max(4, round((9 if i == 0 else 5) * scale))
            color = "#ffffff" if i == 0 else "#f2d36b"
            self.canvas.create_oval(px-radius, py-radius, px+radius, py+radius, fill=color, outline="#263238", width=2)
            if i == 0:
                self.canvas.create_text(px + 16 * scale, py - 16 * scale, text="START", fill="white", anchor="w", font=("Arial", max(7, int(9 * scale)), "bold"))
        if len(view_points) >= 2:
            x0, y0 = view_points[0]
            x1, y1 = view_points[1]
            angle = math.atan2(y1-y0, x1-x0)
            self.canvas.create_line(x0, y0, x0 + 35*scale*math.cos(angle), y0 + 35*scale*math.sin(angle), fill="white", width=max(1, round(3*scale)), arrow=tk.LAST)

    def _safe_filename(self, name: str) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]', "_", name).strip(" .")
        return cleaned or "my_course"

    def _course_data(self) -> dict:
        points = self.points[:]
        if len(points) >= 2 and math.dist(points[0], points[-1]) < 12:
            points.pop()
        if len(points) < 3:
            raise ValueError("コースには3点以上必要です。")
        if len(points) > 1200:
            raise ValueError("点が多すぎます。ペンで描く場合は少し簡単な形にしてください。")
        for i in range(len(points)):
            if math.dist(points[i], points[(i + 1) % len(points)]) < 2:
                raise ValueError("近すぎる点があります。点を少し離してください。")
        return {
            "version": 1,
            "name": self.course_name.get().strip() or "My Course",
            "canvas_width": CANVAS_W,
            "canvas_height": CANVAS_H,
            "road_width": self.road_width.get(),
            "closed": True,
            "points": [[round(x, 2), round(y, 2)] for x, y in points],
        }

    def save_course(self) -> Path | None:
        try:
            data = self._course_data()
        except ValueError as exc:
            messagebox.showwarning("コースを保存できません", str(exc))
            return None
        COURSE_DIR.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(data["name"]) + ".json"
        named_path = COURSE_DIR / filename
        active_path = COURSE_DIR / "active_course.json"
        try:
            encoded = json.dumps(data, ensure_ascii=False, indent=2)
            named_path.write_text(encoded, encoding="utf-8")
            active_path.write_text(encoded, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("保存エラー", str(exc))
            return None
        self._refresh_saved_courses()
        self.selected_saved.set(data["name"])
        self.status.set(f"保存しました：{named_path.name}\nこのコースをシミュレーターで使います。")
        return named_path

    def save_and_run(self) -> None:
        saved = self.save_course()
        if saved is None:
            return
        simulator = ROOT / "car_simulator.py"
        if not simulator.is_file():
            messagebox.showwarning("起動できません", "同じフォルダーに car_simulator.py が見つかりません。\nコースは保存されています。")
            return
        try:
            subprocess.Popen([sys.executable, str(simulator)], cwd=str(ROOT))
            self.status.set("コースを保存し、シミュレーターを起動しました。")
        except OSError as exc:
            messagebox.showerror("起動エラー", str(exc))

    def _refresh_saved_courses(self) -> None:
        COURSE_DIR.mkdir(parents=True, exist_ok=True)
        names = []
        for path in sorted(COURSE_DIR.glob("*.json")):
            if path.name == "active_course.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                names.append(str(data.get("name") or path.stem))
            except (OSError, json.JSONDecodeError):
                continue
        self.saved_course_names = names
        self.saved_combo["values"] = names

    def load_selected(self) -> None:
        wanted = self.selected_saved.get()
        if not wanted:
            messagebox.showinfo("コース選択", "読み込むコースを選択してください。")
            return
        for path in COURSE_DIR.glob("*.json"):
            if path.name == "active_course.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("name") == wanted:
                try:
                    old_w = float(data.get("canvas_width", 1200))
                    old_h = float(data.get("canvas_height", 800))
                    sx, sy = CANVAS_W / old_w, CANVAS_H / old_h
                    points = data["points"]
                    self.points = [(float(p[0]) * sx, float(p[1]) * sy) for p in points]
                    width = float(data.get("road_width", 90)) * min(sx, sy)
                    self.road_width.set(max(45, min(180, round(width))))
                    self.width_scale.set(self.road_width.get())
                    self.width_value.configure(text=f"{self.road_width.get()} px")
                    self.course_name.set(str(data.get("name", wanted)))
                    self.status.set(f"{wanted} を読み込みました。")
                    self.redraw()
                except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError):
                    messagebox.showerror("読み込みエラー", "コースファイルの形式が正しくありません。")
                return
        messagebox.showwarning("読み込みエラー", "選択したコースファイルが見つかりません。")


def main() -> None:
    root = tk.Tk()
    CourseEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
