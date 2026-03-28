#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  8 18:25:06 2026

@author: duher
"""

import nibabel as nib
import numpy as np
import os

datapath = '/home/duher/Nextcloud/SFB_1436_Serviceprojekt_Z02/duher/00_misc/14_batman_mrtrix/DWI/'
dat = nib.load(os.path.join(datapath, '_DTI_17_Richtungen_2.5mm_96_AP_20180524132459_5.nii'))
imdata = dat.get_fdata()

mask = nib.load(os.path.join(datapath, 'mask.nii'))
maskdata = mask.get_fdata()

b0 = nib.load(os.path.join(datapath, '_DTI_17_Richtungen_2.5mm_96_AP_20180524132459_5_meanb0.nii'))
b0data = b0.get_fdata()

slc = b0data[:,:,30]



