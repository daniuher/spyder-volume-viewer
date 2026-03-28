# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2026, fried-pineapple0
# Licensed under the terms of the GNU General Public License v3
# ----------------------------------------------------------------------------
"""
VolumeViewer Main Widget.
"""

# Third party imports
from qtpy.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSplitter,
    QListWidgetItem, QSizePolicy, QListWidget,
    QWidget, QVBoxLayout, QCheckBox, QSlider, QComboBox, QFrame
)
from qtpy.QtCore import Qt, QEvent
from qtpy.QtGui import QImage, QPixmap, QPainter

import numpy as np

# Spyder imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from qtpy.QtWidgets import QMessageBox

import matplotlib.cm as mcm

_ = get_translation("volumeviewer.spyder")


# ---------------------------------------------------------------------------
# ImageCanvas
# ---------------------------------------------------------------------------

class ImageCanvas(QWidget):
    """
    QPainter-based 2D slice viewer with optional overlay compositing.

    Base image and overlay are each converted to a QPixmap once per slice
    change (in _rebuild_*_pixmap). paintEvent only does two drawPixmap calls,
    keeping the paint path allocation-free.
    """

    # OVERLAY_ALPHA = 255  # 0-255 global overlay opacity

    def __init__(self, parent=None):
        super().__init__(parent)

        # Base
        self._pixmap = None
        self._raw_slice = None          # float32 (H, W), image convention
        self._vmin = 0.0
        self._vmax = 1.0
        self._cmap = mcm.get_cmap("gray")

        # Overlay
        self._overlay_pixmap = None
        self._overlay_slice = None      # float32 (H, W) or None
        self._overlay_cmap = mcm.get_cmap("hot")
        self._overlay_vmin = 0.0
        self._overlay_vmax = 1.0
        self._overlay_opacity = 255
        self._overlay_transp_bg = False  # zero-voxels → fully transparent

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(64, 64)
        self.setStyleSheet("background-color: black;")

    # --- Base image API ---

    def set_slice(self, arr2d: np.ndarray):
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

    # --- Overlay API ---

    def set_overlay_slice(self, arr2d: np.ndarray):
        """arr2d in array indexing (X, Y); transposed internally."""
        self._overlay_slice = np.asarray(arr2d.T, dtype=np.float32)
        self._rebuild_overlay_pixmap()
        self.update()

    def set_overlay_params(self, vmin: float, vmax: float, cmap_name: str = "hot"):
        self._overlay_vmin = vmin
        self._overlay_vmax = vmax
        self._overlay_cmap = mcm.get_cmap(cmap_name)
        self._rebuild_overlay_pixmap()
        self.update()

    def set_overlay_transp_bg(self, enabled: bool):
        self._overlay_transp_bg = enabled
        self._rebuild_overlay_pixmap()
        self.update()

    def set_overlay_opacity(self, slider_value: float):
        self._overlay_opacity = slider_value
        self._rebuild_overlay_pixmap()
        self.update()
        
    def set_overlay_cmap(self, cmap_name: str):
        self._overlay_cmap = mcm.get_cmap(cmap_name)
        self._rebuild_overlay_pixmap()
        self.update()

    def clear_overlay(self):
        self._overlay_slice = None
        self._overlay_pixmap = None
        self.update()

    # --- Internal pixmap builders ---

    def _rebuild_pixmap(self):
        if self._raw_slice is None:
            return
        span = self._vmax - self._vmin or 1.0
        norm = np.clip((self._raw_slice - self._vmin) / span, 0.0, 1.0)
        rgba = np.ascontiguousarray((self._cmap(norm) * 255).astype(np.uint8))
        h, w = rgba.shape[:2]
        qimg = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888)
        self._pixmap = QPixmap.fromImage(qimg).scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

    def _rebuild_overlay_pixmap(self):
        if self._overlay_slice is None:
            self._overlay_pixmap = None
            return

        span = self._overlay_vmax - self._overlay_vmin or 1.0
        norm = np.clip(
            (self._overlay_slice - self._overlay_vmin) / span, 0.0, 1.0
        )

        # RGBA float → uint8
        rgba = (self._overlay_cmap(norm) * 255).astype(np.uint8)

        # Bake per-voxel alpha into the A channel
        if self._overlay_transp_bg:
            # Zero source voxels → fully transparent; others → OVERLAY_ALPHA
            mask = self._overlay_slice > 0
            rgba[..., 3] = np.where(mask, self._overlay_opacity, 0).astype(np.uint8)
        else:
            rgba[..., 3] = self._overlay_opacity

        rgba = np.ascontiguousarray(rgba)
        h, w = rgba.shape[:2]
        qimg = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888)
        self._overlay_pixmap = QPixmap.fromImage(qimg).scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

    # --- Qt overrides ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if self._pixmap is not None:
            x = (self.width()  - self._pixmap.width())  // 2
            y = (self.height() - self._pixmap.height()) // 2
            painter.drawPixmap(x, y, self._pixmap)
        if self._overlay_pixmap is not None:
            # Overlay pixmap is scaled to the same size, so offsets are identical
            x = (self.width()  - self._overlay_pixmap.width())  // 2
            y = (self.height() - self._overlay_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._overlay_pixmap)
        painter.end()

    def resizeEvent(self, event):
        self._rebuild_pixmap()
        self._rebuild_overlay_pixmap()
        super().resizeEvent(event)


# ---------------------------------------------------------------------------
# VolumeViewerWidget
# ---------------------------------------------------------------------------

class VolumeViewerActions:
    ExampleAction = "example_action"

class VolumeViewerToolBarSections:
    ExampleSection = "example_section"

class VolumeViewerOptionsMenuSections:
    ExampleSection = "example_section"


class VolumeViewerWidget(PluginMainWidget):

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        self.global_vars = list(globals().keys())
        self.shellwidget = None

        # Base volume state
        self._data = None           # (X, Y, Z, N) float32
        self._data_max = None
        self._data_min = None
        self._name = ""
        self._slice_idx = 0
        self._vol_idx = 0
        self._vmin = 0.0
        self._vmax = 1.0

        # Overlay state
        self._overlay_data = None   # (X, Y, Z, N) float32 or None
        self._overlay_name = ""
        self._overlay_vmin = 0.0
        self._overlay_vmax = 1.0

        # Namespace shape cache: {var_name: tuple}
        self._ns_shapes = {}

        self._build_ui()
        self._test_console_connection()

        # arr = self._make_test_volume()
        # self.set_data(arr, name="test_volume")

    # --- UI construction ----------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        outer.setSpacing(2)

        # ── Top toolbar (Refresh + future global controls) ──────────────────
        top_toolbar = QHBoxLayout()
        self._refresh_btn = QPushButton("↻ Refresh")
        self._refresh_btn.setFixedWidth(90)
        self._refresh_btn.setToolTip(
            "Rescan kernel namespace for numpy arrays or NIFTI objects"
        )
        self._refresh_btn.clicked.connect(self.refresh_variable_list)
        top_toolbar.addWidget(self._refresh_btn)
        top_toolbar.addStretch()
        outer.addLayout(top_toolbar)

        # ── Main horizontal splitter: [left panel | right column] ───────────
        h_splitter = QSplitter(Qt.Horizontal)

        # Left panel: vertical splitter with base list on top, overlay below
        left_splitter = QSplitter(Qt.Vertical)
        
        self._listwidget = QListWidget()
        self._listwidget.setMaximumWidth(180)
        self._listwidget.setMinimumWidth(80)
        self._listwidget.setToolTip("Click to load variable as base image")
        self._listwidget.itemClicked.connect(self._on_item_clicked)
        
        left_splitter.addWidget(self._listwidget)

        # Overlay sub-panel (hidden until a base is loaded)
        self._overlay_panel = QWidget()
        overlay_layout = QVBoxLayout(self._overlay_panel)
        overlay_layout.setContentsMargins(0, 4, 0, 0)
        overlay_layout.setSpacing(2)

        overlay_header = QLabel("Overlays")
        overlay_header.setStyleSheet("font-weight: bold; color: gray;")
        overlay_layout.addWidget(overlay_header)

        self._overlay_listwidget = QListWidget()
        self._overlay_listwidget.setMaximumWidth(180)
        self._overlay_listwidget.setMinimumWidth(80)
        self._overlay_listwidget.setToolTip(
            "Arrays with matching spatial dimensions - click to overlay"
        )
        self._overlay_listwidget.itemClicked.connect(self._on_overlay_clicked)
        overlay_layout.addWidget(self._overlay_listwidget)

        left_splitter.addWidget(self._overlay_panel)
        self._overlay_panel.setVisible(False)

        left_splitter.setStretchFactor(0, 2)
        left_splitter.setStretchFactor(1, 1)
        h_splitter.addWidget(left_splitter)

        # Right column: canvas toolbar + canvas
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        # Canvas toolbar (hidden until an overlay is active; extend here later)
        self._canvas_toolbar = QWidget()
        canvas_tb_layout = QHBoxLayout(self._canvas_toolbar)
        canvas_tb_layout.setContentsMargins(4, 2, 4, 2)
        canvas_tb_layout.setSpacing(8)

        self._transp_bg_cb = QCheckBox("Transparent BG")
        self._transp_bg_cb.setToolTip(
            "Make zero-valued overlay voxels fully transparent"
        )
        self._transp_bg_cb.setChecked(False)
        self._transp_bg_cb.stateChanged.connect(self._on_transp_bg_changed)
        canvas_tb_layout.addWidget(self._transp_bg_cb)
        
        # ---- Opacity slider ----
        canvas_tb_layout.addWidget(self._make_separator())
        opacity_label = QLabel("Opacity:")
        canvas_tb_layout.addWidget(opacity_label)
        
        self._overlay_opacity_slider = QSlider(Qt.Orientation.Horizontal, self)
        self._overlay_opacity_slider.setRange(0, 255)
        self._overlay_opacity_slider.setValue(255)
        self._overlay_opacity_slider.setSingleStep(5)
        self._overlay_opacity_slider.setPageStep(10)
        self._overlay_opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._overlay_opacity_slider.valueChanged.connect(self._on_opacitiy_slider_changed)
        self._overlay_opacity_slider.setFixedWidth(80)
        
        # canvas_tb_layout.addWidget(self._overlay_opacity_label)
        canvas_tb_layout.addWidget(self._overlay_opacity_slider)
        
        # -------- Color map selector ----------------
        canvas_tb_layout.addWidget(self._make_separator())
        self._cmap_combo = QComboBox()
        self._cmap_combo.addItems(["hot", "viridis", "gray"])
        self._cmap_combo.setFixedWidth(80)
        self._cmap_combo.currentTextChanged.connect(self._on_cmap_changed)
        canvas_tb_layout.addWidget(self._cmap_combo)
        
        # --------------------------------------------
        # align to left
        canvas_tb_layout.addStretch(1)
        
        right_layout.addWidget(self._canvas_toolbar)
        self._canvas_toolbar.setVisible(False)

        self._canvas = ImageCanvas()
        self._canvas.setFocusPolicy(Qt.StrongFocus)
        self._canvas.installEventFilter(self)
        right_layout.addWidget(self._canvas, stretch=1)

        h_splitter.addWidget(right_col)
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)
        outer.addWidget(h_splitter, stretch=1)

        # ── Status bar ───────────────────────────────────────────────────────
        self._status = QLabel(
            "No data loaded — select a variable or press ↻ to refresh"
        )
        self._status.setAlignment(Qt.AlignCenter)
        outer.addWidget(self._status)

    # --- Helpers ------------------------------------------------------------
    def _make_separator(self) -> QFrame:
        """Returns a vertical separator line for use in horizontal toolbars."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setFixedWidth(2)
        return sep

    # --- Shell / namespace --------------------------------------------------

    def set_shellwidget(self, shellwidget):
        self.shellwidget = shellwidget
        self.refresh_variable_list()

    def _test_console_connection(self):
        try:
            ns = self.shellwidget.call_kernel(blocking=True).get_namespace_view()
            self._status.setText(f"Namespace view success! {ns}")
        except Exception as e:
            self._status.setText(f"get_namespace_view Error: {e}")

    def refresh_variable_list(self):
        self._listwidget.clear()
        self._ns_shapes.clear()
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
                    shape_arr = info.get("size", "") if isinstance(info, dict) else ""
                    QMessageBox.information(self, "Debug", f"error: {type(shape_arr)}")
                    
                    if isinstance(shape_arr, str):
                        shape_tuple = tuple([int(x) for x in shape_arr.strip('()').split(', ')])
                    elif isinstance(shape_arr, tuple):
                        shape_tuple = shape_arr
                    elif isinstance(shape_arr, list):
                        shape_tuple = tuple(shape_arr)
                    else:
                        shape_tuple = ()
                    
                    # QMessageBox.information(self, "Debug", f"error: {shape_tuple}")
                        
                    self._ns_shapes[name] = shape_tuple
    
                    
                    item = QListWidgetItem(name)
                    item.setToolTip(f"{type_str}  {shape_tuple}")
                    self._listwidget.addItem(item)
                    
        except Exception as e:
            self._status.setText(f"Namespace error: {e}")

    # --- Base image selection -----------------------------------------------

    # def _on_item_clicked(self, item: QListWidgetItem):
    #     var_name = item.text()
    #     QMessageBox.information(self, "Debug", f"error: {var_name}")
        
    #     if self.shellwidget is None:
    #         return
    #     self._status.setText(f"Loading '{var_name}'…")
    #     try:
    #         arr = self.shellwidget.call_kernel(blocking=True).get_value(var_name)
    #     except Exception as e:
    #         self._status.setText(f"Could not fetch '{var_name}': {e}")
    #         return
    #     if not isinstance(arr, np.ndarray):
    #         self._status.setText(f"'{var_name}' is not a numpy array.")
    #         return

    #     self.set_data(arr, name=var_name)
    #     self._clear_overlay()
    #     self._populate_overlay_list(arr.shape[:3])
    #     self._overlay_panel.setVisible(True)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        var_name = item.text()
        if self.shellwidget is None:
            return
        self._status.setText(f"Loading '{var_name}'…")
        try:
            self.shellwidget.call_kernel(
                interrupt=False,
                blocking=False,
                callback=lambda arr: self._on_value_received(var_name, arr),
            ).get_value(var_name)
        except Exception as e:
            self._status.setText(f"Could not fetch '{var_name}': {e}")
    
    def _on_value_received(self, var_name: str, arr):
        if isinstance(arr, list):
            try:
                arr = np.array(arr)
            except Exception as e:
                self._status.setText(f"Could not convert '{var_name}' to array: {e}")
                return
            
        if not isinstance(arr, np.ndarray):
            self._status.setText(f"'{var_name}' is not a numpy array (got {type(arr).__name__}).")
            return
        
        self.set_data(arr, name=var_name)
        self._clear_overlay()
        self._populate_overlay_list(arr.shape[:3])
        self._overlay_panel.setVisible(True)

    # --- Overlay list -------------------------------------------------------

    def _populate_overlay_list(self, base_spatial: tuple):
        """Fill overlay list with arrays whose first 3 dims match base_spatial."""
        self._overlay_listwidget.clear()

        # Always offer a 'None' item to clear the overlay
        none_item = QListWidgetItem("[ None ]")
        none_item.setToolTip("Remove overlay")
        self._overlay_listwidget.addItem(none_item)

        for name, shape in sorted(self._ns_shapes.items()):
            if name == self._name:
                continue  # skip the base itself
            spatial = shape[:3] if len(shape) >= 3 else shape
            if spatial == base_spatial:
                item = QListWidgetItem(name)
                item.setToolTip(f"shape: {shape}")
                self._overlay_listwidget.addItem(item)

    def _on_overlay_clicked(self, item: QListWidgetItem):
        var_name = item.text()

        if var_name == "[ None ]":
            self._clear_overlay()
            return

        if self.shellwidget is None:
            return
        self._status.setText(f"Loading overlay '{var_name}'…")
        try:
            arr = self.shellwidget.call_kernel(blocking=True).get_value(var_name)
        except Exception as e:
            self._status.setText(f"Could not fetch overlay '{var_name}': {e}")
            return
        if not isinstance(arr, np.ndarray):
            try:
                arr = np.array(arr)
            except Exception as e:
                self._status.setText(f"'{var_name}' is not a numpy array. {e}")
                return

        self.set_overlay(arr, name=var_name)

    # --- Overlay data management --------------------------------------------

    def set_overlay(self, arr: np.ndarray, name: str = ""):
        if arr.ndim == 2:
            arr = arr[..., np.newaxis, np.newaxis]
        if arr.ndim == 3:
            arr = arr[..., np.newaxis]
        if arr.ndim != 4:
            self._status.setText(
                f"Overlay '{name}': expected 3D or 4D array, got {arr.ndim}D."
            )
            return

        self._overlay_data = np.ascontiguousarray(arr, dtype=np.float32)
        self._overlay_name = name
        self._overlay_vmin = float(np.percentile(arr, 2))
        self._overlay_vmax = float(np.percentile(arr, 98))

        self._canvas.set_overlay_params(
            self._overlay_vmin, self._overlay_vmax, cmap_name="hot"
        )
        self._canvas_toolbar.setVisible(True)
        self._draw()
        self._update_status()

    def _clear_overlay(self):
        self._overlay_data = None
        self._overlay_name = ""
        self._canvas.clear_overlay()
        self._canvas_toolbar.setVisible(False)
        self._transp_bg_cb.setChecked(False)
        self._update_status()

    # --- Canvas toolbar slots -----------------------------------------------

    def _on_transp_bg_changed(self, state):
        self._canvas.set_overlay_transp_bg(bool(state))
        
    def _on_opacitiy_slider_changed(self, value):
        self._canvas.set_overlay_opacity(float(value))
        
    def _on_cmap_changed(self, cmap_name: str) -> None:
        # if not hasattr(self, '_overlay') or self._overlay is None:
        #     return
        # safe to proceed
        # QMessageBox.information(self, "Debug", f"{cmap_name}")
        self._canvas.set_overlay_cmap(cmap_name)  

    # --- Core draw ----------------------------------------------------------

    def _draw(self):
        if self._data is None:
            return

        sl = self._data[:, :, self._slice_idx, self._vol_idx]
        self._canvas.set_slice(sl)

        if self._overlay_data is not None:
            N_ov = self._overlay_data.shape[3]
            ov_vol = min(self._vol_idx, N_ov - 1)  # clamp: single-vol overlays stick
            ov_sl = self._overlay_data[:, :, self._slice_idx, ov_vol]
            self._canvas.set_overlay_slice(ov_sl)
        
        self._update_status()

    def _update_status(self):
        if self._data is None:
            return
        X, Y, Z, N = self._data.shape
        ov_txt = f" |  overlay: {self._overlay_name}" if self._overlay_data is not None else ""
        
        range_txt = ""
        if self._data_min is not None and self._data_max is not None:
            range_txt = f" | Vol range {self._data_min[self._vol_idx]:.2f}–{self._data_max[self._vol_idx]:.2f}"
        
        self._status.setText(
            f"{self._name} | {X}×{Y}×{Z}×{N}"
            f" | Slice {self._slice_idx}/{Z - 1}"
            f" | Vol {self._vol_idx}/{N - 1}"
            f" {range_txt}"
            f" {ov_txt}"
        )

    # --- Synthetic test data ------------------------------------------------

    def _make_test_volume(self):
        X, Y, Z, N = 64, 64, 30, 5
        x = np.linspace(-1, 1, X)
        y = np.linspace(-1, 1, Y)
        z = np.linspace(-1, 1, Z)
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
        volumes = []
        for v in range(N):
            r2 = xx**2 + yy**2 + (zz - 0.1 * v)**2
            volumes.append(np.exp(-r2 / 0.3))
        return np.stack(volumes, axis=-1).astype(np.float32)

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
        
        self._data = np.ascontiguousarray(arr, dtype=np.float32)
        self._data_max = np.max(self._data, axis=(0,1,2))
        self._data_min = np.min(self._data, axis=(0,1,2))
        self._name = name
        self._slice_idx = arr.shape[2] // 2
        self._vol_idx = 0
        self._vmin = float(np.percentile(arr, 2))
        self._vmax = float(np.percentile(arr, 98))
        self._canvas.set_window(self._vmin, self._vmax)
        self._canvas.setFocus()
        self._draw()

    # --- Plugin API ---------------------------------------------------------

    def get_title(self):
        return _("VolumeViewer")

    def get_focus_widget(self):
        pass

    def setup(self):
        example_action = self.create_action(
            name=VolumeViewerActions.ExampleAction,
            text="Example action",
            tip="Example hover hint",
            icon=self.create_icon("spyder"),
            triggered=lambda: print("Example action triggered!"),
        )
        menu = self.get_options_menu()
        self.add_item_to_menu(
            example_action, menu, VolumeViewerOptionsMenuSections.ExampleSection,
        )
        toolbar = self.get_main_toolbar()
        self.add_item_to_toolbar(
            example_action, toolbar, VolumeViewerOptionsMenuSections.ExampleSection,
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
