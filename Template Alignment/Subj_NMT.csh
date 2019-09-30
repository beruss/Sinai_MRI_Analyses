#!/bin/tcsh

# affine alignment of individual dataset to D99/NMT/any template
#
# usage:
#    NMT_subject_align.csh dset template_dset [segmentation_dset]
#
# example:
#    tcsh -x NMT_subject_align.csh Puffin_3mar11_MDEFT_500um+orig
#
set atlas_dir = "../.."


setenv AFNI_COMPRESSOR GZIP

set dset = $1
set base = $2
set dfunc = $3

set finalmaster = $dset
 
# get the non-NIFTI name out, dset+orig, dset.nii, dset.nii.gz all -> 'dset'
set dsetprefix = `@GetAfniPrefix $dset`
set dsetprefix = `basename $dsetprefix .gz`
set dsetprefix = `basename $dsetprefix .nii`

set dfuncprefix = `@GetAfniPrefix $dfunc`
set dfuncprefix = `basename $dfuncprefix .gz`
set dfuncprefix = `basename $dfuncprefix .nii`

set origdsetprefix = $dsetprefix
set origdfuncprefix = $dfuncprefix

# which afni view is used even if NIFTI dataset is used as base
# usually +tlrc
set baseview = `3dinfo -av_space $base`

# this fails for AFNI format, but that's okay!
3dcopy $dset $dsetprefix
# get just the first occurrence if both +orig, +tlrc
set dset = ( $dsetprefix+*.HEAD )
set dset = $dset[1]

# put the center of the dataset on top of the center of the template
@Align_Centers -base $base -dset $dset
@Align_Centers -base $base -dset $dfunc 

# keep a copy of the inverse translation too 
# (should just be negation of translation column)
cat_matvec ${dsetprefix}_shft.1D -I > ${dsetprefix}_inv_shft.1D

set origview = `@GetAfniView $dset`
set dset = ${dsetprefix}_shft${origview}
set dsetprefix = `@GetAfniPrefix $dset`
set dfunc = ${dfuncprefix}_shft
set dfuncprefix = `@GetAfniPrefix $dfunc`

# figure out short name for template to insert into output files
echo $base |grep D99
if ($status == 0) then
   set templatename = D99
else
   echo $base | grep NMT
   if ($status == 0) then
      set templatename = NMT
   else
      set templatename = template
   endif
endif
 
# goto apply_warps

# do affine alignment with lpa cost
# using dset as dset2 input and the base as dset1 
# (the base and source are treated differently 
# by align_epi_anats resampling and by 3dAllineate)
align_epi_anat.py -dset2 $dset -dset1 $base -overwrite -dset2to1 \
    -giant_move -suffix _al2std -dset1_strip None -dset2_strip None
#
## put affine aligned data on template grid
# similar to al2std dataset but with exactly same grid
3dAllineate -1Dmatrix_apply ${dsetprefix}_al2std_mat.aff12.1D \
    -prefix ${dsetprefix}_aff -base $base -master BASE         \
    -source $dset -overwrite
    
3dAllineate -1Dmatrix_apply ${dsetprefix}_al2std_mat.aff12.1D \
    -prefix ${dfuncprefix}_aff -base $base -master SOURCE         \
    -source $dfunc -overwrite
    

#exit


# nonlinear alignment of affine skullstripped dataset to template
#  by default,the warp and the warped dataset are computed
#  by using "-qw_opts ", one could save the inverse warp and do extra padding
#  with -qw_opts '-iwarp -expad 30'
# change qw_opts to remove max_lev 2 for final   ********************
rm -rf awpy_${dsetprefix}
auto_warp.py -base $base -affine_input_xmat ID -qworkhard 0 2 \
   -input ${dsetprefix}_aff${baseview} -overwrite \
   -output_dir awpy_${dsetprefix} -qw_opts -iwarp


apply_warps:
# the awpy has the result dataset, copy the warped data, the warp, inverse warp
# don´t copy the warped dataset - combine the transformations instead below
# cp awpy_${dsetprefix}/${dsetprefix}_aff.aw.nii ./${dsetprefix}_warp2std.nii
cp awpy_${dsetprefix}/anat.un.qw_WARP.nii ${dsetprefix}_WARP.nii
cp awpy_${dsetprefix}/anat.un.qw_WARPINV.nii ${dsetprefix}_WARPINV.nii

# if the datasets are compressed, then copy those instead
# note - not using the autowarped dataset, just the WARP
#  see 3dNwarpApply just below
# cp awpy_${dsetprefix}/${dsetprefix}_aff.aw.nii.gz ./${dsetprefix}_warp2std.nii.gz
cp awpy_${dsetprefix}/anat.un.qw_WARP.nii.gz  ./${dsetprefix}_WARP.nii.gz

# compress these copies (if not already compressed)
# gzip -f ${dsetprefix}_warp2std.nii ${dsetprefix}_WARP.nii
gzip -f ${dsetprefix}_WARP.nii ${dsetprefix}_WARPINV.nii

# combine nonlinear and affine warps for dataset warped to standard template space
#   **** mod - DRG 07 Nov 2016
3dNwarpApply -prefix ${origdsetprefix}_warp2std.nii.gz                      \
   -nwarp "${dsetprefix}_WARP.nii.gz ${dsetprefix}_al2std_mat.aff12.1D" \
   -source $dset -master $base
 
echo  ${dfunc}

3dNwarpApply -prefix ${origdfuncprefix}_warp2std.nii.gz                      \
   -nwarp "${dsetprefix}_WARP.nii.gz ${dsetprefix}_al2std_mat.aff12.1D" \
   -source ${dfunc}.nii