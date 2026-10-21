#完走時間、衝突、進行距離などの評価

def calculate_fitness(
    distance,
    survival_time,
    completed=False,
    progress=0.0,
    laps=0,
    lap_times=None,
    lap_distances=None,
    track_length=1900.0,
):
    if lap_times is None:
        lap_times = []

    if lap_distances is None:
        lap_distances = []

    # まだ周回できていない個体にも、進捗に応じた評価を与える
    if laps <= 0 or not lap_times:
        return max(0.0, progress) + max(0.0, survival_time) * 0.1

    score = 0.0

    for lap_time, lap_distance in zip(lap_times, lap_distances):
        if lap_time <= 0:
            continue

        # 周回成功の基本報酬
        score += 2000.0

        # 速い周回ほど高得点
        score += 1000.0 * (15.0 / max(lap_time, 0.1))

        # 走行距離が長すぎる場合は減点
        # コース中央の経路長を基準にする
        score += 500.0 * (
            track_length / max(lap_distance, track_length)
        )

    # 周回に成功した個体では、未完了の周回進捗は加点しない
    return score
