#個体数、速度、コース設定などの共通設定

# 画面設定
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
WINDOW_TITLE = "3E Car Simulator"

# AI設定
POPULATION_SIZE = 20 #車の台数

# シミュレーション設定
MAX_SURVIVAL_TIME = 15.0 #車を走らせる時間

# シミュレーション速度の選択肢
SIMULATION_SPEEDS = [1, 2, 4, 8, 16] #スピード倍率
DEFAULT_SPEED_INDEX = 2

# 描画設定
SHOW_SENSORS_DEFAULT = True

# 学習結果の保存先
BEST_GENOME_PATH = "saved_models/best_genome.json"
TRAINING_HISTORY_PATH = "saved_models/training_history.csv"
TRAINING_GRAPH_PATH = "saved_models/training_graph.png"

