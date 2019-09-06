#!/usr/bin/env python3

"""
  Analysis script to read a ROOT TTree of track information
  and do jet-finding, and save basic histograms.
  
  Author: James Mulligan (james.mulligan@berkeley.edu)
"""

from __future__ import print_function

# General
import os
import sys
import argparse
import math
import time

# Data analysis and plotting
import uproot
import pandas
import numpy as np
import ROOT

# Fastjet via python (from external library heppy)
import fastjet as fj
import fjcontrib
import fjext

# Analysis utilities
import analysis_utils

# Prevent ROOT from stealing focus when plotting
ROOT.gROOT.SetBatch(True)

# Set debug level (0 = no debug info, 1 = some debug info, 2 = all debug info)
debugLevel = 0

#---------------------------------------------------------------
def process_rg_data(inputFile, outputDir):
  
  start_time = time.time()
  
  # Create output dir
  if not outputDir.endswith("/"):
    outputDir = outputDir + "/"
  if not os.path.exists(outputDir):
    os.makedirs(outputDir)

  # Convert ROOT TTree to pandas dataframe
  # track_df is a dataframe with one row per jet constituent: run_number, ev_id, ParticlePt, ParticleEta, ParticlePhi
  print('--- {} seconds ---'.format(time.time() - start_time))
  print('Convert ROOT trees to pandas dataframes...')
  track_df = analysis_utils.load_dataframe(inputFile)

  # Transform the track dataframe into a SeriesGroupBy object of fastjet particles per event
  print('--- {} seconds ---'.format(time.time() - start_time))
  print('Transform the track dataframe into a series object of fastjet particles per event...')

  # (i) Group the track dataframe by event
  #     track_df_grouped is a DataFrameGroupBy object with one track dataframe per event
  track_df_grouped = track_df.groupby(['run_number','ev_id'])

  # (ii) Transform the DataFrameGroupBy object to a SeriesGroupBy of fastjet particles
  df_fjparticles = track_df_grouped.apply(analysis_utils.get_fjparticles)
  
  if debugLevel > 0:
    print(df_fjparticles.dtypes)
    print(df_fjparticles)
  print('--- {} seconds ---'.format(time.time() - start_time))

  # Print number of events
  nEvents = track_df_grouped.size().count()
  print('Number of events: {}'.format(nEvents))
  nTracks = len(track_df.index)
  print('Number of tracks: {}'.format(nTracks))

  # Initialize histogram dictionary
  hDict = initializeHistograms()
  
  # Find jets and fill histograms
  print('Find jets...')
  analyzeEvents(df_fjparticles, hDict, outputDir)

  # Plot histograms
  print('Plot histograms...')
  saveHistograms(hDict, outputDir)

  print('--- {} seconds ---'.format(time.time() - start_time))

#---------------------------------------------------------------
def initializeHistograms():
  
  hDict = {}
  
  hJetPt = ROOT.TH1F('hJetPt', 'hJetPt', 200, 0, 200)
  hJetPt.GetXaxis().SetTitle('p_{T,jet}')
  hJetPt.GetYaxis().SetTitle('dN/dp_{T}')
  hDict['hJetPt'] = hJetPt

  hAJ = ROOT.TH2F('hAJ', 'hAJ', 100, 0, 1., 100, 0, 4.)
  hAJ.GetXaxis().SetTitle('A_{J}')
  hAJ.GetYaxis().SetTitle('#Delta #phi')
  hDict['hAJ'] = hAJ

  hZg = ROOT.TH1F('hZg', 'hZg', 100, 0, 1.)
  hZg.GetXaxis().SetTitle('z_{g}')
  hZg.GetYaxis().SetTitle('dN/dz_{g}')
  hDict['hZg'] = hZg

  hRg = ROOT.TH1F('hRg', 'hRg', 100, 0, 1.)
  hRg.GetXaxis().SetTitle('R_{g}')
  hRg.GetYaxis().SetTitle('dN/dR_{g}')
  hDict['hRg'] = hRg

  return hDict

#---------------------------------------------------------------
def analyzeEvents(df_fjparticles, hDict, outputDir):
  
  fj.ClusterSequence.print_banner()
  print()
  
  # Set jet definition and a jet selector
  jetR = 0.4
  jet_def = fj.JetDefinition(fj.antikt_algorithm, jetR)
  jet_selector = fj.SelectorPtMin(5.0) & fj.SelectorAbsRapMax(0.9 - jetR)
  print('jet definition is:', jet_def)
  print('jet selector is:', jet_selector,'\n')
  
  # Define SoftDrop settings
  beta = 0
  zcut = 0.1
  sd = fjcontrib.SoftDrop(beta, zcut, jetR)
  print('SoftDrop groomer is: {}'.format(sd.description()));

  # Use list comprehension to do jet-finding and fill histograms
  result = [analyzeJets(fj_particles, jet_def, jet_selector, sd, hDict) for fj_particles in df_fjparticles]

#---------------------------------------------------------------
def analyzeJets(fj_particles, jet_def, jet_selector, sd, hDict):
  
  # Do jet finding
  cs = fj.ClusterSequence(fj_particles, jet_def)
  jets = fj.sorted_by_pt(cs.inclusive_jets())
  jets_accepted = jet_selector(jets)

  fillJetHistograms(hDict, jets_accepted)

  # Loop through jets and perform SoftDrop grooming
  jets_sd = []
  for jet in jets_accepted:
    jets_sd.append(sd.result(jet))

  fillSoftDropHistograms(hDict, jets_sd)

#---------------------------------------------------------------
def fillJetHistograms(hDict, jets_accepted):

  # Loop through jets, and fill histograms
  for jet in jets_accepted:
    if debugLevel > 1:
      print('jet:')
      print(jet)
      
    hDict['hJetPt'].Fill(jet.pt())

  # Find di-jets and fill histograms
  if len(jets_accepted) > 1:

    pT1 = jets_accepted[0].pt()
    pT2 = jets_accepted[1].pt()
    phi1 = jets_accepted[0].phi()
    phi2 = jets_accepted[1].phi()
  
    AJ = (pT1 - pT2) / (pT1 + pT2)
    deltaPhi = abs(phi1 - phi2)
    
    hDict['hAJ'].Fill(AJ, deltaPhi)

#---------------------------------------------------------------
def fillSoftDropHistograms(hDict, jets_sd):
  
  for jet in jets_sd:
    
    sd_info = fjcontrib.get_SD_jet_info(jet)
    zg = sd_info.z
    Rg = sd_info.dR
    
    hDict['hZg'].Fill(zg)
    hDict['hRg'].Fill(Rg)

#---------------------------------------------------------------
def saveHistograms(hDict, outputDir):
  
  fout = ROOT.TFile("AnalysisResults.root", "recreate")
  fout.cd()
  for key, val in hDict.items():
    val.Write()
  fout.Close()

#----------------------------------------------------------------------
if __name__ == '__main__':
  # Define arguments
  parser = argparse.ArgumentParser(description='Plot analysis histograms')
  parser.add_argument('-f', '--inputFile', action='store',
                      type=str, metavar='inputFile',
                      default='AnalysisResults.root',
                      help='Path of ROOT file containing TTrees')
  parser.add_argument('-o', '--outputDir', action='store',
                      type=str, metavar='outputDir',
                      default='./myTestFigures',
                      help='Output directory for QA plots to be written to')
  
  # Parse the arguments
  args = parser.parse_args()
  
  print('Configuring...')
  print('inputFile: \'{0}\''.format(args.inputFile))
  print('ouputDir: \'{0}\"'.format(args.outputDir))
  print('----------------------------------------------------------------')
  
  # If invalid inputFile is given, exit
  if not os.path.exists(args.inputFile):
    print('File \"{0}\" does not exist! Exiting!'.format(args.inputFile))
    sys.exit(0)

  process_rg_data(inputFile = args.inputFile, outputDir = args.outputDir)
