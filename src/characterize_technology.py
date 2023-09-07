# Modified from: https://github.com/aviralpandey/CT-DS-ADC_generator

"""
Notes:

- loops ~2500 times, with 1 DC opt point at each
- each iteration is 5s, of which ngspice is like 99%
- it seems others report long load times for ngpisce, with xyce being faster
- How fast would Spectre be? How can I run it without running my code inside a container? (This might be hard, as container is OS-level vitualization, not just filesystem)
    - This would be one reason to use Rocky 8 or 9 as a desktop, so that I can communicate easily on the same machine
    - But running a simulator on another machine (real physical machine) is common, and this is a similar situation. 
- Why is only one image being written? (no with or legth variation?)
- How can I save the small signal params using a generic Hdl21 sim.save statment, and be simulator portable?
- What does the database look like on the inside?
- Do I understand the nuance of the per-loop saving to the arrays at the end?
- How are these databases used by the higher level routines?
- Integrate this: https://github.com/ChrisZonghaoLi/gm_id_gf180mcu
"""

from pathlib import Path

import hdl21 as h
from hdl21.primitives import Vdc
from vlsirtools.spice import SimOptions, SupportedSimulators, ResultFormat

from matplotlib import pyplot as plt
from matplotlib import cm as cm

import numpy as np
import scipy.interpolate

sim_options = SimOptions(
    rundir=Path("./scratch"),
    fmt=ResultFormat.SIM_DATA,
    simulator=SupportedSimulators.XYCE,
)

tb_prefix = 'tb_mos_ibias'
np_filename = 'database_nch.npy'
mos_list = ['nch']
w_unit = 0.5
lch_list = [0.15, 1]

vgs_list = np.linspace(0,1.8,num=21)
vds_list = np.linspace(0,1.8,num=21)
vbs_list = [0, -0.9, -1.8]

@h.paramclass
class MosParams:
    w = h.Param(dtype=float, desc="Channel Width")
    l = h.Param(dtype=float, desc="Channel Length")
    nf = h.Param(dtype=int, desc="Number of fingers")


nch = h.ExternalModule(
    name="sky130_fd_pr__nfet_01v8_lvt", desc="Sky130 NMOS", 
    port_list=[h.Inout(name="D"), h.Inout(name="G"), h.Inout(name="S"), h.Inout(name="B")], 
    paramtype=MosParams)
pch = h.ExternalModule(
    name="sky130_fd_pr__pfet_01v8_lvt", desc="Sky130 PMOS", 
    port_list=[h.Inout(name="D"), h.Inout(name="G"), h.Inout(name="S"), h.Inout(name="B")], 
    paramtype=MosParams)


@h.paramclass
class CommonSourceParams:
    nmos_params = h.Param(dtype=MosParams, desc="NMOS Parameters")
    res_value = h.Param(dtype=float, desc="Drain resistor Value")

# Common source amp, un-used
@h.generator
def common_source_amp_gen(params: CommonSourceParams) -> h.Module:
    @h.module
    class CommonSource:
        VSS = h.Inout()
        VDD = h.Inout()
        vin = h.Input()
        vout = h.Output()
        nmos = nch(params.nmos_params)(D=vout, G=vin, S=VSS, B=VSS)
        res = h.Resistor(r=params.res_value)(p=VDD, n=vout)
    
    return CommonSource
    

def get_tb_name(mos_type, lch):
    lch_int = int(round(lch*1e3))
    return '%s_%s_%dnm' % (tb_prefix, mos_type, lch_int)

def run_characterization_sims(np_filename):
    
    ids = np.zeros([np.size(mos_list),np.size(lch_list),np.size(vbs_list),np.size(vgs_list),np.size(vds_list)])
    vth = np.zeros([np.size(mos_list),np.size(lch_list),np.size(vbs_list),np.size(vgs_list),np.size(vds_list)])     # not used
    cgg = np.zeros([np.size(mos_list),np.size(lch_list),np.size(vbs_list),np.size(vgs_list),np.size(vds_list)])
    cdd = np.zeros([np.size(mos_list),np.size(lch_list),np.size(vbs_list),np.size(vgs_list),np.size(vds_list)])
    gm = np.zeros([np.size(mos_list),np.size(lch_list),np.size(vbs_list),np.size(vgs_list),np.size(vds_list)])
    gds = np.zeros([np.size(mos_list),np.size(lch_list),np.size(vbs_list),np.size(vgs_list),np.size(vds_list)])
    
    for mos_type_index in range(np.size(mos_list)):
        mos_type = mos_list[mos_type_index]
        for lch_index in range(np.size(lch_list)):
            lch = lch_list[lch_index]
            for vbs_index in range(np.size(vbs_list)):
                vbs = vbs_list[vbs_index]
                for vgs_index in range(np.size(vgs_list)):
                    vgs = vgs_list[vgs_index]
                    for vds_index in range(np.size(vds_list)):
                        vds = vds_list[vds_index]
                        print("Starting simulation for:")
                        print(mos_type)
                        print("L = " + str(int(lch*1e3)) + "nm")
                        print("vgs = " + str(vgs) + "V")
                        print("vds = " + str(vds) + "V")
                        print("vbs = " + str(vbs) + "V")

                        # start building TB, procedurally
                        tb_name  = get_tb_name(mos_type,lch)
                        tb = h.sim.tb(tb_name)
                        tb.VDS = h.Signal()
                        tb.VGS = h.Signal()
                        tb.VBS = h.Signal()
                        if mos_type == "nch":
                            tb.dut = nch(MosParams(w=w_unit, l=lch, nf=1))(D=tb.VDS, G=tb.VGS, S=tb.VSS, B=tb.VBS)
                            tb.VDS_src = Vdc(Vdc.Params(dc=str(vds)))(p=tb.VDS, n=tb.VSS)
                            tb.VGS_src = Vdc(Vdc.Params(dc=str(vgs)))(p=tb.VGS, n=tb.VSS)
                            tb.VBS_src = Vdc(Vdc.Params(dc=str(vbs)))(p=tb.VBS, n=tb.VSS)
                        elif mos_type == "pch":
                            tb.dut = pch(MosParams(w=w_unit, l=lch, nf=1))(D=tb.VDS, G=tb.VGS, S=tb.VSS, B=tb.VBS)
                            tb.VDS_src = Vdc(Vdc.Params(dc=str(-vds)))(p=tb.VDS, n=tb.VSS)
                            tb.VGS_src = Vdc(Vdc.Params(dc=str(-vgs)))(p=tb.VGS, n=tb.VSS)
                            tb.VBS_src = Vdc(Vdc.Params(dc=str(-vbs)))(p=tb.VBS, n=tb.VSS)
                        # Test bench built now, let's put it inside a simulation class...


                        # This is the simulation class, which will contain the testbench
                        sim = h.sim.Sim(tb=tb)
                        sim.lib(f"/tools/kits/SKY/sky130A/libs.tech/ngspice/sky130.lib.spice", 'tt')
                        sim.op()
                        if mos_type == "nch":
                            # sim.literal(".save @m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[gm]")      # Can I make these tool agnostic?
                            # sim.literal(".save @m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[gds]")
                            # sim.literal(".save @m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[cgg]")
                            # sim.literal(".save @m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[cdd]")
                            # sim.literal(".save @m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[cdb]")
                            # sim.literal(".save all")
                            sim.save(tb.VDS)
                            sim.save(SaveMode.SELECTED)
                            sim_results = sim.run(sim_options)
                            ids[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = -sim_results[0].data['i(v.xtop.vvds_src)']
                            cgg[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[cgg]']
                            cdd[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[cdd]']
                            cdd[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[cdb]']
                            gm[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[gm]']
                            gds[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__nfet_01v8_lvt[gds]']
                        elif mos_type == "pch":
                            sim.literal(".save @m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[gm]")
                            sim.literal(".save @m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[gds]")
                            sim.literal(".save @m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[cgg]")
                            sim.literal(".save @m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[cdd]")
                            sim.literal(".save @m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[cdb]")
                            sim.literal(".save all")
                            sim_results = sim.run(sim_options)
                            ids[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['i(v.xtop.vvds_src)']
                            cgg[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[cgg]']
                            cdd[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[cdd]']
                            cdd[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[cdb]']
                            gm[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[gm]']
                            gds[mos_type_index,lch_index,vbs_index,vgs_index,vds_index] = sim_results[0].data['@m.xtop.xdut.msky130_fd_pr__pfet_01v8_lvt[gds]']
                        
                        
                        
    print("a")
    results = {
        "keys" : "[mos_list_index,lch_list_idnex,vbs_list_index,vgs_list_index,vds_list_index]",
        "mos_list" : mos_list,
        "lch_list" : lch_list,
        "vbs_list" : vbs_list,
        "vgs_list" : vgs_list,
        "vds_list" : vds_list,
        "ids" : ids,
        "gm" : gm,
        "gds" : gds,
        "cgg" : cgg,
        "cdd" : cdd,
        }
    # np.save(np_filename,results)
    return results

def compute_small_signal_parameters(filename,plot_results=True):
    results = np.load(filename,allow_pickle=True).item()
    
    ids_raw = results['ids'][0,0,0,:,:]
    vgs_raw = results['vgs_list']
    vds_raw = results['vds_list']
    gm_raw = results['gm'][0,0,0,:,:]
    
    ids_spline = scipy.interpolate.RectBivariateSpline(vgs_raw, vds_raw, ids_raw)
    gm_spline = ids_spline.partial_derivative(1,0)
    gds_spline = ids_spline.partial_derivative(0,1)
    
    if plot_results:
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
        vds, vgs = np.meshgrid(vds_raw,vgs_raw)
        ax.plot_surface(vds,vgs,gm_raw,cmap=cm.jet)


        ax.set_xlabel('Vds')
        ax.set_ylabel('Vgs')
        ax.set_zlabel('gm')

        plt.savefig('nch_minsize.png')

        # plt.show()
    # breakpoint()


if __name__ == '__main__':
    run_characterization_sims(np_filename)
    
    # compute_small_signal_parameters(np_filename)
