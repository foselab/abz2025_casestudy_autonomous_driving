//Single lane enforcement model
// Main assumption: the enforcement is activated if there is a front car within the observable distance (100m)
// SLOWER action before reaching the safety distance WITHOUT derived function with parameters

asm SafetyEnforcerKeepRight

import ../libraries/StandardLibrary

signature:
	enum domain Actions={FASTER, SLOWER, IDLE, LANE_LEFT, LANE_RIGHT}
	monitored inputAction: Actions
	monitored v_self: Real //Absolute speed of the controlled vehicle
	monitored v_front: Real //Absolute speed of the front vehicle
	
	monitored x_self: Real //Absolute position of the controlled vehicle
	monitored x_front: Real //Absolute position of the front vehicle
	
	monitored rightLaneFree: Boolean //no cars in the right lane within 200 meters - perception distance
	
	//monitored le osservazioni per le regole di enforcement? 
	
	out outAction: Actions
	out currentAgentAction: Actions
	
	controlled a_max: Real //Maximum acceleration of rear vehicle before breaking: m/s^2
	controlled b_min: Real 
	controlled b_max: Real
	controlled resp_time: Real
	controlled l_vehicle: Real
	controlled w_vehicle: Real
	
	controlled dRSS_contr: Real
	controlled actual_distance_contr: Real
	
	static v_max: Real // m/s
	
	static gofast_perc: Real
	static dRSS_breakdist: Real //quando frenare prima di violare la safety distance -> dRSS + dRSS_perc%
	
	derived dRSS: Real //Safety distance
	derived actual_distance: Real //Actual distance between two vehicles considering their length
	derived current_max_acc: Real //current maximum acceleration
	
definitions:
	
	function v_max = 40.0
	function gofast_perc = 1.7
	function dRSS_breakdist = 5.0
	
	function current_max_acc = if (v_self=v_max) then  0.0 else a_max endif
	//if vehicle reaches max speed, the maximum acceleration is 0, otherwise is a_max.
	// Since from req spec, once the vehicle reaches the maximum speed, it cannot accelerate further.
	
	function dRSS = max(0.0, ((v_self*resp_time) + 
	(0.5 *current_max_acc * (resp_time * resp_time)) + 
	(((v_self+resp_time*current_max_acc) * (v_self+resp_time*current_max_acc))/(2.0*b_min)) - 
	((v_front * v_front)/(2.0*b_max))))
	function actual_distance = x_front - x_self - l_vehicle

	
	// Keep the same action decided by the agent - no risk of collision	
	macro rule r_Hold = 
		if (actual_distance>(dRSS + dRSS_breakdist) and actual_distance<=(dRSS*gofast_perc)) then 
		if (not rightLaneFree) then
			outAction := inputAction
		endif endif
	
	// Distance from front vehicle lower than safe distance: break
	macro rule r_unsafeDistance = 
		if (actual_distance<=(dRSS+dRSS_breakdist)) then 
			if (not rightLaneFree) then
				outAction := SLOWER
		endif endif
	
	// Rear vehicle very far: increase speed	
	macro rule r_goFast = 
		if (actual_distance>(dRSS*gofast_perc)) then 
			if (not rightLaneFree) then
				outAction := FASTER
		endif endif
	
	// Keep right if right lane free
	macro rule r_keepRight =
		 if (rightLaneFree) then
		 	outAction := LANE_RIGHT
		 endif
		
	main rule r_Main =
		par
			currentAgentAction := inputAction
			r_Hold[]
			r_unsafeDistance[]
			r_goFast[]
			r_keepRight[]
			dRSS_contr := dRSS
			actual_distance_contr := actual_distance
		endpar
	

  
 default init s0:
   function a_max = 5.0
   function b_max = 5.0
   function b_min = 3.0
   function resp_time = 1.0
   function l_vehicle = 5.0
   function w_vehicle = 2.0
   
   
