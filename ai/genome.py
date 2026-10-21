#個体の重み配列の保持・複製

import numpy as np


class Genome:
    def __init__(self, weights=None):
        # 重みが渡されなければランダムに生成
        if weights is None:
            self.weights = np.random.randn(66) * 0.5
        else:
            self.weights = np.asarray(
                weights, dtype=float
            ).copy()

        self.fitness = 0.0

    def mutate(self, mutation_rate=0.1, mutation_strength=0.3):
        # 各重みに一定確率で変異を加える
        mask = np.random.random(self.weights.shape) < mutation_rate
        changes = np.random.randn(self.weights.size) * mutation_strength

        self.weights += mask * changes

    def copy(self):
        # 重みを複製（配列は別のものにする）
        child = Genome(self.weights)
        child.fitness = self.fitness
        return child
