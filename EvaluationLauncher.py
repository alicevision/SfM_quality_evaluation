#!/usr/bin/python
#! -*- encoding: utf-8 -*-

# Copyright (c) 2014, 2015 Pierre MOULON.

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#
# this script is to evaluate the Global SfM pipeline to a known camera trajectory
# Notes:
#  - OpenMVG 0.8 is required
#
# Usage:
#  $ python EvaluationLauncher.py ./Benchmarking_Camera_Calibration_2008 ./Benchmarking_Camera_Calibration_2008_out
#
#

import commands
import os
import subprocess
import sys
import argparse

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

# Configure arguments parser
#

parser = argparse.ArgumentParser(description='Run OpenMVG SfM on several datasets to evaluate the precision according to a ground truth.')

# OpenMVG SfM programs
parser.add_argument('-s', '--software', required=True, help='OpenMVG SfM software folder ( like [...]/build/software/SfM)', metavar='SOFTWARE_PATH')
# input folder where datasets are stored
parser.add_argument('-i', '--input', required='True', help='Input datasets folder (he should contains folder where there is in each images/, gt_dense_cameras/ and K.txt)', metavar='DATASETS_PATH')
# Output folder
parser.add_argument('-o', '--output', default='reconstructions', help='Output folder (it will contains features, matches and reconstructions for each datasets)', metavar='RECONSTRUCTIONS_PATH')
# Result file
parser.add_argument('-r', '--result', default='results.json', help='File to store the results', metavar='RESULT_VAR')

args = parser.parse_args()

OPENMVG_SFM_BIN = args.software
if not (os.path.exists(OPENMVG_SFM_BIN)):
  print("/!\ Please update the OPENMVG_SFM_BIN to the openMVG_Build/software/SfM/ path.")
  sys.exit(1)

input_eval_dir = args.input
output_eval_dir = args.output

# Run for each dataset of the input eval dir perform
#  . intrinsic setup
#  . compute features
#  . compute matches
#  . compute camera motion
#  . perform quality evaluation regarding ground truth camera trajectory

for directory in os.listdir(input_eval_dir):

  print directory
  matches_dir = os.path.join(output_eval_dir, directory, "matching")

  ensure_dir(matches_dir)

  intrinsic = ''
  with open(input_eval_dir + "/" + directory + "/K.txt") as f:
      for line in f:
          for x in line.split():
              intrinsic += x + ';'
  intrinsic = intrinsic = intrinsic[:-1]

  print (". intrinsic setup")
  command = OPENMVG_SFM_BIN + "/openMVG_main_SfMInit_ImageListing"
  command = command + " -i " + input_eval_dir + "/" + directory + "/images/"
  command = command + " -o " + matches_dir
  command = command + " -k \"" + intrinsic + "\""
  command = command + " -c 1" # force pinhole camera
  command = command + " -g 1" # shared intrinsic
  proc = subprocess.Popen((str(command)), shell=True)
  proc.wait()

  print (". compute features")
  command = OPENMVG_SFM_BIN + "/openMVG_main_ComputeFeatures"
  command = command + " -i " + matches_dir + "/sfm_data.json"
  command = command + " -o " + matches_dir
  proc = subprocess.Popen((str(command)), shell=True)
  proc.wait()

  print (". compute matches")
  command = OPENMVG_SFM_BIN + "/openMVG_main_ComputeMatches"
  command = command + " -i " + matches_dir + "/sfm_data.json"
  command = command + " -o " + matches_dir + " -r .8 -g e"
  proc = subprocess.Popen((str(command)), shell=True)
  proc.wait()

  print (". compute camera motion")
  outGlobal_dir = os.path.join(output_eval_dir, directory, "SfM_Global")
  command = OPENMVG_SFM_BIN + "/openMVG_main_GlobalSfM"
  command = command + " -i " + matches_dir + "/sfm_data.json"
  command = command + " -m " + matches_dir
  command = command + " -o " + outGlobal_dir
  command = command + " -r 2" # L2 rotation averaging
  command = command + " -f 0" # Do not refine intrinsics
  proc = subprocess.Popen((str(command)), shell=True)
  proc.wait()

  print (". perform quality evaluation")
  gt_camera_dir = os.path.join(input_eval_dir, directory, "gt_dense_cameras")
  outStatistics_dir = os.path.join(outGlobal_dir, "stats")
  command = OPENMVG_SFM_BIN + "/openMVG_main_evalQuality"
  command = command + " -i " + gt_camera_dir
  command = command + " -c " + outGlobal_dir + "/sfm_data.json"
  command = command + " -o " + outStatistics_dir
  proc = subprocess.Popen((str(command)), shell=True)
  proc.wait()

sys.exit(1)
