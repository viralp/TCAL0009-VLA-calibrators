# Processing TCAL0009 data with VLA pipeline

TCAL0009 is a VLA calibrators monitoring program. Every month VLA monitors following 14 flux calibrators. It has been observed with all VLA bands L, S, C, X, KU, K, KA, and Q.  Each calibrator is observed for a total integration time of 22 sec and total run time of appx. 2 hrs. It also includes 3C286 as the polarisation (angle) calibrator. This monthly data has been reduced with the special developed casa pipeline. This pipeline generates cubes and stokes I, Q, U and V images per band, per calibrator sources.  We have started to use the standard VLA calibration (https://science.nrao.edu/facilities/vla/data-processing/pipeline) and imaging (https://science.nrao.edu/facilities/vla/data-processing/pipeline/vipl_661_v2) pipelines to reduce and image the calibrators of TCAL0009 program. This pipeline will automatically generate self-calibrated cubes and diagnostic plots. 

TCAL0009 flux calibrators = [ "J1800+7828","J1419+5423","0137+331=3C48","0542+498=3C147","J2355+4950","J0813+4813","J0713+4349",  
                              "J0437+2940","J0217+7349","1411+522=3C295","J1153+8058","J0319+4130","0521+166=3C138","1331+305=3C286"]
## Processing Steps                              
                              
## Download TCAL0009 data from NRAO archive (un-calibrated)

1. Copy data and above script in the same folder.   
2. Execute the script as follows   - 
   1. On NRAO luster system  
   add this line into the sbatch script for single thread job  
   > xvfb-run -d casa-pipe --nogui -c TCAL0009_casa_cal_selfcal.py # this will use the latest pipeline  
   
   add this into the sbatch script for multi thread job (X=no. of cpus to parallelize the process)
   >export CASAPATH=/home/casa/packages/pipeline/casa-6.6.1-17-pipeline-2024.1.1.22/
   >$CASAPATH/bin/mpicasa -n X $CASAPATH/bin/casa --pipeline --nogui -c TCAL0009_casa_cal_selfcal_V4.py
   or 
   2. On other system
   > casa-6.6.1-17-pipeline-2024.1.1.22/bin/casa --pipeline -c TCAL0009_casa_cal_selfcal.py
   One has to edit the script to add the measurement set name with "orig_vis" input parameter.  
3. Users can select the required band to process/image with the "bands_to_process" option. For example, if one wants to process only L and S band data then  
   bands_to_process = ['L', 'S']    
4. In order to image the calibrators, one has to add the "OBSERVE_TARGET#UNSPECIFIED"  intent into the ms. intent_add = True option will do this.  
   It will apply "OBSERVE_TARGET#UNSPECIFIED"  intents to the those fields which have any one of these intents already present:
       intselect = [
        "CALIBRATE_AMPLI",
        "CALIBRATE_PHASE",
        "CALIBRATE_BANDPASS",
        "CALIBRATE_FLUX",
        "CALIBRATE_POL_ANGLE",
        "CALIBRATE_POL_LEAKAGE"
    ]
5. Script will automatically find the date of observation and based on that it will create a YYYY-MM-DD directory and move the original data into it.     
6. From the above created directory, further it will generate directories with different bands, and under each band directory, it will split the ms and copy under it.  
7. It will process each band data under respective directories with standard VLA pipeline.  
8. It will apply all standard calibration steps - setjy, bandpass, gaincal, fluxboot, polcal, etc.  
9. After applying calibration tables, it will split the target calibrators and do imaging and self-calibration with "specmode=cube" in tclean task.   
10. Finally it will copy all output images (in fits format) under the product directory, one level above the band directory.  
   


