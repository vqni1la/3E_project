# 車体、コース、センサーなどの描画
import pygame
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import POPULATION_SIZE


def _draw_ranking_panel(
    screen,
    title,
    ranking_data,
    x,
    y,
    panel_width=245,
    max_rows=20,
):
    """前回または現在のゴール順位を描画する。"""
    ranking_data = ranking_data or {}
    rankings = ranking_data.get("rankings", [])
    generation = ranking_data.get("generation")
    course_name = ranking_data.get("course", "")

    row_height = 22
    visible = rankings[:max_rows]
    extra_count = max(0, len(rankings) - len(visible))
    panel_height = 62 + row_height * max(1, len(visible))
    if extra_count:
        panel_height += row_height

    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((15, 20, 30, 215))
    pygame.draw.rect(
        panel,
        (130, 150, 175, 230),
        panel.get_rect(),
        width=1,
        border_radius=8,
    )

    title_font = pygame.font.Font(None, 23)
    row_font = pygame.font.Font(None, 22)
    generation_text = f"  GEN {generation}" if generation is not None else ""
    header = title_font.render(f"{title}{generation_text}", True, (255, 255, 255))
    panel.blit(header, (10, 9))

    if course_name:
        course_surface = pygame.font.Font(None, 18).render(
            str(course_name)[:28], True, (165, 180, 200)
        )
        panel.blit(course_surface, (10, 31))

    if not rankings:
        empty_text = row_font.render("No finishers", True, (190, 195, 205))
        panel.blit(empty_text, (10, 48))
    else:
        medal_colors = [
            (255, 215, 80),
            (215, 220, 230),
            (205, 145, 100),
        ]
        for index, item in enumerate(visible):
            rank = int(item.get("rank", index + 1))
            color = medal_colors[rank - 1] if 1 <= rank <= 3 else (235, 240, 245)
            number = int(item.get("number", 0))
            finish_time = float(item.get("time", 0.0))
            line = row_font.render(
                f"{rank:>2}.  AI {number:02d}   {finish_time:.2f}s",
                True,
                color,
            )
            panel.blit(line, (10, 51 + index * row_height))

        if extra_count:
            more_text = row_font.render(
                f"... and {extra_count} more",
                True,
                (190, 195, 205),
            )
            panel.blit(more_text, (10, 51 + len(visible) * row_height))

    screen.blit(panel, (x, y))



def draw_control_panel(
    screen,
    font,
    environment,
    manual_mode,
    show_sensors,
    player_crashed=False,
    player_goal_reached=False,
):
    """画面下部にマウス操作用のボタンを描画し、クリック判定領域を返す。"""
    screen_width, screen_height = screen.get_size()
    panel_width = min(720, max(360, screen_width - 32))
    panel_height = 108
    panel_x = 16
    panel_y = max(8, screen_height - panel_height - 14)

    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((10, 16, 27, 232))
    pygame.draw.rect(
        panel, (105, 125, 150, 240), panel.get_rect(),
        width=1, border_radius=10,
    )
    screen.blit(panel, (panel_x, panel_y))

    title_font = pygame.font.Font(None, 22)
    small_font = pygame.font.Font(None, 18)
    title = title_font.render("SIMULATOR CONTROLS", True, (235, 242, 252))
    screen.blit(title, (panel_x + 10, panel_y + 7))

    course_name = str(getattr(environment, "course_name", "Course"))
    current_course = int(getattr(environment, "course_index", 0))
    course_count = int(environment.course_count())
    course_info = small_font.render(
        f"CURRENT STAGE: {current_course + 1} / {course_count}  |  {course_name}",
        True, (175, 195, 220),
    )
    screen.blit(course_info, (panel_x + 260, panel_y + 9))

    buttons = {}

    def draw_button(key, label, x, y, width, enabled=True, accent=None):
        rect = pygame.Rect(x, y, width, 29)
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        if not enabled:
            fill = (48, 54, 64)
            border = (75, 82, 94)
            text_color = (125, 132, 143)
        elif accent is not None:
            fill = accent if not hovered else tuple(min(255, c + 22) for c in accent)
            border = (225, 230, 240)
            text_color = (255, 255, 255)
        else:
            fill = (55, 72, 94) if not hovered else (78, 101, 130)
            border = (145, 170, 200)
            text_color = (245, 248, 255)

        pygame.draw.rect(screen, fill, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, width=1, border_radius=6)
        text_surface = small_font.render(label, True, text_color)
        screen.blit(
            text_surface,
            (rect.centerx - text_surface.get_width() // 2,
             rect.centery - text_surface.get_height() // 2),
        )
        if enabled:
            buttons[key] = rect

    row1_y = panel_y + 31
    x = panel_x + 10
    draw_button(
        "mode", "EXIT PLAYER MODE" if manual_mode else "ENTER PLAYER MODE",
        x, row1_y, 158, accent=(35, 105, 85) if manual_mode else (45, 85, 125),
    )
    x += 166
    draw_button(
        "sensors", "SENSORS: ON" if show_sensors else "SENSORS: OFF",
        x, row1_y, 132,
    )
    x += 140
    if player_crashed:
        restart_accent = (155, 65, 65)
    elif player_goal_reached:
        restart_accent = (35, 125, 80)
    else:
        restart_accent = (95, 78, 52)
    draw_button(
        "restart", "RESTART PLAYER", x, row1_y, 145,
        enabled=manual_mode, accent=restart_accent if manual_mode else None,
    )
    x += 153
    draw_button("quit", "QUIT", x, row1_y, 72, accent=(125, 55, 55))

    row2_y = panel_y + 69
    label_surface = small_font.render("STAGE:", True, (225, 232, 242))
    screen.blit(label_surface, (panel_x + 11, row2_y + 7))
    stage_x = panel_x + 67
    for index in range(6):
        enabled = index < course_count
        selected = index == current_course
        color = (40, 115, 145) if selected else None
        draw_button(
            f"course_{index}", str(index + 1),
            stage_x + index * 43, row2_y, 37,
            enabled=enabled, accent=color,
        )

    hint = small_font.render(
        "Click stage number | M: mode | ESC: quit",
        True, (155, 170, 190),
    )
    hint_x = stage_x + 6 * 43 + 8
    if hint_x + hint.get_width() <= panel_x + panel_width - 8:
        screen.blit(hint, (hint_x, row2_y + 7))

    return buttons

def draw_simulation(
    screen,
    font,
    environment,
    individuals,
    generation,
    show_sensors,
    simulation_speed,
    previous_ranking=None,
    manual_mode=False,
):
    # コースを描画
    environment.draw(screen)

    # ゴールした個体は走行画面から非表示にする。
    # クラッシュ・タイムアウトした個体は従来どおり表示する。
    for index, individual in enumerate(individuals):
        if individual.get("goal_reached", False):
            continue

        car = individual["car"]

        if show_sensors and not individual["finished"]:
            individual["sensor"].draw(screen, car)

        car.draw(screen)

        label = font.render(str(index + 1), True, (255, 255, 255))
        screen.blit(label, (int(car.x) - 5, int(car.y) - 30))

    # 今回の走行でゴールした個体を、ゴール時刻順に並べる。
    finishers = sorted(
        (
            individual for individual in individuals
            if individual.get("goal_reached", False)
        ),
        key=lambda individual: (
            individual.get("finish_time")
            if individual.get("finish_time") is not None
            else float("inf"),
            individual.get("number", 0),
        ),
    )
    current_ranking = {
        "generation": generation,
        "course": getattr(environment, "course_name", ""),
        "rankings": [
            {
                "rank": rank,
                "number": individual.get("number", 0),
                "time": individual.get("finish_time", 0.0) or 0.0,
            }
            for rank, individual in enumerate(finishers, start=1)
        ],
    }

    # 2つの順位表を右上に横並びで表示する。
    panel_width = 245
    gap = 10
    right_margin = 18
    current_x = max(10, screen.get_width() - panel_width - right_margin)
    previous_x = max(10, current_x - panel_width - gap)
    panel_y = 18
    max_rows = max(1, min(POPULATION_SIZE, (screen.get_height() - 100) // 22))

    # 表示行数を画面の高さに合わせるため、描画関数で使う最大行数を渡す。
    _draw_ranking_panel(
        screen,
        "PREVIOUS RESULT",
        previous_ranking,
        previous_x,
        panel_y,
        panel_width=panel_width,
        max_rows=max_rows,
    )
    _draw_ranking_panel(
        screen,
        "CURRENT RESULT",
        current_ranking,
        current_x,
        panel_y,
        panel_width=panel_width,
        max_rows=max_rows,
    )

    control_buttons = draw_control_panel(
        screen, font, environment, manual_mode, show_sensors, False
    )
    pygame.display.flip()
    return control_buttons


def draw_manual_mode(
    screen,
    font,
    environment,
    player_car,
    ghost,
    generation,
    show_sensors,
    simulation_speed,
    individuals=None,
    previous_ranking=None,
    player_crashed=False,
    player_goal_reached=False,
    player_finish_time=None,
):
    """手動プレイ画面。プレイヤー車と切替時に選んだAIゴーストを描画する。"""
    environment.draw(screen)

    ghost_car = ghost["car"]
    if show_sensors and not ghost["finished"]:
        ghost["sensor"].draw(screen, ghost_car)

    # ゴーストは半透明の青で描画する。
    ghost_width = max(1, int(round(ghost_car.width)))
    ghost_height = max(1, int(round(ghost_car.height)))
    ghost_surface = pygame.Surface(
        (ghost_width, ghost_height), pygame.SRCALPHA
    )
    pygame.draw.rect(
        ghost_surface,
        (65, 165, 255, 105),
        (0, 0, ghost_width, ghost_height),
    )
    pygame.draw.rect(
        ghost_surface,
        (165, 225, 255, 210),
        (0, 0, ghost_width, ghost_height),
        width=max(1, int(round(ghost_car.width * 0.05))),
    )
    rotated_ghost = pygame.transform.rotate(ghost_surface, -ghost_car.angle)
    ghost_rect = rotated_ghost.get_rect(
        center=(round(ghost_car.x), round(ghost_car.y))
    )
    screen.blit(rotated_ghost, ghost_rect)

    # プレイヤーはゴーストより手前に描画する。
    player_car.draw(screen)

    ghost_status = (
        "GOAL" if ghost.get("goal_reached", False)
        else "CRASHED" if ghost.get("crashed", False)
        else "TIME UP" if ghost.get("finished", False)
        else "RUNNING"
    )
    ghost_number = int(ghost.get("number", 0))

    hud_lines = [
        ("PLAYER MODE  |  M: return to evolution", (255, 255, 255)),
        ("W/S: forward/back   A/D: turn   R: restart   V: sensors", (225, 230, 240)),
        (f"BEST AI GHOST: AI {ghost_number:02d}  [{ghost_status}]", (110, 205, 255)),
        (f"Generation: {generation}   Simulation: {simulation_speed}x", (225, 230, 240)),
    ]
    if player_crashed:
        hud_lines.append(("PLAYER OFF TRACK - Press R or click RESTART PLAYER", (255, 105, 105)))
    elif player_goal_reached:
        finish_text = (
            f"{player_finish_time:.2f}s"
            if player_finish_time is not None else "--"
        )
        hud_lines.append((
            f"PLAYER GOAL! FINISH: {finish_text} - Click RESTART PLAYER to run again",
            (105, 245, 155),
        ))

    for index, (text, color) in enumerate(hud_lines):
        screen.blit(font.render(text, True, color), (18, 15 + index * 26))

    player_label = font.render("YOU", True, (255, 235, 110))
    screen.blit(
        player_label,
        (int(player_car.x) - player_label.get_width() // 2,
         int(player_car.y) - int(player_car.height) - 18),
    )
    ghost_label = font.render(f"GHOST {ghost_number:02d}", True, (120, 210, 255))
    screen.blit(
        ghost_label,
        (int(ghost_car.x) - ghost_label.get_width() // 2,
         int(ghost_car.y) - int(ghost_car.height) - 18),
    )

    # 手動モード中も左右の前回・今回順位表を維持する。
    if individuals is not None:
        finishers = sorted(
            (item for item in individuals if item.get("goal_reached", False)),
            key=lambda item: (
                item.get("finish_time") if item.get("finish_time") is not None else float("inf"),
                item.get("number", 0),
            ),
        )
        current_ranking = {
            "generation": generation,
            "course": getattr(environment, "course_name", ""),
            "rankings": [
                {
                    "rank": rank,
                    "number": item.get("number", 0),
                    "time": item.get("finish_time", 0.0) or 0.0,
                }
                for rank, item in enumerate(finishers, start=1)
            ],
        }
        panel_width = 245
        gap = 10
        right_margin = 18
        current_x = max(10, screen.get_width() - panel_width - right_margin)
        previous_x = max(10, current_x - panel_width - gap)
        panel_y = 18
        max_rows = max(1, min(POPULATION_SIZE, (screen.get_height() - 100) // 22))
        _draw_ranking_panel(
            screen, "PREVIOUS RESULT", previous_ranking,
            previous_x, panel_y, panel_width=panel_width, max_rows=max_rows,
        )
        _draw_ranking_panel(
            screen, "CURRENT RESULT", current_ranking,
            current_x, panel_y, panel_width=panel_width, max_rows=max_rows,
        )

    control_buttons = draw_control_panel(
        screen, font, environment, True, show_sensors,
        player_crashed, player_goal_reached,
    )
    pygame.display.flip()
    return control_buttons


class SimulationDashboard:
    """シミュレーション情報を表示する別ウィンドウ。"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("3E Car Simulator - Statistics")
        self.root.geometry("340x300")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        title = ttk.Label(
            self.root,
            text="Simulation Statistics",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=(15, 10))

        self.generation_var = tk.StringVar()
        self.running_var = tk.StringVar()
        self.finished_var = tk.StringVar()
        self.sensor_var = tk.StringVar()
        self.speed_var = tk.StringVar()
        self.best_lap_var = tk.StringVar()

        self._add_row("Generation", self.generation_var)
        self._add_row("Running", self.running_var)
        self._add_row("Finished", self.finished_var)
        self._add_row("Sensors", self.sensor_var)
        self._add_row("Simulation Speed", self.speed_var)
        self._add_row("Best Lap", self.best_lap_var)

        self.is_open = True

    def _add_row(self, label_text, variable):
        frame = ttk.Frame(self.root, padding=(15, 5))
        frame.pack(fill="x")

        ttk.Label(frame, text=f"{label_text}:", width=18).pack(side="left")
        ttk.Label(frame, textvariable=variable).pack(side="left")

    def update_info(self, generation, individuals, show_sensors, simulation_speed):
        if not self.is_open:
            return

        active_count = sum(not individual["finished"] for individual in individuals)
        finished_count = len(individuals) - active_count
        lap_times = [
            lap_time
            for individual in individuals
            for lap_time in individual["lap_times"]
        ]
        best_lap = (
            f"{min(lap_times):.2f} seconds"
            if lap_times
            else "No lap completed"
        )

        self.generation_var.set(str(generation))
        self.running_var.set(f"{active_count}/{POPULATION_SIZE}")
        self.finished_var.set(f"{finished_count}/{POPULATION_SIZE}")
        self.sensor_var.set("ON" if show_sensors else "OFF")
        self.speed_var.set(f"{simulation_speed}x")
        self.best_lap_var.set(best_lap)

        try:
            self.root.update()
        except tk.TclError:
            self.is_open = False

    def update_manual_info(
        self,
        ghost,
        show_sensors,
        simulation_speed,
        player_crashed=False,
        player_goal_reached=False,
        player_finish_time=None,
    ):
        if not self.is_open:
            return

        ghost_status = (
            "GOAL" if ghost.get("goal_reached", False)
            else "CRASHED" if ghost.get("crashed", False)
            else "TIME UP" if ghost.get("finished", False)
            else "RUNNING"
        )
        lap_times = ghost.get("lap_times", [])
        best_lap = (
            f"{min(lap_times):.2f} seconds" if lap_times else "No lap completed"
        )

        self.generation_var.set("PLAYER MODE")
        if player_goal_reached:
            self.running_var.set("PLAYER GOAL")
            finish_text = (
                f"{player_finish_time:.2f}s"
                if player_finish_time is not None else "--"
            )
            self.finished_var.set(f"PLAYER FINISH: {finish_text}")
        elif player_crashed:
            self.running_var.set("PLAYER CRASHED")
            self.finished_var.set(f"GHOST: {ghost_status}")
        else:
            self.running_var.set("PLAYER")
            self.finished_var.set(f"GHOST: {ghost_status}")
        self.sensor_var.set("ON" if show_sensors else "OFF")
        self.speed_var.set(f"{simulation_speed}x")
        self.best_lap_var.set(best_lap)

        try:
            self.root.update()
        except tk.TclError:
            self.is_open = False

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        try:
            self.root.destroy()
        except tk.TclError:
            pass


class SimulationSettings:
    """シミュレーション速度と学習リセットを操作する設定ウィンドウ。"""

    def __init__(self, speed_index, speed_values):
        self.speed_values = speed_values
        self.speed_index = speed_index
        self.is_open = True
        self.reset_requested = False

        self.root = tk.Toplevel()
        self.root.title("3E Car Simulator - Settings")
        self.root.geometry("320x290")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        ttk.Label(
            self.root,
            text="Simulation Settings",
            font=("Arial", 14, "bold"),
        ).pack(pady=15)

        ttk.Label(self.root, text="Simulation Speed").pack(pady=5)

        self.speed_var = tk.StringVar()
        self.speed_label = ttk.Label(
            self.root,
            textvariable=self.speed_var,
            font=("Arial", 12),
        )
        self.speed_label.pack(pady=5)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame,
            text="-",
            width=5,
            command=self.decrease_speed,
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="+",
            width=5,
            command=self.increase_speed,
        ).pack(side="left", padx=5)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=15, pady=8)

        ttk.Button(
            self.root,
            text="Reset Learning",
            command=self.request_learning_reset,
        ).pack(fill="x", padx=25, pady=(4, 10))

        self.update_label()

    def update_label(self):
        speed = self.speed_values[self.speed_index]
        self.speed_var.set(f"{speed}x")

    def decrease_speed(self):
        self.speed_index = max(0, self.speed_index - 1)
        self.update_label()

    def increase_speed(self):
        self.speed_index = min(len(self.speed_values) - 1, self.speed_index + 1)
        self.update_label()

    def get_speed_index(self):
        return self.speed_index

    def request_learning_reset(self):
        if not self.is_open:
            return

        confirmed = messagebox.askyesno(
            "Reset Learning?",
            "現在の世代を中止し、Generation 1から新しく学習を始めます。\n\n"
            "現在の best_genome.json と training_history.csv は"
            "バックアップに保存されます。\n\n"
            "学習をリセットしますか？",
            parent=self.root,
        )
        if confirmed:
            self.reset_requested = True

    def consume_reset_request(self):
        requested = self.reset_requested
        self.reset_requested = False
        return requested

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        try:
            self.root.destroy()
        except tk.TclError:
            pass
