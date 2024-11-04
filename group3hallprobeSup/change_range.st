program change_range("P,SENSOR_ID")

#include "ibexSeqPVmacros.h"
%% #include "seq_snc.h"
%% #include "epicsTime.h"
%% #include "string.h"
%% #include "math.h"
%% #include "errlog.h"
%% #include "alarm.h"

option +d;
option +r;
option +s;

/* Debugging: current state of this state machine */
PV(string, statemachine_state, "{P}{SENSOR_ID}:STATEMACHINE:STATE", NoMon);

/* Name of this probe (used for debug messages) */
PV(string, name, "{P}{SENSOR_ID}:NAME", Monitor);

/* Delay enforced between state changes to let device settle in new range */
PV(double, state_change_delay, "{P}{SENSOR_ID}:STATEMACHINE:STATE_CHANGE_DELAY", Monitor);

/* Change range */
PV(int, range_sp, "{P}{SENSOR_ID}:RANGE:SP", NoMon);

/* Reinitialize device (e.g. after comms loss). */
PV(int, reinit, "{P}{SENSOR_ID}:INIT.PROC", NoMon);

/* Field as number and raw string, to cope with OVER RANGE condition */
PV(double, raw_field, "{P}{SENSOR_ID}:FIELD:_RAW", Monitor);
PV(string, raw_field_str, "{P}{SENSOR_ID}:FIELD:_RAWSTR", Monitor);
PV(int, raw_field_sevr, "{P}{SENSOR_ID}:FIELD:_RAW.SEVR", Monitor);
PV(int, raw_field_str_sevr, "{P}{SENSOR_ID}:FIELD:_RAWSTR.SEVR", Monitor);

/* Move up and move down thresholds */
PV(double, r3_down, "{P}{SENSOR_ID}:STATEMACHINE:R3:DOWN", Monitor);
PV(double, r2_up, "{P}{SENSOR_ID}:STATEMACHINE:R2:UP", Monitor);
PV(double, r2_down, "{P}{SENSOR_ID}:STATEMACHINE:R2:DOWN", Monitor);
PV(double, r1_up, "{P}{SENSOR_ID}:STATEMACHINE:R1:UP", Monitor);
PV(double, r1_down, "{P}{SENSOR_ID}:STATEMACHINE:R1:DOWN", Monitor);
PV(double, r0_up, "{P}{SENSOR_ID}:STATEMACHINE:R0:UP", Monitor);


%{
  static const char* const PROGRAM_NAME = "change_range.st";

  /* This needs to be a macro as the call to pvIndex has to happen from SNL code, not C code. */
  /* See https://www-csr.bessy.de/control/SoftDist/sequencer/EscapeToC.html?highlight=pvindex#calling-pv-functions-from-c */
  #define G3HP_TRANSITION_TO_STATE(x) g3hp_state_transition(ssId, pVar, pvIndex(statemachine_state), (x))
  
  static void g3hp_state_transition(SS_ID ssId, struct seqg_vars* const pVar, CH_ID index, const char* const new_state_name);
}%

ss change_range
{

  /* Initial state. */
  state disconnected
  {
    entry {
      G3HP_TRANSITION_TO_STATE("disconnected");
    }
	
    when (raw_field_str_sevr != INVALID_ALARM) {
	  PVPUT(reinit, 1);
	} state r3
  }
  
  state r3 {
    entry {
	  G3HP_TRANSITION_TO_STATE("r3");
	  PVPUT(range_sp, 3)
	}
	
	/* Move down */
	when(delay(state_change_delay) && raw_field_sevr == NO_ALARM && fabs(raw_field) < r3_down) {} state r2
	
	/* Cannot move up from r3 */
	
	/* Disconnected device */
	when(raw_field_str_sevr == INVALID_ALARM) {} state disconnected
  }
  
  state r2 {
    entry {
	  G3HP_TRANSITION_TO_STATE("r2");
	  PVPUT(range_sp, 2)
	}
	
	/* Move down */
	when(delay(state_change_delay) && raw_field_sevr == NO_ALARM && fabs(raw_field) < r2_down) {} state r1
	
	/* Move up */
	when(delay(state_change_delay) && raw_field_sevr == NO_ALARM && fabs(raw_field) > r2_up) {} state r3
	when(delay(state_change_delay) && raw_field_str_sevr == NO_ALARM && strcmp(raw_field_str, "OVER RANGE") == 0) {} state r3
	
	/* Disconnected device */
	when(raw_field_str_sevr == INVALID_ALARM) {} state disconnected
  }
  
  state r1 {
    entry {
	  G3HP_TRANSITION_TO_STATE("r1");
	  PVPUT(range_sp, 1)
	}
	
	/* Move down */
	when(delay(state_change_delay) && raw_field_sevr == NO_ALARM && fabs(raw_field) < r1_down) {} state r0
	
	/* Move up */
	when(delay(state_change_delay) && raw_field_sevr == NO_ALARM && fabs(raw_field) > r1_up) {} state r2
	when(delay(state_change_delay) && raw_field_str_sevr == NO_ALARM && strcmp(raw_field_str, "OVER RANGE") == 0) {} state r2
	
	/* Disconnected device */
	when(raw_field_str_sevr == INVALID_ALARM) {} state disconnected
  }
  
  state r0 {
    entry {
	  G3HP_TRANSITION_TO_STATE("r0");
	  PVPUT(range_sp, 0)
	}
	
	/* Cannot move down from r0 */
	
	/* Move up */
	when(delay(state_change_delay) && raw_field_sevr == NO_ALARM && fabs(raw_field) > r0_up) {} state r1
	when(delay(state_change_delay) && raw_field_str_sevr == NO_ALARM && strcmp(raw_field_str, "OVER RANGE") == 0) {} state r1
	
	/* Disconnected device */
	when(raw_field_str_sevr == INVALID_ALARM) {} state disconnected
  }
}

%{
  /**
   * Called on any state transitions that occur in the state machine - primarily for debugging.
   */
  static void g3hp_state_transition(SS_ID ssId, struct seqg_vars* const pVar, CH_ID index, const char* const new_state_name)
  {
    strncpy(pVar->statemachine_state, new_state_name, MAX_STRING_SIZE);
	seq_pvPut(ssId, index, SYNC);
	errlogSevPrintf(errlogInfo, "%s: %s Entering state %s\n", PROGRAM_NAME, pVar->name, new_state_name);
  }
}%
