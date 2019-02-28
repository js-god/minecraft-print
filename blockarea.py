import math

class BlockArea():
    
    
    def __init__ (self):
        # Define build area start and size (above build plate)
        # buildplate is calculated from these (x,z same - y = -1)
        self.block_area_set = False
        # Normally the block area is visible, but for Build Plate may want it 
        # to be transparent. There is no effect of setting it within this class
        # other than returning status
        self.block_area_visible = True
        self.block_area_start = [0,0,0]
        self.block_area_size = [10,10,10]
    
    def get_start(self):
        return self.block_area_start 
    
    def set_start(self,coords):
        x,y,z = coords
        self.block_area_start[0] = x
        self.block_area_start[1] = y
        self.block_area_start[2] = z
        # Set that this is set, note that size always has a default 
        # so a set_start means the block area is now valid even if size was not explicitly set
        self.block_area_set = True
    
    def get_size(self):
        return self.block_area_size 
        
    def set_size(self, size):
        x,y,z = size
        self.block_area_size[0] = x
        self.block_area_size[1] = y
        self.block_area_size[2] = z
        
    # Sets the start based on the size (which must be set already) and the current x,y,z position
    # Set start position based Where player is centre X,Z and Y = current position + offset
    # start position becomes bottom corner
    # If y requires an offset then that should be provided within the value of y passed to it
    def set_middle(self,coords):
        x,y,z = coords
        self.block_area_start[0] = x - math.floor(self.block_area_size[0]/2)
        self.block_area_start[1] = y
        self.block_area_start[2] = z - math.floor(self.block_area_size[2]/2)
        self.block_area_set = True
        
    def set_visible(self,status):
        self.block_area_visible = status
        
    def is_visible(self):
        return self.block_area_visible
    
    
    
        
        