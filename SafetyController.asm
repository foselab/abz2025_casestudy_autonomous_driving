asm SafetyController

import ../libraries/StandardLibrary

signature:
	domain Actions subsetof Integer
	monitored inputAction: Actions
	controlled randomAction: Actions
	controlled sameAction: Actions
	out outputAction: Actions
	
	
definitions:
	domain Actions = {0,1,2,3,4}
	
	main rule r_Main =
		seq
			par
				choose $a in Actions with true do randomAction := $a
				sameAction := inputAction
			endpar
			outputAction := randomAction
		endseq