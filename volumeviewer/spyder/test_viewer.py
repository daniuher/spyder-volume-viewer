#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  8 13:57:31 2026

@author: duher
"""


import sys
import numpy as np
from qtpy.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton

# --- Make sure your package is importable (run from repo root, or pip install -e .) ---
from widgets import VolumeViewerWidget


def make_test_volume():
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


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VolumeViewer — standalone test")
        self.resize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # The viewer widget — no shellwidget, no Spyder
        self.viewer = VolumeViewerWidget(self)
        layout.addWidget(self.viewer, stretch=1)

        # Button to load test data directly, bypassing the variable list entirely
        btn = QPushButton("Load test volume (64×64×30×5)")
        btn.clicked.connect(self._load_test_data)
        layout.addWidget(btn)

    def _load_test_data(self):
        arr = make_test_volume()
        # Call set_data() directly — skips get_value() / shellwidget completely
        self.viewer.set_data(arr, name="test_volume")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    # Load data immediately on startup so you don't even need to click
    win._load_test_data()
    sys.exit(app.exec_())
