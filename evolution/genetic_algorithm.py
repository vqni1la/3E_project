#選択・交叉・突然変異・世代更新

import numpy as np
from ai.genome import Genome


class GeneticAlgorithm:
    def __init__(
        self,
        population_size=20,
        elite_rate=0.2,
        mutation_rate=0.1,
        mutation_strength=0.3
    ):
        self.population_size = population_size
        self.elite_count = max(
            1, int(population_size * elite_rate)
        )
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength

        # 初期世代をランダムに生成
        self.population = [
            Genome() for _ in range(population_size)
        ]

        self.generation = 0

    def evaluate(self, fitness_scores):
        """各個体の評価点を設定する。"""
        if len(fitness_scores) != len(self.population):
            raise ValueError(
                "評価点の数と個体数が一致していません"
            )

        for genome, score in zip(
            self.population, fitness_scores
        ):
            genome.fitness = float(score)

    def select_parent(self):
        """ランダムに3個体を選び、最も優秀な個体を親にする。"""
        candidates = np.random.choice(
            self.population,
            size=min(3, len(self.population)),
            replace=False
        )

        return max(
            candidates,
            key=lambda genome: genome.fitness
        )

    def crossover(self, parent1, parent2):
        """親2個体の重みを組み合わせて子を作る。"""
        mask = np.random.random(
            parent1.weights.shape
        ) < 0.5

        child_weights = np.where(
            mask,
            parent1.weights,
            parent2.weights
        )

        return Genome(child_weights)

    def evolve(self):
        """評価結果を使って次世代を生成する。"""
        # 評価点が高い順に並べる
        ranked = sorted(
            self.population,
            key=lambda genome: genome.fitness,
            reverse=True
        )

        best_fitness = ranked[0].fitness

        # 優秀な個体をそのまま次世代へ残す
        next_population = [
            genome.copy()
            for genome in ranked[:self.elite_count]
        ]

        # 残りは交叉と突然変異で生成
        while len(next_population) < self.population_size:
            parent1 = self.select_parent()
            parent2 = self.select_parent()

            child = self.crossover(parent1, parent2)
            child.mutate(
                mutation_rate=self.mutation_rate,
                mutation_strength=self.mutation_strength
            )

            next_population.append(child)

        self.population = next_population
        self.generation += 1

        return best_fitness
