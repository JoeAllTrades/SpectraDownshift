# SpectraDownshift Processor

![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)![License](https://img.shields.io/badge/license-MIT-green.svg)

A specialized utility to preserve high-frequency content when working with AI audio separation models.

![Spectradownshift GUI](https://user-images.githubusercontent.com/592181/279401948-c2b4e478-cc82-4cde-a1d2-05469fa7f4a2.png)
*(Note: You will need to upload your own screenshot and update this link.)*

## What is this?

Many audio separation models, especially older ones like **MDX-B** and **VR**, operate with a limited frequency range. They often have a hard high-frequency cutoff (e.g., at 17 kHz). Processing full-bandwidth audio through these models can result in a loss of high-end detail ("air").

Spectradownshift works around this limitation by temporarily compressing the audio's spectrum before processing it with an AI model, and then restoring it afterward.

## How it Works

The workflow involves two steps:

1.  **Prepare:**
    *   This process takes your source track and compresses its full frequency spectrum into a narrower band that fits below the AI model's cutoff frequency.
    *   The resulting file is longer and has a lower pitch (similar to a pitch shift effect). It can now be safely fed to the AI model, as the high-frequency information is preserved in a lower register.

2.  **Restore:**
    *   After the AI model has separated the "prepared" file into stems (e.g., vocals, instrumental), you feed those stems into this process.
    *   It performs the inverse operation: it expands the compressed spectrum back to its original range, restoring the file's original pitch and speed.
    *   **Important:** To work correctly, the `Restore` process must use the exact same settings (Cutoff and Quality) as the `Prepare` process.

## Resampling Engines

Spectradownshift provides two resampling engines with different trade-offs:

*   **Scipy (Accurate):** This engine is mathematically lossless and fully reversible. It is slower, but a file that undergoes a `Prepare -> Restore` cycle (using the same settings) will be identical to the original (it will pass a null test). Choose this for maximum fidelity.

*   **Soxr (Fast):** This engine is much faster and provides a near-lossless result. Due to its internal anti-aliasing methods, a tiny amount of high-frequency information may be lost during the `Prepare -> Restore` cycle (it will not pass a null test). The difference is often inaudible. Choose this for speed.

## Installation

This project requires Python 3.11 or newer.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/Spectradownshift.git
    cd Spectradownshift
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    # On Windows
    python -m venv venv
    .\venv\Scripts\activate

    # On macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

You can use the application via its Graphical User Interface (GUI) or a Command-Line Interface (CLI).

### GUI Version

To launch the GUI, run:
```bash
python run_gui.py
```
-   **Profile:** Save and load your settings as presets. Using profiles is the best way to ensure consistent settings between `Prepare` and `Restore`.
-   **Input / Output:** Select the source file/folder and a destination folder.
-   **Quality:** Choose between the `Scipy` (Accurate) and `Soxr` (Fast) engines.
-   **Cutoff Target (Hz):** Set this to match the cutoff frequency of your AI model.
-   **Process:** Select `Prepare` before AI processing or `Restore` after.

**⚠️ Important:** For the `Restore` process, you **must** use the exact same `Cutoff Target` and `Quality` settings that you used for the `Prepare` step.

### CLI Version

A command-line interface is available for scripting and automation.
*(Note: You will need to create a `cli.py` file or adapt `run_gui.py` to handle command-line arguments.)*

**Examples:**

*   **Prepare a file with a 17 kHz cutoff using soxr:**
    ```bash
    python cli.py prepare -i "path/to/source.wav" -o "path/to/output_folder" -c 17000 -e soxr
    ```

*   **Restore a file using the SAME settings:**
    ```bash
    python cli.py restore -i "path/to/vocals_prepared.wav" -o "path/to/output_folder" -c 17000 -e soxr
    ```

**Arguments:**
-   `prepare | restore`: The operation mode.
-   `-i, --input`: Path to the input file or folder.
-   `-o, --output`: Path to the output folder.
-   `-c, --cutoff`: The target cutoff frequency. **Required for both modes.**
-   `-e, --engine`: The resampler to use: `scipy` or `soxr`. **Required for both modes.**