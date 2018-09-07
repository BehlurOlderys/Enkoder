#include "Arduino.h"
#include "opticalencoder.h"
#include "constants.h"

namespace{
//-----------------------------------
analogReadout_t readFew(int ch, int N){
//-----------------------------------
  analogReadout_t uReadout = 0;
  int maxI = 1 << N;
  for (int i=0; i<maxI; ++i){
    uReadout += analogRead(ch);
  }
  return uReadout >> (N/2);
}
}

//-----------------------------------
OpticalEncoder::OpticalEncoder() :
//-----------------------------------
  m_channelA(0),
  m_channelB(0),
  m_magA(3630.0 - 1890.0), m_offA(2*1890.0 + m_magA), m_errorA(0.), m_calcA(0.),
  m_magB(3640.0 - 1980.0), m_offB(2*1980.0 + m_magB), m_errorB(0.), m_calcB(0.),
  m_lambda_OA(0.1), 
  m_lambda_MA(0.1),
  m_lambda_OB(0.1),
  m_lambda_MB(0.1)
{}

//-----------------------------------
double OpticalEncoder::ReadAngle(){
//-----------------------------------
  m_channelA = readFew(CHANNEL_A_ANALOG_PIN, 8);
  m_channelB = readFew(CHANNEL_B_ANALOG_PIN, 8);

  double bareA = (m_channelA - m_offA) / m_magA;
  double bareB = (m_channelB - m_offB) / m_magB;

  double phi = atan2(bareA, bareB);

  double sinphi = sin(phi);
  double cosphi = cos(phi);
  m_calcA = m_offA + m_magA * sinphi;
  m_calcB = m_offB + m_magB * cosphi;
  m_errorA = m_channelA - m_calcA;  
  m_errorB = m_channelB - m_calcB;
  
  m_offA += m_lambda_OA * m_errorA;
  m_offB += m_lambda_OB * m_errorB;
  m_magA += m_lambda_MA * m_errorA * sinphi;
  m_magB += m_lambda_MB * m_errorB * cosphi;
  return phi;
}
