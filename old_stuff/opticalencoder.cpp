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
  m_minA(3900.), m_maxA(6885.), m_magA((m_maxA - m_minA)/2.0), m_offA(m_minA + m_magA), m_errorA(0.), m_calcA(0.),
  m_minB(3695.), m_maxB(7075.), m_magB((m_maxB - m_minB)/2.0), m_offB(m_minB + m_magB), m_errorB(0.), m_calcB(0.),
  m_lambda_OA(0.05), 
  m_lambda_MA(0.05),
  m_lambda_OB(0.05),
  m_lambda_MB(0.05)
{}

//-----------------------------------
void OpticalEncoder::RecalculateAmplitudes(){
//-----------------------------------
  m_magA = (m_maxA - m_minA)/2.0;
  m_offA = m_minA + m_magA;
  m_magB = (m_maxB - m_minB)/2.0;
  m_offB = m_minB + m_magB;
}

//-----------------------------------
double OpticalEncoder::ReadAngle(){
//-----------------------------------
  m_channelA = readFew(CHANNEL_A_ANALOG_PIN, 8);
  m_channelB = readFew(CHANNEL_B_ANALOG_PIN, 8);

  if (m_channelA > m_maxA){
    m_maxA = m_channelA;
  }else{
    m_maxA -= 1.0;
  }
  if (m_channelA < m_minA){
    m_minA = m_channelA;
  }else{
    m_minA += 1.0;
  }
  if (m_channelB > m_maxB){
    m_maxB = m_channelB;
  }else{
    m_maxB -= 1.0;
  }
  if (m_channelB < m_minB){
    m_minB = m_channelB;
  }else{
    m_minB += 1.0;
  }

//  RecalculateAmplitudes();

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
