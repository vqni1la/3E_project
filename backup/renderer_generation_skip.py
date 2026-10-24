#車体、コース、センサーなどの描画
import pygame
import tkinter as tk
from tkinter import ttk

from config.settings import POPULATION_SIZE

def draw_simulation(
    screen,
    font,
    environment,
    individuals,
    generation,
    show_sensors,
    simulation_speed,
):
    # コースを描画
    environment.draw(screen)

    # AIカーとセンサーを描画
    for index, individual in enumerate(individuals):
        car = individual["car"]

        if show_sensors and not individual["finished"]:
            individual["sensor"].draw(screen, car)

        car.draw(screen)

        label = font.render(
            str(index + 1),
            True,
            (255, 255, 255),
        )
        screen.blit(
            label,
            (int(car.x) - 5, int(car.y) - 30),
        )

    pygame.display.flip()
    

class SimulationDashboard:
    """シミュレーション情報を表示する別ウィンドウ。"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("3E Car Simulator - Statistics")
        self.root.geometry("340x300")
        self.root.resizable(False, False)

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

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

        ttk.Label(
            frame,
            text=f"{label_text}:",
            width=18,
        ).pack(side="left")

        ttk.Label(
            frame,
            textvariable=variable,
        ).pack(side="left")

    def update_info(
        self,
        generation,
        individuals,
        show_sensors,
        simulation_speed,
    ):
        if not self.is_open:
            return

        active_count = sum(
            not individual["finished"]
            for individual in individuals
        )

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
        self.running_var.set(
            f"{active_count}/{POPULATION_SIZE}"
        )
        self.finished_var.set(
            f"{finished_count}/{POPULATION_SIZE}"
        )
        self.sensor_var.set(
            "ON" if show_sensors else "OFF"
        )
        self.speed_var.set(f"{simulation_speed}x")
        self.best_lap_var.set(best_lap)

        # Tkinterの画面を更新する
        try:
            self.root.update()
        except tk.TclError:
            self.is_open = False

    def close(self):
        self.is_open = False
        self.root.destroy()
        
class SimulationSettings:
    """シミュレーションの速度などを変更する設定ウィンドウ。"""

    def __init__(self, speed_index, speed_values):
        self.speed_values = speed_values
        self.speed_index = speed_index
        self.is_open = True

        self.root = tk.Toplevel()
        self.root.title("3E Car Simulator - Settings")
        self.root.geometry("340x360")
        self.root.resizable(False, False)

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

        ttk.Label(
            self.root,
            text="Simulation Settings",
            font=("Arial", 14, "bold"),
        ).pack(pady=15)

        ttk.Label(
            self.root,
            text="Simulation Speed",
        ).pack(pady=5)

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

        self.update_label()

        ttk.Separator(self.root, orient="horizontal").pack(
            fill="x", padx=15, pady=8
        )
        ttk.Label(self.root, text="Skip to generation").pack(pady=(3, 2))

        self.target_generation_var = tk.StringVar(value="1000")
        self.target_generation_entry = ttk.Entry(
            self.root, textvariable=self.target_generation_var, width=12
        )
        self.target_generation_entry.pack(pady=3)

        self.skip_status_var = tk.StringVar(value="")
        ttk.Label(
            self.root, textvariable=self.skip_status_var, wraplength=300
        ).pack(pady=2)

        ttk.Button(
            self.root, text="Skip to generation", command=self.request_skip
        ).pack(pady=5)

        self.skip_target = None

    def request_skip(self):
        try:
            target = int(self.target_generation_var.get().strip())
            if target < 1:
                raise ValueError
        except ValueError:
            self.skip_status_var.set("Enter a whole number greater than 0.")
            return

        self.skip_target = target
        self.skip_status_var.set(
            f"Skip requested: generation {target}. "
            "The current generation will finish first."
        )

    def consume_skip_target(self):
        target = self.skip_target
        self.skip_target = None
        return target

    def update_label(self):
        speed = self.speed_values[self.speed_index]
        self.speed_var.set(f"{speed}x")

    def decrease_speed(self):
        self.speed_index = max(0, self.speed_index - 1)
        self.update_label()

    def increase_speed(self):
        self.speed_index = min(
            len(self.speed_values) - 1,
            self.speed_index + 1,
        )
        self.update_label()

    def get_speed_index(self):
        return self.speed_index

    def close(self):
        self.is_open = False
        self.root.destroy()

