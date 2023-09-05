# -*- coding: utf-8 -*-
"""NAND gate generation using laygo2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1tpuUvqb6BujzZI6RBf2cFdAfMqBsxpep

# **NAND Gate Layout Generation with Laygo2**

spdx-license-identifier: bsd-3-clause

This notebook demonstrates the generation of a NAND gate layout using [laygo2](https://laygo2.github.io) for a simplified test technology (laygo2_tech_quick_start) and the export of the layout to a GDS file.

## Setup
"""

#@title Install dependencies
#@markdown - Click the ▷ button to install the necessary packages in Colab. Please note that the setup time and commands may differ based on the design environment.
!pip install laygo2
!pip install cairosvg
!pip install pyyaml
!pip install gdspy

"""Once the packages have been installed, run the following code block to retrieve the latest laygo2 repository from GitHub. For the technology setup (**laygo2_tech**), we will use the simplified setup (**laygo2_tech_quick_start**) in this tutorial."""

# Load test technology (laygo2_tech_quick_start).
!git clone https://github.com/niftylab/laygo2.git
!ln -s ./laygo2/laygo2_tech_quick_start .

"""##Import packages and set parameter variables
Run the following code block to import [laygo2](https://laygo2.github.io) and technology packages and define parameter variables.

* **nf_a** and **nf_b** represent the number of fingers of the MOSFETs connected to inputs **a** and **b**  respectively.
"""

import laygo2
import laygo2.interface
import laygo2_tech_quick_start as tech

# Parameter definitions ##############
# Templates
tpmos_name = "pmos"
tnmos_name = "nmos"
# Grids
pg_name = "placement_cmos"
r12_name = "routing_12_cmos"
r23_name = "routing_23_cmos"
# Design hierarchy
libname = "laygo2_test"
cellname = "nand2"
# Design parameters
nf_a = 3
nf_b = 4
# (optional) matplotlib export
mpl_params = tech.tech_params["mpl"]
# End of parameter definitions #######

"""## Load templates and grids
Laygo2 uses a template and grid-based layout generation method to encapsulate design rules and ensure process compatibility (although it is still possible to generate layouts using physical coordinates). To load the templates and grids, run the _load_templates()_ and _load_grids()_ functions defined in the technology library (_laygo_tech_).

Execute the following code cell to load the template and grid libraries and display some of their components.
"""

# Generation start ###################
# 1. Load templates and grids.
print("Load templates")
templates = tech.load_templates()
tpmos, tnmos = templates[tpmos_name], templates[tnmos_name]
print(templates[tpmos_name], templates[tnmos_name], sep="\n")

print("Load grids")
grids = tech.load_grids(templates=templates)
pg, r12, r23 = grids[pg_name], grids[r12_name], grids[r23_name]
print(grids[pg_name], grids[r12_name], grids[r23_name], sep="\n")

"""## Create design hierarchy

Simliar to conventional design frameworks, laygo2 supports hierarchical management of multiple designs through libraries and design entities. Run the following code cell to create a [Library](https://laygo2.github.io/laygo2.object.database.Library.html) and [Design](https://laygo2.github.io/laygo2.object.database.Design.html) object for the layout to be generated.
"""

# 2. Create a design hierarchy.
lib = laygo2.object.database.Library(name=libname)
dsn = laygo2.object.database.Design(name=cellname)
lib.append(dsn)

"""## Create instances

The first step in creating a layout after setting up the design entity is to generate instances from templates. By executing the [generate()](https://laygo2.github.io/laygo2.object.template.UserDefinedTemplate.html#laygo2.object.template.UserDefinedTemplate.generate) function with design parameters as arguments, you can create and backstage an instance (or virtual instance) that corresponds to the template and parameters.
"""

# 3. Create instances.
print("Create instances")
in0 = tnmos.generate(name="MN0", params={"nf": nf_b, "tie": "S"})
ip0 = tpmos.generate(name="MP0", transform="MX", params={"nf": nf_b, "tie": "S"})
in1 = tnmos.generate(name="MN1", params={"nf": nf_a, "trackswap": True})
ip1 = tpmos.generate(name="MP1", transform="MX", params={"nf": nf_a, "tie": "S"})

print(in1)

"""## Place instances

Call the [place()](https://laygo2.github.io/laygo2.object.database.Design.place.html) function to arrange the generated (and backstaged) instances on the grid. It is important to note that the placement grid **pg** and its grid conversion function [pg.mn([x, y])](https://laygo2.github.io/laygo2.object.grid.PlacementGrid.html#laygo2.object.grid.PlacementGrid.mn) are used in conjunction with various positional functions (such as [top_left()](https://laygo2.github.io/laygo2.object.grid.Grid.html#laygo2.object.grid.Grid.top_left) and [height_vec()](https://laygo2.github.io/laygo2.object.grid.Grid.html#laygo2.object.grid.Grid.height_vec)) to enable grid-based, relative placement.

The placed instances contain all the geometries required to assemble the transistor structure and base interconnects.
"""

# 4. Place instances.
# place the first P/N pair.

# Option 1: vector-based placement
dsn.place(grid=pg, inst=in0, mn=[0, 0])
dsn.place(grid=pg, inst=ip0, mn=pg.mn.top_left(in0) + pg.mn.height_vec(ip0))
# plot
fig = laygo2.interface.mpl.export(lib, cellname=None, colormap=mpl_params["colormap"], order=mpl_params["order"])
# place the rest two MOSFETs.
dsn.place(grid=pg, inst=in1, mn=pg.mn.bottom_right(in0))
dsn.place(grid=pg, inst=ip1, mn=pg.mn.top_right(ip0))

# Option 2: anchor-based placement
#dsn.place(grid=pg, inst=in0, mn=[0, 0])
#dsn.place(grid=pg, inst=ip0, anchor_xy=[in0.top_left, ip0.bottom_left])
#dsn.place(grid=pg, inst=in1, anchor_xy=[in0.bottom_right, in1.bottom_left])
#dsn.place(grid=pg, inst=ip1, anchor_xy=[in1.top_left, ip1.bottom_left])

# Option 3: array-based placement
#dsn.place(grid=pg, inst=[[in0, in1], [ip0, ip1]], mn=[0, 0])

# plot
fig = laygo2.interface.mpl.export(lib, cellname=None, colormap=mpl_params["colormap"], order=mpl_params["order"])

"""## Create and place wires

After arranging instances, you can generate interconnecting wires between nodes. Execute the following code cell to create routing patterns to implement the NAND functionality. For details on the routing functions, see the descriptions of [route()](https://laygo2.github.io/laygo2.object.database.Design.route.html) and [route_via_track()](https://laygo2.github.io/laygo2.object.database.Design.route_via_track.html).
"""

# 5. Create and place wires.
print("Create wires")
# A: from in1.G to ip1.G
_mn = [r23.mn(in1.pins["G"])[0], r23.mn(ip1.pins["G"])[0]]
va0, ra0, va1 = dsn.route(grid=r23, mn=_mn, via_tag=[True, True])
# B: from in0.G to ip0.G
_mn = [r23.mn(in0.pins["G"])[0], r23.mn(ip0.pins["G"])[0]]
vb0, rb0, vb1 = dsn.route(grid=r23, mn=_mn, via_tag=[True, True])
# internal: from in0.D to in1.S
_mn = [r12.mn(in0.pins["D"])[1], r12.mn(in1.pins["S"])[0]]
dsn.route(grid=r23, mn=_mn)
# output: from ip0.D to ip1.D, in1.D to ip1.D
_mn = [r12.mn(ip0.pins["D"])[1], r12.mn(ip1.pins["D"])[0]]
dsn.route(grid=r23, mn=_mn)
_mn = [r23.mn(in1.pins["D"])[1], r23.mn(ip1.pins["D"])[1]]
_, rout0, _ = dsn.route(grid=r23, mn=_mn, via_tag=[True, True])

print(ra0)
# plot
fig = laygo2.interface.mpl.export(lib, cellname=None, colormap=mpl_params["colormap"], order=mpl_params["order"])

"""## Create pins

Execute the following code block to create terminals that can be accessed from higher levels.
"""

# 6. Create pins.
pB = dsn.pin(name="B", grid=r23, mn=r23.mn(rb0))
pA = dsn.pin(name="A", grid=r23, mn=r23.mn(ra0))
pout0 = dsn.pin(name="O", grid=r23, mn=r23.mn(rout0))
_mn = [r12.mn(in0.pins["RAIL"])[0], r12.mn(in1.pins["RAIL"])[1]]
pvss0 = dsn.pin(name="VSS", grid=r12, mn=_mn)
_mn = [r12.mn(ip0.pins["RAIL"])[0], r12.mn(ip1.pins["RAIL"])[1]]
pvdd0 = dsn.pin(name="VDD", grid=r12, mn=_mn)

print(dsn)

"""## Export to physical database

The following code block exports the generated layout to a GDS file and a Skill script. It also registers the layout as a template in YAML format for hierarchical layout generation.
"""

# 7. Export to physical database.
print("Export design")
filename = libname + "_" + cellname
# gds export
laygo2.interface.gdspy.export(
    lib,
    filename=filename + ".gds",
    cellname=None,
    scale=1e-9,
    layermapfile="./laygo2_tech_quick_start/laygo2_tech.layermap",
    physical_unit=1e-9,
    logical_unit=0.001,
    pin_label_height=0.1,
    svg_filename=filename + ".svg",
    png_filename=filename + ".png",
    # pin_annotation_layer=['text', 'drawing'], text_height=0.1,abstract_instances=abstract,
)
# skill export
skill_str = laygo2.interface.skill.export(lib, filename=libname + "_" + cellname + ".il", cellname=None, scale=1e-3)
# print(skill_str)

# 8. Export to a template database file.
nat_temp = dsn.export_to_template()
laygo2.interface.yaml.export_template(nat_temp, filename=libname + "_templates.yaml", mode="append")

from IPython.display import Image
Image('laygo2_test_nand2.png')

