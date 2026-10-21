#完走時間、衝突、進行距離などの評価

def calculate_fitness(distance, survival_time, completed=False):
    """
    走行結果から個体の評価点を計算する。

    distance: 走行距離（ピクセル）
    survival_time: 走行できた時間（秒）
    completed: コースを完走したか
    """
    score = max(0.0, distance)
    score += max(0.0, survival_time) * 0.1

    if completed:
        score += 1000.0

    return score
