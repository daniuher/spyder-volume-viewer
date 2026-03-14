#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  8 18:25:06 2026

@author: duher
"""

import nibabel as nib
import numpy as np
import os

datapath = '/home/duher/Downloads/dv26_x250/nifti/'
dat = nib.load(os.path.join(datapath, 'hm_fg_mp2_0p6_cs4_6000_aon_fastwe_filt_UNI-DEN_22.nii'))

im = dat.get_fdata()

im_new = np.rot90(np.rot90(im))

im_mask = nib.load(os.path.join(datapath, 't1w_brainmask.nii.gz')).get_fdata()>0
im_mask = im_mask.astype(int)

#%% 
a = 1
a = np.array([1])

slc = im_new[:,:,240]
