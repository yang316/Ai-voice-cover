"""Demucs wrapper that patches torchaudio.save to use soundfile."""
import sys
import soundfile as sf
import torchaudio

# Patch torchaudio.save to use soundfile instead of torchcodec
def _patched_save(uri, src, sample_rate, **kw):
    data = src.numpy().T if src.ndim == 2 else src.numpy()
    sf.write(str(uri), data, sample_rate)

torchaudio.save = _patched_save

# Run demucs
import runpy
runpy.run_module('demucs', run_name='__main__')
