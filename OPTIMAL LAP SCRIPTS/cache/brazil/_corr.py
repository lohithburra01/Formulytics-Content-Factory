"""Speed-profile correlation of sim CSVs vs the 2025 Q trace (by lap fraction, best circular shift)."""
import sys, numpy as np, pandas as pd
ref = pd.read_csv(sys.argv[1]); N = 1000
def prof(df):
    d = df["distance"].to_numpy(float); v = df["speed"].to_numpy(float)
    return np.interp(np.linspace(0, 1, N, endpoint=False), d / d[-1], v)
r = prof(ref); r = (r - r.mean()) / r.std()
for f in sys.argv[2:]:
    s = prof(pd.read_csv(f)); s = (s - s.mean()) / s.std()
    c = np.real(np.fft.ifft(np.fft.fft(r) * np.conj(np.fft.fft(s)))) / N
    k = int(np.argmax(c)); print(f"{f}: corr {c[k]:.3f} at shift {k/N*100:.1f}% (zero-shift corr {c[0]:.3f})")
