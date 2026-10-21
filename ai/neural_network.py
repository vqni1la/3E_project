#センサー入力からモーター出力を計算

import numpy as np


class NeuralNetwork:
    def __init__(self, input_size=5, hidden_size=8, output_size=2):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size

        # 重みとバイアスをランダムに初期化
        self.w1 = np.random.randn(input_size, hidden_size) * 0.5
        self.b1 = np.zeros(hidden_size)

        self.w2 = np.random.randn(hidden_size, output_size) * 0.5
        self.b2 = np.zeros(output_size)

    def predict(self, inputs):
        # センサー値を 0～1 に正規化
        x = np.asarray(inputs, dtype=float) / 150.0
        x = np.clip(x, 0.0, 1.0)

        # 入力層 → 隠れ層
        hidden = np.tanh(x @ self.w1 + self.b1)

        # 隠れ層 → 出力層
        output = np.tanh(hidden @ self.w2 + self.b2)

        # 出力は -1～1
        # output[0]：操舵（左～右）
        # output[1]：速度（後退～前進）
        return output

    def get_weights(self):
        # 全重み・バイアスを1次元配列にまとめる
        return np.concatenate([
            self.w1.flatten(),
            self.b1.flatten(),
            self.w2.flatten(),
            self.b2.flatten()
        ])

    def set_weights(self, weights):
        # 1次元配列から重み・バイアスを復元
        weights = np.asarray(weights, dtype=float)

        expected_size = (
            self.input_size * self.hidden_size
            + self.hidden_size
            + self.hidden_size * self.output_size
            + self.output_size
        )

        if weights.size != expected_size:
            raise ValueError(
                f"Expected {expected_size} weights, "
                f"got {weights.size}"
            )

        i = 0

        size = self.input_size * self.hidden_size
        self.w1 = weights[i:i + size].reshape(
            self.input_size, self.hidden_size
        )
        i += size

        size = self.hidden_size
        self.b1 = weights[i:i + size].copy()
        i += size

        size = self.hidden_size * self.output_size
        self.w2 = weights[i:i + size].reshape(
            self.hidden_size, self.output_size
        )
        i += size

        size = self.output_size
        self.b2 = weights[i:i + size].copy()
