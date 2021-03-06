##
# \file stack_mask_morphological_operations.py
# \brief      { item_description }
#
# \author     Michael Ebner (michael.ebner.14@ucl.ac.uk)
# \date       May 2017
#


import sys
import itk
import numpy as np
import SimpleITK as sitk

import pysitk.simple_itk_helper as sitkh
import pysitk.python_helper as ph

import niftymic.base.stack as st


##
# Class implementing the segmentation propagation from one image to another
# \date       2017-05-10 23:48:08+0100
#
class StackMaskMorphologicalOperations(object):

    ##
    # { constructor_description }
    # \date       2017-05-18 16:58:23+0100
    #
    # \param      self                        The object
    # \param      mask_sitk                   The mask sitk
    # \param      dilation_radius             The dilation radius
    # \param      dilation_kernel             The dilation kernel
    # \param      use_dilation_in_plane_only  The use dilation in plane only
    #
    def __init__(self, dilation_radius, dilation_kernel, use_dilation_in_plane_only):

        self._dilation_radius = dilation_radius
        self._dilation_kernel = dilation_kernel
        self._use_dilation_in_plane_only = use_dilation_in_plane_only

    @classmethod
    def from_sitk_mask(cls, mask_sitk=None, dilation_radius=0, dilation_kernel="Ball", use_dilation_in_plane_only=True):

        self = cls(dilation_radius=dilation_radius, dilation_kernel=dilation_kernel,
                   use_dilation_in_plane_only=use_dilation_in_plane_only)

        self._mask_sitk = mask_sitk
        self._stack = None

        return self

    @classmethod
    def from_stack(cls, stack=None, dilation_radius=0, dilation_kernel="Ball", use_dilation_in_plane_only=True):

        self = cls(dilation_radius=dilation_radius, dilation_kernel=dilation_kernel,
                   use_dilation_in_plane_only=use_dilation_in_plane_only)

        self._mask_sitk = stack.sitk_mask
        self._stack = stack

        return self

    def set_mask_sitk(self, mask_sitk):
        self._mask_sitk = mask_sitk

    def get_mask_sitk(self):
        return self._mask_sitk

    def get_stack(self):
        return st.Stack.from_stack(self._stack)

    def set_dilation_radius(self, dilation_radius):
        self._dilation_radius = dilation_radius

    def get_dilation_radius(self):
        return self._dilation_radius

    def set_dilation_kernel(self, dilation_kernel):
        if dilation_kernel not in ['Ball', 'Box', 'Annulus', 'Cross']:
            raise ValueError(
                "Dilation kernel must be 'Ball', 'Box', 'Annulus' or 'Cross'.")
        self._dilation_kernel = dilation_kernel

    def get_dilation_kernel(self):
        return self._dilation_kernel

    def get_processed_mask_sitk(self):
        return sitk.Image(self._mask_sitk)

    def get_processed_stack(self):
        if self._stack is None:
            raise ValueError("No Stack instance was provided")
        else:
            return st.Stack.from_sitk_image(self._stack.sitk, self._stack.get_filename(), self._mask_sitk)

    def get_computational_time(self):
        return self._computational_time

    def run_dilation(self):

        time_start = ph.start_timing()

        dilater = sitk.BinaryDilateImageFilter()
        dilater.SetKernelType(eval("sitk.sitk" + self._dilation_kernel))
        dilater.SetKernelRadius(self._dilation_radius)

        if self._use_dilation_in_plane_only:

            shape = self._mask_sitk.GetSize()
            N_slices = shape[2]
            nda_mask = np.zeros(shape[::-1], dtype=np.uint8)

            for i in range(0, N_slices):
                slice_mask_sitk = self._mask_sitk[:, :, i:i + 1]
                mask_sitk = dilater.Execute(slice_mask_sitk)
                nda_mask[i, :, :] = sitk.GetArrayFromImage(mask_sitk)

            mask_sitk = sitk.GetImageFromArray(nda_mask)
            mask_sitk.CopyInformation(self._mask_sitk)
            self._mask_sitk = mask_sitk

        else:
            self._mask_sitk = dilater.Execute(self._mask_sitk)

        if self._stack is not None:
            self._stack = st.Stack.from_sitk_image(
                self._stack.sitk,
                image_sitk_mask=self._mask_sitk,
                filename=self._stack.get_filename(),
                slice_thickness=self._stack.get_slice_thickness(),
            )

        self._computational_time = ph.stop_timing(time_start)
