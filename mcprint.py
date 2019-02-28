#!/usr/bin/env python3
import sys, os
import math
import platform
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QProgressDialog
from mcpgui import *
#from mcpdialog import *
from mcpi.minecraft import Minecraft
import mcpi.block as block
from blockarea import * 

##########################################################################
# mcprint.py [args]
# GUI app for capturing 3D model from Minecraft and converting into 
# OpenSCAD model for 3D printing
# 
# Copyright 2019 Stewart Watkiss
# Licensed under GPL-3.0-or-later
# 
# Arguments:
#     --notpi    (disable Raspberry Pi detection - do not use this 
#                 with Minecraft Pi edition)
#     --useundo  (enable auto undo creation for Minecraft Pi edition,
#                 no effect on other editions.) 
#                 Warning - performance issues for large capture areas
#
###########################################################################


# x (longitude), y (height), z (latitude)
# getBlocks returns in incrementing order of z, x, y

undo_buildplate_filename = "undo-build.tmp"
undo_otherblocks_filename = "undo-print.tmp"

debug = True

# No block is actually an air block
no_block = block.AIR.id



# stair blocks - data can be 0=East, 1=West, 2=South, 3=North
# bit and with 0x4 to determine if upside down
stair_blocks = [53,67,164,203]
# half blocks - slabs / planks
half_blocks = [5,44,126]
# Exclude blocks (eg. air, lava, water)
# These are kept in minecraft file, but excluded from OpenSCAD
# For details of blocks see https://www.stuffaboutcode.com/p/minecraft-api-reference.html
# Glass is excluded - so will be a gap
exclude_blocks = [0,6,8,9,10,11,30,31,37,38,39,40,50,51,65,83,95,102]

class Mcprint(QMainWindow):

    mc = None
        
    # Print area is the area that will be printed
    print_area = BlockArea()
    # Build plate is the area 1 block below the print area where the buildplate 
    # normally is. This will normally be set to a block type, but may be invisible
    build_plate = BlockArea()
     
    # Platform = other, can be linux or windows
    # If change to RaspberryPi then drop use of getBlocks
    mcpi_platform = 'raspberryjuice'
    full_undo = True
    
    # When file saved store here so can use in OpenSCAD
    minecraft_saved_file = None
    
    # Save smallest and largest x,y,z values for print size 
    # These will be replaced with arrays
    # Note that this uses xyz openscad rather than minecraft
    # Excludes air blocks (includes all other blocks)
    print_dimension_smallest = None
    print_dimension_largest = None
    
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        #self.progress_bar = McpDialog()   
        
        override_pi = False
        override_undo = False
        # Handle command line arguments
        if any("--notpi" in this_arg for this_arg in sys.argv):
            override_pi = True
        if any("--useundo" in this_arg for this_arg in sys.argv):
            override_undo = True
        
        # Detect if RaspberryPi (as Minecraft Pi has limited functionality)
        # This is only approximate - detects arm processor if running full 
        # minecraft client on a ARM processor then can override with --notpi
        this_system = platform.platform()
        if (not override_pi and "arm" in this_system):
            print ("Raspberry Pi detected - limited functionality")
            # Set Raspberry Pi (eg. don't use getBlocks as not supported)
            self.mcpi_platform = 'raspberrypi'
            # Disable undo for performance (unless override)
            if (not override_undo):
                full_undo = False
        
        # Setup handlers (slots)
        self.ui.pushButtonCreate.clicked.connect(self.create_print_area)
        self.ui.pushButtonRemove.clicked.connect(self.restore_buildplate)
        self.ui.pushButtonClearArea.clicked.connect(self.clear_area_above)
        self.ui.pushButtonResetArea.clicked.connect(self.restore_area_above)
        self.ui.pushButtonSaveCapture.clicked.connect(self.save_capture)
        self.ui.pushButtonLoadMBFile.clicked.connect(self.load_mbf)
        self.ui.pushButtonSaveSCAD.clicked.connect(self.save_scad)
        self.ui.pushButtonSaveSCADAs.clicked.connect(self.save_scad_as)
        self.ui.doubleSpinBoxBlockSize.valueChanged.connect(self.update_print_size)
        self.ui.actionConnect.triggered.connect(self.connect_to_minecraft)
        self.ui.actionQuit.triggered.connect(self.exit)
        self.show()
        
        #self.progress_bar.ui.buttonBox.accepted.connect(self.accept)
        #self.progress_bar.ui.buttonBox.rejected.connect(self.cancel_progress)
        
        # Check for restore files and enable buttons
        if (os.path.isfile(undo_buildplate_filename)):
            self.ui.pushButtonRemove.setEnabled(True)
        if (os.path.isfile(undo_otherblocks_filename)):
            self.ui.pushButtonResetArea.setEnabled(True)

        
    # Returns true if we think this is a raspberry pi, else false
    def is_pi (self):
        if (self.mcpi_platform == 'raspberrypi'):
            return True
        return False
        
              
    # Change blocks for buildplate
    # Will only create on first layer - so size_y is ignored
    # Undo file (if required) should be created before this
    def draw_buildplate(self, start_position, size, block_type):
        #print ("Drawing build plate {}".format(block_type))
        (start_x,start_y,start_z) = start_position
        (size_x,size_y,size_z) = size
        
        # Does not support data values (eg. different textures)
        self.mc.postToChat ("Setting build plate blocks")
        self.mc.setBlocks(start_x,start_y,start_z,start_x+size_x-1,start_y+size_y-1,start_z+size_z-1,block_type)



    # Creates print area and sets buildplate 
    # Does not clear space above
    def create_print_area(self):
        self.connect_to_minecraft() 
        self.mc.postToChat ("Creating print area")
    
        # Get position of player
        position = self.mc.player.getTilePos()
        #print ("My print area position is "+str(position))
        
        # Get size of area from GUI
        self.print_area.set_size((
            self.ui.spinBoxBuildX.value(),
            self.ui.spinBoxBuildY.value(),
            self.ui.spinBoxBuildZ.value()
            ))
        
        # Get offset from GUI
        offset = self.ui.spinBoxYOffset.value()
        
        # Get block type from GUI
        selected_block = self.ui.comboBoxBaseplate.itemText(self.ui.comboBoxBaseplate.currentIndex())
        # Convert block text (from gui) to block_id
        buildplate_block = self.convert_to_blockid(selected_block)
        
        # Set start position based Where player is centre X,Z and Y = current position + offset
        self.print_area.set_middle ((position.x, position.y + offset, position.z))
        # Get the actual start position and size back as a temporary variable
        print_area_size = self.print_area.get_size()
        print_area_start = self.print_area.get_start()
        
        #print ("Size "+str(print_area_size)+" start "+str(print_area_start))
        
        # Set build plate based on position below print area
        self.build_plate.set_size((print_area_size[0],1,print_area_size[2]))
        self.build_plate.set_start((print_area_start[0],print_area_start[1] - 1,print_area_start[2]))
        
        
        ## TODO - check if existing backup whether to keep or not
        
        # Create undo file for buildplate
        # Created for Pi or RaspberryJuice regardless
        #print ("About to save blocks - start "+str(self.build_plate.get_start())+" size "+str(self.build_plate.get_size()))
        self.save_blocks (undo_buildplate_filename, self.build_plate.get_start(), self.build_plate.get_size(), True)
        
        # Check if transparent (ie. don't create any buildplate)
        if (buildplate_block != -1):
            # Create buildplate
            self.draw_buildplate (self.build_plate.get_start(), self.build_plate.get_size(), buildplate_block)
            self.build_plate.set_visible(True)
        else:
            self.build_plate.set_visible(False)

        self.ui.pushButtonRemove.setEnabled(True)
        self.ui.pushButtonClearArea.setEnabled(True)
        
        self.ui.labelBuildareaInfo.setText("Build plate enabled ({},{},{}) to ({},{},{})"
            .format(print_area_start[0],print_area_start[1],print_area_start[2],
            print_area_start[0]+print_area_size[0],print_area_start[1]+print_area_size[1],print_area_start[2]+print_area_size[2],
            ))
        self.ui.pushButtonSaveCapture.setEnabled(True)
         
    
    
    # save minecraft block data (undo file or print export)
    # overwrites contents of save_filename
    # get_all_data is an optional parameter. If set to true then it will get the block
    # data for all blocks. This is more accurate (less loss of information), but 
    # much slower - recommended for build plate, but not large areas
    def save_blocks (self, save_filename, start_position, size, get_all_data = False):
        start_x,start_y,start_z = start_position
        size_x,size_y,size_z = size
        
        #print ("Saving blocks {},{},{} size {},{},{} {}".format(
        #    start_x,start_y,start_z,
        #    size_x,size_y,size_z,
        #    get_all_data))
        
        self.print_dimension_smallest = None
        
        cancelled = False
        
        # Enclose within try catch in case of file errors
        try:
            with open(save_filename, 'w') as file:               
                # Show save dialog whilst reading data
                #self.progress_bar.start()
                #print ("Creating progress bar")
                progress = QtWidgets.QProgressDialog("Reading blocks", "Cancel", 0, 100, self)
                progress.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint | QtCore.Qt.CustomizeWindowHint)
                progress.setModal(True)
                progress.setMinimumDuration(0)
                progress.setCancelButton(None)  # Remove the cancel button. Possibly add a slot that has load() check and cancel
                progress.setValue(1)  # Set an initial value to show the dialog
                
                
                if (not self.is_pi() and get_all_data == False):
                    blocks = list(self.mc.getBlocks(start_x,start_y,start_z,start_x+size_x-1,start_y+size_y-1,start_z+size_z-1))
                # Data from getBlocks is in z,x,y - so use that order to read out of getblocks (or test each block individually)     
                index = 0
                for y in range (0, size_y):
                    for x in range(0, size_x):
                        for z in range (0, size_z):
                            block_pos = (start_x+x, start_y+y, start_z+z)
                            if (self.is_pi() or get_all_data == True):
                                # Todo - may take a while
                                block_obj = self.mc.getBlockWithData(block_pos[0], block_pos[1], block_pos[2])
                                block_id = block_obj.id
                                block_data = block_obj.data
                            else :
                                block_data = 0
                                block_id = blocks[index]
                                # if either of these then retrieve again to get the data
                                if (block_id in stair_blocks or block_id in half_blocks):
                                    block_obj = self.mc.getBlockWithData(block_pos[0], block_pos[1], block_pos[2])
                                    block_id = block_obj.id
                                    block_data = block_obj.data
                            # Get extra data
                            file.write("{},{},{},{},{}\n".format(block_pos[0],block_pos[1],block_pos[2],block_id,block_data))
                            
                            # If id is > air block then count it as a valid block
                            # record smallest and largest so we can workout size
                            # x,y,z are in minecraft format so convert to scad
                            if block_id > block.AIR.id:
                                if (self.print_dimension_smallest == None):
                                    # min / max values
                                    self.print_dimension_smallest = [x, z, y]
                                    self.print_dimension_largest = [x, z, y]
                                else:
                                    if (x < self.print_dimension_smallest[0]):
                                        self.print_dimension_smallest[0] = x
                                    if (z < self.print_dimension_smallest[1]):
                                        self.print_dimension_smallest[1] = z
                                    if (y < self.print_dimension_smallest[2]):
                                        self.print_dimension_smallest[2] = y
                                    if (x > self.print_dimension_largest[0]):
                                        self.print_dimension_largest[0] = x
                                    if (z > self.print_dimension_largest[1]):
                                        self.print_dimension_largest[1] = z
                                    if (y > self.print_dimension_largest[2]):
                                        self.print_dimension_largest[2] = y
                            
                            
                            index += 1
                    if progress.wasCanceled():
                        cancelled = True
                        break

                    progress.setValue((y / size_y ) * 100)
                    
                #print ("progress done")
                #progress.close()
                progress.setValue(100)

        except Exception as e:
            # Unable to write to file - warn to console
            if (debug == True):
                print ("Unable to write to file "+save_filename+str(e))



    def restore_buildplate (self):
        self.connect_to_minecraft()
        self.restore_undo (undo_buildplate_filename)
        
    def restore_area_above (self):
        self.connect_to_minecraft()
        self.restore_undo (undo_otherblocks_filename)
                
    # Restores content of undo file - either just buildplate or entire
    # use whichever file is appropriate - eg buildplate / area undo file
    def restore_undo (self, filename):
                
        # Get stats about the restore file (bottomleft, topright, mostusedblockid)
        info = self.get_file_info (filename)
        
        # Make sure we have returned a valid entry (valid file)
        if (info['mostusedblock'] == None):
            print ("No undo file, or undo file is corrupt")
            return
        
        # First set all positions to most common block
        # Most common block is used for performance reasons as each setBlock
        # adds delay in executing
        # Set all blocks to the most common and then replace those that don't 
        # match. Improves time, more significant with large number of blocks
        # of same type eg Air Blocks
        # Alternative is to use getBlocks and compare to decide if need to change 
        # block. Which could be faster in some circumstances 
        # Disadvantage of alt is that this would not always improve performance
        # if all blocks are different from the undo file and not with buildplate
        # Also this alternative will not work with Raspberry Pi (which doesn't
        # have getBlocks() )
        # Note that mostusedblock assumes data = 0. The block is highly likely
        # to be Air - so data is not relevant
        

        self.mc.setBlocks(
            info['bottomleft'][0],info['bottomleft'][1],info['bottomleft'][2],
            info['topright'][0],info['topright'][1],info['topright'][2],
            info['mostusedblock']
            )
        
        # Now replace all blocks which don't match the most common (if match undo type)
        with open(filename, 'r') as fp:
            while True:
                this_line = fp.readline()
                if not this_line :
                    break
                # split based on comma into x,y,z,block_id
                #split_line = this_line.split(",")
                split_line = [int(x) for x in this_line.split(",")]
                # skip if already matches mostcommon
                if (split_line[3] == info['mostusedblock']):
                    continue
                # Reach here then we need to update
                self.mc.setBlock(split_line[0], split_line[1], split_line[2], split_line[3])

        # Move player on top of the highest block in current x,z position 
        position = self.mc.player.getTilePos()
        # Work through that position x,z looking for highest y with air
        for y in range (info['topright'][1],info['bottomleft'][1],-1):
            block_id = self.mc.getBlock(position.x, y, position.z)
            if (block_id != no_block):
                self.mc.player.setPos (position.x, y+1, position.z)
                break

                
                
    # From file get information on the restore file
    # Restore file must be cuboid (eg buildplate or full undo file)
    def get_file_info (self, filename):
        lowest_pos = [None, None, None]
        highest_pos = [None, None, None]
        block_use = {}
        
        
        with open(filename, 'r') as fp:
            while True:
                this_line = fp.readline()
                if not this_line :
                    break
                # split based on comma into x,y,z,block_id
                split_line = [int(x) for x in this_line.split(",")]
                # If first line set as lowest and highest
                if (lowest_pos[0] == None):
                    lowest_pos = [split_line[0],split_line[1],split_line[2]]
                    highest_pos = [split_line[0],split_line[1],split_line[2]]
                # If any of the co-ordinate positions are lower then replace
                # May result in swapping with one where that co-ord is lower,but a different higher
                # eventually will result in finding the lowest for all as that 
                # can't be swapped out - same for highest but opposite
                elif (split_line[0] < lowest_pos[0] or split_line[1] < lowest_pos[1] or split_line[2] < lowest_pos[2]):
                    lowest_pos = [split_line[0],split_line[1],split_line[2]]
                elif (split_line[0] > highest_pos[0] or split_line[1] > highest_pos[1] or split_line[2] > highest_pos[2]):
                    highest_pos = [split_line[0],split_line[1],split_line[2]]
                    
                # increment block count (or create if new) [only if data = 0]
                if (split_line[4] == 0):
                    if (split_line[3] in block_use):
                        block_use[split_line[3]] += 1
                    else:
                        block_use[split_line[3]] = 1

        most_common_block = None
        most_common_block_count = 0
        # get most common block from block_use
        for key, value in block_use.items():
            if (value > most_common_block_count):
                most_common_block = key
                most_common_block_count = value

        return {'bottomleft':lowest_pos, 'topright':highest_pos, 'mostusedblock':most_common_block}      

    # Clears any blocks in the area above the buildplate
    def clear_area_above (self):       
        start_pos = self.print_area.get_start()
        size = self.print_area.get_size()
        
        ## TODO - prompt if unable to create backup
        if (self.full_undo):
            self.save_blocks (undo_otherblocks_filename, start_pos, size)
            self.ui.pushButtonResetArea.setEnabled(True)
        
        (start_x,start_y,start_z) = start_pos
        (size_x, size_y, size_z) = size
        self.mc.setBlocks(
            start_x,start_y,start_z,
            start_x+size_x-1, start_y+size_y-1, start_z+size_z-1,
            no_block
            )
        

    # Converts from string (used in GUI) to blockid
    def convert_to_blockid (self, block_text):
        block_names = {
            'transparent': -1,           # Special case - don't change block
            'air': block.AIR.id,
            'stone': block.STONE.id,
            'bedrock': block.BEDROCK.id,
            'wood': block.WOOD.id,
            'wool': block.WOOL.id,
            'obsidian': block.OBSIDIAN.id
            }
        if (block_text.lower() in block_names):
            return block_names[block_text.lower()]
        else:
            return block.AIR.id
            
            
    # Update filename through here - then it can update the OpenSCAD tab        
    def set_mbf(self, filename):
        self.ui.pushButtonSaveSCAD.setEnabled(True)
        self.ui.pushButtonSaveSCADAs.setEnabled(True)
        self.minecraft_saved_file = filename
        #### Todo shorten text (eg strip path information to just leave filename)
        self.ui.labelFileSelected.setText("File: {}".format(filename))
        self.update_print_size()
            
    def load_mbf(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()","data-files","Minecraft Blocks File (*.mbf);;All Files (*)", options=options)
        self.set_mbf(filename)
        # Read through file to get dimensions
        self.load_mbf_dimensions(filename)
        

    def save_scad(self):
        (filepath, extension) = os.path.splitext(self.minecraft_saved_file)
        if (extension == '.mbf'):
            filename = filepath + ".scad"
        else:
            filename = self.minecraft_saved_file + ".scad"
        self.convert_to_openscad_file(self.minecraft_saved_file, filename)
    
    def save_scad_as(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","data-files","OpenSCAD File (*.scad);;All Files (*)", options=options)
        # Check for extension - if none then add one 
        if not ("." in filename):
            filename += ".scad"
        self.convert_to_openscad_file(self.minecraft_saved_file, filename)


    # Requests filename from user, captures print area and saves to file
    def save_capture(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","data-files","Minecraft Blocks File (*.mbf);;All Files (*)", options=options)
        # Check for extension - if none then add one 
        if not ("." in filename):
            filename += ".mbf"
        start_pos = self.print_area.get_start()
        size = self.print_area.get_size()
        #print ("Saving capture - start pos "+str(start_pos)+" - size "+str(size))
        self.save_blocks (filename, start_pos, size)

        #### Todo - confirmation complete (or for long saves - status bar)
        #### Todo - load file into openSCAD export tab
                
        self.set_mbf (filename)
        
        
    def create_openscad (self):
        self.convert_to_openscad_file ()
        #### HERE Need to indicate complete
    
    
    def convert_to_openscad_file (self, minecraft_filename, scad_filename):
        # offset values for x, y, z
        offset = [None,None,None]
        with open(minecraft_filename, 'r') as infile:
            with open(scad_filename, 'w') as outfile:
                # import module file
                outfile.write("include <minecraft-print.scad>\n")
                # Set blocksize variable
                outfile.write("block_size = {};\n".format(self.ui.doubleSpinBoxBlockSize.value()))

                while True:
                    this_line = infile.readline()
                    if not this_line :
                        break
                    # split based on comma into x,y,z,block_id
                    #split_line = [int(x) for x in this_line.split(",")]
                    ### Minecraft uses z for y axis, so swap with y when loading as OpenSCAD
                    (x,z,y,blockid,data) = [int(i) for i in this_line.split(",")]
                    
                    # minecraft x axis is the opposite way to openSCAD, so invert here
                    x *= -1
                    
                    # If first line then set the offsets
                    # This moves the blocks to be near to the 0,0,0 axis
                    # Due to the way we have to invert the x axis (above) this means that the
                    # x axis is negative. 
                    # This is not classified as a bug as OpenSCAD works just as well with the 
                    # X axis being negative as positive.
                    # If want to change then need to read file in twice or to create
                    # offset as a variable and then add that later.
                    if (offset[0] == None):
                        offset[0] = -1 * x
                        offset[1] = -1 * y
                        offset[2] = -1 * z
                        
                        
                    # Ignore any air blocks
                    if (blockid in exclude_blocks):
                        continue
                    # Ignore any less than 0 (although should not be any)
                    elif (blockid < 0):
                        continue
                    elif (blockid in stair_blocks):
                        # pass data to the stair_block
                        outfile.write("translate([{},{},{}]){}({});\n".format(
                            "block_size*" + str(x + offset[0]),
                            "block_size*" + str(y + offset[1]),
                            "block_size*" + str(z + offset[2]),
                            "stair_block", data))
                        
                    ### Todo - analyze stair blocks. If stair has no adjacent
                    # on one side, but does at right angle, then change to a 
                    # corner block
                    
                    elif (blockid in half_blocks):
                        outfile.write("translate([{},{},{}]){}({});\n".format(
                            "block_size*" + str(x + offset[0]),
                            "block_size*" + str(y + offset[1]),
                            "block_size*" + str(z + offset[2]),
                            "half_block", data))
                        
                    # If not handled above then use the default block
                    else:
                        outfile.write("translate([{},{},{}]){}();\n".format(
                            "block_size*" + str(x + offset[0]),
                            "block_size*" + str(y + offset[1]),
                            "block_size*" + str(z + offset[2]),
                            "standard_block"))
                        

    # Read through mbf file looking for dimensions
    def load_mbf_dimensions (self, filename):
        self.print_dimension_smallest = None
        
        with open(filename, 'r') as infile:
            while True:
                this_line = infile.readline()
                if not this_line :
                    break
                ### Minecraft uses z for y axis, so swap with y when loading as OpenSCAD
                (x,y,z,blockid,data) = [int(i) for i in this_line.split(",")]
                # If id is not in exclude count it as a valid block
                # record smallest and largest so we can workout size
                # x,y,z are in minecraft format so convert to scad
                if not blockid in exclude_blocks:
                    if (self.print_dimension_smallest == None):
                        # min / max values
                        self.print_dimension_smallest = [x, z, y]
                        self.print_dimension_largest = [x, z, y]
                    else:
                        if (x < self.print_dimension_smallest[0]):
                            self.print_dimension_smallest[0] = x
                        if (z < self.print_dimension_smallest[1]):
                            self.print_dimension_smallest[1] = z
                        if (y < self.print_dimension_smallest[2]):
                            self.print_dimension_smallest[2] = y
                        if (x > self.print_dimension_largest[0]):
                            self.print_dimension_largest[0] = x
                        if (z > self.print_dimension_largest[1]):
                            self.print_dimension_largest[1] = z
                        if (y > self.print_dimension_largest[2]):
                            self.print_dimension_largest[2] = y
        self.update_print_size()



    def connect_to_minecraft (self):
        if (self.mc == None):
            try:
                self.mc = Minecraft.create()
            except Exception as e:
                print ("Error connecting to Minecraft\nPlease ensure that Minecraft is running")
            
    
    # Updates the display of the print size
    def update_print_size(self):
        # if dimensions are not set then return empty string
        if (self.print_dimension_largest == None or self.print_dimension_smallest == None):
            self.ui.labelPrintSize.setText("")
            return
        # Get size of blocks
        block_size = self.ui.doubleSpinBoxBlockSize.value()
        
        # Create string for value
        size_string = "{} , {} , {}".format(
            (self.print_dimension_largest[0] - self.print_dimension_smallest[0] + 1) * block_size,
            (self.print_dimension_largest[1] - self.print_dimension_smallest[1] + 1) * block_size,
            (self.print_dimension_largest[2] - self.print_dimension_smallest[2] + 1) * block_size
            )
        self.ui.labelPrintSize.setText(size_string)



    def exit(self):
        sys.exit()
    

    def accept(self):
        pass
    
    def cancel_progress(self):
        pass


if __name__ == "__main__":

    app = QApplication(sys.argv)
    w = Mcprint()
    w.show()
    sys.exit(app.exec_())

    
