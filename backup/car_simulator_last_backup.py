# 全体の起動、各モジュールの連携

import csv
import json
import os
import math
import shutil
from datetime import datetime

import pygame
import ctypes
from ctypes import wintypes

from simulation.car import Car
from simulation.environment import Environment
from simulation.sensor import Sensor
from ai.neural_network import NeuralNetwork
from evolution.genetic_algorithm import GeneticAlgorithm
from evolution.fitness import calculate_fitness
from simulation.renderer import (
    draw_simulation,
    SimulationDashboard,
    SimulationSettings,
)
from config.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    WINDOW_TITLE,
    POPULATION_SIZE,
    MAX_SURVIVAL_TIME,
    SIMULATION_SPEEDS,
    DEFAULT_SPEED_INDEX,
    SHOW_SENSORS_DEFAULT,
    BEST_GENOME_PATH,
    TRAINING_HISTORY_PATH,
)

CAR_COLORS = [
    (255, 70, 70), (70, 180, 255), (255, 210, 50),
    (70, 230, 120), (220, 100, 255), (255, 150, 60),
    (80, 240, 220), (255, 120, 190), (180, 220, 80),
    (180, 180, 255), (255, 100, 100), (100, 255, 170),
    (255, 180, 80), (130, 160, 255), (230, 230, 100),
    (100, 220, 220), (220, 130, 255), (150, 255, 100),
    (255, 140, 140), (200, 200, 200),
]


def create_individual(environment, genome, index):
    display_scale = getattr(environment, "scale", 1.0)

    car = Car(environment.start_x, environment.start_y)
    car.angle = environment.start_angle
    car.color = CAR_COLORS[index % len(CAR_COLORS)]

    # マップと一緒に車体寸法・速度・左右車輪間隔を拡大縮小する
    for attribute in ("width", "height", "speed", "track_width"):
        value = getattr(car, attribute, None)
        if isinstance(value, (int, float)):
            setattr(car, attribute, value * display_scale)

    sensor = Sensor(max_distance=150 * display_scale)

    brain = NeuralNetwork()
    brain.set_weights(genome.weights)

    return {
        "car": car,
        "sensor": sensor,
        "brain": brain,
        "elapsed_time": 0.0,
        "distance": 0.0,
        "progress": 0.0,
        "previous_progress": environment.get_track_progress(car.x, car.y),
        "laps": 0,
        "lap_start_time": 0.0,
        "lap_start_distance": 0.0,
        "lap_times": [],
        "lap_distances": [],
        "crashed": False,
        "finished": False,
        "fitness": None,
        "display_scale": display_scale,
        "number": index + 1,
        "goal_reached": False,
        "finish_time": None,
    }


def update_individual(individual, environment, dt):
    if individual["finished"]:
        return

    car = individual["car"]
    sensor = individual["sensor"]
    brain = individual["brain"]

    sensor.update(car, environment)
    display_scale = individual.get("display_scale", 1.0)
    sensor_inputs = [distance / display_scale for distance in sensor.distances]
    output = brain.predict(sensor_inputs)

    old_x, old_y = car.x, car.y

    car.update_ai(
        dt,
        float(output[0]),
        float(output[1]),
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
    )

    moved_distance = math.hypot(car.x - old_x, car.y - old_y)
    individual["distance"] += moved_distance
    individual["elapsed_time"] += dt

    current_progress = environment.get_track_progress(car.x, car.y)
    delta = current_progress - individual["previous_progress"]

    if delta < -environment.track_length / 2:
        delta += environment.track_length
    elif delta > environment.track_length / 2:
        delta -= environment.track_length

    if 0 <= delta <= 30 * getattr(environment, "scale", 1.0):
        individual["progress"] += delta

    individual["previous_progress"] = current_progress

    # 周回数が増えたら、その周のタイムと距離を記録する
    new_laps = int(individual["progress"] // environment.track_length)

    while new_laps > individual["laps"]:
        individual["lap_times"].append(
            individual["elapsed_time"] - individual["lap_start_time"]
        )
        individual["lap_distances"].append(
            individual["distance"] - individual["lap_start_distance"]
        )

        individual["lap_start_time"] = individual["elapsed_time"]
        individual["lap_start_distance"] = individual["distance"]
        individual["laps"] += 1

        lap_number = individual["laps"]
        lap_time = individual["lap_times"][-1]
        lap_distance = individual["lap_distances"][-1]
        print(
            f"AI 周回達成: {lap_number}周目 | "
            f"タイム: {lap_time:.2f}秒 | 距離: {lap_distance:.1f}"
        )

    if not environment.is_on_track(car.x, car.y):
        individual["crashed"] = True
        individual["finished"] = True
    elif individual["laps"] >= 1:
        # 1周完了をゴールとする。ゴール後はこの個体の更新を停止する。
        individual["goal_reached"] = True
        individual["finish_time"] = individual["elapsed_time"]
        individual["finished"] = True
        print(
            f"AI {individual['number']:02d} ゴール！ "
            f"タイム: {individual['finish_time']:.2f}秒"
        )
    elif individual["elapsed_time"] >= MAX_SURVIVAL_TIME:
        individual["finished"] = True

    if individual["finished"]:
        individual["fitness"] = calculate_fitness(
            distance=individual["distance"],
            survival_time=individual["elapsed_time"],
            completed=(individual["laps"] > 0),
            progress=individual["progress"],
            laps=individual["laps"],
            lap_times=individual["lap_times"],
            lap_distances=individual["lap_distances"],
            track_length=environment.track_length,
        )


def archive_learning_data(history_path, best_path):
    """現在の学習履歴と最優秀モデルを保存用フォルダへ退避する。"""
    existing_files = [path for path in (history_path, best_path) if os.path.isfile(path)]
    if not existing_files:
        return None

    archive_root = os.path.join("saved_models", "learning_archives")
    os.makedirs(archive_root, exist_ok=True)

    timestamp = datetime.now().strftime("reset_%Y%m%d_%H%M%S")
    archive_dir = os.path.join(archive_root, timestamp)
    suffix = 1
    while os.path.exists(archive_dir):
        archive_dir = os.path.join(archive_root, f"{timestamp}_{suffix}")
        suffix += 1

    os.makedirs(archive_dir)

    # 先にすべてコピーし、コピーが成功してから元ファイルを削除する。
    for source_path in existing_files:
        shutil.copy2(
            source_path,
            os.path.join(archive_dir, os.path.basename(source_path)),
        )

    for source_path in existing_files:
        os.remove(source_path)

    return archive_dir


def make_ranking_record(individuals, generation, course_name):
    """この世代でゴールした個体の順位表を保存用データにする。"""
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

    return {
        "generation": generation,
        "course": str(course_name),
        "rankings": [
            {
                "rank": rank,
                "number": int(individual.get("number", 0)),
                "time": float(individual.get("finish_time") or 0.0),
            }
            for rank, individual in enumerate(finishers, start=1)
        ],
    }


def load_previous_ranking(path):
    """前回の完了結果を読み込む。ファイルがなければ空欄にする。"""
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict) or not isinstance(data.get("rankings"), list):
            raise ValueError("順位表のJSON形式が正しくありません。")
        return data
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"前回の順位表を読み込めませんでした: {error}")
        return None


def save_previous_ranking(path, ranking_record):
    """今回の完了結果を、次回表示する前回記録として安全に保存する。"""
    temporary_path = path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(ranking_record, file, ensure_ascii=False, indent=2)
    os.replace(temporary_path, path)


def main():
    pygame.init()

    global SCREEN_WIDTH, SCREEN_HEIGHT

    # 通常のサイズ変更可能なウィンドウを作成
    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
    pygame.display.set_caption("3E Car Simulator - Parallel Evolution")

    # Windowsのウィンドウを最大化
    hwnd = pygame.display.get_wm_info().get("window")
    if hwnd:
        user32 = ctypes.windll.user32
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE

    # 最大化後の実際の描画領域を取得
    SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 26)

    dashboard = SimulationDashboard()
    settings = SimulationSettings(
        speed_index=DEFAULT_SPEED_INDEX,
        speed_values=SIMULATION_SPEEDS,
    )

    environment = Environment()
    pygame.display.set_caption(
        f"3E Car Simulator - {environment.course_name}"
    )

    ga = GeneticAlgorithm(population_size=POPULATION_SIZE)

    os.makedirs("saved_models", exist_ok=True)
    history_path = "saved_models/training_history.csv"
    best_path = "saved_models/best_genome.json"
    previous_ranking_path = "saved_models/previous_ranking.json"
    previous_ranking = load_previous_ranking(previous_ranking_path)

    if previous_ranking:
        print(
            "前回の順位表を読み込みました。"
            f"（Generation {previous_ranking.get('generation', '?')}）"
        )

    best_fitness_ever = float("-inf")
    generation = 1
    show_sensors = True
    running = True

    while running:
        individuals = [
            create_individual(environment, genome, index)
            for index, genome in enumerate(ga.population)
        ]

        course_changed = False
        learning_reset = False

        print(f"\n世代 {generation} の走行を開始します。")

        while running and any(
            not individual["finished"] for individual in individuals
        ):
            real_dt = clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.VIDEORESIZE:
                    SCREEN_WIDTH = event.w
                    SCREEN_HEIGHT = event.h
                    screen = pygame.display.set_mode(
                        (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE
                    )

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_s:
                        show_sensors = not show_sensors
                    # 1～6キーでコースを切り替える
                    elif pygame.K_1 <= event.key <= pygame.K_6:
                        new_course_index = event.key - pygame.K_1
                        if new_course_index < environment.course_count():
                            if new_course_index != environment.course_index:
                                environment.set_course(new_course_index)
                                pygame.display.set_caption(
                                    f"3E Car Simulator - {environment.course_name}"
                                )
                                course_changed = True
                                print(
                                    f"コース変更: {environment.course_name}"
                                    "。同じ世代のAIを新コースで再スタートします。"
                                )

            if not running:
                break
            if course_changed:
                break

            speed_index = settings.get_speed_index()
            simulation_speed = SIMULATION_SPEEDS[speed_index]
            dt = min(real_dt * simulation_speed, 0.1)

            for individual in individuals:
                update_individual(individual, environment, dt)

            draw_simulation(
                screen,
                font,
                environment,
                individuals,
                generation,
                show_sensors,
                simulation_speed,
                previous_ranking=previous_ranking,
            )

            dashboard.update_info(
                generation,
                individuals,
                show_sensors,
                simulation_speed,
            )

            # Tkinter設定画面のリセットボタンからの要求を確認
            if settings.consume_reset_request():
                learning_reset = True
                break

            if not dashboard.is_open or not settings.is_open:
                running = False

        if not running:
            break

        if learning_reset:
            try:
                archive_dir = archive_learning_data(history_path, best_path)
            except OSError as error:
                print(f"学習データのバックアップに失敗しました: {error}")
                print("安全のため、学習リセットを中止します。")
                continue

            # GAを新規作成して全個体の重みをランダムに初期化する
            ga = GeneticAlgorithm(population_size=POPULATION_SIZE)
            generation = 1
            best_fitness_ever = float("-inf")

            if archive_dir:
                print(f"以前の学習データを退避しました: {archive_dir}")
            print("学習をリセットしました。Generation 1から再開します。")
            continue

        if course_changed:
            continue

        # 全個体の走行が完了したタイミングで、今回の結果を前回記録として保存。
        # コース変更・学習リセット・途中終了ではここに到達しないため、
        # 未完了の順位で前回記録が上書きされることはない。
        completed_ranking = make_ranking_record(
            individuals,
            generation,
            environment.course_name,
        )
        try:
            save_previous_ranking(previous_ranking_path, completed_ranking)
            previous_ranking = completed_ranking
            print(
                f"Generation {generation} の順位表を保存しました。"
                f"（ゴール {len(completed_ranking['rankings'])} 台）"
            )
        except OSError as error:
            print(f"順位表の保存に失敗しました: {error}")

        fitness_scores = [individual["fitness"] for individual in individuals]
        ga.evaluate(fitness_scores)

        best_index = max(
            range(len(individuals)),
            key=lambda i: fitness_scores[i],
        )
        best_individual = individuals[best_index]
        average_fitness = sum(fitness_scores) / len(fitness_scores)

        print(f"世代 {generation} の評価終了")
        print(f"最高評価: {fitness_scores[best_index]:.2f}")
        print(f"平均評価: {average_fitness:.2f}")
        print(f"最高評価のAI: {best_index + 1}")
        print(f"最高進捗: {best_individual['progress']:.1f}")
        print(f"周回数: {best_individual['laps']}")

        if best_individual["lap_times"]:
            print(f"最速周回: {min(best_individual['lap_times']):.2f}秒")

        file_exists = os.path.exists(history_path)
        with open(history_path, "a", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["generation", "best_fitness", "average_fitness"])
            writer.writerow([
                generation,
                fitness_scores[best_index],
                average_fitness,
            ])

        if fitness_scores[best_index] > best_fitness_ever:
            best_fitness_ever = fitness_scores[best_index]
            with open(best_path, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "generation": generation,
                        "fitness": best_fitness_ever,
                        "weights": ga.population[best_index].weights.tolist(),
                    },
                    file,
                    indent=2,
                )
            print("過去最高のAIを保存しました。")

        ga.evolve()
        generation += 1
        print("次世代を生成しました。")

    if dashboard.is_open:
        dashboard.close()
    if settings.is_open:
        settings.close()

    pygame.quit()


if __name__ == "__main__":
    main()
