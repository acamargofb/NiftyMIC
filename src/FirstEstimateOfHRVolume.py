## \file FirstEstimateOfHRVolume.py
#  \brief Compute first estimate of HR volume based on given stacks
# 
#  \author Michael Ebner (michael.ebner.14@ucl.ac.uk)
#  \date November 2015
#  \version{0.1} Estimate first HR volume based on averaging stacks, Nov 2015
#  \version{0.2} Add possibility to not register stacks to target first, March 2016


## Import libraries
import os                       # used to execute terminal commands in python
import sys
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt

## Import modules from src-folder
import SimpleITKHelper as sitkh
import InPlaneRigidRegistration as iprr
import Stack as st


## Class to compute first estimate of HR volume. Steps included are:
#  -# In-plane registration of all stacks (optional)
#  -# (Resample in-plane registered stacks to 3D-volumes)
#  -# Pick one (planarly-aligned) stack and assign it as target volume
#  -# Resample target volume on isotropic grid
#  -# Register all (planarly-aligned) stacks to target-volume (optional)
#  -# Create first HR volume estimate: Average all registered planarly-aligned stacks
#  -# Update all slice transformations: Each slice position gets updated according to alignment with HR volume
class FirstEstimateOfHRVolume:

    ## Constructor
    #  \param[in] stack_manager instance of StackManager containing all stacks and additional information
    #  \param[in] filename_reconstructed_volume chosen filename for created HR volume, Stack object
    #  \param[in] target_stack_number stack chosen to define space and coordinate system of HR reconstruction, integer
    def __init__(self, stack_manager, filename_reconstructed_volume, target_stack_number):
        self._stack_manager = stack_manager
        self._stacks = stack_manager.get_stacks()
        self._N_stacks = stack_manager.get_number_of_stacks()

        self._target_stack_number = target_stack_number
        self._HR_volume = None

        self._filename_reconstructed_volume = filename_reconstructed_volume

        self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate = False
        self._flag_register_stacks_before_initial_volume_estimate = False


    ## Set flag to use in-plane of all slices to each other within their stacks
    def use_in_plane_registration_for_initial_volume_estimate(self, flag):
        self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate = flag


    ## Set flag to globally register each stack with chosen target stack.
    #  Otherwise, the initial positions as given from the original files are used
    def register_stacks_before_initial_volume_estimate(self, flag):
        self._flag_register_stacks_before_initial_volume_estimate = flag


    ## Execute computation for first estimate of HR volume.
    #  This function steers the estimation of first HR volume which then updates
    #  self._HR_volume
    #  The process consists of several steps:
    #  -# In-plane registration of all stacks (optional)
    #  -# (Resample in-plane registered stacks to 3D-volumes)
    #  -# Pick one (planarly-aligned) stack and assign it as target volume
    #  -# Resample target volume on isotropic grid
    #  -# Register all (planarly-aligned) stacks to target-volume (optional)
    #  -# Create first HR volume estimate: Average all registered planarly-aligned stacks
    #  -# Update all slice transformations: Each slice position gets updated according to alignment with HR volume
    # \param[in] use_in_plane_registration states whether in-plane registration is used prior registering (bool)
    def compute_first_estimate_of_HR_volume(self):

        ## Use stacks with in-plane aligned slices
        if self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate:
            print("In-plane alignment of slices within each stack is performed")
            ## Run in-plane rigid registration of all stacks
            in_plane_rigid_registration =  iprr.InPlaneRigidRegistration(self._stack_manager)

            ## Get resampled stacks of planarly aligned slices as Stack objects (3D volume)
            stacks = in_plane_rigid_registration.get_resampled_planarly_aligned_stacks() # with in-plane alignment

        ## Use "raw" stacks as given by their originally given physical positions
        else:
            print("In-plane alignment of slices within each stack is NOT performed")
            stacks = self._stacks 

        ## Resample chosen target volume and its mask to isotropic grid
        ## \todo replace self._target_stack_number with "best choice" of stack
        self._HR_volume = self._get_isotropically_resampled_stack(stacks[self._target_stack_number])

        ## If desired: Register all (planarly) aligned stacks to resampled target volume
        if self._flag_register_stacks_before_initial_volume_estimate:
            print("Rigid registration between each stack and target is performed")
            rigid_registrations = self._rigidly_register_all_stacks_to_HR_volume(print_trafos=False)
        
        ## No rigid registration, i.e. set to identity
        else:
            print("Rigid registration between each stack and target is NOT performed")
            rigid_registrations = [sitk.Euler3DTransform()] * self._N_stacks

        ## Update HR volume: Compute average of all (registered) stacks
        self._update_estimate_of_HR_volume(stacks, rigid_registrations)

        ## Update all slice transformations of each stack according to rigid alignment with HR volume
        self._update_slice_transformations(rigid_registrations)


    ## Get first estimation of the HR volume.
    #  \return Stack of HR volume
    def get_first_estimate_of_HR_volume(self):
        try:
            if self._HR_volume is None:
                raise ValueError("Error: First estimate of HR volume has not been computed yet.")

            else:
                return self._HR_volume

        except ValueError as err:
            print(err.message)


    ## Resample stack to isotropic grid
    #  The image and its mask get resampled to isotropic grid 
    #  (in-plane resolution also in through-plane direction)
    #  \param[in] target_stack Stack being resampled
    #  \return Isotropically resampled Stack
    def _get_isotropically_resampled_stack(self, target_stack):
        
        ## Read original spacing (voxel dimension) and size of target stack:
        spacing = np.array(target_stack.sitk.GetSpacing())
        size = np.array(target_stack.sitk.GetSize())

        ## Update information according to isotropic resolution
        size[2] = np.round(spacing[2]/spacing[0]*size[2])
        spacing[2] = spacing[0]

        ## Resample image and its mask to isotropic grid
        default_pixel_value = 0.0

        HR_volume_sitk =  sitk.Resample(
            target_stack.sitk, 
            size, 
            sitk.Euler3DTransform(), 
            sitk.sitkNearestNeighbor, 
            target_stack.sitk.GetOrigin(), 
            spacing,
            target_stack.sitk.GetDirection(),
            default_pixel_value,
            target_stack.sitk.GetPixelIDValue())

        HR_volume_sitk_mask =  sitk.Resample(
            target_stack.sitk_mask, 
            size, 
            sitk.Euler3DTransform(), 
            sitk.sitkNearestNeighbor, 
            target_stack.sitk.GetOrigin(), 
            spacing,
            target_stack.sitk.GetDirection(),
            default_pixel_value,
            target_stack.sitk.GetPixelIDValue())

        ## Create Stack instance of HR_volume
        HR_volume = st.Stack.from_sitk_image(HR_volume_sitk, self._filename_reconstructed_volume)
        HR_volume.add_mask(HR_volume_sitk_mask)

        return HR_volume


    ## Register all stacks to chosen target stack (HR volume)
    #  \return list of rigid registrations (sitk.Euler3DTransform objects) 
    #  for each given stack
    def _rigidly_register_all_stacks_to_HR_volume(self, print_trafos=False):

        ## Allocate list
        rigid_registrations = [None]*self._N_stacks

        ## Compute rigid registrations aligning each stack with the HR volume
        for i in range(0, self._N_stacks):
            rigid_registrations[i] = self._get_rigid_registration_transform_3D_sitk(self._stacks[i], self._HR_volume)

            ## Print rigid registration results (optional)
            if print_trafos:
                sitkh.print_rigid_transformation(rigid_registrations[i])

        return rigid_registrations


    ## Rigid registration routine based on SimpleITK
    #  \param[in] fixed_3D fixed Stack representing acquired stacks
    #  \param[in] moving_3D moving Stack representing current HR volume estimate
    #  \param[in] display_registration_info display registration summary at the end of execution (default=0)
    #  \return Rigid registration as sitk.Euler3DTransform object
    def _get_rigid_registration_transform_3D_sitk(self, fixed_3D, moving_3D, display_registration_info=0):

        ## Instantiate interface method to the modular ITKv4 registration framework
        registration_method = sitk.ImageRegistrationMethod()

        ## Select between using the geometrical center (GEOMETRY) of the images or using the center of mass (MOMENTS) given by the image intensities
        initial_transform = sitk.CenteredTransformInitializer(fixed_3D.sitk, moving_3D.sitk, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.GEOMETRY)

        # initial_transform = sitk.Euler3DTransform()

        ## Set the initial transform and parameters to optimize
        registration_method.SetInitialTransform(initial_transform)

        ## Set an image masks in order to restrict the sampled points for the metric
        # registration_method.SetMetricFixedMask(fixed_3D.sitk_mask)
        # registration_method.SetMetricMovingMask(moving_3D.sitk_mask)

        ## Set percentage of pixels sampled for metric evaluation
        # registration_method.SetMetricSamplingStrategy(registration_method.NONE)

        ## Set interpolator to use
        registration_method.SetInterpolator(sitk.sitkLinear)

        """
        similarity metric settings
        """
        ## Use normalized cross correlation using a small neighborhood for each voxel between two images, with speed optimizations for dense registration
        # registration_method.SetMetricAsANTSNeighborhoodCorrelation(radius=5)
        
        ## Use negative normalized cross correlation image metric
        # registration_method.SetMetricAsCorrelation()

        ## Use demons image metric
        # registration_method.SetMetricAsDemons(intensityDifferenceThreshold=1e-3)

        ## Use mutual information between two images
        # registration_method.SetMetricAsJointHistogramMutualInformation(numberOfHistogramBins=100, varianceForJointPDFSmoothing=3)
        
        ## Use the mutual information between two images to be registered using the method of Mattes2001
        registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=100)

        ## Use negative means squares image metric
        # registration_method.SetMetricAsMeanSquares()
        
        """
        optimizer settings
        """
        ## Set optimizer to Nelder-Mead downhill simplex algorithm
        # registration_method.SetOptimizerAsAmoeba(simplexDelta=0.1, numberOfIterations=100, parametersConvergenceTolerance=1e-8, functionConvergenceTolerance=1e-4, withStarts=false)

        ## Conjugate gradient descent optimizer with a golden section line search for nonlinear optimization
        # registration_method.SetOptimizerAsConjugateGradientLineSearch(learningRate=1, numberOfIterations=100, convergenceMinimumValue=1e-8, convergenceWindowSize=10)

        ## Set the optimizer to sample the metric at regular steps
        # registration_method.SetOptimizerAsExhaustive(numberOfSteps=50, stepLength=1.0)

        ## Gradient descent optimizer with a golden section line search
        # registration_method.SetOptimizerAsGradientDescentLineSearch(learningRate=1, numberOfIterations=100, convergenceMinimumValue=1e-6, convergenceWindowSize=10)

        ## Limited memory Broyden Fletcher Goldfarb Shannon minimization with simple bounds
        # registration_method.SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, numberOfIterations=500, maximumNumberOfCorrections=5, maximumNumberOfFunctionEvaluations=200, costFunctionConvergenceFactor=1e+7)

        ## Regular Step Gradient descent optimizer
        registration_method.SetOptimizerAsRegularStepGradientDescent(learningRate=0.5, minStep=0.05, numberOfIterations=2000)

        ## Estimating scales of transform parameters a step sizes, from the maximum voxel shift in physical space caused by a parameter change
        ## (Many more possibilities to estimate scales)
        registration_method.SetOptimizerScalesFromPhysicalShift()
        
        """
        setup for the multi-resolution framework            
        """
        ## Set the shrink factors for each level where each level has the same shrink factor for each dimension
        registration_method.SetShrinkFactorsPerLevel(shrinkFactors = [4,2,1])

        ## Set the sigmas of Gaussian used for smoothing at each level
        registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2,1,0])

        ## Enable the smoothing sigmas for each level in physical units (default) or in terms of voxels (then *UnitsOff instead)
        registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

        ## Connect all of the observers so that we can perform plotting during registration
        # registration_method.AddCommand(sitk.sitkStartEvent, start_plot)
        # registration_method.AddCommand(sitk.sitkEndEvent, end_plot)
        # registration_method.AddCommand(sitk.sitkMultiResolutionIterationEvent, update_multires_iterations) 
        # registration_method.AddCommand(sitk.sitkIterationEvent, lambda: plot_values(registration_method))

        # print('  Final metric value: {0}'.format(registration_method.GetMetricValue()))
        # print('  Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))
        # print("\n")

        ## Execute 3D registration
        final_transform_3D_sitk = registration_method.Execute(fixed_3D.sitk, moving_3D.sitk) 

        if display_registration_info:
            print("SimpleITK Image Registration Method:")
            print('  Final metric value: {0}'.format(registration_method.GetMetricValue()))
            print('  Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))

        return sitk.Euler3DTransform(final_transform_3D_sitk)


    ## Compute average of all registered stacks and update self._HR_volume
    #  \param[in] stacks_planarly_aligned stacks (type Stack) containing planarly aligned slices
    #  \param[in] rigid_registrations registrations (type sitk.Euler3DTransform) aligning the stacks with the HR volume
    #  \post self._HR_volume is overwritten with new estimate
    def _update_estimate_of_HR_volume(self, stacks_planarly_aligned, rigid_registrations):

        default_pixel_value = 0.0

        ## Define helpers to obtain averaged stack
        shape = sitk.GetArrayFromImage(self._HR_volume.sitk).shape
        array = np.zeros(shape)
        array_mask = np.zeros(shape)
        ind = np.zeros(shape)

        ## Average over domain specified by the joint mask ("union mask")
        for i in range(0,self._N_stacks):
            ## Resample warped stacks
            stack_sitk =  sitk.Resample(
                stacks_planarly_aligned[i].sitk,
                self._HR_volume.sitk, 
                rigid_registrations[i], 
                sitk.sitkLinear, 
                default_pixel_value,
                self._HR_volume.sitk.GetPixelIDValue())

            ## Resample warped stack masks
            stack_sitk_mask =  sitk.Resample(
                stacks_planarly_aligned[i].sitk_mask,
                self._HR_volume.sitk, 
                rigid_registrations[i], 
                sitk.sitkNearestNeighbor, 
                default_pixel_value,
                stacks_planarly_aligned[i].sitk_mask.GetPixelIDValue())

            ## Get arrays of resampled warped stack and mask
            array_tmp = sitk.GetArrayFromImage(stack_sitk)
            array_mask_tmp = sitk.GetArrayFromImage(stack_sitk_mask)

            ## Sum intensities of stack and mask
            array += array_tmp
            array_mask += array_mask_tmp

            ## Store indices of voxels with non-zero contribution
            ind[np.nonzero(array_tmp)] += 1

        ## Average over the amount of non-zero contributions of the stacks at each index
        ind[ind==0] = 1                 # exclude division by zero
        array = np.divide(array,ind.astype(float))    # elemenwise division

        ## Create (joint) binary mask. Mask represents union of all masks
        array_mask[array_mask>0] = 1

        ## Set pixels of the image not specified by the mask to zero
        array[array_mask==0] = 0

        ## Update HR volume (sitk image)
        helper = sitk.GetImageFromArray(array)
        helper.CopyInformation(self._HR_volume.sitk)
        self._HR_volume.sitk = helper

        ## Update HR volume (sitk image mask)
        helper = sitk.GetImageFromArray(array_mask)
        helper.CopyInformation(self._HR_volume.sitk_mask)
        self._HR_volume.sitk_mask = helper


    ## Update all slice transformations of each stack given the rigid transformations
    #  computed to align each stack with the HR volume
    #  \param[in] rigid_registrations list of rigid registrations 
    #             (sitk.Euler3DTransform objects) to align stack with HR volume
    def _update_slice_transformations(self, rigid_registrations):

        for i in range(0, self._N_stacks):
            stack = self._stacks[i]

            ## Rigid transformation to align stack i with target (HR volume)
            T = rigid_registrations[i]

            for j in range(0, stack.get_number_of_slices()):
                slice = stack._slices[j]
                
                ## Trafo from physical origin to origin of slice j
                slice_trafo = slice.get_affine_transform()

                ## New affine transform of slice j with respect to rigid registration
                affine_transform = sitkh.get_composited_sitk_affine_transform(T, slice_trafo)

                ## Update affine transform of slice j
                slice.set_affine_transform(affine_transform)

