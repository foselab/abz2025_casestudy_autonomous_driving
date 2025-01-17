//Single lane enforcement model
// Main assumption: the enforcement is activated if there is a front car within the observable distance (100m)

asm SafetyEnforcer

import StandardLibrary

signature:
	enum domain Actions={FASTER, SLOWER, IDLE, LANE_LEFT, LANE_RIGHT}
	monitored inputAction: Actions
	monitored v_self: Real //Absolute speed of the controlled vehicle
	monitored v_front: Real //Absolute speed of the front vehicle
	
	monitored x_self: Real //Absolute position of the controlled vehicle
	monitored x_front: Real //Absolute position of the front vehicle
	
	//monitored le osservazioni per le regole di enforcement? 
	
	out outAction: Actions
	
	controlled a_max: Real //Maximum acceleration of rear vehicle before breaking: m/s^2
	controlled b_min: Real 
	controlled b_max: Real
	controlled resp_time: Real
	
	static v_max: Real // m/s
	
	static gofast_perc: Real
	
	derived dRSS: Prod(Real,Real)-> Real //Safety distance
	
definitions:
	
	function v_max = 40.0
	function gofast_perc = 1.7
	
	function dRSS ($v_r in Real, $v_f in Real) = max(0.0, (($v_r*resp_time) + 
	(0.5 *a_max * pwr(resp_time,2.0)) + 
	(pwr(($v_r+resp_time*a_max),2.0)/(2.0*b_min)) - 
	(pwr($v_f,2.0)/(2.0*b_max))))

	
	
	macro rule r_randomAction=
		choose $a in Actions with true
				do
					outAction := $a
	
	// Keep current speed - no risk of collision	
	macro rule r_Hold = 
		if ((x_front-x_self)>dRSS(v_self,v_front) and (x_front-x_self)<=(dRSS(v_self,v_front)*gofast_perc)) then 
			if (inputAction != IDLE) then
				outAction := IDLE
			endif
		endif
	
	// Distance from front vehicle lower than safe distance: break
	macro rule r_unsafeDistance = 
		if ((x_front-x_self)<=dRSS(v_self,v_front)) then 
			if (inputAction != SLOWER) then
				outAction := SLOWER
			endif
		endif
	
	// Rear vehicle very far: increase speed	
	macro rule r_goFast = 
		if ((x_front-x_self)>(dRSS(v_self,v_front)*gofast_perc)) then 
			if (inputAction != FASTER) then
				outAction := FASTER
			endif
		endif
		
	main rule r_Main =
		par
			r_Hold[]
			r_unsafeDistance[]
			r_goFast[]
		endpar
	

	//Esempi di enforcement rule 
	// se distanza da front  d_f > d_min and agent action diversa da IDLE then IDLE
	// se  d_f <= d_min and action diversa da SLOWER then SLOWER and alert
        // se distanza da front  d_f >> d_min and agent action diversa da FASTER then FASTER
        
   default init s0:
   function a_max = 5.0
   function b_max = 5.0
   function b_min = 3.0
   function resp_time = 1.0
   
   
