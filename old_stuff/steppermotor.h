#ifndef ENKODER_SIMPLE_STEPPERMOTOR
#define ENKODER_SIMPLE_STEPPERMOTOR

#include "typedefs.h"
#include "constants.h"

//-----------------------------------
struct StepperMotor{
//-----------------------------------
          StepperMotor      (int initialDir=DIR_STARWISE);
  void    Step              (int N=1);
  void    SetDirection      (int setDir);
  void    ReactToError      (double error);
  void    operator()        (){ Step(); }
private:
  int     m_direction;  
};

#endif
