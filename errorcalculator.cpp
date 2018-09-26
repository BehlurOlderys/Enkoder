#include "errorcalculator.h"
#include "constants.h"
#include "Arduino.h"
#include "limits.h"

namespace{
const int     angleThreshold = 10;
}

//-----------------------------------
ErrorCalculator::ErrorCalculator():
  m_lastTime(0),
  m_lastPhi(0.0),
  m_shouldPhi(0.0)
//-----------------------------------
{}

//------------------------------------------------
timestamp_t ErrorCalculator::GetDeltaTime(){
//------------------------------------------------
  timestamp_t currentTime = micros();
  timestamp_t delta = currentTime - m_lastTime;
  if (delta > currentTime){
    delta = currentTime + (ULONG_MAX - m_lastTime);
  }
  return delta;
}

//------------------------------------------------
double ErrorCalculator::GetShouldPhiArcSec(){
//------------------------------------------------
  const timestamp_t deltaTime = GetDeltaTime();
  double shouldPhi = ((double(deltaTime) * AngularVelocityArcSecPerUs)) + m_lastPhi;
  
  while (shouldPhi > 2*arcsecsForPulse){
    shouldPhi -= arcsecsForPulse;
  }
  return shouldPhi;
}

//-----------------------------------
double ErrorCalculator::CalculateError(const double phiArcSec){
//----------------------------------- 
  m_shouldPhi = GetShouldPhiArcSec();

  if (m_lastPhi > (arcsecsForPulse - angleThreshold) && phiArcSec < angleThreshold){ // over bar
    m_shouldPhi -= arcsecsForPulse;
  }
  else if (m_lastPhi < angleThreshold && phiArcSec > (arcsecsForPulse - angleThreshold)){ // under bar
    m_shouldPhi += arcsecsForPulse;
  }
  return m_shouldPhi - phiArcSec; 
}

