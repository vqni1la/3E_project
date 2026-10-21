
import csv
import matplotlib.pyplot as plt

CSV_PATH = "saved_models/training_history.csv"


def main():
    generations = []
    best_scores = []
    average_scores = []

    # CSVから学習履歴を読み込む
    with open(CSV_PATH, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            generations.append(int(row["generation"]))
            best_scores.append(float(row["best_fitness"]))
            average_scores.append(float(row["average_fitness"]))

    if not generations:
        print("学習履歴がありません。")
        return

    # 最高評価のグラフ
    plt.figure(figsize=(10, 5))
    plt.plot(generations, best_scores, label="Best Fitness")
    plt.plot(generations, average_scores, label="Average Fitness")

    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title("AI Evolution Progress")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig("saved_models/training_graph.png")
    plt.show()


if __name__ == "__main__":
    main()
