# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2026, fried-pineapple0
#
# Licensed under the terms of the GNU General Public License v3
# ----------------------------------------------------------------------------
"""
VolumeViewer Plugin.
"""

# Third-party imports
from qtpy.QtGui import QIcon

# Spyder imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation

# Local imports
from volumeviewer.spyder.confpage import VolumeViewerConfigPage
from volumeviewer.spyder.widgets import VolumeViewerWidget

_ = get_translation("volumeviewer.spyder")


class VolumeViewer(SpyderDockablePlugin):
    """
    VolumeViewer plugin.
    """

    NAME = "volumeviewer"
    REQUIRES = [Plugins.IPythonConsole]
    OPTIONAL = []
    
    # If it is a SpyderDockablePlugin you should set a constant class named WIDGET_CLASS with an instance of PluginMainWidget.
    WIDGET_CLASS = VolumeViewerWidget
    
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = VolumeViewerConfigPage

    # --- Signals

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("VolumeViewer")

    def get_description(self):
        return _("A dockable Spyder plugin to view 3D and 4D numpy arrays or NIFTI images.")

    def get_icon(self):
        return QIcon()

    def on_initialize(self):
        widget = self.get_widget()
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        
        # Connect to the signal that fires when tabs are switched or created
        ipyconsole.sig_shellwidget_changed.connect(widget.set_shellwidget)
        
        # Get the currently active shell immediately if it exists
        current_sw = ipyconsole.get_current_shellwidget()
        # print(dir(current_sw))
        if current_sw is not None:
            widget.set_shellwidget(current_sw)    

    def check_compatibility(self):
        valid = True
        message = ""  # Note: Remember to use _("") to localize the string
        return valid, message

    def on_close(self, cancellable=True):
        return True

    # --- Public API
    # ------------------------------------------------------------------------
