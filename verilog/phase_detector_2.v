//Verilog HDL for "dmc65v2", "pll_phase_detector" "functional"

//Phase detector module at input of PLL
module pll_phase_detector(ref_clk_in,synth_clk_in,up_pulse_out,down_pulse_out,reset);
	//parameter real pd_td = 30p from [0:inf);		//phase detector output prop. delay time
	//parameter real pd_tslew = 30p from (0:inf);	//phase detector slew rate
	//parameter real pd_twidth = 80p from [0:inf);	//phase detector output up/down pulse width
	
	output up_pulse_out, down_pulse_out;
	input reset, synth_clk_in, ref_clk_in;
	wire fv_rst, fr_rst;
	reg q0, q1;
	assign fr_rst = reset | (q0 & q1);
	assign fv_rst = reset | (q0 & q1);

	always @ (posedge synth_clk_in or posedge fv_rst) begin
		if (fv_rst) q0 <= 0; else q0 <= 1;
	end
	always @ (posedge ref_clk_in or posedge fr_rst) begin
		if (fr_rst) q1 <= 0; else q1 <= 1;
	end
	
	assign up_pulse_out = q1;
	assign down_pulse_out = q0; endmodule
endmodule