"""3E Car Simulator - visual course editor (Tkinter, no extra packages)."""
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
CANVAS_W = 800
CANVAS_H = 600
BG = "#27613b"
ROAD = "#4b4e52"
BORDER = "#d5d5cd"
GRID = "#39764d"
ACCENT = "#f2d36b"


class CourseEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("3E Car Simulator - コースエディター")
        self.root.geometry("1110x790")
        self.root.minsize(1000, 720)

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
        self.redraw()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
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
        self.canvas.pack(side="left", fill="both", expand=False)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        panel = ttk.Frame(outer, width=270, padding=(14, 0, 0, 0))
        panel.pack(side="left", fill="both", expand=True)
        panel.pack_propagate(False)

        ttk.Label(panel, text="コースエディター", font=("Yu Gothic UI", 16, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            panel,
            text="道路の中心線を描くだけでコースを作れます。\n最後の点と最初の点は自動でつながります。",
            wraplength=245,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

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
        width_scale = ttk.Scale(panel, from_=45, to=150, orient="horizontal", command=self._width_changed)
        width_scale.set(90)
        width_scale.pack(fill="x", pady=(2, 8))
        self.width_scale = width_scale

        ttk.Separator(panel).pack(fill="x", pady=8)
        ttk.Label(panel, text="コース名", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w")
        ttk.Entry(panel, textvariable=self.course_name).pack(fill="x", pady=(4, 8))

        action_row = ttk.Frame(panel)
        action_row.pack(fill="x", pady=(0, 8))
        ttk.Button(action_row, text="1つ戻す", command=self.undo).pack(side="left", fill="x", expand=True)
        ttk.Button(action_row, text="全消去", command=self.clear).pack(side="left", fill="x", expand=True, padx=(6, 0))

        ttk.Button(panel, text="保存", command=self.save_course).pack(fill="x", pady=(3, 5))
        ttk.Button(panel, text="保存してシミュレーター起動", command=self.save_and_run).pack(fill="x", pady=3)

        ttk.Separator(panel).pack(fill="x", pady=10)
        ttk.Label(panel, text="保存したコースを開く", font=("Yu Gothic UI", 10, "bold")).pack(anchor="w")
        self.saved_combo = ttk.Combobox(panel, textvariable=self.selected_saved, state="readonly")
        self.saved_combo.pack(fill="x", pady=(4, 5))
        ttk.Button(panel, text="選択したコースを読み込む", command=self.load_selected).pack(fill="x")

        ttk.Separator(panel).pack(fill="x", pady=10)
        help_text = (
            "【点を配置】\n"
            "左クリック：点を追加\n"
            "点をドラッグ：位置を変更\n\n"
            "【ペンで描く】\n"
            "左ボタンを押したままドラッグ\n\n"
            "【コース作成のコツ】\n"
            "・点を増やすとカーブが滑らかになります\n"
            "・始点と終点は近づけると自然です\n"
            "・道路幅は後から変更できます\n"
            "・保存するとシミュレーターで使うコースに設定されます"
        )
        ttk.Label(panel, text=help_text, justify="left", wraplength=250).pack(anchor="w")

        ttk.Separator(panel).pack(fill="x", pady=10)
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
        return (max(4.0, min(CANVAS_W - 4.0, float(event.x))), max(4.0, min(CANVAS_H - 4.0, float(event.y))))

    def _nearest_point(self, x: float, y: float) -> int | None:
        if not self.points:
            return None
        index = min(range(len(self.points)), key=lambda i: math.hypot(self.points[i][0] - x, self.points[i][1] - y))
        px, py = self.points[index]
        return index if math.hypot(px - x, py - y) <= 15 else None

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
                self.status.set(f"点を {len(self.points)} 個配置しました。点をドラッグして調整できます。")
        else:
            # Pen mode starts a fresh path; this avoids accidentally creating disconnected roads.
            self.points = [(x, y)]
            self.drawing = True
            self.status.set("描画中です。始点の近くまで戻ってからマウスを離すと自然なループになります。")
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
        self.canvas.delete("all")
        # Subtle reference grid.
        for x in range(0, CANVAS_W + 1, 50):
            self.canvas.create_line(x, 0, x, CANVAS_H, fill=GRID, width=1)
        for y in range(0, CANVAS_H + 1, 50):
            self.canvas.create_line(0, y, CANVAS_W, y, fill=GRID, width=1)

        if not self.points:
            self.canvas.create_text(CANVAS_W / 2, CANVAS_H / 2, text="ここにコースを描いてください", fill="#dce8dc", font=("Yu Gothic UI", 20))
            return

        coords = [coord for point in self.points for coord in point]
        width = max(8, self.road_width.get())
        border_width = width + 14
        closed = len(self.points) >= 3
        if len(self.points) >= 2:
            if closed:
                closed_coords = coords + [self.points[0][0], self.points[0][1]]
            else:
                closed_coords = coords
            self.canvas.create_line(*closed_coords, fill=BORDER, width=border_width, capstyle="round", joinstyle="round", smooth=False)
            self.canvas.create_line(*closed_coords, fill=ROAD, width=width, capstyle="round", joinstyle="round", smooth=False)
            # Round joins keep tight corners from leaving gaps.
            radius_border = border_width / 2
            radius_road = width / 2
            for px, py in self.points:
                self.canvas.create_oval(px-radius_border, py-radius_border, px+radius_border, py+radius_border, fill=BORDER, outline=BORDER)
                self.canvas.create_oval(px-radius_road, py-radius_road, px+radius_road, py+radius_road, fill=ROAD, outline=ROAD)
            self.canvas.create_line(*closed_coords, fill="#d5c36f", width=2, dash=(12, 12))

        # Waypoint markers.
        for i, (px, py) in enumerate(self.points):
            r = 5 if i else 9
            color = "#ffffff" if i == 0 else "#f2d36b"
            self.canvas.create_oval(px-r, py-r, px+r, py+r, fill=color, outline="#263238", width=2)
            if i == 0:
                self.canvas.create_text(px + 16, py - 16, text="START", fill="white", anchor="w", font=("Arial", 9, "bold"))
        if len(self.points) >= 2:
            x0, y0 = self.points[0]
            x1, y1 = self.points[1]
            angle = math.atan2(y1-y0, x1-x0)
            self.canvas.create_line(x0, y0, x0 + 35*math.cos(angle), y0 + 35*math.sin(angle), fill="white", width=3, arrow=tk.LAST)

    def _safe_filename(self, name: str) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]', "_", name).strip(" .")
        return cleaned or "my_course"

    def _course_data(self) -> dict:
        points = self.points[:]
        # Remove accidental final point that duplicates the start; the loop is closed by the simulator.
        if len(points) >= 2 and math.dist(points[0], points[-1]) < 12:
            points.pop()
        if len(points) < 3:
            raise ValueError("コースには3点以上必要です。")
        if len(points) > 1200:
            raise ValueError("点が多すぎます。ペンで描く場合は、少し簡単な形にしてください。")
        # Reject zero-length adjacent segments.
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
                    points = data["points"]
                    self.points = [(float(p[0]), float(p[1])) for p in points]
                    self.road_width.set(int(data.get("road_width", 90)))
                    self.width_scale.set(self.road_width.get())
                    self.width_value.configure(text=f"{self.road_width.get()} px")
                    self.course_name.set(str(data.get("name", wanted)))
                    self.status.set(f"{wanted} を読み込みました。")
                    self.redraw()
                except (KeyError, TypeError, ValueError, IndexError):
                    messagebox.showerror("読み込みエラー", "コースファイルの形式が正しくありません。")
                return
        messagebox.showwarning("読み込みエラー", "選択したコースファイルが見つかりません。")


def main() -> None:
    root = tk.Tk()
    CourseEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
