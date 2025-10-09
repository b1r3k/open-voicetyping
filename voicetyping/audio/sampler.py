import numpy as np


class Resampler:
    def __init__(self, input_rate: int, target_rate: int):
        self.input_rate = input_rate
        self.target_rate = target_rate

    @staticmethod
    def resample_linear(pcm: np.ndarray, input_rate: int, target_rate: int) -> np.ndarray:
        if input_rate == target_rate:
            return pcm
        n_input = len(pcm)
        n_target = int(n_input * target_rate / input_rate)
        x_old = np.linspace(0, 1, n_input)
        x_new = np.linspace(0, 1, n_target)
        resampled = np.interp(x_new, x_old, pcm.astype(np.float32))
        return resampled.astype(np.int16)

    def resample(self, in_data: bytes) -> bytes:
        pcm = np.frombuffer(in_data, dtype=np.int16)
        resampled_pcm = self.resample_linear(pcm, self.input_rate, self.target_rate)
        return resampled_pcm.tobytes()
