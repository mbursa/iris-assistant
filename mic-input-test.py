import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

print("Default input device:", sd.default.device)
print("All devices:")
print(sd.query_devices())

def callback(indata, frames, time_info, status):
    x = indata[:, 0].astype(np.int32)
    rms = float(np.sqrt(np.mean(x * x))) if len(x) else 0.0
    print("rms:", rms)

with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, callback=callback):
    time.sleep(5)
