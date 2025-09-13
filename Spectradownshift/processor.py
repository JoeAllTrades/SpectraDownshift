# Spectradownshift/processor.py
import numpy as np

# Dependencies are imported lazily. The calling code (GUI/CLI) is responsible
# for handling missing libraries and informing the user.
try:
    from scipy.signal import resample as scipy_resample, butter, filtfilt
except ImportError:
    scipy_resample, butter, filtfilt = None, None, None
try:
    import soxr
except ImportError:
    soxr = None

class AudioProcessor:
    """Core class for audio processing tasks."""

    def __init__(self, data: np.ndarray, original_sr: int, cutoff_freq: int):
        """
        Initializes the audio processor.

        Args:
            data: Floating-point NumPy array of audio data.
            original_sr: The original sample rate of the data.
            cutoff_freq: The target cutoff frequency for filtering.
        """
        if not isinstance(data, np.ndarray) or not np.issubdtype(data.dtype, np.floating):
            raise TypeError("Input data must be a floating-point NumPy array.")

        self.data = data
        self.original_sr = original_sr
        self.cutoff_freq = cutoff_freq
        self.intermediate_sr = float(cutoff_freq * 2)

    def _apply_zero_phase_filter(self, data: np.ndarray, sr: int, passes: int = 3) -> np.ndarray:
        """Applies a multi-pass, zero-phase filter for a steep cutoff."""
        if butter is None or filtfilt is None:
            raise ImportError("SciPy is not installed; cannot apply filter.")

        final_order = 8 * passes
        print(f"    > Applying {passes}-pass filter (order: {final_order}) at {self.cutoff_freq} Hz...")

        nyquist = 0.5 * sr
        if self.cutoff_freq >= nyquist:
            return data

        normal_cutoff = self.cutoff_freq / nyquist
        b, a = butter(final_order, normal_cutoff, btype='low', analog=False)
        return filtfilt(b, a, data, axis=0)

    def _resample(self, data: np.ndarray, in_sr: float, out_sr: float, engine: str) -> np.ndarray:
        """Resamples audio data using the selected engine."""
        print(f"    > Resampling from {in_sr:.0f} Hz to {out_sr:.0f} Hz (engine: {engine})...")

        if engine == 'scipy':
            if scipy_resample is None:
                raise ImportError("SciPy is not installed; cannot use its resampler.")
            num_samples = int(np.round(len(data) * out_sr / in_sr))
            return scipy_resample(data, num_samples, axis=0)

        if engine == 'soxr':
            if soxr is None:
                raise ImportError("soxr is not installed; cannot use its resampler.")
            return soxr.resample(data, in_sr, out_sr, quality='VHQ')

        raise ValueError(f"Unknown resampler engine: {engine}")

    def prepare(self, resampler_engine: str = 'scipy') -> tuple[np.ndarray, int]:
        """
        Prepares an audio file for downshifting (time-stretching).

        This process simulates a virtual slowdown by re-interpreting the
        sample rate, then resamples the audio back to the original sample rate.

        Args:
            resampler_engine: The engine to use ('scipy' or 'soxr').

        Returns:
            A tuple of (processed_data, final_sample_rate).
        """
        print("\n--- Starting Preparation Step ---")

        speed_factor = self.intermediate_sr / self.original_sr
        print(f"  > Interpreting speed: x{speed_factor:.4f} (from {self.original_sr} Hz to {self.intermediate_sr:.0f} Hz)")

        processed_data = self._resample(self.data, self.intermediate_sr, self.original_sr, resampler_engine)

        # A filter pass is needed for soxr to guarantee the cutoff frequency.
        if resampler_engine == 'soxr':
            processed_data = self._apply_zero_phase_filter(processed_data, self.original_sr)

        print("--- Preparation Finished ---")
        return processed_data, self.original_sr

    def restore(self, resampler_engine: str = 'scipy') -> tuple[np.ndarray, int]:
        """
        Restores a prepared audio file (time-compression).

        This process first resamples the audio down to an intermediate rate,
        then virtually speeds it up by re-interpreting the final sample rate.

        Args:
            resampler_engine: The engine to use ('scipy' or 'soxr').

        Returns:
            A tuple of (processed_data, final_sample_rate).
        """
        print("\n--- Starting Restoration Step ---")

        data_converted = self._resample(self.data, self.original_sr, self.intermediate_sr, resampler_engine)

        final_sr = self.original_sr
        speed_factor = final_sr / self.intermediate_sr
        print(f"  > Interpreting speed: x{speed_factor:.4f} (from {self.intermediate_sr:.0f} Hz to {final_sr} Hz)")

        print("--- Restoration Finished ---")
        return data_converted, final_sr