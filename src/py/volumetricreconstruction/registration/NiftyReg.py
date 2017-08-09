# \file NiftyReg.py
# \brief      Class to use registration method NiftyReg
#
# \author     Michael Ebner (michael.ebner.14@ucl.ac.uk)
# \date       Aug 2017


# Import libraries
import os
import numpy as np
import SimpleITK as sitk
from abc import ABCMeta, abstractmethod

import pythonhelper.PythonHelper as ph
import registrationtools.NiftyReg

import volumetricreconstruction.base.Stack as st
from volumetricreconstruction.registration.RegistrationMethod \
    import RegistrationMethod
from volumetricreconstruction.registration.RegistrationMethod \
    import AffineRegistrationMethod


class RegAladin(AffineRegistrationMethod):

    def __init__(self,
                 fixed=None,
                 moving=None,
                 use_fixed_mask=False,
                 use_moving_mask=False,
                 use_verbose=False,
                 options="",
                 registration_type="Rigid",
                 ):

        AffineRegistrationMethod.__init__(self,
                                          fixed=fixed,
                                          moving=moving,
                                          use_fixed_mask=use_fixed_mask,
                                          use_moving_mask=use_moving_mask,
                                          use_verbose=use_verbose,
                                          registration_type=registration_type,
                                          )
        self._options = options

    ##
    # Sets the options used for FLIRT
    # \date       2017-08-08 19:57:47+0100
    #
    # \param      self     The object
    # \param      options  The options as string
    #
    def set_options(self, options):
        self._options = options

    ##
    # Gets the options.
    # \date       2017-08-08 19:58:14+0100
    #
    # \param      self  The object
    #
    # \return     The options as string.
    #
    def get_options(self):
        return self._options

    def _run_registration(self):

        if self._use_fixed_mask:
            fixed_sitk_mask = self._fixed.sitk_mask
        else:
            fixed_sitk_mask = None

        if self._use_moving_mask:
            moving_sitk_mask = self._moving.sitk_mask
        else:
            moving_sitk_mask = None

        options = self._options
        if self._registration_type == "Rigid":
            options += " -rigOnly"

        if not self._use_verbose:
            options += " -voff"

        self._registration_method = registrationtools.NiftyReg.RegAladin(
            fixed_sitk=self._fixed.sitk,
            moving_sitk=self._moving.sitk,
            fixed_sitk_mask=fixed_sitk_mask,
            moving_sitk_mask=moving_sitk_mask,
            options=options,
        )
        self._registration_method.run()

        self._registration_transform_sitk = \
            self._registration_method.get_registration_transform_sitk()


class RegF3D(RegistrationMethod):

    def __init__(self,
                 fixed=None,
                 moving=None,
                 use_fixed_mask=False,
                 use_moving_mask=False,
                 use_verbose=False,
                 options="",
                 ):

        RegistrationMethod.__init__(self,
                                    fixed=fixed,
                                    moving=moving,
                                    use_fixed_mask=use_fixed_mask,
                                    use_moving_mask=use_moving_mask,
                                    use_verbose=use_verbose,
                                    )
        self._options = options

    ##
    # Sets the options used for FLIRT
    # \date       2017-08-08 19:57:47+0100
    #
    # \param      self     The object
    # \param      options  The options as string
    #
    def set_options(self, options):
        self._options = options

    ##
    # Gets the options.
    # \date       2017-08-08 19:58:14+0100
    #
    # \param      self  The object
    #
    # \return     The options as string.
    #
    def get_options(self):
        return self._options

    def _run_registration(self):

        if self._use_fixed_mask:
            fixed_sitk_mask = self._fixed.sitk_mask
        else:
            fixed_sitk_mask = None

        if self._use_moving_mask:
            moving_sitk_mask = self._moving.sitk_mask
        else:
            moving_sitk_mask = None

        options = self._options

        if not self._use_verbose:
            options += " -voff"

        self._registration_method = registrationtools.NiftyReg.RegF3D(
            fixed_sitk=self._fixed.sitk,
            moving_sitk=self._moving.sitk,
            fixed_sitk_mask=fixed_sitk_mask,
            moving_sitk_mask=moving_sitk_mask,
            options=options
        )
        self._registration_method.run()

        self._registration_transform_sitk = \
            self._registration_method.get_registration_transform_sitk()

    ##
    # Gets the warped moving image, i.e. moving image warped and resampled to
    # the fixed grid
    # \date       2017-08-08 16:58:30+0100
    #
    # \param      self  The object
    #
    # \return     The warped moving image as Stack/Slice object
    #
    def get_warped_moving(self):

        warped_moving_mask_sitk = \
            self._registration_method.get_deformed_image_sitk(
                fixed_sitk=self._fixed.sitk_mask,
                moving_sitk=self._moving.sitk_mask,
                interpolation_order=0,
            )

        if isinstance(self._moving, st.Stack):
            warped_moving = st.Stack.from_sitk_image(
                image_sitk=self._registration_method.get_warped_moving_sitk(),
                filename=self._moving.get_filename(),
                image_sitk_mask=warped_moving_mask_sitk
            )
        else:
            warped_moving = sl.Slice.from_sitk_image(
                image_sitk=self._registration_method.get_warped_moving_sitk(),
                filename=self._moving.get_filename(),
                image_sitk_mask=warped_moving_mask_sitk
            )
        return warped_moving