#ifndef ENKODER_SIMPLE_ERRORCALCULATOR
#define ENKODER_SIMPLE_ERRORCALCULATOR

#include "typedefs.h"
#include "Arduino.h"

//-----------------------------------
struct ErrorCalculator{
//-----------------------------------
              ErrorCalculator          ();
  double      CalculateError           (const double phiArcSec);
  void        Reset                    (const double phiArcSec){ m_lastTime = micros();
                                        m_lastPhi = phiArcSec;
                                        m_beginPhi = phiArcSec;
                                        }
  double      GetLastShouldPhi         () const { return m_shouldPhi; }
private:
  timestamp_t GetDeltaTime             ();
  double      GetShouldPhiArcSec       ();
         
  timestamp_t m_lastTime;
  double      m_lastPhi;
  double      m_shouldPhi;
  double      m_beginPhi;
};

#endif

