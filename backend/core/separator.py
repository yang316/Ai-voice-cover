"""Vocal separation using Demucs."""
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VocalSeparator:
    """Separate vocals from accompaniment using Demucs."""

    def __init__(self, model_name: str = "htdemucs"):
        self.model_name = model_name

    async def separate(
        self,
        input_path: Path,
        output_dir: Path,
    ) -> tuple[Path, Path]:
        """
        Separate input audio into vocals and accompaniment.

        Returns: (vocals_path, accompaniment_path)
        """
        vocals_path = output_dir / "vocals.wav"
        accomp_path = output_dir / "accompaniment.wav"

        if vocals_path.exists() and accomp_path.exists():
            logger.info("Using cached separated files")
            return vocals_path, accomp_path

        await asyncio.to_thread(
            self._separate_sync, input_path, output_dir, vocals_path, accomp_path
        )

        return vocals_path, accomp_path

    def _separate_sync(
        self, input_path: Path, output_dir: Path, vocals_path: Path, accomp_path: Path
    ):
        """Run demucs separation synchronously — NO torchaudio, pure soundfile."""
        import numpy as np
        import torch
        import soundfile as sf

        # Load audio with soundfile (avoids torchaudio torchcodec requirement)
        logger.info(f"Loading audio: {input_path}")
        audio_np, sr = sf.read(str(input_path), dtype="float32")
        # audio_np shape: (samples, channels)
        if audio_np.ndim == 1:
            audio_np = audio_np[:, np.newaxis]
        # Demucs expects stereo (2 channels) — duplicate mono if needed
        if audio_np.shape[1] == 1:
            audio_np = np.tile(audio_np, (1, 2))
        # Convert to (channels, samples) torch tensor
        wav = torch.from_numpy(audio_np.T).float()

        # Import demucs (these don't trigger torchaudio load/save at import time)
        from demucs.pretrained import get_model
        from demucs.apply import apply_model

        # Load model
        logger.info(f"Loading Demucs model: {self.model_name}")
        model = get_model(self.model_name)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()

        # Resample if needed
        if sr != model.samplerate:
            import torchaudio
            wav = torchaudio.functional.resample(wav, sr, model.samplerate)

        # Normalize — guard against silent audio (std=0)
        ref = wav.mean(0)
        std_val = ref.std()
        if std_val > 1e-8:
            wav = (wav - ref.mean()) / std_val
        mix = wav.unsqueeze(0).to(device)

        # Apply model
        logger.info("Running Demucs separation (CPU, may take a while)...")
        with torch.no_grad():
            sources = apply_model(model, mix, device=device, progress=True)

        # Un-normalize (use saved std_val to avoid stale reference)
        if std_val > 1e-8:
            sources = sources * std_val + ref.mean()
        else:
            sources = sources + ref.mean()

        # sources shape: (1, num_sources, channels, samples)
        sources = sources[0]

        source_names = model.sources
        logger.info(f"Sources: {source_names}")

        # Extract vocals and no_vocals
        vocals_idx = source_names.index("vocals")
        vocals = sources[vocals_idx].cpu().numpy()  # (channels, samples)
        other_indices = [i for i in range(len(source_names)) if i != vocals_idx]
        no_vocals = sum(sources[i] for i in other_indices).cpu().numpy()

        # Save with soundfile (channels, samples) -> (samples, channels)
        sf.write(str(vocals_path), vocals.T, model.samplerate)
        logger.info(f"Saved vocals: {vocals_path}")

        sf.write(str(accomp_path), no_vocals.T, model.samplerate)
        logger.info(f"Saved accompaniment: {accomp_path}")
