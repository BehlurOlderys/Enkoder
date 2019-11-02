#include "steppermotor.h"

//-----------------------------------
StepperMotor::StepperMotor(int initialDir) :
  m_direction(initialDir)
//-----------------------------------
{}

//-----------------------------------
void StepperMotor::Step(int N/*=1*/){
//-----------------------------------
  for (int i=0; i<N; ++i){
    digitalWrite(OUTPUT_PIN_STEP, HIGH);
    delayMicroseconds(minimalStepperDelayUs);
    digitalWrite(OUTPUT_PIN_STEP, LOW);
    delayMicroseconds(minimalStepperDelayUs);
  }
}

//-----------------------------------
void StepperMotor::SetDirection(int setDir){
//-----------------------------------
  m_direction = setDir;
  digitalWrite(OUTPUT_PIN_DIR, setDir);
}

//-----------------------------------
void StepperMotor::ReactToError(double error){
//-----------------------------------
  if (error < 0.3){
    return;
  }
  if (error < 0.6){
    Step(1);
  }else if (error < 1){
    Step(2);
  }
  else{
    Step(3);
  }
}

