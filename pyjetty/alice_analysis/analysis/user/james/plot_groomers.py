#!/usr/bin/env python3

"""
  Plotting utilities for jet substructure analysis with track dataframe.
  
  Author: James Mulligan (james.mulligan@berkeley.edu)
"""

from __future__ import print_function

# General
import os
import sys
import math
import yaml
import argparse

# Data analysis and plotting
import numpy as np
from array import *
import ROOT

# Base class
from pyjetty.alice_analysis.analysis.base import common_base
from pyjetty.alice_analysis.analysis.user.substructure import analysis_utils_obs
from pyjetty.alice_analysis.analysis.user.james import plotting_utils

# Prevent ROOT from stealing focus when plotting
ROOT.gROOT.SetBatch(True)

# Suppress a lot of standard output
ROOT.gErrorIgnoreLevel = ROOT.kWarning

################################################################
class PlotGroomers(common_base.CommonBase):
  
  #---------------------------------------------------------------
  # Constructor
  #---------------------------------------------------------------
  def __init__(self, output_dir = '.', config_file = '', **kwargs):
    super(PlotGroomers, self).__init__(**kwargs)
    
    # Initialize utils class
    self.utils = analysis_utils_obs.AnalysisUtils_Obs()
    
    self.utils.set_plotting_options()
    ROOT.gROOT.ForceStyle()
    
    # Read config file
    self.config_file = config_file
    with open(config_file, 'r') as stream:
      config = yaml.safe_load(stream)
    
    self.observables = config['process_observables']
    thermal_data = config['main_response']
    self.fMC = ROOT.TFile(thermal_data, 'READ')
    
    self.eta_max = config['eta_max']
    self.max_distance = config['constituent_subtractor']['max_distance']
    self.R_max = config['constituent_subtractor']['main_R_max']
    
    self.file_format = config['file_format']
    self.output_dir = config['output_dir']
    
    self.min_theta_list = config['min_theta_list']
    
    #self.legend_list = ['subleading', 'leading (swap)', 'leading (mis-tag)', 'ungroomed', 'outside', 'other', 'combined fail', 'truth fail', 'both fail']
    self.legend_list = ['subleading', 'leading (swap)', 'leading (mis-tag)', 'ungroomed', 'outside', 'other']
    

    self.ColorArray = [ROOT.kViolet-8, ROOT.kAzure-4, ROOT.kTeal-8, ROOT.kOrange+6, ROOT.kOrange-3, ROOT.kRed-7, ROOT.kPink+1, ROOT.kCyan-2, ROOT.kGray]
    self.MarkerArray = [20, 21, 22, 23, 33, 34, 24, 25, 26, 32]
    self.OpenMarkerArray = [24, 25, 26, 32, 27, 28]
    
    print(self)

  #---------------------------------------------------------------
  def init_observable(self, observable):
    
    with open(self.config_file, 'r') as stream:
      config = yaml.safe_load(stream)
    
    # Get the sub-configs
    self.jetR_list = config['jetR']
    self.obs_config_dict = config[observable]
    self.obs_subconfig_list = [name for name in list(self.obs_config_dict.keys()) if 'config' in name ]
    self.grooming_settings = self.utils.grooming_settings(self.obs_config_dict)
    self.obs_settings = self.utils.obs_settings(observable, self.obs_config_dict, self.obs_subconfig_list)
    self.obs_labels = [self.utils.obs_label(self.obs_settings[i], self.grooming_settings[i])
                       for i in range(len(self.obs_subconfig_list))]
    self.xtitle = self.obs_config_dict['common_settings']['xtitle']
    self.ytitle = self.obs_config_dict['common_settings']['ytitle']
    self.pt_bins_reported = self.obs_config_dict['common_settings']['pt_bins_reported']
    self.plot_overlay_list = self.obs_config_dict['common_settings']['plot_overlay_list']
    
    if observable == 'theta_g':
      self.xmin = 0.
      self.xmax = 1.
      self.axis = 2
      self.rebin_value = 5
    elif observable == 'zg':
      self.xmin = 0.
      self.xmax = 0.5
      self.axis = 1
      self.rebin_value = 5
    elif observable == 'kappa':
      self.xmin = 0.
      self.xmax = 0.5
      self.rebin_value = 1
    elif observable == 'tf':
      self.xmin = 0.
      self.xmax = 0.5
      self.rebin_value = 1

    # Create output dirs
    output_dir = os.path.join(self.output_dir, observable)
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

  #---------------------------------------------------------------
  def plot_groomers(self):
  
    # Loop through all observables
    for observable in self.observables:
      self.init_observable(observable)
  
      # Plot for each R_max
      for R_max in self.max_distance:
      
        # Plot for each R
        for jetR in self.jetR_list:
        
          # Create output dir
          output_dir = os.path.join(self.output_dir, observable)
          output_dir = os.path.join(output_dir, 'jetR{}'.format(jetR))
          output_dir = os.path.join(output_dir, 'Rmax{}'.format(R_max))
        
          # Plot money plot for all observables
          for i, _ in enumerate(self.obs_subconfig_list):

            obs_setting = self.obs_settings[i]
            grooming_setting = self.grooming_settings[i]
            obs_label = self.utils.obs_label(obs_setting, grooming_setting)
            self.create_output_subdir(output_dir, self.utils.grooming_label(grooming_setting))
            self.set_zmin(observable, grooming_setting)
                
            self.plot_money_plot(observable, jetR, R_max, obs_label, obs_setting, grooming_setting, output_dir)
           
          self.create_output_subdir(output_dir, 'ratios_Embedded_Truth')
          self.plot_money_ratios(observable, output_dir, jetR, 'Embedded/Truth')
          
          self.create_output_subdir(output_dir, 'ratios_Purity')
          self.plot_money_ratios(observable, output_dir, jetR, 'Tagging purity')

          # Plot performance plots only once
          if observable == 'theta_g':

            # Create output subdirectories
            output_dir = os.path.join(self.output_dir, 'performance')
            self.create_output_subdir(output_dir, 'delta_pt')
            self.create_output_subdir(output_dir, 'prong_matching_fraction_pt')
            self.create_output_subdir(output_dir, 'prong_matching_deltaR')
            self.create_output_subdir(output_dir, 'prong_matching_deltaZ')
            self.create_output_subdir(output_dir, 'prong_matching_correlation')
            
            self.plotting_utils = plotting_utils.PlottingUtils(output_dir, self.config_file, R_max=R_max,
                                                               thermal = False, groomer_studies = True)
        
            # Plot some subobservable-independent performance plots
            self.plotting_utils.plot_delta_pt(jetR, self.pt_bins_reported)

            # Plot prong matching histograms
            self.prong_match_threshold = 0.5
            min_pt = 80.
            max_pt = 100.
            prong_list = ['leading', 'subleading']
            match_list = ['leading', 'subleading', 'ungroomed', 'outside']
            for i, overlay_list in enumerate(self.plot_overlay_list):
              for prong in prong_list:
                for match in match_list:

                  hname = 'hProngMatching_{}_{}_JetPt_R{}'.format(prong, match, jetR)
                  self.plotting_utils.plot_prong_matching(i, jetR, hname, self.obs_subconfig_list, self.obs_settings, self.grooming_settings, overlay_list, self.prong_match_threshold)
                  self.plotting_utils.plot_prong_matching_delta(i, jetR, hname, self.obs_subconfig_list, self.obs_settings, self.grooming_settings, overlay_list, self.prong_match_threshold, min_pt, max_pt, plot_deltaz=False)

                  if 'subleading' in prong or 'leading' in prong:
                    hname = 'hProngMatching_{}_{}_JetPtZ_R{}'.format(prong, match, jetR)
                    self.plotting_utils.plot_prong_matching_delta(i, jetR, hname, self.obs_subconfig_list, self.obs_settings, self.grooming_settings, overlay_list, self.prong_match_threshold, min_pt, max_pt, plot_deltaz=True)

              hname = 'hProngMatching_subleading-leading_correlation_JetPt_R{}'.format(jetR)
              self.plotting_utils.plot_prong_matching_correlation(i, jetR, hname, self.obs_subconfig_list, self.obs_settings, self.grooming_settings, overlay_list, self.prong_match_threshold)

  #---------------------------------------------------------------
  def plot_money_plot(self, observable, jetR, R_max, obs_label, obs_setting, grooming_setting, output_dir):
      
    if observable in ['zg', 'theta_g']:
      # (pt, zg, theta_g, flag)
      #  Flag based on where >50% of subleading matched pt resides:
      #    1: subleading
      #    2: leading
      #    3: ungroomed
      #    4: outside
      #    5: other (i.e. 50% is not in any of the above)
      #    6: pp-truth passed grooming, but combined jet failed grooming
      #    7: combined jet passed grooming, but pp-truth failed grooming
      #    8: both pp-truth and combined jet failed SoftDrop
      # Note that 8 doesn't affect the relative normalization of combined / truth.
      # We will further assume 6,7 are of equal magnitude, and ignore 6-8 when
      # comparing combined to truth distributions.
      # (Note that 6,8 don't enter the combined distribution, since it has no splitting).
      name = 'h_theta_g_zg_JetPt_R{}_{}_Rmax{}'.format(jetR, obs_label, R_max)
      h4D = self.fMC.Get(name)
      h4D.Sumw2()
        
      name = 'h_theta_g_zg_JetPt_Truth_R{}_{}'.format(jetR, obs_label)
      h3D_truth = self.fMC.Get(name)
      
      # Loop through pt slices, and plot 1D projection onto observable
      for i in range(0, len(self.pt_bins_reported) - 1):
        min_pt = self.pt_bins_reported[i]
        max_pt = self.pt_bins_reported[i+1]
        
        # Set pt range
        h4D.GetAxis(0).SetRangeUser(min_pt, max_pt)
        h3D_truth.GetXaxis().SetRangeUser(min_pt, max_pt)
        
        for min_theta in self.min_theta_list:
          self.plot_obs_projection(observable, h4D, h3D_truth, min_theta,
                                   jetR, obs_label, obs_setting, grooming_setting,
                                   min_pt, max_pt, output_dir)
      
    elif observable in ['kappa', 'tf']:
    
      name = 'h_{}_JetPt_R{}_{}_Rmax{}'.format(observable, jetR, obs_label, R_max)
      h3D = self.fMC.Get(name)
      h3D.Sumw2()
        
      name = 'h_{}_JetPt_Truth_R{}_{}'.format(observable, jetR, obs_label)
      h2D_truth = self.fMC.Get(name)
        
      # Loop through pt slices, and plot 1D projection onto observable
      for i in range(0, len(self.pt_bins_reported) - 1):
        min_pt = self.pt_bins_reported[i]
        max_pt = self.pt_bins_reported[i+1]
        
        # Set pt range
        h3D.GetXaxis().SetRangeUser(min_pt, max_pt)
        h2D_truth.GetXaxis().SetRangeUser(min_pt, max_pt)
        
        for min_theta in self.min_theta_list:
          self.plot_obs_projection_kappa(observable, h3D, h2D_truth,
                                         jetR, obs_label, obs_setting, grooming_setting,
                                         min_pt, max_pt, output_dir)

  #---------------------------------------------------------------
  def plot_obs_projection(self, observable, h4D, h3D_truth, min_theta, jetR, obs_label, obs_setting,
                          grooming_setting, min_pt, max_pt, output_dir):
    
    # Reset projections for normalization
    
    # zg
    h4D.GetAxis(1).SetRangeUser(-10, self.xmax)
    h3D_truth.GetYaxis().SetRangeUser(-10, self.xmax)
    
    # Theta
    h4D.GetAxis(2).SetRangeUser(-10, 1)
    h3D_truth.GetZaxis().SetRangeUser(-10, 1)

    # Flag
    h4D.GetAxis(3).SetRange(0, 11)
    
    # Set RAA (optionally) due to theta_g cut from jet quenching
    if observable == 'zg':
      self.RAA = 1-min_theta
    else:
      self.RAA = 1.

    # Get normalization for embeddeed case
    h_normalization = h4D.Projection(self.axis)
    h_normalization.SetName('h_normalization_emb_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))
    N_inclusive_emb = h_normalization.Integral()/self.RAA
    if N_inclusive_emb < 1e-3:
      print('Emb Integral is 0, check for problem')
      return
      
    # Get normalization for truth case
    if observable == 'theta_g':
      h_normalization_truth = h3D_truth.Project3D('z')
    elif observable == 'zg':
      h_normalization_truth = h3D_truth.Project3D('y')
    h_normalization_truth.SetName('h_normalization_truth_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))
    N_inclusive_truth = h_normalization_truth.Integral()
    if N_inclusive_truth < 1e-3:
      print('Truth Integral is 0, check for problem')
      return
      
    # Set theta cut
    h4D.GetAxis(2).SetRangeUser(min_theta, 1)
    h3D_truth.GetZaxis().SetRangeUser(min_theta, 1)

    # Draw histogram
    c = ROOT.TCanvas('c','c: hist', 600, 650)
    c.cd()
    
    pad1 = ROOT.TPad('myPad', 'The pad',0,0.3,1,1)
    pad1.SetLeftMargin(0.2)
    pad1.SetTopMargin(0.04)
    pad1.SetRightMargin(0.04)
    pad1.SetBottomMargin(0.)
    pad1.Draw()
    pad1.cd()
    
    leg = ROOT.TLegend(0.65,0.5,0.8,0.8)
    self.utils.setup_legend(leg, 0.04)

    myBlankHisto = ROOT.TH1F('myBlankHisto','Blank Histogram', 20, self.xmin, self.xmax)
    myBlankHisto.SetNdivisions(505)
    myBlankHisto.SetMinimum(0.01)
    myBlankHisto.GetXaxis().SetTitle(self.xtitle)
    myBlankHisto.GetXaxis().SetTitleSize(30)
    myBlankHisto.GetXaxis().SetTitleFont(43)
    myBlankHisto.GetXaxis().SetTitleOffset(1.95)
    myBlankHisto.GetXaxis().SetLabelFont(43)
    myBlankHisto.GetXaxis().SetLabelSize(25)
    myBlankHisto.GetYaxis().SetTitleSize(25)
    myBlankHisto.GetYaxis().SetTitleFont(43)
    myBlankHisto.GetYaxis().SetTitleOffset(1.7)
    myBlankHisto.GetYaxis().SetLabelFont(43)
    myBlankHisto.GetYaxis().SetLabelSize(25)
    myBlankHisto.GetYaxis().SetNdivisions(505)
    myBlankHisto.GetYaxis().SetTitle(self.ytitle)
    myBlankHisto.Draw('E')
    
    c.cd()
    pad2 = ROOT.TPad('pad2', 'pad2', 0, 0.02, 1, 0.3)
    pad2.SetTopMargin(0)
    pad2.SetBottomMargin(0.35)
    pad2.SetLeftMargin(0.2)
    pad2.SetRightMargin(0.04)
    pad2.SetTicks(0,1)
    pad2.Draw()
    pad2.cd()
    
    leg_ratio = ROOT.TLegend(0.65,0.77,0.8,0.92)
    self.utils.setup_legend(leg_ratio, 0.1)
    
    myBlankHisto2 = myBlankHisto.Clone('myBlankHisto_C')
    ytitle = 'Ratio'
    myBlankHisto2.SetYTitle(ytitle)
    myBlankHisto2.SetXTitle(self.xtitle)
    myBlankHisto2.GetXaxis().SetTitleSize(30)
    myBlankHisto2.GetXaxis().SetTitleFont(43)
    myBlankHisto2.GetXaxis().SetTitleOffset(3.5)
    myBlankHisto2.GetXaxis().SetLabelFont(43)
    myBlankHisto2.GetXaxis().SetLabelSize(25)
    myBlankHisto2.GetYaxis().SetTitleSize(25)
    myBlankHisto2.GetYaxis().SetTitleFont(43)
    myBlankHisto2.GetYaxis().SetTitleOffset(2.)
    myBlankHisto2.GetYaxis().SetLabelFont(43)
    myBlankHisto2.GetYaxis().SetLabelSize(25)
    myBlankHisto2.GetYaxis().SetNdivisions(505)
    myBlankHisto2.SetMinimum(0.01)
    myBlankHisto2.SetMaximum(1.99)
    myBlankHisto2.Draw('')
    
    h_stack = ROOT.THStack('h_stack', 'stacked')
    h_sum = None
    h_sum_tagged = None

    # Loop over each flag
    for i in range(len(self.legend_list)):
      flag = i+1
      h4D.GetAxis(3).SetRange(flag, flag)
      if observable == 'zg':
        h4D.GetAxis(1).SetRangeUser(self.zmin, self.xmax)

      # Project onto 1D
      h1D = h4D.Projection(self.axis)
      h1D.SetName('h1D_{}'.format(i))
      h1D.Rebin(self.rebin_value)
      h1D.Scale(1./N_inclusive_emb, 'width')
        
      h1D.SetLineColor(self.ColorArray[i])
      h1D.SetFillColor(self.ColorArray[i])
      h1D.SetLineWidth(2)

      h_stack.Add(h1D)
      leg.AddEntry(h1D, self.legend_list[i], 'F')
      
      if h_sum:
        h_sum.Add(h1D)
      else:
        h_sum = h1D.Clone()
        h_sum.SetName('h_sum_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))

      if self.legend_list[i] in ['subleading', 'leading (swap)']:
        if h_sum_tagged:
          h_sum_tagged.Add(h1D)
        else:
          h_sum_tagged = h1D.Clone()
          h_sum_tagged.SetName('h_sum_tagged_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))
    
    # Draw truth histogram
    if observable == 'theta_g':
      h1D_truth = h3D_truth.Project3D('z')
    elif observable == 'zg':
      h3D_truth.GetYaxis().SetRangeUser(self.zmin, self.xmax)
      h1D_truth = h3D_truth.Project3D('y')
    h1D_truth.Rebin(self.rebin_value)
    h1D_truth.Scale(1./N_inclusive_truth, 'width')
    h1D_truth.SetLineColor(1)
    h1D_truth.SetLineWidth(2)
    myBlankHisto.SetMaximum(2.3*h1D_truth.GetMaximum())
    leg.AddEntry(h1D_truth, 'Truth', 'L')
    
    pad1.cd()
    leg.Draw('same')
    h_stack.Draw('same hist')
    h1D_truth.Draw('same hist')
    
    text_latex = ROOT.TLatex()
    text_latex.SetNDC()
    
    x = 0.23
    y = 0.9
    text_latex.SetTextSize(0.05)
    text = 'PYTHIA8 embedded in thermal background'
    text_latex.DrawLatex(x, y, text)
        
    text = '#sqrt{#it{s_{#it{NN}}}} = 5.02 TeV'
    text_latex.DrawLatex(x, y-0.06, text)

    text = 'Charged jets   anti-#it{k}_{T}'
    text_latex.DrawLatex(x, y-0.12, text)
    
    text = '#it{R} = ' + str(jetR) + '   | #it{{#eta}}_{{jet}}| < {:.2f}'.format(self.eta_max - jetR)
    text_latex.DrawLatex(x, y-0.18, text)
   
    text = str(int(min_pt)) + ' < #it{p}_{T, ch jet}^{PYTHIA} < ' + str(int(max_pt)) + ' GeV/#it{c}'
    text_latex.DrawLatex(x, y-0.25, text)
   
    text = self.utils.formatted_grooming_label(grooming_setting)
    text_latex.DrawLatex(x, y-0.32, text)
    
    if min_theta > 1e-3:
      text = '#Delta#it{{R}} > {}'.format(min_theta*jetR)
      text_latex.DrawLatex(x, y-0.38, text)
    
    # Build ratio Embedded/Truth
    pad2.cd()
    setattr(self, 'h_ratio_{}'.format(obs_label), None)
    h_ratio = h_sum.Clone()
    h_ratio.SetMarkerStyle(self.MarkerArray[0])
    h_ratio.SetMarkerColor(1)
    h_ratio.Divide(h1D_truth)
    if h_ratio.GetMaximum() > myBlankHisto2.GetMaximum():
      myBlankHisto2.SetMaximum(1.5*h_ratio.GetMaximum())
    h_ratio.Draw('PE same')
    leg_ratio.AddEntry(h_ratio, 'Embedded / Truth', 'P')
    setattr(self, 'h_ratio_{}_{}-{}_dR{}'.format(obs_label, min_pt, max_pt, min_theta*jetR), h_ratio)
    
    # Build ratio of embedded tagging purity
    setattr(self, 'h_ratio_tagged_{}'.format(obs_label), None)
    h_ratio_tagged = h_sum_tagged.Clone()
    h_ratio_tagged.SetMarkerStyle(self.MarkerArray[1])
    h_ratio_tagged.SetMarkerColor(self.ColorArray[0])
    h_ratio_tagged.Divide(h_sum)
    if h_ratio_tagged.GetMinimum() < myBlankHisto2.GetMinimum():
      myBlankHisto2.SetMinimum(0.8*h_ratio_tagged.GetMinimum())
    h_ratio_tagged.Draw('PE same')
    leg_ratio.AddEntry(h_ratio_tagged, 'Tagging purity', 'P')
    setattr(self, 'h_ratio_tagged_{}_{}-{}_dR{}'.format(obs_label, min_pt, max_pt, min_theta*jetR), h_ratio_tagged)
    
    leg_ratio.Draw('same')
    
    line = ROOT.TLine(self.xmin,1,self.xmax,1)
    line.SetLineColor(920+2)
    line.SetLineStyle(2)
    line.Draw('same')

    output_filename = os.path.join(output_dir, '{}/money_plot_{}_{}-{}_dR{}.pdf'.format(self.utils.grooming_label(grooming_setting),
                                          obs_label, min_pt, max_pt, self.utils.remove_periods(min_theta*jetR)))
    c.SaveAs(output_filename)
    c.Close()

  #---------------------------------------------------------------
  def plot_obs_projection_kappa(self, observable, h3D, h2D_truth, jetR, obs_label, obs_setting,
                          grooming_setting, min_pt, max_pt, output_dir):
    
    # Reset projections for normalization
    
    # zg
    h3D.GetYaxis().SetRangeUser(-10, self.xmax)
    h2D_truth.GetYaxis().SetRangeUser(-10, self.xmax)
    
    # Flag
    h3D.GetZaxis().SetRange(0, 11)

    # Get normalization for embeddeed case
    h_normalization = h3D.Project3D('y')
    h_normalization.SetName('h_normalization_emb_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))
    N_inclusive_emb = h_normalization.Integral()
    if N_inclusive_emb < 1e-3:
      print('Emb Integral is 0, check for problem')
      return
      
    # Get normalization for truth case
    h_normalization_truth = h2D_truth.ProjectionY()
    h_normalization_truth.SetName('h_normalization_truth_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))
    N_inclusive_truth = h_normalization_truth.Integral()
    if N_inclusive_truth < 1e-3:
      print('Truth Integral is 0, check for problem')
      return
      
    # Draw histogram
    c = ROOT.TCanvas('c','c: hist', 600, 650)
    c.cd()
    
    pad1 = ROOT.TPad('myPad', 'The pad',0,0.3,1,1)
    pad1.SetLeftMargin(0.2)
    pad1.SetTopMargin(0.04)
    pad1.SetRightMargin(0.04)
    pad1.SetBottomMargin(0.)
    pad1.Draw()
    pad1.cd()
    
    leg = ROOT.TLegend(0.65,0.5,0.8,0.8)
    self.utils.setup_legend(leg, 0.04)

    myBlankHisto = ROOT.TH1F('myBlankHisto','Blank Histogram', 20, self.xmin, self.xmax)
    myBlankHisto.SetNdivisions(505)
    myBlankHisto.SetMinimum(0.01)
    myBlankHisto.GetXaxis().SetTitle(self.xtitle)
    myBlankHisto.GetXaxis().SetTitleSize(30)
    myBlankHisto.GetXaxis().SetTitleFont(43)
    myBlankHisto.GetXaxis().SetTitleOffset(1.95)
    myBlankHisto.GetXaxis().SetLabelFont(43)
    myBlankHisto.GetXaxis().SetLabelSize(25)
    myBlankHisto.GetYaxis().SetTitleSize(25)
    myBlankHisto.GetYaxis().SetTitleFont(43)
    myBlankHisto.GetYaxis().SetTitleOffset(1.7)
    myBlankHisto.GetYaxis().SetLabelFont(43)
    myBlankHisto.GetYaxis().SetLabelSize(25)
    myBlankHisto.GetYaxis().SetNdivisions(505)
    myBlankHisto.GetYaxis().SetTitle(self.ytitle)
    myBlankHisto.Draw('E')
    
    c.cd()
    pad2 = ROOT.TPad('pad2', 'pad2', 0, 0.02, 1, 0.3)
    pad2.SetTopMargin(0)
    pad2.SetBottomMargin(0.35)
    pad2.SetLeftMargin(0.2)
    pad2.SetRightMargin(0.04)
    pad2.SetTicks(0,1)
    pad2.Draw()
    pad2.cd()
    
    leg_ratio = ROOT.TLegend(0.65,0.77,0.8,0.92)
    self.utils.setup_legend(leg_ratio, 0.1)
    
    myBlankHisto2 = myBlankHisto.Clone('myBlankHisto_C')
    ytitle = 'Ratio'
    myBlankHisto2.SetYTitle(ytitle)
    myBlankHisto2.SetXTitle(self.xtitle)
    myBlankHisto2.GetXaxis().SetTitleSize(30)
    myBlankHisto2.GetXaxis().SetTitleFont(43)
    myBlankHisto2.GetXaxis().SetTitleOffset(3.5)
    myBlankHisto2.GetXaxis().SetLabelFont(43)
    myBlankHisto2.GetXaxis().SetLabelSize(25)
    myBlankHisto2.GetYaxis().SetTitleSize(25)
    myBlankHisto2.GetYaxis().SetTitleFont(43)
    myBlankHisto2.GetYaxis().SetTitleOffset(2.)
    myBlankHisto2.GetYaxis().SetLabelFont(43)
    myBlankHisto2.GetYaxis().SetLabelSize(25)
    myBlankHisto2.GetYaxis().SetNdivisions(505)
    myBlankHisto2.SetMinimum(0.01)
    myBlankHisto2.SetMaximum(1.99)
    myBlankHisto2.Draw('')
    
    h_stack = ROOT.THStack('h_stack', 'stacked')
    h_sum = None
    h_sum_tagged = None
    
    # Loop over each flag
    for i in range(len(self.legend_list)):
      flag = i+1
      h3D.GetZaxis().SetRange(flag, flag)

      # Project onto 1D
      h1D = h3D.Project3D('y')
      h1D.SetName('h1D_{}'.format(i))
      h1D.Rebin(self.rebin_value)
      h1D.Scale(1./N_inclusive_emb, 'width')
        
      h1D.SetLineColor(self.ColorArray[i])
      h1D.SetFillColor(self.ColorArray[i])
      h1D.SetLineWidth(2)

      h_stack.Add(h1D)
      leg.AddEntry(h1D, self.legend_list[i], 'F')
      
      if h_sum:
        h_sum.Add(h1D)
      else:
        h_sum = h1D.Clone()
        h_sum.SetName('h_sum_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))

      if self.legend_list[i] in ['subleading', 'leading (swap)']:
        if h_sum_tagged:
          h_sum_tagged.Add(h1D)
        else:
          h_sum_tagged = h1D.Clone()
          h_sum_tagged.SetName('h_sum_tagged_{}_{}_{}-{}'.format(observable, obs_label, min_pt, max_pt))
    
    # Draw truth histogram
    h1D_truth = h2D_truth.ProjectionY()
    h1D_truth.Rebin(self.rebin_value)
    h1D_truth.Scale(1./N_inclusive_truth, 'width')
    h1D_truth.SetLineColor(1)
    h1D_truth.SetLineWidth(2)
    myBlankHisto.SetMaximum(2.3*h1D_truth.GetMaximum())
    leg.AddEntry(h1D_truth, 'Truth', 'L')
    
    pad1.cd()
    leg.Draw('same')
    h_stack.Draw('same hist')
    h1D_truth.Draw('same hist')
    
    text_latex = ROOT.TLatex()
    text_latex.SetNDC()
    
    x = 0.23
    y = 0.9
    text_latex.SetTextSize(0.05)
    text = 'PYTHIA8 embedded in thermal background'
    text_latex.DrawLatex(x, y, text)
        
    text = '#sqrt{#it{s_{#it{NN}}}} = 5.02 TeV'
    text_latex.DrawLatex(x, y-0.06, text)

    text = 'Charged jets   anti-#it{k}_{T}'
    text_latex.DrawLatex(x, y-0.12, text)
    
    text = '#it{R} = ' + str(jetR) + '   | #it{{#eta}}_{{jet}}| < {:.2f}'.format(self.eta_max - jetR)
    text_latex.DrawLatex(x, y-0.18, text)
   
    text = str(int(min_pt)) + ' < #it{p}_{T, ch jet}^{PYTHIA} < ' + str(int(max_pt)) + ' GeV/#it{c}'
    text_latex.DrawLatex(x, y-0.25, text)
   
    text = self.utils.formatted_grooming_label(grooming_setting)
    text_latex.DrawLatex(x, y-0.32, text)
    
    # Build ratio Embedded/Truth
    pad2.cd()
    setattr(self, 'h_ratio_{}'.format(obs_label), None)
    h_ratio = h_sum.Clone()
    h_ratio.SetMarkerStyle(21)
    h_ratio.SetMarkerColor(1)
    h_ratio.Divide(h1D_truth)
    if h_ratio.GetMaximum() > myBlankHisto2.GetMaximum():
      myBlankHisto2.SetMaximum(1.2*h_ratio.GetMaximum())
    h_ratio.Draw('PE same')
    leg_ratio.AddEntry(h_ratio, 'Embedded / Truth', 'P')
    setattr(self, 'h_ratio_{}_{}-{}'.format(obs_label, min_pt, max_pt), h_ratio)
    
    # Build ratio of embedded tagging purity
    setattr(self, 'h_ratio_tagged_{}'.format(obs_label), None)
    h_ratio_tagged = h_sum_tagged.Clone()
    h_ratio_tagged.SetMarkerStyle(self.MarkerArray[1])
    h_ratio_tagged.SetMarkerColor(self.ColorArray[0])
    h_ratio_tagged.Divide(h_sum)
    if h_ratio_tagged.GetMinimum() < myBlankHisto2.GetMinimum():
      myBlankHisto2.SetMinimum(0.8*h_ratio_tagged.GetMinimum())
    h_ratio_tagged.Draw('PE same')
    leg_ratio.AddEntry(h_ratio_tagged, 'Tagging purity', 'P')
    setattr(self, 'h_ratio_tagged_{}_{}-{}'.format(obs_label, min_pt, max_pt), h_ratio_tagged)
    
    leg_ratio.Draw('same')
    
    line = ROOT.TLine(self.xmin,1,self.xmax,1)
    line.SetLineColor(920+2)
    line.SetLineStyle(2)
    line.Draw('same')

    output_filename = os.path.join(output_dir, '{}/money_plot_{}_{}-{}.pdf'.format(self.utils.grooming_label(grooming_setting),
                                          obs_label, min_pt, max_pt))
    c.SaveAs(output_filename)
    c.Close()

  #---------------------------------------------------------------
  # Plot ratio of money plot for each groomer
  #---------------------------------------------------------------
  def plot_money_ratios(self, observable, output_dir, jetR, option):
  
    for i_theta, min_theta in enumerate(self.min_theta_list):
  
      for i_overlay, overlay_list in enumerate(self.plot_overlay_list):

        # Loop through pt slices, and plot 1D projection onto observable
        for i in range(0, len(self.pt_bins_reported) - 1):
          min_pt_truth = self.pt_bins_reported[i]
          max_pt_truth = self.pt_bins_reported[i+1]
          
          if observable in ['zg', 'theta_g']:
            self.plot_money_ratio(observable, output_dir, overlay_list, i_overlay, min_theta, jetR, min_pt_truth, max_pt_truth, option)
          elif observable in ['kappa', 'tf']:
            if i_theta == 0:
              self.plot_money_ratio(observable, output_dir, overlay_list, i_overlay, min_theta, jetR, min_pt_truth, max_pt_truth, option)
 
  #---------------------------------------------------------------
  # Plot ratio of money plot for each groomer
  #---------------------------------------------------------------
  def plot_money_ratio(self, observable, output_dir, overlay_list, i_overlay, min_theta, jetR, min_pt, max_pt, option):
  
    if option == 'Tagging purity':
      ratio_suffix = '_tagged'
      output_dir = os.path.join(output_dir, 'ratios_Purity')
    else:
      ratio_suffix = ''
      output_dir = os.path.join(output_dir, 'ratios_Embedded_Truth')
 
    self.utils.set_plotting_options()
    ROOT.gROOT.ForceStyle()

    # Draw histogram
    c = ROOT.TCanvas('c','c: hist', 600, 450)
    c.cd()
    
    pad1 = ROOT.TPad('myPad', 'The pad',0,0,1,1)
    pad1.SetLeftMargin(0.2)
    pad1.SetTopMargin(0.08)
    pad1.SetRightMargin(0.04)
    pad1.SetBottomMargin(0.2)
    pad1.SetTicks(0,1)
    pad1.Draw()
    pad1.cd()
  
    leg = ROOT.TLegend(0.6,0.62,0.8,0.8)
    self.utils.setup_legend(leg, 0.04)
    
    myBlankHisto = ROOT.TH1F('myBlankHisto','Blank Histogram', 1, self.xmin, self.xmax)
    myBlankHisto.SetNdivisions(505)
    myBlankHisto.SetXTitle(self.xtitle)
    myBlankHisto.SetYTitle(option)
    myBlankHisto.SetMaximum(2.49)
    myBlankHisto.SetMinimum(0.01) # Don't draw 0 on top panel
    myBlankHisto.GetXaxis().SetTitleSize(0.06)
    myBlankHisto.GetXaxis().SetTitleOffset(1.2)
    myBlankHisto.GetXaxis().SetLabelSize(0.05)
    myBlankHisto.GetYaxis().SetTitleSize(0.05)
    myBlankHisto.GetYaxis().SetTitleOffset(1.2)
    myBlankHisto.GetYaxis().SetLabelSize(0.05)
    myBlankHisto.Draw('E')
  
    i_reset = 0
    for i, subconfig_name in enumerate(self.obs_subconfig_list):
    
      if subconfig_name not in overlay_list:
        continue

      obs_setting = self.obs_settings[i]
      grooming_setting = self.grooming_settings[i]
      obs_label = self.utils.obs_label(obs_setting, grooming_setting)
      self.set_zmin(observable, grooming_setting)
      
      if observable in ['zg', 'theta_g']:
        h_ratio = getattr(self, 'h_ratio{}_{}_{}-{}_dR{}'.format(ratio_suffix, obs_label, min_pt, max_pt, min_theta*jetR))
      elif observable in ['kappa', 'tf']:
        h_ratio = getattr(self, 'h_ratio{}_{}_{}-{}'.format(ratio_suffix, obs_label, min_pt, max_pt))
      h_ratio.SetMarkerStyle(0)
      h_ratio.SetLineStyle(0)
      h_ratio.SetLineColor(0)
      h_ratio.SetFillColor(self.ColorArray[i_reset])
      h_ratio.SetFillColorAlpha(self.ColorArray[i_reset], 0.75)
      
      if h_ratio.GetMaximum() > 0.5*myBlankHisto.GetMaximum():
        myBlankHisto.SetMaximum(2*h_ratio.GetMaximum())

      i_reset += 1
      h_ratio.SetLineWidth(2)
      h_ratio.Draw('E3 same')
      
      leg.AddEntry(h_ratio, self.utils.formatted_grooming_label(grooming_setting), 'F')

    leg.Draw('same')
    
    line = ROOT.TLine(self.xmin,1,self.xmax,1)
    line.SetLineColor(920+2)
    line.SetLineStyle(2)
    line.Draw('same')
    
    text_latex = ROOT.TLatex()
    text_latex.SetNDC()
    
    x = 0.23
    y = 0.87
    dy = 0.05
    text_latex.SetTextSize(0.04)
    text = 'PYTHIA8 embedded in thermal background'
    text_latex.DrawLatex(x, y, text)
    
    text = '#sqrt{#it{s_{#it{NN}}}} = 5.02 TeV'
    text_latex.DrawLatex(x, y-dy, text)

    text = 'Charged jets   anti-#it{k}_{T}'
    text_latex.DrawLatex(x, y-2*dy, text)
    
    text = '#it{R} = ' + str(jetR) + '   | #it{{#eta}}_{{jet}}| < {:.1f}'.format(self.eta_max-jetR)
    text_latex.DrawLatex(x, y-3*dy, text)
  
    text = str(int(min_pt)) + ' < #it{p}_{T, ch jet}^{PYTHIA} < ' + str(int(max_pt)) + ' GeV/#it{c}'
    text_latex.DrawLatex(x, y-4*dy-0.02, text)
    
    if observable in ['zg', 'theta_g']:
      if min_theta > 1e-3:
        text = '#Delta#it{{R}} > {}'.format(min_theta*jetR)
        text_latex.DrawLatex(x, y-5*dy-0.04, text)
  
      output_filename = os.path.join(output_dir, 'money_plot_ratio_{}-{}_dR{}_{}.pdf'.format(
                                     min_pt, max_pt, self.utils.remove_periods(min_theta*jetR),
                                     i_overlay))
                                     
    elif observable in ['kappa', 'tf']:
      output_filename = os.path.join(output_dir, 'money_plot_ratio_{}-{}_{}.pdf'.format(
                                     min_pt, max_pt, i_overlay))
                                       
    c.SaveAs(output_filename)
    c.Close()

  #---------------------------------------------------------------
  # Set xmin for zg
  #---------------------------------------------------------------
  def set_zmin(self, observable, grooming_setting):
  
    if observable == 'zg':
      self.zmin = 0.
      for key, value in grooming_setting.items():
        if key == 'sd' and np.abs(value[1]) < 1e-3:
          self.zmin = value[0]

  #---------------------------------------------------------------
  # Create a single output subdirectory
  #---------------------------------------------------------------
  def create_output_subdir(self, output_dir, name):

    output_subdir = os.path.join(output_dir, name)
    setattr(self, 'output_dir_{}'.format(name), output_subdir)
    if not os.path.isdir(output_subdir):
      os.makedirs(output_subdir)

    return output_subdir

#----------------------------------------------------------------------
if __name__ == '__main__':

  # Define arguments
  parser = argparse.ArgumentParser(description='Jet substructure analysis')
  parser.add_argument('-c', '--configFile', action='store',
                      type=str, metavar='configFile',
                      default='analysis_config.yaml',
                      help='Path of config file for analysis')

  # Parse the arguments
  args = parser.parse_args()
  
  print('Configuring...')
  print('configFile: \'{0}\''.format(args.configFile))
  
  # If invalid configFile is given, exit
  if not os.path.exists(args.configFile):
    print('File \"{0}\" does not exist! Exiting!'.format(args.configFile))
    sys.exit(0)

  analysis = PlotGroomers(config_file = args.configFile)
  analysis.plot_groomers()
