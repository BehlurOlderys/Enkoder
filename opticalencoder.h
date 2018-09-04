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
  
private:
  analogReadout_t m_channelA;
  analogReadout_t m_channelB;
  
  double m_magA, m_offA, m_errorA;
  double m_magB, m_offB, m_errorB;

  const double m_lambda_OA;
  const double m_lambda_MA;
  const double m_lambda_OB;
  const double m_lambda_MB;
};

