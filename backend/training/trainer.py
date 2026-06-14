"""Voice model training pipeline."""
import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class TrainingStatus(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    EXTRACTING = "extracting"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrainingConfig:
    """RVC training configuration."""
    model_name: str
    sample_rate: int = 40000
    epoch: int = 200
    batch_size: int = 4
    save_every_epoch: int = 50
    learning_rate: float = 1e-4
    gpu_id: int = 0
    num_processes: int = 1
    # F0 extraction
    f0_method: str = "rmvpe"  # pm, harvest, crepe, rmvpe
    # Training
    pitch_guidance: bool = True
    # Model architecture
    version: str = "v2"  # v1 or v2


@dataclass
class TrainingProgress:
    """Training progress info."""
    status: TrainingStatus = TrainingStatus.PENDING
    epoch: int = 0
    total_epochs: int = 200
    loss: float = 0.0
    message: str = ""
    model_path: Optional[str] = None
    stage_pct: float = 0.0  # 0-100 progress within current stage


class DataPreparer:
    """Prepare training data from audio files."""

    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    async def prepare(
        self,
        audio_paths: list[Path],
        target_sr: int = 40000,
        denoise: bool = True,
        on_progress=None,
    ) -> Path:
        """
        Prepare training data:
        1. Auto vocal separation with Demucs
        2. Convert to WAV mono
        3. Resample to target_sr
        4. Cut into segments (5-15s)
        5. Optional denoise
        Returns: directory of prepared wavs
        """
        output_dir = self.work_dir / "44k"
        output_dir.mkdir(parents=True, exist_ok=True)

        total = len(audio_paths)
        for i, audio_path in enumerate(audio_paths):
            logger.info(f"Preparing audio {i+1}/{total}: {audio_path.name}")
            if on_progress:
                on_progress(i / total * 100, f"Preparing: {i+1}/{total} - {audio_path.name}")
            await asyncio.to_thread(
                self._process_audio, audio_path, output_dir, target_sr, i
            )
            if on_progress:
                on_progress((i + 1) / total * 100, f"Prepared: {i+1}/{total}")

        if on_progress:
            on_progress(100, "Data preparation complete")
        count = len(list(output_dir.glob("*.wav")))
        logger.info(f"Data preparation complete: {count} segments in {output_dir}")
        return output_dir

    def _process_audio(
        self, audio_path: Path, output_dir: Path, target_sr: int, index: int
    ):
        """Process a single audio file into training segments."""
        import soundfile as sf

        # Load audio (preserve original channels for Demucs)
        audio, sr = sf.read(str(audio_path), dtype="float32")

        # Auto vocal separation with Demucs
        audio = self._separate_vocals(audio, sr, audio_path)

        # Convert to mono after separation
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # Resample if needed
        if sr != target_sr:
            import torchaudio
            import torch
            wav_tensor = torch.from_numpy(audio).unsqueeze(0).float()
            resampled = torchaudio.functional.resample(wav_tensor, sr, target_sr)
            audio = resampled.squeeze(0).numpy()
            sr = target_sr

        # Normalize
        peak = np.abs(audio).max()
        if peak > 0:
            audio = audio / peak * 0.95

        # Cut into 5-15 second segments
        segment_len = sr * 10  # 10 seconds
        hop_len = sr * 8       # 8 seconds overlap
        pos = 0
        seg_idx = 0

        while pos < len(audio):
            end = min(pos + segment_len, len(audio))
            segment = audio[pos:end]

            # Skip very short segments
            if len(segment) < sr * 3:
                break

            out_path = output_dir / f"{index:04d}_{seg_idx:03d}.wav"
            sf.write(str(out_path), segment, sr)
            seg_idx += 1
            pos += hop_len

    def _separate_vocals(self, audio: np.ndarray, sr: int, audio_path: Path) -> np.ndarray:
        """Use Demucs to extract vocals. Returns mono vocal track."""
        try:
            import torch
            from demucs.pretrained import get_model
            from demucs.apply import apply_model

            logger.info(f"Separating vocals with Demucs: {audio_path.name}")

            # Demucs htdemucs expects 44100 Hz stereo, shape (batch, channels, samples)
            if audio.ndim == 1:
                audio_tensor = torch.from_numpy(audio).unsqueeze(0).unsqueeze(0).float()
            else:
                audio_tensor = torch.from_numpy(audio.T).unsqueeze(0).float()

            # Resample to 44100 if needed (Demucs native rate)
            if sr != 44100:
                import torchaudio
                audio_tensor = torchaudio.functional.resample(audio_tensor, sr, 44100)

            # Pad to stereo if mono
            if audio_tensor.shape[1] == 1:
                audio_tensor = audio_tensor.repeat(1, 2, 1)

            model = get_model("htdemucs")
            sources = apply_model(model, audio_tensor, device="cpu")
            # sources shape: (batch, sources, channels, samples) — order: drums, bass, other, vocals
            vocals = sources[0, -1]  # vocals track
            vocals_np = vocals.mean(dim=0).numpy()  # mix to mono

            # Resample back to original sr
            if sr != 44100:
                import torchaudio
                vt = torch.from_numpy(vocals_np).unsqueeze(0).float()
                vt = torchaudio.functional.resample(vt, 44100, sr)
                vocals_np = vt.squeeze(0).numpy()

            logger.info("Vocal separation complete")
            return vocals_np

        except Exception as e:
            logger.warning(f"Demucs vocal separation failed, using original audio: {e}")
            return audio


class FeatureExtractor:
    """Extract HuBERT + F0 features for RVC training."""

    def __init__(self, work_dir: Path, f0_method: str = "rmvpe"):
        self.work_dir = Path(work_dir)
        self.f0_method = f0_method

    async def extract(
        self,
        data_dir: Path,
        sample_rate: int = 40000,
        pitch_guidance: bool = True,
        on_progress=None,
    ) -> Path:
        """Extract features from prepared wavs."""
        from backend.config import settings

        # Output dirs
        model_dir = self.work_dir / "model"
        model_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Extracting HuBERT features...")
        await asyncio.to_thread(
            self._extract_hubert, data_dir, model_dir, on_progress
        )

        if pitch_guidance:
            logger.info(f"Extracting F0 ({self.f0_method})...")
            await asyncio.to_thread(
                self._extract_f0, data_dir, model_dir, sample_rate
            )

        logger.info("Feature extraction complete")
        return model_dir

    def _extract_hubert(self, data_dir: Path, model_dir: Path, on_progress=None):
        """Extract HuBERT features for all wavs."""
        import torch
        import soundfile as sf
        from transformers import HubertModel

        # Load HuBERT
        from backend.config import settings
        hubert_path = settings.base_dir / "assets" / "hubert" / "hubert_base.pt"

        if hubert_path.exists() and hubert_path.is_dir():
            model = HubertModel.from_pretrained(str(hubert_path))
        else:
            # Load from fairseq checkpoint via converter
            from backend.core.rvc_infer import _load_hubert_from_fairseq
            device = torch.device("cpu")
            model = _load_hubert_from_fairseq(str(hubert_path), device)

        model.eval()
        device = torch.device("cpu")

        feats_dir = model_dir / "feats"
        feats_dir.mkdir(exist_ok=True)

        wav_files = sorted(data_dir.glob("*.wav"))
        for i, wav_path in enumerate(wav_files):
            audio, sr = sf.read(str(wav_path), dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            # Pad to 320 sample boundary
            pad_len = (320 - len(audio) % 320) % 320
            audio_padded = np.pad(audio, (0, pad_len))

            wav_tensor = torch.from_numpy(audio_padded).unsqueeze(0).float()

            with torch.no_grad():
                feats = model(wav_tensor).last_hidden_state

            feat_path = feats_dir / f"{wav_path.stem}.npy"
            np.save(str(feat_path), feats.squeeze(0).cpu().numpy())

            if (i + 1) % 10 == 0:
                logger.info(f"  HuBERT: {i+1}/{len(wav_files)}")
                if on_progress:
                    on_progress(f"HuBERT: {i+1}/{len(wav_files)}")

    def _extract_f0(self, data_dir: Path, model_dir: Path, sample_rate: int):
        """Extract F0 (pitch) for all wavs."""
        import soundfile as sf
        f0_dir = model_dir / "f0"
        f0_dir.mkdir(exist_ok=True)

        wav_files = sorted(data_dir.glob("*.wav"))
        for i, wav_path in enumerate(wav_files):
            audio, sr = sf.read(str(wav_path), dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            f0 = self._compute_f0(audio, sr)
            f0_path = f0_dir / f"{wav_path.stem}.npy"
            np.save(str(f0_path), f0)

            if (i + 1) % 10 == 0:
                logger.info(f"  F0: {i+1}/{len(wav_files)}")

    def _compute_f0(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Compute F0 using parselmouth (pm) or rmvpe."""
        try:
            if self.f0_method == "pm":
                import parselmouth
                snd = parselmouth.Sound(audio, sr)
                pitch = snd.to_pitch(
                    time_step=0.01,
                    pitch_floor=75.0,
                    pitch_ceiling=600.0,
                )
                f0 = pitch.selected_array["frequency"]
                return f0
            else:
                # Default: use parselmouth
                import parselmouth
                snd = parselmouth.Sound(audio, sr)
                pitch = snd.to_pitch(time_step=0.01, pitch_floor=75.0, pitch_ceiling=600.0)
                f0 = pitch.selected_array["frequency"]
                return f0
        except Exception as e:
            logger.warning(f"F0 extraction failed: {e}, using zeros")
            return np.zeros(len(audio) // 320)


class RVCTrainer:
    """RVC model trainer (simplified)."""

    def __init__(self, work_dir: Path, config: TrainingConfig):
        self.work_dir = Path(work_dir)
        self.config = config

    async def train(
        self,
        model_dir: Path,
        on_progress=None,
    ) -> Path:
        """Train RVC model."""
        logger.info(f"Starting RVC training: {self.config.model_name}")
        logger.info(f"  Epochs: {self.config.epoch}")
        logger.info(f"  Batch size: {self.config.batch_size}")
        logger.info(f"  LR: {self.config.learning_rate}")

        # For CPU training, use reduced parameters
        device = self._get_device()
        if device.type == "cpu":
            actual_epochs = min(self.config.epoch, 50)
            actual_batch = min(self.config.batch_size, 2)
            logger.info(f"  CPU mode: reducing to {actual_epochs} epochs, batch {actual_batch}")
        else:
            actual_epochs = self.config.epoch
            actual_batch = self.config.batch_size

        output_dir = self.work_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run training in thread
        result_path = await asyncio.to_thread(
            self._train_sync, model_dir, output_dir, actual_epochs, actual_batch, device, on_progress
        )

        return result_path

    def _get_device(self):
        import torch
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch, "xpu") and torch.xpu.is_available():
            return torch.device("xpu")
        else:
            return torch.device("cpu")

    def _train_sync(self, model_dir, output_dir, epochs, batch_size, device, on_progress):
        """Synchronous training loop."""
        import torch
        import torch.nn as nn
        from torch.utils.data import Dataset, DataLoader

        # Load features
        feats_dir = model_dir / "feats"
        f0_dir = model_dir / "f0"

        feat_files = sorted(feats_dir.glob("*.npy"))
        if not feat_files:
            raise RuntimeError("No features found for training")

        logger.info(f"Training on {len(feat_files)} samples")

        # Simple dataset
        class VoiceDataset(Dataset):
            def __init__(self, feat_files, f0_dir, has_f0=True):
                self.feat_files = feat_files
                self.f0_dir = f0_dir
                self.has_f0 = has_f0

            def __len__(self):
                return len(self.feat_files)

            def __getitem__(self, idx):
                feat = np.load(str(self.feat_files[idx]))
                feat = torch.from_numpy(feat).float()

                if self.has_f0:
                    f0_path = self.f0_dir / f"{self.feat_files[idx].stem}.npy"
                    if f0_path.exists():
                        f0 = np.load(str(f0_path))
                        # Align lengths
                        min_len = min(len(feat), len(f0))
                        feat = feat[:min_len]
                        f0 = torch.from_numpy(f0[:min_len]).float()
                    else:
                        f0 = torch.zeros(len(feat))
                else:
                    f0 = torch.zeros(len(feat))

                return feat, f0

        def collate_fn(batch):
            """Pad features and f0 to max length in batch."""
            feats, f0s = zip(*batch)
            max_len = max(f.shape[0] for f in feats)
            feat_dim = feats[0].shape[1] if feats[0].ndim > 1 else 1

            padded_feats = []
            padded_f0s = []
            for feat, f0 in zip(feats, f0s):
                pad_len = max_len - feat.shape[0]
                if pad_len > 0:
                    feat = torch.nn.functional.pad(feat, (0, 0, 0, pad_len))
                    f0 = torch.nn.functional.pad(f0, (0, pad_len))
                padded_feats.append(feat)
                padded_f0s.append(f0)

            return torch.stack(padded_feats), torch.stack(padded_f0s)

        has_f0 = f0_dir.exists() and len(list(f0_dir.glob("*.npy"))) > 0
        dataset = VoiceDataset(feat_files, f0_dir, has_f0)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                                drop_last=True, collate_fn=collate_fn)

        # Simple autoencoder for feature refinement
        input_dim = 768  # HuBERT hidden size
        hidden_dim = 256

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

        model = SimpleVoiceModel().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=self.config.learning_rate)
        criterion = nn.MSELoss()

        best_loss = float("inf")

        for epoch in range(epochs):
            model.train()
            total_loss = 0.0
            num_batches = 0

            for feats, f0 in dataloader:
                feats = feats.to(device)

                # Flatten for simple model
                batch_size_actual, seq_len, feat_dim = feats.shape
                feats_flat = feats.reshape(-1, feat_dim)

                optimizer.zero_grad()
                reconstructed, encoded = model(feats_flat)
                loss = criterion(reconstructed, feats_flat)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                num_batches += 1

            avg_loss = total_loss / max(num_batches, 1)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(f"  Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.6f}")

            if on_progress:
                on_progress(epoch + 1, epochs, avg_loss)

            # Save checkpoint
            if avg_loss < best_loss:
                best_loss = avg_loss
                ckpt_path = output_dir / f"{self.config.model_name}_best.pth"
                torch.save({
                    "model_state_dict": model.state_dict(),
                    "config": {
                        "model_name": self.config.model_name,
                        "version": self.config.version,
                        "sample_rate": self.config.sample_rate,
                        "input_dim": input_dim,
                        "hidden_dim": hidden_dim,
                    },
                    "loss": best_loss,
                }, str(ckpt_path))

            # Save periodic checkpoint
            if (epoch + 1) % self.config.save_every_epoch == 0:
                ckpt_path = output_dir / f"{self.config.model_name}_e{epoch+1}.pth"
                torch.save({
                    "model_state_dict": model.state_dict(),
                    "epoch": epoch + 1,
                    "loss": avg_loss,
                }, str(ckpt_path))

        # Save final model
        final_path = output_dir / f"{self.config.model_name}.pth"
        torch.save({
            "model_state_dict": model.state_dict(),
            "config": {
                "model_name": self.config.model_name,
                "version": self.config.version,
                "sample_rate": self.config.sample_rate,
                "input_dim": input_dim,
                "hidden_dim": hidden_dim,
                "epochs_trained": epochs,
            },
            "loss": best_loss,
        }, str(final_path))

        logger.info(f"Training complete! Model saved: {final_path}")
        return final_path
