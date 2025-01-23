asm SafetyController

import ../libraries/StandardLibrary

signature:
	domain Actions subsetof Integer
	monitored inputAction: Actions
	//monitored vr,vf per il safety constraint (gli altri sono fissi)
	//monitored le osservazioni per le regole di enforcement? 
	
	controlled randomAction: Actions
	controlled sameAction: Actions
	//out outAction: Actions
	
	
definitions:
	domain Actions = {0,1,2,3,4} //meglio enumeration FASTER, SLOWER, ...
	
	main rule r_Main =
		par
			choose $a in Actions with true
				do
					randomAction := $a
			sameAction := inputAction
		endpar

	//Esempi di enforcement rule 
	// se distanza da front  d_f > d_min and agent action diversa da IDLE then IDLE
	// se  d_f <= d_min and action diversa da SLOWER then SLOWER and alert
        // se distanza da front  d_f >> d_min and agent action diversa da FASTER then FASTER
