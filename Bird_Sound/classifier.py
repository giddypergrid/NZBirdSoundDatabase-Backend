"""
Bird Sound Classifier (singleton, loaded once at startup).

Pipeline: audio bytes → BirdNET embedding (1024-d) → AutoGluon → eBird code.
Call get_classifier().classify_bytes(data, suffix) from a view.

Classifer itself has a predictor and an extractor(construted with the BirdNET analyzer). The extractor runs the TFLite model to get the embedding, then the predictor runs the AutoGluon model to get class probabilities and maps to eBird codes.
"""

import os
import io
import sys
import json
import struct
import pickle
import logging
import tempfile
from threading import Lock
from pathlib import Path

import numpy as np
import pandas as pd

from .key_files import key_files

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024

# ── Singleton holder ──────────────────────────────────────
_classifier_instance = None
_classifier_lock = Lock()


def get_classifier():
    """Return the singleton BirdClassifier (lazy-loaded on first call)."""
    global _classifier_instance
    if _classifier_instance is None:
        with _classifier_lock:
            if _classifier_instance is None:
                _classifier_instance = BirdClassifier()
    return _classifier_instance


class EmbeddingExtractor:
    """TFLite embedding extractor over BirdNET. preserve_all_tensors keeps the
    1024-d layer reachable after invoke (Windows/XNNPACK workaround)."""

    def __init__(self, analyzer):
        import tensorflow.lite as tflite

        self.interp = tflite.Interpreter(
            model_path=analyzer.model_path,
            num_threads=2,
            experimental_preserve_all_tensors=True,
        )
        self.interp.allocate_tensors()
        self.input_index = analyzer.input_layer_index
        self.embedding_index = analyzer.output_layer_index - 1

    def _get_embedding_for_chunk(self, chunk: np.ndarray) -> np.ndarray:
        data = np.array([chunk], dtype="float32")
        self.interp.resize_tensor_input(self.input_index, list(data.shape))
        self.interp.allocate_tensors()
        self.interp.set_tensor(self.input_index, data)
        self.interp.invoke()
        return self.interp.get_tensor(self.embedding_index)[0]

    def extract_from_file(self, audio_path: str, analyzer) -> np.ndarray:
        """Average embeddings across all 3-second chunks of the audio file."""
        from birdnetlib import Recording

        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            rec = Recording(analyzer, audio_path)
            rec.read_audio_data()
        finally:
            sys.stdout = old_out
            sys.stderr = old_err

        chunks = getattr(rec, "chunks", None)
        if not chunks or len(chunks) == 0:
            raise ValueError("No audio chunks extracted (file too short or invalid)")

        vectors = [self._get_embedding_for_chunk(c) for c in chunks]
        avg = np.mean(vectors, axis=0)

        if avg.shape[0] != EMBEDDING_DIM:
            raise ValueError(f"Unexpected embedding dim: {avg.shape[0]} (expected {EMBEDDING_DIM})")

        return avg


class BirdClassifier:
    """Loads BirdNET + trained AutoGluon model once. Thread-safe for reads."""

    def __init__(self):
        model_path = key_files.classifier_model_path
        artifacts_path = key_files.classifier_artifacts_path

        logger.info("Loading bird classifier...")

        # ── Load scaler ──
        with open(artifacts_path / "scaler.pkl", "rb") as f:
            self.scaler = pickle.load(f)

        # ── Load label encoder ──
        with open(artifacts_path / "label_encoder.pkl", "rb") as f:
            self.label_encoder = pickle.load(f)

        # ── Load class mapping (int → eBird code) ──
        with open(artifacts_path / "class_mapping.json", "r") as f:
            self.class_mapping = json.load(f)

        # ── Load AutoGluon predictor ──
        from autogluon.tabular import TabularPredictor
        self.predictor = TabularPredictor.load(str(model_path), require_py_version_match=False)

        # ── Load BirdNET analyzer + embedding extractor ──
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

        # swallow loading output
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            from birdnetlib.analyzer import Analyzer
            self.analyzer = Analyzer()
        finally:
            sys.stdout = old_out
            sys.stderr = old_err

        self.extractor = EmbeddingExtractor(self.analyzer)
        self._predict_lock = Lock()

        logger.info(
            "Bird classifier loaded: %d classes, model=%s",
            len(self.class_mapping),
            self.predictor.model_best,
        )

    def classify_bytes(self, audio_bytes: bytes, suffix: str) -> dict:
        """Classify raw audio bytes. `suffix` is e.g. '.flac' (used for tempfile name).
        Returns {eBird, confidence, top_predictions}."""
        # BirdNET reads from a path, so spill bytes to a tempfile once.
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            with self._predict_lock:
                embedding = self.extractor.extract_from_file(tmp_path, self.analyzer)
                scaled = self.scaler.transform(embedding.reshape(1, -1))
                df = pd.DataFrame(scaled, columns=[f"f{i}" for i in range(EMBEDDING_DIM)])
                proba = self.predictor.predict_proba(df).values[0]
            top_idx = np.argsort(proba)[::-1][:5]

            return {
                "eBird": self.class_mapping.get(str(top_idx[0]), f"unknown_{top_idx[0]}"),
                "confidence": round(float(proba[top_idx[0]]), 4),
                "top_predictions": [
                    {
                        "eBird": self.class_mapping.get(str(i), f"unknown_{i}"),
                        "confidence": round(float(proba[i]), 4),
                    }
                    for i in top_idx
                ],
            }
        finally:
            os.unlink(tmp_path)
