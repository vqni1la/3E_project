# 全体の起動、各モジュールの連携

import csv
import json
import os
import math
import shutil
from datetime import datetime
from types import SimpleNamespace

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
    draw_manual_mode,
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


def create_player_car(environment):
    """WASD操作用のプレイヤー車を作成する。"""
    display_scale = getattr(environment, "scale", 1.0)
    car = Car(environment.start_x, environment.start_y)
    car.angle = environment.start_angle
    car.color = (255, 220, 75)

    for attribute in ("width", "height", "speed", "track_width"):
        value = getattr(car, attribute, None)
        if isinstance(value, (int, float)):
            setattr(car, attribute, value * display_scale)

    return car


def estimate_current_fitness(individual, environment):
    """現在時点の成績を比較する。未終了個体は途中経過から暫定評価する。"""
    saved_fitness = individual.get("fitness")
    if saved_fitness is not None:
        return float(saved_fitness)

    return float(calculate_fitness(
        distance=individual["distance"],
        survival_time=individual["elapsed_time"],
        completed=(individual["laps"] > 0),
        progress=individual["progress"],
        laps=individual["laps"],
        lap_times=individual["lap_times"],
        lap_distances=individual["lap_distances"],
        track_length=environment.track_length,
    ))


def create_ghost_from_weights(environment, weights, ai_number):
    """切替時に選ばれた重みを固定して、AIゴーストを作成する。"""
    genome_snapshot = SimpleNamespace(weights=weights)
    ghost = create_individual(environment, genome_snapshot, ai_number - 1)
    ghost["number"] = int(ai_number)
    ghost["car"].color = (75, 175, 255)
    return ghost


def advance_player_progress(
    previous_progress,
    total_progress,
    current_progress,
    moved_distance,
    track_length,
    display_scale=1.0,
):
    """プレイヤーのコース進捗を更新し、1周到達を判定する。

    コースの始点をまたぐと progress が track_length 付近から 0 付近へ
    戻るため、その差分を正方向の進捗として補正する。
    """
    if track_length <= 0:
        return total_progress, current_progress, False

    delta = current_progress - previous_progress

    if delta < -track_length / 2:
        delta += track_length
    elif delta > track_length / 2:
        delta -= track_length

    # 近接した別区間への投影ジャンプを進捗として誤認しないよう、
    # 実際の移動距離を基準に1フレームあたりの進捗量を制限する。
    scale = max(float(display_scale), 0.01)
    maximum_progress_delta = max(40.0 * scale, moved_distance * 3.0 + 10.0 * scale)

    if 0.0 <= delta <= maximum_progress_delta:
        total_progress += delta

    return total_progress, current_progress, total_progress >= track_length


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
    
    # デフォルトのコースをステージ5に設定
    environment.set_course(4)

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

    # Mキーで切り替える手動プレイ用の状態
    manual_mode = False
    manual_player = None
    manual_ghost = None
    manual_ghost_weights = None
    manual_ghost_number = None
    manual_crashed = False
    manual_goal_reached = False
    manual_finish_time = None
    manual_player_elapsed_time = 0.0
    manual_player_progress = 0.0
    manual_player_previous_progress = 0.0
    manual_course_changed = False
    control_buttons = {}

    def reset_player_state():
        """プレイヤーをスタート地点へ戻し、ゴール計測を初期化する。"""
        nonlocal manual_player, manual_crashed, manual_goal_reached
        nonlocal manual_finish_time, manual_player_elapsed_time
        nonlocal manual_player_progress, manual_player_previous_progress

        manual_player = create_player_car(environment)
        manual_crashed = False
        manual_goal_reached = False
        manual_finish_time = None
        manual_player_elapsed_time = 0.0
        manual_player_progress = 0.0
        manual_player_previous_progress = environment.get_track_progress(
            manual_player.x, manual_player.y
        )

    def toggle_manual_mode():
        nonlocal manual_mode, manual_player, manual_ghost
        nonlocal manual_ghost_weights, manual_ghost_number, manual_crashed
        if not manual_mode:
            scores = [
                estimate_current_fitness(item, environment)
                for item in individuals
            ]
            best_index_now = max(
                range(len(individuals)),
                key=lambda i: (
                    scores[i],
                    individuals[i]["progress"],
                    individuals[i]["distance"],
                    -i,
                ),
            )
            manual_ghost_number = best_index_now + 1
            manual_ghost_weights = ga.population[best_index_now].weights.copy()
            reset_player_state()
            manual_ghost = create_ghost_from_weights(
                environment, manual_ghost_weights, manual_ghost_number
            )
            manual_crashed = False
            manual_mode = True
            print(
                f"手動プレイ開始。AI {manual_ghost_number:02d} をゴーストに選択しました。"
                f"（切替時点の暫定評価: {scores[best_index_now]:.2f}）"
            )
        else:
            manual_mode = False
            manual_player = None
            manual_ghost = None
            manual_ghost_weights = None
            manual_ghost_number = None
            print("進化シミュレーションに戻ります。")

    def restart_player():
        nonlocal manual_ghost
        if not manual_mode or manual_ghost_weights is None:
            return
        reset_player_state()
        manual_ghost = create_ghost_from_weights(
            environment, manual_ghost_weights, manual_ghost_number
        )
        print("プレイヤーとAIゴーストをスタート地点に戻しました。")

    def select_course(new_course_index):
        nonlocal course_changed
        if (
            0 <= new_course_index < environment.course_count()
            and new_course_index != environment.course_index
        ):
            environment.set_course(new_course_index)
            pygame.display.set_caption(
                f"3E Car Simulator - {environment.course_name}"
            )
            course_changed = True
            print(
                f"コース変更: {environment.course_name}。"
                "同じ世代のAIを新コースで再スタートします。"
            )

    while running:
        individuals = [
            create_individual(environment, genome, index)
            for index, genome in enumerate(ga.population)
        ]

        course_changed = False
        learning_reset = False

        print(f"\n世代 {generation} の走行を開始します。")

        while running and (
            manual_mode or any(
                not individual["finished"] for individual in individuals
            )
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

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for action, button_rect in control_buttons.items():
                        if not button_rect.collidepoint(event.pos):
                            continue

                        if action == "mode":
                            toggle_manual_mode()
                        elif action == "sensors":
                            show_sensors = not show_sensors
                        elif action == "restart":
                            restart_player()
                        elif action == "quit":
                            running = False
                        elif action.startswith("course_"):
                            select_course(int(action.split("_", 1)[1]))
                        break

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_m:
                        toggle_manual_mode()

                    elif event.key == pygame.K_s and not manual_mode:
                        show_sensors = not show_sensors
                    elif event.key == pygame.K_v and manual_mode:
                        show_sensors = not show_sensors

                    elif event.key == pygame.K_r and manual_mode:
                        restart_player()

                    elif pygame.K_1 <= event.key <= pygame.K_6:
                        select_course(event.key - pygame.K_1)

            if not running:
                break

            # 手動プレイ中は進化個体を停止し、プレイヤーと固定ゴーストだけを動かす。
            if manual_mode:
                if course_changed:
                    reset_player_state()
                    manual_ghost = create_ghost_from_weights(
                        environment,
                        manual_ghost_weights,
                        manual_ghost_number,
                    )
                    manual_course_changed = True
                    course_changed = False

                speed_index = settings.get_speed_index()
                simulation_speed = SIMULATION_SPEEDS[speed_index]
                dt = min(real_dt * simulation_speed, 0.1)

                keys = pygame.key.get_pressed()
                steering = float(keys[pygame.K_d]) - float(keys[pygame.K_a])
                throttle = float(keys[pygame.K_w]) - float(keys[pygame.K_s])

                # クラッシュ後・ゴール後はWASD入力を受け付けず、その場で停止する。
                if not manual_crashed and not manual_goal_reached:
                    old_x, old_y, old_angle = (
                        manual_player.x, manual_player.y, manual_player.angle
                    )
                    manual_player.update_ai(
                        dt,
                        steering,
                        throttle,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT,
                    )

                    if not environment.is_on_track(manual_player.x, manual_player.y):
                        manual_player.x = old_x
                        manual_player.y = old_y
                        manual_player.angle = old_angle
                        manual_crashed = True
                        print("プレイヤーがコース外に出ました。RキーまたはRESTART PLAYERで再スタートできます。")
                    else:
                        moved_distance = math.hypot(
                            manual_player.x - old_x,
                            manual_player.y - old_y,
                        )
                        manual_player_elapsed_time += dt
                        current_progress = environment.get_track_progress(
                            manual_player.x, manual_player.y
                        )
                        (
                            manual_player_progress,
                            manual_player_previous_progress,
                            manual_goal_reached,
                        ) = advance_player_progress(
                            manual_player_previous_progress,
                            manual_player_progress,
                            current_progress,
                            moved_distance,
                            environment.track_length,
                            getattr(environment, "scale", 1.0),
                        )

                        if manual_goal_reached:
                            # ゴール判定されたフレームで車体中心をゴールライン上に固定する。
                            manual_player.x = environment.start_x
                            manual_player.y = environment.start_y
                            manual_player.angle = environment.start_angle
                            manual_finish_time = manual_player_elapsed_time
                            print(
                                f"プレイヤーがゴールしました！ "
                                f"タイム: {manual_finish_time:.2f}秒"
                            )

                if not manual_ghost["finished"]:
                    update_individual(manual_ghost, environment, dt)

                control_buttons = draw_manual_mode(
                    screen,
                    font,
                    environment,
                    manual_player,
                    manual_ghost,
                    generation,
                    show_sensors,
                    simulation_speed,
                    individuals=individuals,
                    previous_ranking=previous_ranking,
                    player_crashed=manual_crashed,
                    player_goal_reached=manual_goal_reached,
                    player_finish_time=manual_finish_time,
                )

                dashboard.update_manual_info(
                    manual_ghost,
                    show_sensors,
                    simulation_speed,
                    player_crashed=manual_crashed,
                    player_goal_reached=manual_goal_reached,
                    player_finish_time=manual_finish_time,
                )

                if settings.consume_reset_request():
                    learning_reset = True
                    manual_mode = False
                    break

                if not dashboard.is_open or not settings.is_open:
                    running = False

                continue

            # 手動モード中にコースを変えていた場合は、進化側も新コースで再評価する。
            if course_changed or manual_course_changed:
                course_changed = True
                manual_course_changed = False
                break

            speed_index = settings.get_speed_index()
            simulation_speed = SIMULATION_SPEEDS[speed_index]
            dt = min(real_dt * simulation_speed, 0.1)

            for individual in individuals:
                update_individual(individual, environment, dt)

            control_buttons = draw_simulation(
                screen,
                font,
                environment,
                individuals,
                generation,
                show_sensors,
                simulation_speed,
                previous_ranking=previous_ranking,
                manual_mode=False,
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
