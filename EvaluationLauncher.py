#!/usr/bin/python
#! -*- encoding: utf-8 -*-

#import commands
import os
import subprocess
import sys
import argparse
import json
import time

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

# Configure arguments parser

parser = argparse.ArgumentParser(description='Run AliceVision SfM on several datasets to evaluate the precision according to a ground truth.')
parser.add_argument('-s', '--software', required=True, help='AliceVision SfM software folder ( like [...]/build/software/SfM)', metavar='SOFTWARE_PATH')
parser.add_argument('-i', '--input', required='True', help='Input datasets folder (he should contains folder where there is in each images/, gt_dense_cameras/ and K.txt)', metavar='DATASETS_PATH')
parser.add_argument('-o', '--output', default='reconstructions', help='Output folder (it will contains features, matches and reconstructions for each datasets)', metavar='RECONSTRUCTIONS_PATH')
parser.add_argument('-r', '--result', default='results.json', help='File to store the results', metavar='RESULT_FILE.json')
parser.add_argument('-l', '--limit', default=-1, type=int, help='Limit the number of reconstructions to perform')
parser.add_argument('-v', '--verbose', help='Verbose output', action='store_true')

args = parser.parse_args()

logHandler = sys.stdout if args.verbose else open(os.devnull, 'w')

ALICEVISION_SFM_BIN = args.software
if not (os.path.exists(ALICEVISION_SFM_BIN)):
  print("/!\ Please update the ALICEVISION_SFM_BIN to the aliceVision_Build/software/SfM/ path.")
  print("Invalid path : " + ALICEVISION_SFM_BIN)
  sys.exit(1)

input_eval_dir = args.input
output_eval_dir = args.output

# Run for each dataset of the input eval dir perform
#  . intrinsic setup
#  . compute features
#  . compute matches
#  . compute camera motion
#  . perform quality evaluation regarding ground truth camera trajectory

result_folder = {}

for directory in os.listdir(input_eval_dir)[:args.limit]:

  print (directory)
  matches_dir = os.path.join(output_eval_dir, directory, "matching")

  ensure_dir(matches_dir)
  time_folder = {}

  with open(input_eval_dir + "/" + directory + "/intrinsics.json") as f:
    jsonContent = f.read()
    intrinsics = json.loads(jsonContent)

  print (". cameraInit")
  command = ALICEVISION_SFM_BIN + "/aliceVision_cameraInit"
  command = command + " --imageFolder " + input_eval_dir + "/" + directory + "/images/"
  command = command + " -o " + matches_dir + "/" + "cameraInit.sfm"
  command = command + " --defaultFocalLength " + "\"" + str(intrinsics["focalLength"]) + "\""
  command = command + " --defaultFocalRatio " + "\"" + str(intrinsics["focalRatio"]) + "\""
  command = command + " --defaultOffsetX " + "\"" + str(intrinsics["offsetX"]) + "\""
  command = command + " --defaultOffsetY " + "\"" + str(intrinsics["offsetY"]) + "\""
  command = command + " --defaultCameraModel pinhole" # force pinhole camera
  command = command + " --sensorDatabase \"\""
  command = command + " --viewIdMethod filename"
  start_time = time.time()
  print(str(command))
  proc = subprocess.Popen((str(command)), shell=True, stdout=logHandler, stderr=logHandler)
  if proc.wait() != 0:
    print ("Error! The following command exited with non-zero exit status (" + str(proc.returncode) + "):")
    print (command)
    sys.exit(proc.returncode)
  time_folder['image_listing'] = time.time() - start_time

  print (". featureExtraction")
  command = ALICEVISION_SFM_BIN + "/aliceVision_featureExtraction"
  command = command + " -i " + matches_dir + "/cameraInit.sfm"
  command = command + " -o " + matches_dir
  command = command + " --describerPreset low --maxThreads 1 --forceCpuExtraction 1"
  start_time = time.time()
  print(str(command))
  proc = subprocess.Popen((str(command)), shell=True, stdout=logHandler, stderr=logHandler)
  if proc.wait() != 0:
    print ("Error! The following command exited with non-zero exit status (" + str(proc.returncode) + "):")
    print (command)
    sys.exit(proc.returncode)
  time_folder['compute_features'] = time.time() - start_time

  print (". featureMatching")
  command = ALICEVISION_SFM_BIN + "/aliceVision_featureMatching"
  command = command + " -i " + matches_dir + "/cameraInit.sfm"
  command = command + " -f " + matches_dir
  command = command + " -o " + matches_dir
  start_time = time.time()
  print(str(command))
  proc = subprocess.Popen((str(command)), shell=True, stdout=logHandler, stderr=logHandler)
  if proc.wait() != 0:
    print ("Error! The following command exited with non-zero exit status (" + str(proc.returncode) + "):")
    print (command)
    sys.exit(proc.returncode)
  time_folder['compute_matches'] = time.time() - start_time

  print (". incrementalSfM")
  outSfM = os.path.join(output_eval_dir, directory, "sfmData.sfm")
  command = ALICEVISION_SFM_BIN + "/aliceVision_incrementalSfM"
  command = command + " -i " + matches_dir + "/cameraInit.sfm"
  command = command + " -f " + matches_dir
  command = command + " -m " + matches_dir
  command = command + " -o " + outSfM
  command = command + " --lockAllIntrinsics 1"  # Do not refine intrinsics
  start_time = time.time()
  print(str(command))
  proc = subprocess.Popen((str(command)), shell=True, stdout=logHandler, stderr=logHandler)
  if proc.wait() != 0:
    print ("Error! The following command exited with non-zero exit status (" + str(proc.returncode) + "):")
    print (command)
    sys.exit(proc.returncode)
  time_folder['compute_camera'] = time.time() - start_time

  print (". qualityEvaluation")
  # gt_camera_file = os.path.join(input_eval_dir, directory, "gt.abc")
  gt_camera_file = os.path.join(input_eval_dir, directory)
  outStatistics_dir = os.path.join(output_eval_dir, directory, "stats")
  command = ALICEVISION_SFM_BIN + "/aliceVision_qualityEvaluation"
  command = command + " --groundTruthPath " + gt_camera_file
  command = command + " -i " + outSfM
  command = command + " -o " + outStatistics_dir
  start_time = time.time()
  print(str(command))
  proc = subprocess.Popen((str(command)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if proc.wait() != 0:
    print ("Error! The following command exited with non-zero exit status (" + str(proc.returncode) + "):")
    print (command)
    sys.exit(proc.returncode)

  time_folder['quality_evaluation'] = time.time() - start_time

  print(outStatistics_dir + "/evaluation.log")
  result = {}
  evalog = open(outStatistics_dir + "/evaluation.log", "w")
  line = proc.stdout.readline().decode()
  evalog.write(line)
  while line != '':
    if 'Baseline error statistics' in line:
      basestats = {}
      line = proc.stdout.readline().decode()
      evalog.write(line)
      for loop in range(0,4):
        v = line.strip().split(':')
        basestats[v[0]] = float(v[1])
        line = proc.stdout.readline().decode()
        evalog.write(line)
      result['Baseline error statistics'] = basestats
    if 'Angular error statistics' in line:
      basestats = {}
      line = proc.stdout.readline().decode()
      evalog.write(line)
      for loop in range(0,4):
        v = line.strip().split(':')
        basestats[v[0]] = float(v[1])
        line = proc.stdout.readline().decode()
        evalog.write(line)
      result['Angular error statistics'] = basestats
    line = proc.stdout.readline().decode()
    evalog.write(line)

  evalog.close()

  result['time'] = time_folder
  result_folder[directory] = result

with open(args.result, 'w') as savejson:
    json.dump(result_folder, savejson, sort_keys=True, indent=4, separators=(',',':'))

print(json.dumps(result_folder, sort_keys=True, indent=4, separators=(',',':')))

sys.exit(0)
