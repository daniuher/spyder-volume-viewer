# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2026, fried-pineapple0
#
# Licensed under the terms of the GNU General Public License v3
# ----------------------------------------------------------------------------
"""
VolumeViewer Main Widget.
"""


# Third party imports
from qtpy.QtWidgets import (QHBoxLayout, QLabel, 
                            QPushButton, QSplitter, 
                            QListWidgetItem, QPushButton, 
                            QLabel, QSizePolicy,
                            QListWidget, QWidget,
                            QVBoxLayout)

from qtpy.QtCore import Qt, QEvent

from qtpy.QtGui import QImage, QPixmap, QPainter

# other
import numpy as np

# Spyder imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation

from spyder.api.widgets.main_widget import PluginMainWidget

# Matplotlib Qt backend
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import matplotlib.cm as mcm


# Localization
_ = get_translation("volumeviewer.spyder")


class ImageCanvas(QWidget):
    """
    Displays a single 2D float array using Qt native painting.
    Extend paintEvent for overlays, crosshair, MPR viewports, etc.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._raw_slice = None      # float32 (H, W) — image convention
        self._vmin = 0.0
        self._vmax = 1.0
        self._cmap = mcm.get_cmap("gray")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(64, 64)
        self.setStyleSheet("background-color: black;")

    def set_slice(self, arr2d: np.ndarray):
        """
        arr2d: 2D array in array indexing convention (X, Y).
        Transposed here to (row=Y, col=X) for correct image display.
        """
        self._raw_slice = np.asarray(arr2d.T, dtype=np.float32)
        self._rebuild_pixmap()
        self.update()

    def set_window(self, vmin: float, vmax: float):
        self._vmin = vmin
        self._vmax = vmax
        self._rebuild_pixmap()
        self.update()

    def set_colormap(self, name: str):
        self._cmap = mcm.get_cmap(name)
        self._rebuild_pixmap()
        self.update()

    def _rebuild_pixmap(self):
        if self._raw_slice is None:
            return

        # 1. Window/level normalization
        span = self._vmax - self._vmin
        if span == 0.0:
            span = 1.0
        norm = np.clip((self._raw_slice - self._vmin) / span, 0.0, 1.0)

        # 2. Colormap → RGBA uint8
        # matplotlib cmap returns float64 (H, W, 4) in [0,1]
        rgba = (self._cmap(norm) * 255).astype(np.uint8)
        rgba = np.ascontiguousarray(rgba)   # must be C-contiguous for QImage

        # 3. QImage wraps the buffer — call fromImage immediately to deep-copy
        #    into Qt memory before the numpy array can be GC'd
        h, w = rgba.shape[:2]
        qimg = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888)
        self._pixmap = QPixmap.fromImage(qimg).scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if self._pixmap is not None:
            x = (self.width()  - self._pixmap.width())  // 2
            y = (self.height() - self._pixmap.height()) // 2
            painter.drawPixmap(x, y, self._pixmap)
        painter.end()

    def resizeEvent(self, event):
        """Re-scale pixmap to new widget dimensions on resize."""
        self._rebuild_pixmap()
        super().resizeEvent(event)


class VolumeViewerActions:
    ExampleAction = "example_action"


class VolumeViewerToolBarSections:
    ExampleSection = "example_section"


class VolumeViewerOptionsMenuSections:
    ExampleSection = "example_section"


class VolumeViewerWidget(PluginMainWidget):

    # PluginMainWidget class constants
    
    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)
        
        self.global_vars = list(globals().keys())
        self.shellwidget = None
        self._data = None       # (X, Y, Z, N) float32, C-contiguous
        self._name = ""
        self._slice_idx = 0
        self._vol_idx = 0
        self._vmin = 0.0
        self._vmax = 1.0
        
        self._build_ui()
        self._test_console_connection()
        
        arr = self._make_test_volume()
        # Call set_data() directly — skips get_value() / shellwidget completely
        self.set_data(arr, name="test_volume")

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        outer.setSpacing(2)

        # Toolbar
        toolbar = QHBoxLayout()
        self._refresh_btn = QPushButton("↻  Refresh")
        self._refresh_btn.setFixedWidth(90)
        self._refresh_btn.setToolTip("Rescan kernel namespace for numpy arrays or NIFTI objects")
        self._refresh_btn.clicked.connect(self.refresh_variable_list)
        toolbar.addWidget(self._refresh_btn)
        toolbar.addStretch()
        outer.addLayout(toolbar)

        # Splitter: variable list | image canvas
        splitter = QSplitter(Qt.Horizontal)

        self._listwidget = QListWidget()
        self._listwidget.setMaximumWidth(180)
        self._listwidget.setMinimumWidth(80)
        self._listwidget.setToolTip("Click to load variable")
        self._listwidget.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self._listwidget)

        self._canvas = ImageCanvas()
        self._canvas.setFocusPolicy(Qt.StrongFocus)
        self._canvas.installEventFilter(self)
        splitter.addWidget(self._canvas)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, stretch=1)

        # test connection button
        # self._test_btn = QPushButton("Test Connection")
        # self._test_btn.clicked.connect(self._test_console_connection)
        # toolbar.addWidget(self._test_btn) # Add this near your refresh button

        # Status bar
        self._status = QLabel("No data loaded — select a variable or press ↻ to refresh")
        self._status.setAlignment(Qt.AlignCenter)
        outer.addWidget(self._status)
    
    def set_shellwidget(self, shellwidget):
        self.shellwidget = shellwidget
        self.refresh_variable_list()
    
    def _test_console_connection(self):
        """
        Independent test: Asks the kernel for variable names and prints them.
        """
        try:
            ns = self.shellwidget.call_kernel(blocking=True).get_namespace_view()
            self._status.setText(f"Namespace view success! {ns}")
            return
        except Exception as e:
            self._status.setText(f"get_namespace_view Error: {e}")
            return
        
        if self.shellwidget is None:
            print("Test Failed: No shellwidget connected.")
            self._status.setText("Test Failed: No console.")
            return

        current_var_list = list(globals().keys())
        names = [x for x in current_var_list if x not in self.global_vars]
        print(names)
        
        print("--- Testing Console Connection ---")
        try:
            # 1. We ask the kernel to run 'dir()' and return the result
            # get_value() is the most stable way to pull a result back to the plugin
            current_var_list = list(globals().keys())
            names = [x for x in current_var_list if x not in self.global_vars]
            print(names)
            
            # if names:
            #     available_vars = self.shellwidget.get_value(names[0])
            # names = self.shellwidget.get_value()
            
            if names:
                print(f"Variables found in kernel: {names}")
                self._status.setText(f"Connected! Found {len(names)} items. {current_var_list}")
            else:
                print("Connected, but the global namespace appears empty.")
                self._status.setText("Connected (empty namespace).")
                
        except Exception as e:
            print(f"Connection Error: {str(e)}")
            self._status.setText(f"Test Error: {e}")
            
    
    def refresh_variable_list(self):
        self._listwidget.clear()
        if self.shellwidget is None:
            self._status.setText("No active console.")
            return
        try:
            ns = self.shellwidget.call_kernel(blocking=True).get_namespace_view()
            for name, info in sorted(ns.items()):
                type_str = (
                    info.get("type", "") if isinstance(info, dict) else str(info)
                )
                if "ndarray" in type_str or "array" in type_str.lower():
                    shape_str = info.get("size", "") if isinstance(info, dict) else ""
                    item = QListWidgetItem(name)
                    item.setToolTip(f"{type_str}  {shape_str}")
                    self._listwidget.addItem(item)
        except Exception as e:
            self._status.setText(f"Namespace error: {e}")

    def _on_item_clicked(self, item: QListWidgetItem):
        var_name = item.text()
        if self.shellwidget is None:
            return
        self._status.setText(f"Loading '{var_name}'…")
        try:
            arr = self.shellwidget.call_kernel(blocking=True).get_value(var_name)
        except Exception as e:
            self._status.setText(f"Could not fetch '{var_name}': {e}")
            return
        if not isinstance(arr, np.ndarray):
            self._status.setText(f"'{var_name}' is not a numpy array.")
            return
        self.set_data(arr, name=var_name)
    
    
        
    def _make_test_volume(self):
        """
        Synthetic 4D volume that gives visually distinct slices and volumes.
        Shape (64, 64, 30, 5) — small enough to be instant, big enough to test navigation.
        """
        X, Y, Z, N = 64, 64, 30, 5
        x = np.linspace(-1, 1, X)
        y = np.linspace(-1, 1, Y)
        z = np.linspace(-1, 1, Z)
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')

        volumes = []
        for v in range(N):
            # Each volume: a Gaussian blob at a different Z offset — easy to see change
            r2 = xx**2 + yy**2 + (zz - 0.1 * v)**2
            vol = np.exp(-r2 / 0.3)
            volumes.append(vol)

        arr = np.stack(volumes, axis=-1).astype(np.float32)
        return arr    
        
    def set_data(self, arr: np.ndarray, name: str = ""):
        if arr.ndim == 2:
            arr = arr[..., np.newaxis, np.newaxis]    
            
        if arr.ndim == 3:
            arr = arr[..., np.newaxis]
            
        if arr.ndim != 4:
            self._status.setText(
                f"'{name}': expected 3D or 4D array, got {arr.ndim}D."
            )
            return

        # Force C-contiguous — nibabel returns Fortran-order arrays
        self._data = np.ascontiguousarray(arr, dtype=np.float32)
        self._name = name
        self._slice_idx = arr.shape[2] // 2
        self._vol_idx = 0
        self._vmin = float(np.percentile(arr, 2))
        self._vmax = float(np.percentile(arr, 98))

        self._canvas.set_window(self._vmin, self._vmax)
        self._canvas.setFocus()
        self._draw()

    def _draw(self):
        if self._data is None:
            return
        sl = self._data[:, :, self._slice_idx, self._vol_idx]
        self._canvas.set_slice(sl)
        self._update_status()

    def _update_status(self):
        X, Y, Z, N = self._data.shape
        self._status.setText(
            f"{self._name}  |  {X}×{Y}×{Z}×{N}"
            f"  |  Slice {self._slice_idx}/{Z - 1}"
            f"  |  Vol {self._vol_idx}/{N - 1}"
        )
    
    def get_title(self):
        return _("VolumeViewer")

    def get_focus_widget(self):
        pass

    def setup(self):
        # Create an example action
        example_action = self.create_action(
            name=VolumeViewerActions.ExampleAction,
            text="Example action",
            tip="Example hover hint",
            icon=self.create_icon("spyder"),
            triggered=lambda: print("Example action triggered!"),
        )

        # Add an example action to the plugin options menu
        menu = self.get_options_menu()
        self.add_item_to_menu(
            example_action,
            menu,
            VolumeViewerOptionsMenuSections.ExampleSection,
        )

        # Add an example action to the plugin toolbar
        toolbar = self.get_main_toolbar()
        self.add_item_to_toolbar(
            example_action,
            toolbar,
            VolumeViewerOptionsMenuSections.ExampleSection,
        )

    def update_actions(self):
        pass
        
    def eventFilter(self, obj, event):
        if self._data is None:
            return super().eventFilter(obj, event)
        Z = self._data.shape[2]
        N = self._data.shape[3]

        if event.type() == QEvent.Wheel:
            step = 1 if event.angleDelta().y() > 5 else -1
            self._slice_idx = int(np.clip(self._slice_idx + step, 0, Z - 1))
            self._draw()
            return True

        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Right:
                self._vol_idx = (self._vol_idx + 1) % N
                self._draw(); return True
            if key == Qt.Key_Left:
                self._vol_idx = (self._vol_idx - 1) % N
                self._draw(); return True
            if key == Qt.Key_Up:
                self._slice_idx = int(np.clip(self._slice_idx + 1, 0, Z - 1))
                self._draw(); return True
            if key == Qt.Key_Down:
                self._slice_idx = int(np.clip(self._slice_idx - 1, 0, Z - 1))
                self._draw(); return True

        return super().eventFilter(obj, event)

    @on_conf_change
    def on_section_conf_change(self, section):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
