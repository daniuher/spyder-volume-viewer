# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2026, fried-pineapple0
#
# Licensed under the terms of the GNU General Public License v3
# ----------------------------------------------------------------------------
"""
VolumeViewer Preferences Page.
"""
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import get_translation

_ = get_translation("volumeviewer.spyder")


class VolumeViewerConfigPage(PluginConfigPage):

    # --- PluginConfigPage API
    # ------------------------------------------------------------------------
    def setup_page(self):
        pass
