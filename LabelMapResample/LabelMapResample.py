import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import sitkUtils
import LabelStatistics

#
# LabelMapResample
#

class LabelMapResample(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "LabelMapResample" # TODO make this more human readable by adding spaces
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["Junichi Tokuda (BWH)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This scripted module resamples a label map. 
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# LabelMapResampleWidget
#

class LabelMapResampleWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    #--------------------------------------------------
    # For debugging
    #
    # Reload and Test area
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    reloadCollapsibleButton.collapsed = True
    
    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "ComputeT2Star Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)
    #
    #--------------------------------------------------


    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # input volume selector
    #
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.inputSelector.selectNodeUponCreation = True
    self.inputSelector.addEnabled = False
    self.inputSelector.removeEnabled = False
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene( slicer.mrmlScene )
    self.inputSelector.setToolTip( "Pick the input to the algorithm." )
    parametersFormLayout.addRow("Input Volume: ", self.inputSelector)

    #
    # output volume selector
    #
    self.outputSelector = slicer.qMRMLNodeComboBox()
    self.outputSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputSelector.selectNodeUponCreation = True
    self.outputSelector.addEnabled = True
    self.outputSelector.removeEnabled = True
    self.outputSelector.noneEnabled = True
    self.outputSelector.showHidden = False
    self.outputSelector.showChildNodeTypes = False
    self.outputSelector.setMRMLScene( slicer.mrmlScene )
    self.outputSelector.setToolTip( "Pick the output to the algorithm." )
    parametersFormLayout.addRow("Output Volume: ", self.outputSelector)

    #
    # sigma value
    #
    self.imageSigmaSliderWidget = ctk.ctkSliderWidget()
    self.imageSigmaSliderWidget.singleStep = 0.1
    self.imageSigmaSliderWidget.minimum = 0.0
    self.imageSigmaSliderWidget.maximum = 5.0
    self.imageSigmaSliderWidget.value = 1.0
    self.imageSigmaSliderWidget.setToolTip("Set sigma value for computing the output image. Voxels that have intensities lower than this value will set to zero.")
    parametersFormLayout.addRow("Image sigma", self.imageSigmaSliderWidget)

    #
    # slice divide
    #
    self.sliceDivideSliderWidget = ctk.ctkSliderWidget()
    self.sliceDivideSliderWidget.singleStep = 1
    self.sliceDivideSliderWidget.minimum = 1
    self.sliceDivideSliderWidget.maximum = 50
    self.sliceDivideSliderWidget.value = 1
    self.sliceDivideSliderWidget.setToolTip("Set a number of slices divided from each slice. For example, if the slice thickness of the input volume is 5 mm, and sliceDivide is '2', the slice thickness of the resultant image will be 5/2 = 2.5mm.")
    parametersFormLayout.addRow("Slice Divide", self.sliceDivideSliderWidget)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.inputSelector.currentNode() and self.outputSelector.currentNode()

  def onApplyButton(self):
    logic = LabelMapResampleLogic()
    imageSigma = self.imageSigmaSliderWidget.value
    sliceDivide = self.sliceDivideSliderWidget.value
    logic.run(self.inputSelector.currentNode(), self.outputSelector.currentNode(), sliceDivide, imageSigma)

#
# LabelMapResampleLogic
#

class LabelMapResampleLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def hasImageData(self,volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True

  def run(self, inputVolume, outputVolume, sliceDivide, sigma):
    """
    Run the actual algorithm
    """

    if inputVolume==None or outputVolume==None:
      slicer.util.errorDisplay('Input volume is the same as output volume.')
      return False

    logging.info('Processing started')

    ## Resampling
    spacing = inputVolume.GetSpacing()

    highResInputNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
    slicer.mrmlScene.AddNode(highResInputNode)
    highResInputNode.SetName("Input-HR")
    
    spacingParam = '%f,%f,%f' % (spacing[0], spacing[1], spacing[2]/sliceDivide)
    print spacingParam
    resampleCLIParam = {'InputVolume': inputVolume.GetID(), 'OutputVolume': highResInputNode.GetID(), 'outputPixelSpacing': spacingParam, 'interpolationType': 'nearestNeighbor'}
    print resampleCLIParam

    resampleCLINode = slicer.cli.run(slicer.modules.resamplescalarvolume, None, resampleCLIParam, wait_for_completion=True)

    labelImage = sitk.Cast(sitkUtils.PullFromSlicer(highResInputNode.GetID()), sitk.sitkInt8)
    labelStatistics = sitk.LabelStatisticsImageFilter()
    labelStatistics.Execute(labelImage, labelImage)
    labels = labelStatistics.GetLabels()
    
    first = True
    for l in labels:
    
      if l == 0:
        continue

      tempLabelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
      slicer.mrmlScene.AddNode(tempLabelNode)
      tempLabelNodeName = "label-%d" % l
      tempLabelNode.SetName(tempLabelNodeName)
    
      print "Processing label=%d\n" % l
    
      smoothCLIParams = {'inputVolume': highResInputNode.GetID(), 'outputVolume': tempLabelNode.GetID(), 'labelToSmooth': int(l),  'numberOfIterations': 50, 'maxRMSError': 0.01, 'gaussianSigma': sigma}
      
      smoothCLINode = slicer.cli.run(slicer.modules.labelmapsmoothing, None, smoothCLIParams, wait_for_completion=True)

      tempLabelImage = sitk.Cast(sitkUtils.PullFromSlicer(tempLabelNode.GetID()), sitk.sitkInt8)
      tempLabelImage = tempLabelImage * l
      sitkUtils.PushToSlicer(tempLabelImage, tempLabelNodeName, 0, True) 
      tempLabelNode = slicer.util.getNode(tempLabelNodeName)
    
      combineCLIParam = None
    
      if first:
        combineCLIParam = {'InputLabelMap_A': tempLabelNode.GetID(), 'InputLabelMap_B': tempLabelNode.GetID(), 'OutputLabelMap': outputVolume.GetID()}
        first = False
      else:
        combineCLIParam = {'InputLabelMap_A': tempLabelNode.GetID(), 'InputLabelMap_B': outputVolume.GetID(), 'OutputLabelMap': outputVolume.GetID()}
    
      combineCLINode = slicer.cli.run(slicer.modules.imagelabelcombine, None, combineCLIParam, wait_for_completion=True)
      
      slicer.mrmlScene.RemoveNode(tempLabelNode)

    slicer.mrmlScene.RemoveNode(highResInputNode)
    logging.info('Processing completed')

    return True


class LabelMapResampleTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LabelMapResample1()

  def test_LabelMapResample1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = LabelMapResampleLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
