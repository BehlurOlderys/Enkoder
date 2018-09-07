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
  
private:
  analogReadout_t m_channelA;
  analogReadout_t m_channelB;
  
  double m_magA, m_offA, m_errorA, m_calcA;
  double m_magB, m_offB, m_errorB, m_calcB;

  const double m_lambda_OA;
  const double m_lambda_MA;
  const double m_lambda_OB;
  const double m_lambda_MB;
};

