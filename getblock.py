from mcpi.minecraft import Minecraft
import mcpi.block as block
import sys
# Used for debugging returns the block that the player is stood on

try:
    mc = Minecraft.create()
except Exception as e:
    print ("Error connecting to Minecraft\nPlease ensure that Minecraft is running")
    sys.exit()
     
position = mc.player.getTilePos()
block_obj = mc.getBlockWithData(position.x, position.y, position.z)

print ("Position is {},{},{}".format(position.x,position.y,position.z))
print ("Block is {}, data {}".format(block_obj.id, block_obj.data))