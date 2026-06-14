"""Demucs wrapper that patches torchaudio to use soundfile backend."""
import sys

# Patch torchaudio BEFORE importing demucs
# 1. Disable torchcodec backend entirely
import torchaudio

# Patch save to use soundfile
import soundfile as sf
import numpy as np

def _patched_save(uri, src, sample_rate, **kw):
    data = src.detach().cpu().numpy()
    if data.ndim == 2:
        data = data.T  # (channels, samples) -> (samples, channels)
    sf.write(str(uri), data, sample_rate)

torchaudio.save = _patched_save

# Also patch the internal save_with_torchcodec to avoid the import error
try:
    import torchaudio._torchcodec as _tc
    _tc.save_with_torchcodec = _patched_save
except (ImportError, AttributeError):
    pass

# Patch load to use soundfile too
def _patched_load(uri, **kw):
    data, sr = sf.read(str(uri), dtype='float32')
    if data.ndim == 1:
        data = data[np.newaxis, :]
    else:
        data = data.T  # (samples, channels) -> (channels, samples)
    import torch
    return torch.from_numpy(data), sr

torchaudio.load = _patched_load

# Force torchaudio to use soundfile backend
try:
    torchaudio.set_audio_backend("soundfile")
except Exception:
    pass

# Now run demucs
import runpy
runpy.run_module('demucs', run_name='__main__')
