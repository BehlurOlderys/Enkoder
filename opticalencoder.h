#ifndef ENKODER_SIMPLE_OPTICAL_ENCODER
#define ENKODER_SIMPLE_OPTICAL_ENCODER

#include "typedefs.h"

//-----------------------------------
struct OpticalEncoder{
//-----------------------------------
                  OpticalEncoder ();
  double          ReadAngle      ();
  analogReadout_t GetLastChannelA()const{ return m_channelA; }
  analogReadout_t GetLastChannelB()const{ return m_channelB; }
  double GetLastErrorA()const{ return m_errorA; }
  double GetLastErrorB()const{ return m_errorB; }
  double GetCalcA()const{ return m_calcA; }
  double GetCalcB()const{ return m_calcB; }
  double GetOffsetA()const{ return m_offA; }
  double GetOffsetB()const{ return m_offB; }
  double GetMagA()const{ return m_magA; }
  double GetMagB()const{ return m_magB; }
  double GetMaxA()const{ return m_maxA; }
  double GetMinA()const{ return m_minA; }
  double GetMaxB()const{ return m_maxB; }
  double GetMinB()const{ return m_minB; }
  
private:
  void RecalculateAmplitudes();

  analogReadout_t m_channelA;
  analogReadout_t m_channelB;
  
  double m_minA, m_maxA, m_magA, m_offA, m_errorA, m_calcA;
  double m_minB, m_maxB, m_magB, m_offB, m_errorB, m_calcB;

  const double m_lambda_OA;
  const double m_lambda_MA;
  const double m_lambda_OB;
  const double m_lambda_MB;
};

#endif // ENKODER_SIMPLE_OPTICAL_ENCODER

