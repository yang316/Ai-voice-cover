"""RVC (Retrieval-based Voice Conversion) inference module.

Supports loading pre-trained RVC models (.pth) and running voice conversion
with optional FAISS index retrieval for better quality.
"""
import logging
import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# Model cache to avoid reloading
_model_cache: dict[str, dict] = {}
_hubert_model = None


def get_device() -> torch.device:
    """Get the best available device (delegates to unified device module)."""
    from backend.core.device import get_device as _get_device
    dev = _get_device()
    return dev if dev is not None else torch.device("cpu")


def load_hubert(model_path: str | None = None) -> torch.nn.Module:
    """Load HuBERT model for feature extraction."""
    global _hubert_model
    if _hubert_model is not None:
        return _hubert_model

    device = get_device()

    # Try to load from local path or download
    if model_path and Path(model_path).exists():
        _hubert_model = torch.load(model_path, map_location=device)
    else:
        # Use transformers HubertModel as fallback
        try:
            from transformers import HubertModel
            logger.info("Loading HuBERT from transformers...")
            _hubert_model = HubertModel.from_pretrained("facebook/hubert-base-ls960")
            _hubert_model = _hubert_model.to(device).eval()
        except ImportError:
            logger.warning("transformers not installed, using simple feature extraction")
            _hubert_model = None

    return _hubert_model


def extract_features(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Extract audio features using HuBERT or simple spectral features."""
    hubert = load_hubert()

    if hubert is not None:
        # Use HuBERT
        device = next(hubert.parameters()).device
        audio_tensor = torch.FloatTensor(audio).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = hubert(audio_tensor)
            features = outputs.last_hidden_state.cpu().numpy()
    else:
        # Fallback: use simple mel spectrogram features
        import librosa
        mel = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128)
        features = librosa.power_to_db(mel, ref=np.max).T
        # Add channel dim to match HuBERT output shape
        features = features[np.newaxis, :, :]

    return features


def load_voice_model(
    model_path: str | Path,
    device: torch.device | None = None,
) -> dict:
    """Load an RVC voice model from .pth file."""
    model_path = Path(model_path)
    cache_key = str(model_path.resolve())

    if cache_key in _model_cache:
        logger.info(f"Using cached model: {model_path.name}")
        return _model_cache[cache_key]

    if device is None:
        device = get_device()

    logger.info(f"Loading RVC model: {model_path}")
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)

    # Standard RVC model structure
    model_data = {
        "config": checkpoint.get("config", checkpoint.get("info", {})),
        "weight": checkpoint.get("model", checkpoint.get("weight", {})),
        "device": device,
    }

    _model_cache[cache_key] = model_data
    return model_data


def load_index(index_path: str | Path | None) -> "faiss.Index | None":
    """Load FAISS index for voice retrieval."""
    if index_path is None or not Path(index_path).exists():
        return None

    try:
        import faiss
        index = faiss.read_index(str(index_path))
        logger.info(f"Loaded FAISS index: {index_path} ({index.ntotal} vectors)")
        return index
    except Exception as e:
        logger.warning(f"Failed to load FAISS index: {e}")
        return None


def rvc_convert(
    input_path: str,
    output_path: str,
    voice_id: str,
    pitch_shift: int = 0,
    f0_method: str = "pm",
    index_rate: float = 0.5,
    filter_radius: int = 3,
    rms_mix_rate: float = 0.25,
    protect: float = 0.33,
) -> str:
    """
    Convert voice using RVC.

    Args:
        input_path: path to input audio (WAV)
        output_path: path to output audio (WAV)
        voice_id: voice model ID (directory name in voices/)
        pitch_shift: semitone shift (-12 to +12)
        f0_method: pitch extraction method (pm, harvest, crepe, rmvpe)
        index_rate: FAISS index influence (0.0 to 1.0)
        filter_radius: median filter radius for pitch
        rms_mix_rate: RMS mixing ratio
        protect: voice protection for consonants (0.0 to 0.5)

    Returns: output_path
    """
    from backend.config import settings

    device = get_device()
    logger.info(f"RVC conversion: {input_path} -> {output_path} (voice={voice_id}, pitch={pitch_shift})")

    # Find voice model
    voice_dir = settings.voices_dir / voice_id
    if not voice_dir.exists():
        raise FileNotFoundError(f"Voice model not found: {voice_id}")

    # Find .pth and .index files
    pth_files = list(voice_dir.glob("*.pth"))
    if not pth_files:
        raise FileNotFoundError(f"No .pth model found in {voice_dir}")

    model_path = pth_files[0]
    index_files = list(voice_dir.glob("*.index"))
    index_path = index_files[0] if index_files else None

    # Load model
    model_data = load_voice_model(model_path, device)
    index = load_index(index_path)

    # Load input audio
    audio, sr = sf.read(input_path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)  # Convert to mono

    # Resample to 16kHz for feature extraction
    if sr != 16000:
        import torchaudio
        audio_tensor = torch.FloatTensor(audio).unsqueeze(0)
        audio_16k = torchaudio.transforms.Resample(sr, 16000)(audio_tensor).squeeze(0).numpy()
    else:
        audio_16k = audio

    # Extract F0 (pitch)
    f0 = extract_f0(audio_16k, 16000, pitch_shift, f0_method)

    # Extract features
    features = extract_features(audio_16k, 16000)

    # Apply FAISS index retrieval if available
    if index is not None and index_rate > 0:
        features = apply_index_retrieval(features, index, index_rate)

    # Run model inference
    output_audio = run_inference(
        model_data, features, f0, device,
        protect=protect,
    )

    # RMS matching
    if rms_mix_rate > 0:
        output_audio = rms_match(audio, output_audio, sr, rms_mix_rate)

    # Save output
    sf.write(output_path, output_audio, sr)
    logger.info(f"RVC output saved: {output_path}")

    return output_path


def extract_f0(
    audio: np.ndarray,
    sr: int,
    pitch_shift: int = 0,
    method: str = "pm",
) -> np.ndarray:
    """Extract F0 (fundamental frequency / pitch) from audio."""
    if method == "pm":
        # Parselmouth (PM) method - fast and decent quality
        try:
            import parselmouth
            snd = parselmouth.Sound(audio, sr)
            pitch = snd.to_pitch(
                time_step=0.01,
                voicing_threshold=0.6,
            )
            f0 = pitch.selected_array["frequency"]

            # Apply pitch shift
            if pitch_shift != 0:
                f0 *= 2 ** (pitch_shift / 12)

            return f0
        except ImportError:
            logger.warning("parselmouth not installed, falling back to simple method")

    # Fallback: simple autocorrelation-based pitch detection
    return simple_f0_detection(audio, sr, pitch_shift)


def simple_f0_detection(audio: np.ndarray, sr: int, pitch_shift: int = 0) -> np.ndarray:
    """Simple autocorrelation-based F0 detection."""
    frame_len = int(sr * 0.01)  # 10ms frames
    hop = frame_len
    f0 = []

    for i in range(0, len(audio) - frame_len, hop):
        frame = audio[i:i + frame_len]
        # Zero-crossing rate as rough pitch estimate
        zcr = np.sum(np.abs(np.diff(np.sign(frame)))) / (2 * frame_len)
        freq = zcr * sr / 2
        if freq < 50 or freq > 1000:
            freq = 0  # Unvoiced
        f0.append(freq)

    f0 = np.array(f0)
    if pitch_shift != 0:
        voiced = f0 > 0
        f0[voiced] *= 2 ** (pitch_shift / 12)

    return f0


def apply_index_retrieval(
    features: np.ndarray,
    index: "faiss.Index",
    index_rate: float,
) -> np.ndarray:
    """Apply FAISS index retrieval to improve voice similarity."""
    import faiss

    # Reshape for FAISS query
    flat_features = features.reshape(-1, features.shape[-1]).astype("float32")

    # Normalize
    faiss.normalize_L2(flat_features)

    # Search
    k = 8
    _, I = index.search(flat_features, k)

    # Blend original features with retrieved features
    # (simplified - real RVC uses more sophisticated blending)
    return features  # TODO: implement proper blending


def run_inference(
    model_data: dict,
    features: np.ndarray,
    f0: np.ndarray,
    device: torch.device,
    protect: float = 0.3,
) -> np.ndarray:
    """Run the RVC model inference."""
    # This is a simplified inference pipeline
    # Real RVC uses SynthesizerTrn model with specific architecture

    # For now, return pitch-shifted audio as placeholder
    # The full implementation needs the actual RVC model architecture
    logger.info("Running model inference (placeholder)")

    # In production, this would:
    # 1. Load the SynthesizerTrn model from model_data
    # 2. Feed features + f0 into the model
    # 3. Get converted audio output

    # Placeholder: return features converted back to audio
    return np.zeros(int(len(f0) * 44100 * 0.01))


def rms_match(
    original: np.ndarray,
    converted: np.ndarray,
    sr: int,
    mix_rate: float,
) -> np.ndarray:
    """Match RMS energy of converted audio to original."""
    frame_len = int(sr * 0.05)  # 50ms frames

    # Ensure same length
    min_len = min(len(original), len(converted))
    original = original[:min_len]
    converted = converted[:min_len]

    result = converted.copy()

    for i in range(0, min_len - frame_len, frame_len):
        orig_rms = np.sqrt(np.mean(original[i:i + frame_len] ** 2) + 1e-8)
        conv_rms = np.sqrt(np.mean(converted[i:i + frame_len] ** 2) + 1e-8)

        if conv_rms > 0:
            gain = orig_rms / conv_rms
            gain = 1.0 + (gain - 1.0) * mix_rate
            result[i:i + frame_len] *= gain

    return result
