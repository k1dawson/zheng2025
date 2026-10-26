# Data from: Vocal repertoire expansion in singing mice by co-opting a conserved midbrain circuit node

Dataset DOI: [10.5061/dryad.ht76hdrw5](https://doi.org/10.5061/dryad.ht76hdrw5)

## Description of data and file structure

This dataset comprises all data required to reproduce the quantitative analyses and figures presented in the associated manuscript when processed using the accompanying analysis code. Data are organized into `.zip` archives corresponding to individual experiments. Each archive contains a metadata `.csv` file and one or more `.csv` files generated from audio analyses, which include note onset and offset times as well as computed acoustic features. Experiments that incorporate modalities beyond audio additionally include the corresponding processed data files.

### Dataset contents

#### **solo_social.zip**

Data from intact adult singing mice male–female close-range social interactions within the PAIRId paradigm. Two cohorts (each containing three males and two females) were recorded across ten sessions, each lasting five hours, encompassing all opposite-sex dyads (60 hours total).

Included files comprise processed audio vocalization timestamps from the PAIRId assignment algorithm and manual curation, as well as tracked positions of both mice throughout each session in common world coordinates.

The `.zip` contains two metadata files (`solosocial_sessions.csv`, `social_sessions_samples_info.csv`) and three main data directories:

* `08_solosocial/`, `09_solosocial_02/` — *Scotinomys teguina* recordings from solo and social contexts.
* `mmus/` — *Mus musculus* (laboratory mouse) dyad recordings
* `cam_params/` — YAML files containing camera calibration and rig configuration parameters for video alignment and world coordinate reconstruction.

Each *Scotinomys* session folder is named according to the format\
`sessionNumber_date_maleID_femaleID_condition` (e.g., `03_20230921_um006_uf004_mf`) and includes two subcontexts:

* `01_solo/` — recordings from individual animals in acoustic isolated boxes, labelled `top` and `bottom`.
* `02_social/` — recordings from when the mice were allowed to interact within PAIRId, with synchronized video tracking (`process_video)` and multi-microphone audio detections (`process_audio`)

##### File descriptions

* `solosocial_sessions.csv` — Metadata linking each recording session to the corresponding subjects.

  | Column               | Description                                                             |
  | :------------------- | :---------------------------------------------------------------------- |
  | `session`            | Unique session identifier (date + subject IDs)                          |
  | `basepath`           | Filepath                                                                |
  | `mouse_1`, `mouse_2` | Identifiers of the recorded individuals (male and female, respectively) |
* `social_sessions_samples_info.csv` — Summary of total recording frame counts per session, used to relate acoustic and video sample indices

  | Column               | Description                                                      |
  | :------------------- | :--------------------------------------------------------------- |
  | <br />               | Sequential index                                                 |
  | `session_id`         | Session identifier matching entries in `solosocial_sessions.csv` |
  | `audio_total_frames` | Total number of frames in the processed audio data               |
  | `video_total_frames` | Total number of frames in the synchronized video data            |
* `all_notes_corrected_features.csv` — Note-level acoustic feature tables located within `./process_audio/all_notes` then the audio file number folder (`0000###/`).

  | Column                         | Description                                                                                                                                                                        |
  | :----------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | #                              | Sequential note index                                                                                                                                                              |
  | `start`, `end`                 | Start and end time of the note within the session (seconds)                                                                                                                        |
  | `duration`                     | Duration of the note (seconds)                                                                                                                                                     |
  | `maxfreq`, `min`               | Placeholder numeric values displayed in the detection GUI; **these do not represent measured frequencies and are not biologically meaningful**                                     |
  | `type`                         | Automatically assigned call type label (not curated)                                                                                                                               |
  | `code`                         | For social data recorded in PAIRId, indication of assigned source (`0` = left, `1` = right, `6` = unknown). This column missing and not applicable for solo data.                  |
  | `max_amp_high`, `max_amp_song` | Peak amplitude of the note within the 10–120 kHz frequency range as calculated on high-gain audio (`high`) or low-gain audio (`song`)                                              |
  | `note_rate`                    | Instantaneous note rate, calculated as the reciprocal of the interval between the start times of two consecutive notes (1 / Δstart). Reflects the local tempo of vocal production. |
  | `isi`                          | Intervening silence interval, defined as the time difference between one note’s end and the next note’s start. Represents the silent gap between consecutive notes.                |
* `common_coords_00###.npz` — mouse positions estimated using a SLEAP model (stored within `./process_video/common_coords` . The final 5 digit number of each filename indicates the video index.

  | Variable                                     | Description                                                                                                                                                                                                                                     |
  | :------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `l_coordinates_world`, `r_coordinates_world` | For every video frame, world-coordinate (x, y) positions for the six SLEAP pose-estimation nodes for each mouse (`l_` = left mouse, `r_` = right mouse). Nodes include, in order: right ear, left ear, nose, mid-head, mid-back, and tail base. |

#### **heliox.zip**

Data from four unique singing mice male–female dyads recorded while vocalizing first in normal atmospheric conditions and subsequently with heliox gas introduced into the enclosure. Included files contain the fundamental frequency measurements of selected note classes for each pair, encompassing ultrasonic vocalizations (USVs), song notes, and squeaks

##### File descriptions

* `heliox_sessions.csv` — metadata table summarizing each recording session.

  | Column                          | Description                                           |
  | :------------------------------ | :---------------------------------------------------- |
  | `session`                       | Unique session identifier                             |
  | `date`                          | Recording date                                        |
  | `male_id, female_id`            | Subject identifiers for each dyad                     |
  | `atm_num_song_notes_quantified` | Number of song notes analyzed in air                  |
  | `atm_num_usvs_quantified`       | Number of ultrasonic vocalizations analyzed in air    |
  | `atm_num_squeaks_quantified`    | Number of squeaks analyzed in air                     |
  | `hel_num_song_notes_quantified` | Number of song notes analyzed in heliox               |
  | `hel_num_usvs_quantified`       | Number of ultrasonic vocalizations analyzed in heliox |
  | `hel_num_squeaks_quantified`    | Number of squeaks analyzed in heliox                  |
* `helium_manual_calls.csv`, `helium_manual_songs.csv`, `helium_manual_squaks.csv` — Quantified acoustic features for vocalization modes.

  | Column                  | Description                                                                                |
  | :---------------------- | :----------------------------------------------------------------------------------------- |
  | `trial`                 | Unique identifier for the recording trial                                                  |
  | `path`                  | File path                                                                                  |
  | `file_call`             | Name of source audio file containing the call                                              |
  | `file_det`              | Name of source detection file containing the call                                          |
  | `air`                   | Recording atmosphere (`atm` = air, `hel` = heliox)                                         |
  | `class`                 | Vocalization class (`downsweep` or `trill` = USV subtype, `song` = song note, or `squeak`) |
  | `callStart`, `callStop` | Onset and offset time of the call within the file (seconds)                                |
  | `f0_hi`, `f0_lo`        | Highest and lowest measured portion of the fundamental frequency (Hz)                      |

#### **thermistor.zip**

Data from a male singing mouse implanted with an intranasal thermistor used as a proxy for respiration. Included files contain detected vocalization timestamps recorded when the focal male was either alone or paired with a mute female, along with the corresponding analog thermistor signals acquired using an Intan recording controller.

The `.zip` contains a metadata file (`thermistor_sessions.csv`) and three session folders named according to the format\
`YYMMDD_mouseID_sessionNumber`. Each session folder includes two components:

* `process_audio/` — processed acoustic detections and note-level acoustic features.
* `process_intan/` — synchronized thermistor voltage traces recorded via an Intan acquisition system (`.mat` format).

##### File descriptions

* `thermistor_sessions.csv` — Metadata linking each session to the recording base path and subject ID.

  | Column          | Description                                                                                     |
  | :-------------- | :---------------------------------------------------------------------------------------------- |
  | `session`       | Unique session identifier (date + ID code)                                                      |
  | `basepath`      | Relative file path for the session folder                                                       |
  | `mouse_id`      | Identifier of the implanted subject                                                             |
  | `therm_clipped` | Logical indicator for whether thermistor signal contained clipping artifacts (`TRUE` / `FALSE`) |
* `all_notes_corrected_features.csv` — Per-note acoustic feature table generated from processed audio.

  | Column          | Description                                                                                                                                    |
  | :-------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
  | `#`             | Sequential note index                                                                                                                          |
  | `start`, `end`  | Start and end time of the note with the session (seconds)                                                                                      |
  | `duration`      | Duration of note (seconds)                                                                                                                     |
  | `maxfeq`, `min` | Placeholder numeric values displayed in the detection GUI; **these do not represent measured frequencies and are not biologically meaningful** |
  | `type`          | Automatically assigned call type label (not curated)                                                                                           |
  | `max_amp_high`  | Peak amplitude of the note within the 10–120 kHz frequency range                                                                               |
* `therm_*_*.mat` -- Each `.mat` file in `process_intan/` contains synchronized analog recordings acquired using an Intan system. Files are named according to the session date and start time (e.g., `therm_231017_152230.mat`) and include four variables:

  | Variable        | Description                                                                                                                                                                                     |
  | :-------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `cam_trigs_exp` | Digital trigger channel indicating camera frame times used as synchronization events.                                                                                                           |
  | `ch1_audio_exp` | Audio channel 1 waveform recorded from one microphone input                                                                                                                                     |
  | `ch2_audio_exp` | Continuous analog voltage trace from the intranasal thermistor sensor, used as a proxy for respiratory airflow. This is the primary signal of interest for respiration–vocal coupling analyses. |
  | `d2_exp`        | Placeholder variable representing an unused digital input channel in this dataset (values are all 0).                                                                                           |

  <br />

#### **pag_opto.zip**

Data from four male singing mice subjected to unilateral optogenetic stimulation of the caudolateral periaqueductal gray (clPAG) using excitatory opsins. Included files contain detected vocalization timestamps along with corresponding timestamps for optogenetic stimuli of one, two, or four seconds in duration.\
The `.zip` contains a metadata file (`pag_opto_usv_sessions.csv`) and multiple session folders named according to the format\
`YYMMDD_mouseID_sessionNumber`. Each session folder includes two components:

* `process_audio/` — processed acoustic detections and note-level acoustic features.
* `process_intan/` — synchronized optogenetic stimulation timestamps (`.csv` format).

##### File descriptions

* `pag_opto_usv_sessions.csv` — Metadata summarizing all optogenetic recording sessions.

  | Column            | Description                                                              |
  | :---------------- | :----------------------------------------------------------------------- |
  | `session`         | Unique session identifier (date + ID code)                               |
  | `Animal`          | Subject identifier                                                       |
  | `Duration`        | Duration of optogenetic stimuli used in the session (1, 2, or 4 seconds) |
  | `h_audio_file_sr` | audio file sampling rate                                                 |
  | `h_audio_real_sr` | estimated audio sampling rate for synchronization                        |
* `h_T*_corrected.csv` — Per-note acoustic feature table generated from processed audio.

  | Column                        | Description                                                                                                                                    |
  | :---------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
  | `#`                           | Sequential note index                                                                                                                          |
  | `start`, `end`                | Start and end time of the note within the session (seconds)                                                                                    |
  | `duration`                    | Duration of the note (seconds)                                                                                                                 |
  | `maxfreq`, `min`              | Placeholder numeric values displayed in the detection GUI; **these do not represent measured frequencies and are not biologically meaningful** |
  | `type`                        | Automatically assigned call type label (not curated)                                                                                           |
  | `max_amp_low`, `max_amp_high` | Peak amplitude of the note within the 10–120 kHz frequency range as calculated on low-gain audio (`low`) or high-gain audio (`high`)           |
* `opto_stims.csv` — Optogenetic stimulation timestamps.

  | Column                      | Description                                           |
  | :-------------------------- | :---------------------------------------------------- |
  | `stim_starts`, `stim_stops` | Start and end times of optogenetic stimulus (seconds) |

#### **pag_telc.zip**

Data from five male singing mice subjected to bilateral synaptic silencing of neurons in the caudolateral periaqueductal gray (clPAG) via expression of tetanus toxin light chain (TeLC). Included files comprise processed audio vocalization timestamps generated by the PAIRId assignment algorithm and manual curation from recordings collected the day before surgery and during the five to six days following surgery, as the mice produced progressively deteriorating vocalizations before becoming mute.

The `.zip` contains metadata files (`pag_telc_sessions.csv`, `pag_telc_curation.csv`) and multiple session folders named according to the format\
`YYMMDD_mouseID_sessionNumber`. Each session folder includes one or more subdirectories containing the processed acoustic data:

* `process_audio/` or `original_audio/` — folders containing extracted note-level acoustic features in `all_notes_corrected_features.csv` format, organized by audio file number (`0000###`).

##### File descriptions

* `pag_telc_sessions.csv` — Metadata linking each session to the recording path, experimental condition, and post-surgery time point.

  | Column               | Description                                                         |
  | :------------------- | :------------------------------------------------------------------ |
  | `session`            | Unique session identifier (date + subject IDs)                      |
  | `basepath`           | Filepath                                                            |
  | `mouse_1`, `mouse_2` | Identifiers of the recorded individuals                             |
  | `condition`          | Experimental condition (`pre` = pre-surgery, `post` = post-surgery) |
  | `processed`          | date on which the data were processed (`YYMMDD`)                    |
  | `anchor_file_idx`    | the initial audio file index                                        |
  | `num_post_days`      | number of days recorded                                             |
  | `num_vocal_days`     | Number of days in which vocalizations were detected                 |
* `pag_telc_curation.csv` — Manual curation log corresponding to PAIRId output and post-processing review.

  | Condition            | Description                                                                                                                                            |
  | :------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `exptitle`           | Experiment title                                                                                                                                       |
  | `session`            | Session identifier                                                                                                                                     |
  | `basepath`           | Relative file path for the session folder                                                                                                              |
  | `mouse_1`, `mouse_2` | Identifiers of the recorded individuals                                                                                                                |
  | `condition`          | Experimental condition (`pre` = pre-surgery, `post` = post-surgery)                                                                                    |
  | `idx`                | sequential position of curated file                                                                                                                    |
  | `hr`                 | audio file number corresponding to curated file                                                                                                        |
  | `lights_turn_on`     | Logical indicator for whether this was a file where the light turned on for the mice (`1`=TRUE / `0` = FALSE)                                          |
  | `truepos_usvs`       | Count of manually verified ultrasonic vocalizations (true positives); provided as partial internal annotation notes rather than a comprehensive count. |
* `all_notes_corrected_features.csv` — Per-note acoustic feature table generated from processed and manually curated recordings.

  | Column                         | Description                                                                                                                                    |
  | :----------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
  | <br />                         | Sequential note index                                                                                                                          |
  | `start`, `end`                 | Start and end time of the note within the session (seconds)                                                                                    |
  | `duration`                     | Duration of the note (seconds)                                                                                                                 |
  | `maxfreq`, `min`               | Placeholder numeric values displayed in the detection GUI; **these do not represent measured frequencies and are not biologically meaningful** |
  | `type`                         | Automatically assigned call type label (not curated)                                                                                           |
  | `code`                         | Indication of assigned source (`0` = left, `1` = right, `6` = unknown)                                                                         |
  | `max_amp_high`, `max_amp_song` | Peak amplitude of the note within the 10–120 kHz frequency range as calculated on high-gain audio (`high`) or low-gain audio (`song`)          |

## Code/software

The code necessary to reproduce the results in the associated publication are available on GitHub.

[https://github.com/singingmicelab/zheng-harpole-2025-vocalmodes-pag](https://github.com/singingmicelab/zheng-harpole-2025-vocalmodes-pag)
