#!/usr/bin/python

##
# \file run_tests.py
# \brief      main-file to run specified unit tests
#
# \author     Michael Ebner (michael.ebner.14@ucl.ac.uk)
# \date       September 2015
#


# Import libraries
import unittest
import sys
import os

from brain_stripping_test import *
from case_study_fetal_brain_test import *
from cpp_itk_registration_test import *
from data_reader_test import *
from image_similarity_evaluator_test import *
from intensity_correction_test import *
from intra_stack_registration_test import *
from linear_operators_test import *
from niftyreg_test import *
from parameter_normalization_test import *
from registration_test import *
from residual_evaluator_test import *
from segmentation_propagation_test import *
from simulator_slice_acquisition_test import *
from stack_test import *

if __name__ == '__main__':
    print("\nUnit tests:\n--------------")
    unittest.main()
