/********************************************** 
This is a template file used by minecraft-print
Do NOT delete or overwrite this file
If exporting an Minecraft Print OpenSCAD file to 
another system you will need to include this file
**********************************************/


$fn = 40;

// Block size can be overridden later
block_size = 10;

// Default - standard cube block, including any others that don't match
module standard_block () {
    cube(block_size);
}

// stairs
module stair_block (data) {
    // whole block on bottom if  3 or less / top if higher
    if (data <= 3) {
        cube([block_size,block_size,block_size/2]);
    }
    else {
        translate([0,0,block_size/2])cube([block_size,block_size,block_size/2]);
    }
    if (data == 0) {
        translate([0,0,block_size/2])cube([block_size/2,block_size,block_size/2]);
    }
    else if (data == 1) {
        translate([block_size/2,0,block_size/2])cube([block_size/2,block_size,block_size/2]);
    }
    else if (data == 2) {
        translate([0,block_size/2,block_size/2])cube([block_size,block_size/2,block_size/2]);
    }
    else if (data == 3) {
        translate([0,0,block_size/2])cube([block_size,block_size/2,block_size/2]);
    }
    else if (data == 4) {
        translate([0,0,0])cube([block_size/2,block_size,block_size/2]);
    }
    else if (data == 5) {
        translate([block_size/2,0,0])cube([block_size/2,block_size,block_size/2]);
    }
    else if (data == 6) {
        translate([0,block_size/2,0])cube([block_size,block_size/2,block_size/2]);
    }
    else if (data == 7) {
        translate([0,0,0])cube([block_size,block_size/2,block_size/2]);

    }
}

module ramp_stair_block () {
    polyhedron(
        points=[[0,0,0], [block_size,0,0], [block_size,block_size,0], [0,block_size,0], [0,block_size,block_size], [block_size,block_size,block_size]],
        faces=[[0,1,2,3],[5,4,3,2],[0,4,5,1],[0,3,4],[5,2,1]]
    );
}

    
// Slabs concrete / wood
// can be upper (data > 7) or lower
module half_block (data) {
    if (data > 7){
        translate([0,0,block_size/2])cube([block_size,block_size,block_size/2]);
    }
    else {
        cube([block_size,block_size,block_size/2]);
    }
}

// thin vertical block (used by door)
module thin_block () {
    translate ([0,block_size/3, 0]) cube(block_size, block_size/3, block_size);
}