"""RVC (Retrieval-based Voice Conversion) inference module.

Uses transformers HuBERT + RVC Pipeline for real voice conversion.
"""
import logging
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# Add rvc module to path
_rvc_dir = Path(__file__).parent / "rvc"
if str(_rvc_dir) not in sys.path:
    sys.path.insert(0, str(_rvc_dir))

# Model cache
_model_cache: dict = {}
_hubert_model = None
_pipeline = None


class _HubertAdapter:
    """Adapter to make transformers HuBERT compatible with RVC Pipeline's fairseq interface."""

    def __init__(self, model):
        self._model = model

    def extract_features(self, source, padding_mask=None, output_layer=None):
        with torch.no_grad():
            feats = self._model(source).last_hidden_state
        return [feats]

    def final_proj(self, feats):
        return feats

    def to(self, device):
        self._model = self._model.to(device)
        return self

    def eval(self):
        self._model = self._model.eval()
        return self

    def half(self):
        self._model = self._model.half()
        return self

    def float(self):
        self._model = self._model.float()
        return self

    def parameters(self):
        return self._model.parameters()


def get_device() -> torch.device:
    """Get best available device."""
    try:
        from backend.core.device import get_device as _get_device
        dev = _get_device()
        return dev if dev is not None else torch.device("cpu")
    except Exception:
        return torch.device("cpu")


def _load_hubert_from_fairseq(ckpt_path: str, device: torch.device):
    """Load fairseq HuBERT checkpoint into transformers HuBERT model."""
    import types as _types
    from transformers import HubertModel, HubertConfig

    # Create fake fairseq modules so torch.load can unpickle
    for mod_name in ['fairseq', 'fairseq.models', 'fairseq.models.hubert',
                     'fairseq.models.hubert.hubert', 'fairseq.data',
                     'fairseq.data.dictionary', 'fairseq.tasks',
                     'fairseq.tasks.hubert_pretraining']:
        mod = _types.ModuleType(mod_name)
        mod.__dict__['__path__'] = []
        sys.modules[mod_name] = mod

    class _Dummy:
        pass

    sys.modules['fairseq.models.hubert.hubert'].HuBERTModel = _Dummy
    sys.modules['fairseq.data.dictionary'].Dictionary = _Dummy
    sys.modules['fairseq.tasks.hubert_pretraining'].HubertPretrainingTask = _Dummy

    cpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    fairseq_sd = cpt['model']

    # Create transformers HuBERT with matching architecture
    config = HubertConfig(
        hidden_size=768, num_hidden_layers=12, num_attention_heads=12,
        intermediate_size=3072,
        conv_dim=(512, 512, 512, 512, 512, 512, 512),
        conv_stride=(5, 2, 2, 2, 2, 2, 2),
        conv_kernel=(10, 3, 3, 3, 3, 2, 2),
        feat_extract_norm="group", feat_extract_activation="gelu",
        num_conv_pos_embeddings=128, num_conv_pos_embedding_groups=16,
        hidden_act="gelu", vocab_size=32,
    )
    model = HubertModel(config)
    hf_sd = model.state_dict()

    # Key mappings: fairseq -> transformers
    key_map = {
        'self_attn.': 'attention.',
        'self_attn_layer_norm.': 'layer_norm.',
        'fc1.': 'feed_forward.intermediate_dense.',
        'fc2.': 'feed_forward.output_dense.',
    }
    fe_map = {}
    for i in range(7):
        fe_map[f'feature_extractor.conv_layers.{i}.0.weight'] = f'feature_extractor.conv_layers.{i}.conv.weight'
        fe_map[f'feature_extractor.conv_layers.{i}.0.bias'] = f'feature_extractor.conv_layers.{i}.conv.bias'
        fe_map[f'feature_extractor.conv_layers.{i}.2.weight'] = f'feature_extractor.conv_layers.{i}.layer_norm.weight'
        fe_map[f'feature_extractor.conv_layers.{i}.2.bias'] = f'feature_extractor.conv_layers.{i}.layer_norm.bias'
    extra_map = {
        'post_extract_proj.weight': 'feature_projection.projection.weight',
        'post_extract_proj.bias': 'feature_projection.projection.bias',
        'layer_norm.weight': 'feature_projection.layer_norm.weight',
        'layer_norm.bias': 'feature_projection.layer_norm.bias',
        'encoder.pos_conv.0.weight_g': 'encoder.pos_conv_embed.conv.parametrizations.weight.original0',
        'encoder.pos_conv.0.weight_v': 'encoder.pos_conv_embed.conv.parametrizations.weight.original1',
        'encoder.pos_conv.0.bias': 'encoder.pos_conv_embed.conv.bias',
    }

    new_sd = {}
    for fkey, value in fairseq_sd.items():
        if fkey in fe_map:
            hkey = fe_map[fkey]
        elif fkey in extra_map:
            hkey = extra_map[fkey]
        else:
            hkey = fkey
            for old, new in key_map.items():
                if old in hkey:
                    hkey = hkey.replace(old, new)
                    break
        if hkey in hf_sd and hf_sd[hkey].shape == value.shape:
            new_sd[hkey] = value

    model.load_state_dict(new_sd, strict=False)
    model = model.to(device).eval()
    logger.info(f"Loaded HuBERT from fairseq checkpoint ({len(new_sd)} keys)")
    return model


def load_hubert():
    """Load HuBERT model for feature extraction."""
    global _hubert_model
    if _hubert_model is not None:
        return _hubert_model

    device = get_device()

    # Load from local fairseq checkpoint (converted to transformers format)
    local_path = Path(__file__).parent.parent.parent / "assets" / "hubert" / "hubert_base.pt"
    if local_path.exists():
        try:
            model = _load_hubert_from_fairseq(str(local_path), device)
            _hubert_model = _HubertAdapter(model)
            return _hubert_model
        except Exception as e:
            logger.warning(f"Failed to load local HuBERT: {e}")

    # Fallback: try downloading from HuggingFace
    try:
        from transformers import HubertModel
        logger.info("Downloading HuBERT from HuggingFace...")
        model = HubertModel.from_pretrained("facebook/hubert-base-ls960")
        model = model.to(device).eval()
        _hubert_model = _HubertAdapter(model)
        logger.info("Loaded HuBERT from HuggingFace")
        return _hubert_model
    except Exception as e:
        logger.error(f"Failed to load HuBERT: {e}")
        return None


def load_rvc_model(model_path: str, device: torch.device = None) -> dict:
    """Load RVC model from .pth file. Supports both standard RVC and training output formats."""
    model_path = Path(model_path)
    cache_key = str(model_path.resolve())

    if cache_key in _model_cache:
        return _model_cache[cache_key]

    if device is None:
        device = get_device()

    logger.info(f"Loading RVC model: {model_path}")
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)

    # Detect format: training output vs standard RVC
    if "model_state_dict" in checkpoint:
        # Training output format (SimpleVoiceModel)
        logger.info("Detected training output format (SimpleVoiceModel)")
        cfg = checkpoint.get("config", {})
        tgt_sr = cfg.get("sample_rate", 44100)
        version = cfg.get("version", "v2")
        if_f0 = 1

        # Build SimpleVoiceModel and load weights
        input_dim = cfg.get("input_dim", 768)
        hidden_dim = cfg.get("hidden_dim", 256)

        import torch.nn as nn
        class SimpleVoiceModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.encoder = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.ReLU(),
                )
                self.decoder = nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, input_dim),
                )

            def forward(self, x):
                encoded = self.encoder(x)
                decoded = self.decoder(encoded)
                return decoded, encoded

        net_g = SimpleVoiceModel()
        net_g.load_state_dict(checkpoint["model_state_dict"])
        net_g.eval().to(device).float()

        model_data = {
            "net_g": net_g,
            "tgt_sr": tgt_sr,
            "if_f0": if_f0,
            "version": version,
            "device": device,
            "cpt": checkpoint,
            "model_type": "simple",
        }
    else:
        # Standard RVC format
        logger.info("Detected standard RVC format")
        cpt = checkpoint
        tgt_sr = cpt["config"][-1]
        cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]  # n_spk
        if_f0 = cpt.get("f0", 1)
        version = cpt.get("version", "v1")

        from infer.lib.infer_pack.models import (
            SynthesizerTrnMs256NSFsid,
            SynthesizerTrnMs256NSFsid_nono,
            SynthesizerTrnMs768NSFsid,
            SynthesizerTrnMs768NSFsid_nono,
        )

        is_half = device.type == "cuda"
        synth_classes = {
            ("v1", 1): SynthesizerTrnMs256NSFsid,
            ("v1", 0): SynthesizerTrnMs256NSFsid_nono,
            ("v2", 1): SynthesizerTrnMs768NSFsid,
            ("v2", 0): SynthesizerTrnMs768NSFsid_nono,
        }
        SynthClass = synth_classes.get((version, if_f0), SynthesizerTrnMs256NSFsid)

        net_g = SynthClass(*cpt["config"], is_half=is_half)
        del net_g.enc_q
        net_g.load_state_dict(cpt["weight"], strict=False)
        net_g.eval().to(device)
        if is_half:
            net_g = net_g.half()
        else:
            net_g = net_g.float()

        model_data = {
            "net_g": net_g,
            "tgt_sr": tgt_sr,
            "if_f0": if_f0,
            "version": version,
            "device": device,
            "cpt": cpt,
            "model_type": "rvc",
        }

    _model_cache[cache_key] = model_data
    logger.info(f"RVC model loaded: version={version}, sr={tgt_sr}, f0={bool(if_f0)}, type={model_data['model_type']}")
    return model_data


def get_pipeline() -> "Pipeline":
    """Get or create RVC Pipeline instance."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    from infer.modules.vc.pipeline import Pipeline

    class Config:
        def __init__(self):
            self.device = get_device()
            self.is_half = self.device.type == "cuda"
            self.x_pad = 3
            self.x_query = 10
            self.x_center = 60
            self.x_max = 65

    _pipeline = Pipeline(40000, Config())  # Default SR, will be overridden
    return _pipeline


def extract_f0(audio: np.ndarray, sr: int, pitch_shift: int = 0, method: str = "pm") -> np.ndarray:
    """Extract F0 (pitch) from audio using parselmouth."""
    try:
        import parselmouth
        snd = parselmouth.Sound(audio, sr)
        pitch = snd.to_pitch(
            time_step=snd.duration / (len(audio) / 160),  # ~10ms frames
            pitch_floor=75.0,
            pitch_ceiling=600.0,
        )
        f0 = pitch.selected_array["frequency"]
        if pitch_shift != 0:
            voiced = f0 > 0
            f0[voiced] *= 2 ** (pitch_shift / 12)
        return f0
    except Exception as e:
        logger.warning(f"parselmouth F0 extraction failed: {e}")

    # Simple fallback
    frame_len = int(sr * 0.01)
    f0 = []
    for i in range(0, len(audio) - frame_len, frame_len):
        frame = audio[i:i + frame_len]
        zcr = np.sum(np.abs(np.diff(np.sign(frame)))) / (2 * frame_len)
        freq = zcr * sr / 2
        f0.append(freq if 50 < freq < 1000 else 0)
    f0 = np.array(f0)
    if pitch_shift != 0:
        voiced = f0 > 0
        f0[voiced] *= 2 ** (pitch_shift / 12)
    return f0


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
    """Convert voice using RVC Pipeline.

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

    pth_files = list(voice_dir.glob("*.pth"))
    if not pth_files:
        raise FileNotFoundError(f"No .pth model found in {voice_dir}")

    model_path = pth_files[0]
    index_files = list(voice_dir.glob("*.index"))
    index_path = str(index_files[0]) if index_files else ""
    logger.info(f"Model: {model_path}, Index: {index_path or 'none'}, Device: {device}")

    # Load model
    try:
        model_data = load_rvc_model(str(model_path), device)
    except Exception as e:
        logger.error(f"load_rvc_model failed: {e}", exc_info=True)
        raise

    net_g = model_data["net_g"]
    tgt_sr = model_data["tgt_sr"]
    if_f0 = model_data["if_f0"]
    version = model_data["version"]
    model_type = model_data.get("model_type", "rvc")
    logger.info(f"Model loaded: sr={tgt_sr}, f0={if_f0}, version={version}, type={model_type}")

    # SimpleVoiceModel from training is a feature autoencoder, not a full synthesizer.
    # It can't generate audio directly — fall back to pitch shift.
    if model_type == "simple":
        logger.warning("SimpleVoiceModel detected — cannot generate audio directly. Using pitch-shift fallback.")
        return _fallback_convert(input_path, output_path, pitch_shift, tgt_sr)

    # Load HuBERT
    hubert = load_hubert()
    if hubert is None:
        logger.warning("HuBERT not available, using fallback")
        return _fallback_convert(input_path, output_path, pitch_shift, tgt_sr)

    # Get pipeline
    pipe = get_pipeline()

    # Load input audio
    audio, sr = sf.read(input_path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    logger.info(f"Input audio: {len(audio)/sr:.1f}s, sr={sr}")

    # Resample to 16kHz
    if sr != 16000:
        import torchaudio
        audio_t = torch.FloatTensor(audio).unsqueeze(0)
        audio = torchaudio.transforms.Resample(sr, 16000)(audio_t).squeeze(0).numpy()
        sr = 16000

    # Normalize
    audio_max = np.abs(audio).max() / 0.95
    if audio_max > 1:
        audio = audio / audio_max

    # Prepare F0 tensors
    pitch = None
    pitchf = None
    if if_f0:
        f0 = extract_f0(audio, sr, pitch_shift, f0_method)
        pitch = torch.LongTensor(f0).to(device).unsqueeze(0)
        pitchf = pitch.float()

    # Use pipeline for inference
    try:
        times = [0, 0, 0]
        sid = 0

        audio_opt = pipe.pipeline(
            hubert,
            net_g,
            sid,
            audio,
            input_path,
            times,
            pitch_shift,
            f0_method,
            index_path,
            index_rate,
            if_f0,
            filter_radius,
            tgt_sr,
            0,  # resample_sr (0 = no resample)
            rms_mix_rate,
            version,
            protect,
        )

        # Convert to float
        audio_opt = audio_opt.astype(np.float32) / 32768.0

        # Save
        sf.write(output_path, audio_opt, tgt_sr)
        logger.info(f"RVC output saved: {output_path} (len={len(audio_opt)/tgt_sr:.1f}s)")
        return output_path

    except Exception as e:
        logger.error(f"RVC pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return _fallback_convert(input_path, output_path, pitch_shift, tgt_sr)


def _fallback_convert(input_path: str, output_path: str, pitch_shift: int, tgt_sr: int) -> str:
    """Fallback: use FFmpeg pitch shift when RVC model can't load."""
    import subprocess
    from backend.core.ffmpeg_util import get_ffmpeg_path
    ffmpeg = get_ffmpeg_path()
    if pitch_shift == 0:
        import shutil
        shutil.copy2(input_path, output_path)
    else:
        factor = 2 ** (pitch_shift / 12)
        cmd = [
            ffmpeg, "-y", "-i", input_path,
            "-af", f"asetrate={tgt_sr * factor},aresample={tgt_sr}",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    return output_path
