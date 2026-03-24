![Version](https://img.shields.io/github/v/release/daniuher/spyder-volume-viewer)
![Status](https://img.shields.io/badge/status-alpha-orange)
![License](https://img.shields.io/github/license/daniuher/spyder-volume-viewer)


# spyder-volume-viewer
Spyder plugin for viewing 2D, 3D, and 4D numpy arrays during scripting. The goal is to eliminate the need to constantly save a temporary .nii just to look at it in standalone viewers. 

This is a **work in progress**. First stable release (version 1.0.0) is planned for April 2026.

### Limitations
- Development on Linux (Debian 12), untested on other OS
- v0.1.0 is for Spyder 5, most likely not working in Spyder 6

### Functionalities
[x] view 2D [x], 3D [x], and 4D [x] numpy arrays which are currently loaded in the variable explorer
[x] numpy arrays with the same dimensions as the main viewed image can be loaded as overlays
[x] scrolling using mouse wheel through the z-axis
[x] scrolling using UP and DOWN arrow keys through the z-axis
[x] scrolling through the volumes (4th dim) using LEFT and RIGHT arrow keys
[ ] error fixes needed (there's quite a few ... )
[ ] unload the viewed image (currently only overlay can be removed)
[ ] possibility to change the axis of visualization so that separete permute within script is not required
[ ] slider for opacity of overlay
[ ] implementation for Spyder 6

### Sneek peak
![Volume viewer (dockable plugin)](screenshots/spyder-volume-viewer_example_dark.png)
Volume viewer (dockable Spyder plugin). Allows to view and scroll through multi-dimensional numpy arrays during scripting.

<table>
  <tr>
    <td><img src="screenshots/spyder-volume-viewer_example_dark_nooverlay.png" width="350"/></td>
    <td><img src="screenshots/spyder-volume-viewer_example_dark_withoverlay.png" width="350"/></td>
  </tr>
</table>




