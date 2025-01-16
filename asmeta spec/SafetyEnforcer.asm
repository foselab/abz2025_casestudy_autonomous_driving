//Single lane enforcement model
// Main assumption: the enforcement is activated if there is a front car within the observable distance (100m)

asm SafetyEnforcer

import StandardLibrary

signature:
	enum domain Actions={FASTER, SLOWER, IDLE, LANE_LEFT, LANE_RIGHT}
	monitored inputAction: Actions
	monitored v_r: Real //Absolute speed of the controlled vehicle
	monitored v_f: Real //Absolute speed of the front vehicle
	
	monitored x_r: Real //Absolute position of the controlled vehicle
	monitored x_f: Real //Absolute position of the front vehicle
	
	//monitored le osservazioni per le regole di enforcement? 
	
	controlled randomAction: Actions
	controlled sameAction: Actions
	out outAction: Actions
	
	static a_max: Real //Maximum acceleration of rear vehicle before breaking
	static b_min: Real 
	static b_max: Real
	static resp_time: Real
	
	derived dRSS: Real //Safety distance
	
definitions:

	//function dRSS= max(2.3,5.2)
	function dRSS= (v_r*resp_time) + (0.5 *a_max * pwr(resp_time,2)) + (pwr((v_r+resp_time*a_max),2)/(2*b_min)) - (pwr(v_f,2)/(2*b_max))
	//function dRSS = max(0.0, ())
	

	main rule r_Main =
	if ((x_f-x_r)>dRSS) then
		if (inputAction != IDLE) then
			outAction := IDLE
		endif
	endif
	/*	par
			choose $a in Actions with true
				do
					randomAction := $a
			sameAction := inputAction
		endpar*/

	//Esempi di enforcement rule 
	// se distanza da front  d_f > d_min and agent action diversa da IDLE then IDLE
	// se  d_f <= d_min and action diversa da SLOWER then SLOWER and alert
        // se distanza da front  d_f >> d_min and agent action diversa da FASTER then FASTER
