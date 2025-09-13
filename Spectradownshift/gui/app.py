# Spectradownshift/gui/app.py
import sys
import traceback
from pathlib import Path

import soundfile as sf
from PySide6.QtCore import QThread, QObject, Signal, Slot, Qt
from PySide6.QtGui import QTextCursor, QIcon
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLineEdit, QFileDialog, QComboBox,
                               QRadioButton, QGroupBox, QLabel, QTextEdit,
                               QMessageBox, QInputDialog, QGridLayout)

from ..config import ProfileManager
from ..processor import AudioProcessor


class Worker(QObject):
    """
    Performs audio processing in a separate thread to keep the GUI responsive.
    """
    progress_update = Signal(str)
    finished = Signal()

    def __init__(self, files_to_process: list[str], settings: dict):
        super().__init__()
        self.files = files_to_process
        self.settings = settings
        self._is_running = True

    @Slot()
    def run(self):
        """Processes all files in the list."""
        try:
            total_files = len(self.files)
            for i, file_path_str in enumerate(self.files):
                if not self._is_running:
                    self.progress_update.emit("Processing stopped by user.")
                    break
                self.progress_update.emit(f"\n--- [{i+1}/{total_files}] ---")
                self.process_file(Path(file_path_str))
            else:
                self.progress_update.emit("\nAll tasks finished successfully.")
        except Exception:
            self.progress_update.emit(f"\n--- CRITICAL ERROR ---\n{traceback.format_exc()}")
        finally:
            self.finished.emit()

    def process_file(self, file_path: Path):
        self.progress_update.emit(f"Processing: {file_path.name}")
        data, sr = sf.read(file_path, dtype='float64')
        proc = AudioProcessor(data, sr, self.settings['cutoff'])

        if self.settings['process_mode'] == 'prepare':
            output_stem = f"{file_path.stem}_prepared"
            processed_data, final_sr = proc.prepare(resampler_engine=self.settings['resampler'])
        else:
            output_stem = f"{file_path.stem}_restored"
            processed_data, final_sr = proc.restore(resampler_engine=self.settings['resampler'])

        output_folder = Path(self.settings['output_folder'])
        output_format = self.settings['output_format']
        output_filename = output_folder / f"{output_stem}.{output_format}"

        sf.write(output_filename, processed_data, final_sr, subtype='PCM_16')
        self.progress_update.emit(f"  ✓ Saved to: {output_filename.name}")

    def stop(self):
        """Flags the worker to stop processing."""
        self._is_running = False


class GUILogger(QObject):
    """Redirects stdout to a QTextEdit widget."""
    message_written = Signal(str)

    def write(self, text):
        if text.strip():
            self.message_written.emit(text)

    def flush(self):
        pass


class MainWindow(QWidget):
    """The main application window."""
    def __init__(self, pm: ProfileManager):
        super().__init__()
        self.pm = pm
        self.worker_thread = None
        self.worker = None

        self.setWindowTitle("Spectradownshift Processor")
        self.setGeometry(100, 100, 750, 520)

        icon_path = Path(__file__).parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.init_ui()
        self.load_settings()
        self.connect_signals()

        self.gui_logger = GUILogger()
        self.gui_logger.message_written.connect(self.append_log)
        sys.stdout = self.gui_logger

    def init_ui(self):
        """Initializes all UI widgets and layouts."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        profile_layout = self._create_profile_layout()
        main_layout.addLayout(profile_layout)

        settings_grid = self._create_settings_grid()
        main_layout.addLayout(settings_grid)

        action_buttons_layout = self._create_action_buttons_layout()
        main_layout.addLayout(action_buttons_layout)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        main_layout.addWidget(self.log_edit, 1)

        self._apply_stylesheet()

    def connect_signals(self):
        """Connects widget signals to corresponding slots."""
        self.profile_combo.currentIndexChanged.connect(self.apply_profile)
        self.save_profile_button.clicked.connect(self.save_profile)
        self.delete_profile_button.clicked.connect(self.delete_profile)
        self.start_button.clicked.connect(self.start_processing)
        self.stop_button.clicked.connect(self.stop_processing)

    def _create_profile_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Profile:"))

        self.profile_combo = QComboBox()
        layout.addWidget(self.profile_combo, 1)

        self.save_profile_button = QPushButton("Save Profile")
        layout.addWidget(self.save_profile_button)

        self.delete_profile_button = QPushButton("Delete Profile")
        self.delete_profile_button.setObjectName("DeleteButton")
        layout.addWidget(self.delete_profile_button)
        return layout

    def _create_settings_grid(self):
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.addWidget(self._create_io_box(), 0, 0, 2, 1)
        grid.addWidget(self._create_quality_box(), 0, 1)
        grid.addWidget(self._create_cutoff_box(), 1, 1)
        grid.addWidget(self._create_format_box(), 0, 2)
        grid.addWidget(self._create_process_box(), 1, 2)
        grid.setColumnStretch(0, 1)
        return grid

    def _create_action_buttons_layout(self):
        layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("StartButton")

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("StopButton")
        self.stop_button.setEnabled(False)

        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        return layout

    def _create_io_box(self):
        box = QGroupBox("Input / Output")
        layout = QGridLayout()
        layout.setSpacing(10)

        mode_layout = QHBoxLayout()
        self.input_mode_file = QRadioButton("File")
        self.input_mode_file.setChecked(True)
        self.input_mode_folder = QRadioButton("Folder")
        mode_layout.addWidget(self.input_mode_file)
        mode_layout.addWidget(self.input_mode_folder)
        mode_layout.addStretch()

        self.select_input_line_edit = QLineEdit()
        self.select_output_line_edit = QLineEdit()

        layout.addLayout(mode_layout, 0, 0, 1, 2)
        layout.addWidget(QLabel("Input Path"), 1, 0)
        layout.addWidget(self.select_input_line_edit, 1, 1)
        layout.addWidget(self._create_dialog_button(self.select_input_line_edit, "input"), 1, 2)
        layout.addWidget(QLabel("Output Path"), 2, 0)
        layout.addWidget(self.select_output_line_edit, 2, 1)
        layout.addWidget(self._create_dialog_button(self.select_output_line_edit, "output"), 2, 2)
        
        box.setLayout(layout)
        return box

    def _create_dialog_button(self, line_edit: QLineEdit, dialog_type: str):
        button = QPushButton("...")
        button.clicked.connect(lambda: self._open_dialog(line_edit, dialog_type))
        return button

    def _create_quality_box(self):
        box = QGroupBox("Quality")
        layout = QVBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Accurate (Scipy)", "Fast (Soxr)"])
        layout.addWidget(self.quality_combo)
        box.setLayout(layout)
        return box

    def _create_cutoff_box(self):
        box = QGroupBox("Cutoff Target (Hz)")
        layout = QVBoxLayout()
        self.cutoff_edit = QLineEdit()
        layout.addWidget(self.cutoff_edit)
        box.setLayout(layout)
        return box

    def _create_format_box(self):
        box = QGroupBox("Output Format")
        layout = QVBoxLayout()
        self.wav_radio = QRadioButton("WAV")
        self.flac_radio = QRadioButton("FLAC")
        layout.addWidget(self.wav_radio)
        layout.addWidget(self.flac_radio)
        box.setLayout(layout)
        return box

    def _create_process_box(self):
        box = QGroupBox("Process")
        layout = QVBoxLayout()
        self.prepare_radio = QRadioButton("Prepare")
        self.restore_radio = QRadioButton("Restore")
        layout.addWidget(self.prepare_radio)
        layout.addWidget(self.restore_radio)
        box.setLayout(layout)
        return box

    def _apply_stylesheet(self):
        try:
            qss_path = Path(__file__).parent / "dark_theme.qss"
            with open(qss_path, "r", encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("Warning: dark_theme.qss not found. Using default style.")

    def _open_dialog(self, line_edit: QLineEdit, dialog_type: str):
        setting_key = f"last_{dialog_type}_path"
        start_dir = self.pm.get_app_settings().get(setting_key) or str(Path.home())
        path = ""

        if dialog_type == "output":
            path = QFileDialog.getExistingDirectory(self, "Select Output Folder", start_dir)
        elif self.input_mode_folder.isChecked():
            path = QFileDialog.getExistingDirectory(self, "Select Input Folder", start_dir)
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select Input File", start_dir, "Audio Files (*.wav *.flac)")

        if path:
            path_obj = Path(path).resolve()
            line_edit.setText(str(path_obj))
            save_path = path_obj.parent if path_obj.is_file() else path_obj
            self.pm.save_app_setting(setting_key, str(save_path))

    def load_settings(self):
        app_settings = self.pm.get_app_settings()
        self.select_input_line_edit.setText(app_settings.get("last_input_path", ""))
        self.select_output_line_edit.setText(app_settings.get("last_output_path", ""))
        self.load_profiles()
        self.apply_profile()

    @Slot(str)
    def append_log(self, text: str):
        self.log_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.log_edit.insertPlainText(text.strip() + '\n')

    def load_profiles(self):
        current_profile = self.profile_combo.currentText()
        self.profile_combo.clear()
        
        profiles = list(self.pm.get_profiles().keys())
        if profiles:
            self.profile_combo.addItems(profiles)
            if current_profile in profiles:
                self.profile_combo.setCurrentText(current_profile)

    @Slot()
    def apply_profile(self):
        all_profiles = self.pm.get_profiles()
        profile_name = self.profile_combo.currentText()
        settings = all_profiles.get(profile_name)

        if not settings:
            if all_profiles:
                settings = list(all_profiles.values())[0]
            else:
                return

        self.quality_combo.setCurrentIndex(1 if settings.get('resampler') == 'soxr' else 0)
        self.cutoff_edit.setText(str(settings.get('cutoff', 17000)))
        
        is_flac = settings.get('output_format') == 'flac'
        (self.flac_radio if is_flac else self.wav_radio).setChecked(True)
        
        self.prepare_radio.setChecked(True)

    def save_profile(self):
        profile_name, ok = QInputDialog.getText(self, 'Save Profile', 'Enter a name for this profile:')
        if ok and profile_name:
            try:
                cutoff_val = int(self.cutoff_edit.text())
            except ValueError:
                QMessageBox.warning(self, "Warning", "Cutoff Target must be a valid number.")
                return

            settings = {
                "resampler": "soxr" if self.quality_combo.currentIndex() == 1 else "scipy",
                "output_format": "flac" if self.flac_radio.isChecked() else "wav",
                "cutoff": cutoff_val
            }
            self.pm.save_profile(profile_name, settings)
            self.load_profiles()
            self.profile_combo.setCurrentText(profile_name)

    def delete_profile(self):
        profile_name = self.profile_combo.currentText()
        if not profile_name or profile_name not in self.pm.get_profiles():
            return
        
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Delete '{profile_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.pm.delete_profile(profile_name):
                self.load_profiles()

    def _collect_and_validate_inputs(self):
        input_path_str = self.select_input_line_edit.text()
        output_folder_str = self.select_output_line_edit.text()

        if not (input_path_str and output_folder_str and Path(output_folder_str).is_dir()):
            QMessageBox.warning(self, "Warning", "Please select a valid input and an existing output folder.")
            return None, None

        input_path = Path(input_path_str)
        files_to_process = []
        
        if self.input_mode_folder.isChecked():
            if not input_path.is_dir():
                QMessageBox.warning(self, "Warning", f"'{input_path_str}' is not a valid folder.")
                return None, None
            wav_files = sorted(list(input_path.glob("*.wav")))
            flac_files = sorted(list(input_path.glob("*.flac")))
            files_to_process = wav_files + flac_files
            self.append_log(f"Batch mode: Found {len(files_to_process)} audio files.")
        else:
            if not (input_path.is_file() and input_path.suffix.lower() in ['.wav', '.flac']):
                QMessageBox.warning(self, "Warning", f"'{input_path_str}' is not a valid audio file.")
                return None, None
            files_to_process = [input_path]

        if not files_to_process:
            QMessageBox.warning(self, "Warning", "No compatible audio files were found.")
            return None, None
            
        return files_to_process, output_folder_str

    def start_processing(self):
        files_to_process, output_folder = self._collect_and_validate_inputs()
        if not files_to_process:
            return

        try:
            cutoff = int(self.cutoff_edit.text())
            if cutoff <= 0: raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Warning", "Cutoff Target must be a positive number.")
            return
        
        settings = {
            "resampler": "soxr" if self.quality_combo.currentIndex() == 1 else "scipy",
            "output_format": "flac" if self.flac_radio.isChecked() else "wav",
            "cutoff": cutoff,
            "process_mode": "restore" if self.restore_radio.isChecked() else "prepare",
            "output_folder": output_folder
        }

        self.worker_thread = QThread()
        self.worker = Worker([str(p) for p in files_to_process], settings)
        self.worker.moveToThread(self.worker_thread)

        self.worker.progress_update.connect(self.append_log)
        self.worker.finished.connect(self.processing_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        self.worker_thread.start()
        self.set_ui_state(processing=True)

    def stop_processing(self):
        if self.worker:
            self.worker.stop()
            self.append_log(">>> Sending stop signal...")
        self.stop_button.setEnabled(False)

    @Slot()
    def processing_finished(self):
        self.set_ui_state(processing=False)

    def set_ui_state(self, processing: bool):
        """Toggles the enabled state of buttons based on processing status."""
        self.start_button.setEnabled(not processing)
        self.stop_button.setEnabled(processing)
        if not processing:
            self.log_edit.clear()