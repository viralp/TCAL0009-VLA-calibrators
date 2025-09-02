import os
import sys
import shutil
import datetime
from casatools import msmetadata,quanta
import numpy as np

# --- INPUTS ---
orig_vis = "TCAL0009.sb41718421.eb43662710.60002.10992430555.ms"
bands_to_process = ['L', 'S', 'C', 'X', 'KU', 'K' 'KA', 'Q']
intent_add = True


###################################################################################################
# --- Get polarization models ---
def get_polmodel(band, calibrator):
    bands = {
        "L": "1.5GHz",
        "S": "3.0GHz",
        "C": "6.0GHz",
        "X": "10.0GHz",
        "KU": "15.0GHz",
        "K": "22.25GHz",
        "KA": "33.25GHz",
        "Q": "45.0GHz",
    }
    reffreq = bands[band]

    C286 = ["1331+305=3C286", "3C286", "J1331+3030"]
    C138 = ["0521+166=3C138", "3C138", "J0521+1638"]
    C48 = ["0137+331=3C48", "3C48", "J0137+3309"]

    if calibrator in C286:
        I = [2.5434, 0, 0, 0]
        alpha = [-0.74030, -0.03580, 0.03579]
        if band in ["L", "S", "C"]:
            polfrac = [-0.11966016, -1.76647531, -4.64698442, -5.26759862, -2.20039541]
            polangle = [0.65428857, 0.22391022, 0.15916857, -0.03838797, -0.05162862]
        else:
            polfrac = [0.12712041, 0.00912118, -0.00207942, 0.00178416]
            polangle = [0.610752, 0.04614, 0.000383, -0.02358]

        if band == "Q":
            polangle = [0.60875694, 0.07652591, -0.05288407]

        reffreq = "22GHz"

    elif calibrator in C138:
        if band in ["L", "S", "C"]:
            I = [5.471, 0, 0, 0]
            alpha = [-0.6432, -0.082]
            reffreq = "3GHz"
            polfrac = [0.10122, 0.01389, -0.03738, 0.0471, -0.0200]
            polangle = [-0.17557, -0.0163, 0.013, -0.0057]
        else:
            print("ERROR: No polarization model for 3C138 available!")
            sys.exit()

    elif calibrator in C48:
        I = [1.3140, 0, 0, 0]
        alpha = [-0.7546, 0.341979, 0.284538, 0.0801816, 0.0092876]
        reffreq = "25GHz"
        polfrac = [0.0684, 0.0117, -0.0244, -0.0651, -0.0098, 0.1004]
        if band in ["L", "S"]:
            polangle = [2895.99, 10158.55, 11865.53, 4617.47]
        elif band == "C":
            polangle = [125.35, 509.91, 683.44, 304.68]
        else:
            polangle = [-1.2368, -0.3050, 0.00438, 0.05188]

    return reffreq, I, alpha, polfrac, polangle

if intent_add == True:
    target_fields = ["J1800+7828","J1419+5423","0137+331=3C48","0542+498=3C147","J2355+4950","J0813+4813","J0713+4349",
                 "J0437+2940","J0217+7349","1411+522=3C295","J1153+8058","J0319+4130","0521+166=3C138","1331+305=3C286"]

    # === calibration intents to look for ===
    intselect = [
        "CALIBRATE_AMPLI",
        "CALIBRATE_PHASE",
        "CALIBRATE_BANDPASS",
        "CALIBRATE_FLUX",
        "CALIBRATE_POL_ANGLE",
        "CALIBRATE_POL_LEAKAGE"
    ]
    intent_to_add = "OBSERVE_TARGET#UNSPECIFIED"

    # === STEP 1: Open STATE table ===
    tb.open(orig_vis + "/STATE", nomodify=False)
    obs_modes = tb.getcol("OBS_MODE")

    updated = 0
    for i in range(len(obs_modes)):
        intents = obs_modes[i].split(",")
        # check if this state has any of the calibration intents
        if any(any(sel in intent for sel in intselect) for intent in intents):
            if intent_to_add not in intents:
                intents.append(intent_to_add)
                new_intent = ",".join(sorted(set(intents)))
                tb.putcell("OBS_MODE", i, new_intent)
                print(f"Updated OBS_MODE in STATE row {i}: {new_intent}")
                updated += 1

    tb.close()
    print("Done. Total STATE rows updated:", updated)

###################################################################################################
# --- Step 1: Extract observation date ---
msmd = msmetadata()
msmd.open(orig_vis)
timerange = msmd.timerangeforobs(0)
mjd_start = timerange['begin']['m0']['value']
qa = quanta()
sec_start = qa.quantity(mjd_start, 'd')
date_str = qa.time(sec_start, form='ymd', prec=0)[0].replace('/', '-')
date_str = '-'.join(date_str.split('-')[0:3])
msmd.close()
print(f"Observation date: {date_str}")

tb = table()
tb.open(orig_vis + "/ANTENNA")
# Get antenna positions (in meters, ITRF XYZ coordinates)
positions = tb.getcol("POSITION").transpose()  # shape (nant, 3)
tb.close()
# Compute all baseline lengths
baselines = []
for i in range(len(positions)):
    for j in range(i+1, len(positions)):
        d = np.linalg.norm(positions[i] - positions[j])
        baselines.append(d)
max_baseline = max(baselines) / 1000.0  # km
# Rough VLA config classification
if max_baseline > 20:
    config = "A"
elif max_baseline > 6:
    config = "B"
elif max_baseline > 2:
    config = "C"
else:
    config = "D"


# --- Step 2: Create date folder and move MS there ---
date_dir = os.path.join(os.getcwd(), date_str)
os.makedirs(date_dir, exist_ok=True)

new_ms_path = os.path.join(date_dir, os.path.basename(orig_vis))
if not os.path.exists(new_ms_path):
    print(f"Moving {orig_vis} → {new_ms_path}")
    shutil.move(orig_vis, new_ms_path)
else:
    print(f"{new_ms_path} already exists, skipping move.")

orig_vis = new_ms_path
project_prefix = os.path.splitext(os.path.basename(orig_vis))[0]

###################################################################################################
# --- Step 3: Group SPWs by band ---
msmd = msmetadata()
msmd.open(orig_vis)
spwnames = msmd.namesforspws()
angle = msmd.fieldsforintent("*CALIBRATE_POL_ANGLE*")[0]
angle_cal = [angle, msmd.namesforfields(angle)[0]]
intents = msmd.intents()

if "OBSERVE_TARGET#UNSPECIFIED" in intents:
    intselect = '*CALIBRATE_AMPLI*,*CALIBRATE_PHASE*,*CALIBRATE_BANDPASS*,*CALIBRATE_FLUX*,*CALIBRATE_POL_ANGLE*,*OBSERVE_TARGET*,*CALIBRATE_POL_LEAKAGE*'
else:
    intselect = '*CALIBRATE_AMPLI*,*CALIBRATE_PHASE*,*CALIBRATE_BANDPASS*,*CALIBRATE_FLUX*,*CALIBRATE_POL_ANGLE*,*CALIBRATE_POL_LEAKAGE*'

intselect = [
    '*CALIBRATE_AMPLI*',
    '*CALIBRATE_PHASE*',
    '*CALIBRATE_BANDPASS*',
    '*CALIBRATE_FLUX*',
    '*CALIBRATE_POL_ANGLE*',
    '*CALIBRATE_POL_LEAKAGE*'
]

# Collect fields that match any of these intents
kept_fields = set()
for intent in intselect:
    fields = msmd.fieldsforintent(intent)
    kept_fields.update(fields)

# Convert to sorted list
kept_fields = sorted(kept_fields)

# Convert to string
kept_fields_str = ",".join(map(str, kept_fields))

msmd.close()

skip_spws = {"C": ["0", "1"], "X": ["34", "35"]}
band_map = {}
for s in spwnames:
    band = s.split("#")[0].replace("EVLA_", "")
    spw_id = s.split("#")[-1]
    if band in skip_spws and spw_id in skip_spws[band]:
        continue
    band_map.setdefault(band, []).append(spw_id)

###################################################################################################
# --- Step 4: Process each band inside date_dir ---
main_dir = date_dir

if os.path.exists(os.path.join(main_dir, "calibrators.ms")):
    print("Found calibrators.ms, removing...")
    shutil.rmtree(os.path.join(main_dir, "calibrators.ms"))

for band, spw_ids in band_map.items():
    if band not in bands_to_process:
        continue

    outdir = os.path.join(main_dir, band, f"{project_prefix}_{band}")
    os.makedirs(outdir, exist_ok=True)
    print(f"\n Working in {outdir}")

    out_ms = os.path.join(outdir, f"{project_prefix}_{band}.ms")
    if not os.path.exists(out_ms):
        print(f"--- Splitting {band} band ({','.join(spw_ids)}) ---")
        mstransform(vis=orig_vis,
                    outputvis=out_ms,
                    #intent=intselect,
                    field=kept_fields_str,
                    spw=",".join(spw_ids),
                    hanning=True,
                    reindex=True,
                    keepflags=False,
                    datacolumn="data")
    else:
        print(f"MS already exists: {out_ms}")

    # --- Run CASA pipeline ---
    os.chdir(outdir)
    msfile = out_ms
    reffreq, I, alpha, polfrac, polangle = get_polmodel(band, angle_cal[1])
    I0=I[0]
    context = h_init()
    context.set_state('ProjectSummary', 'observatory', 'Karl G. Jansky Very Large Array')
    context.set_state('ProjectSummary', 'telescope', 'EVLA')

    try:
        hifv_importdata(vis=[msfile])
        hifv_hanning()
        hifv_flagdata(hm_tbuff='1.5int', fracspw=0.01,
                      intents='*POINTING*,*FOCUS*,*ATMOSPHERE*,*SIDEBAND_RATIO*,*UNKNOWN*,*SYSTEM_CONFIGURATION*,*UNSPECIFIED#UNSPECIFIED*')
        hifv_vlasetjy()
        hifv_priorcals(show_tec_maps=False)
        hifv_syspower()
        hifv_testBPdcals()
        hifv_checkflag(checkflagmode='bpd-vla')
        hifv_semiFinalBPdcals()
        hifv_checkflag(checkflagmode='allcals-vla')
        hifv_solint()
        hifv_fluxboot()
        hifv_finalcals()

        setjy(vis=msfile, field=angle_cal[1], spw='', intent="*CALIBRATE_POL_ANGLE*",
              standard="manual", fluxdensity=[I0, 0, 0, 0], spix=alpha,
              reffreq=reffreq, polindex=polfrac, polangle=polangle,
              rotmeas=0, usescratch=True)

        hifv_circfeedpolcal(run_setjy=False)
        hifv_applycals()
        hifv_checkflag(checkflagmode='target-vla')
        hifv_statwt()
        hifv_plotsummary()
        hif_makeimlist(intent='PHASE,BANDPASS', specmode='cont')
        hif_editimlist(stokes='IQUV')
        hif_makeimages(hm_masking='centralregion')
        hifv_exportdata()

        hifv_flagtargetsdata()
        hif_mstransform()
        hif_checkproductsize(maxcubesize=20.0, maxcubelimit=40.0, maxproductsize=100.0)
        hif_makeimlist(specmode='cube', datatype='regcal')
        hif_editimlist(stokes='IQUV')
        hif_makeimages(hm_cyclefactor=3.0)
        hif_selfcal()
        hif_makeimlist(specmode='cont', datatype='selfcal')
        hif_editimlist(stokes='IQUV')
        hif_makeimages(hm_cyclefactor=3.0)
        hif_checkproductsize(maxcubesize=20.0, maxcubelimit=40.0, maxproductsize=100.0)
        hif_makeimlist(specmode='cube', datatype='selfcal')
        hif_editimlist(stokes='IQUV')
        hif_makeimages(hm_cyclefactor=3.0)
        hifv_exportdata(pipelinemode="automatic")

    finally:
        h_save()

    os.chdir(main_dir)

print("\n All bands processed sequentially inside", date_dir)

