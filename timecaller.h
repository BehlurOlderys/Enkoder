#ifndef ENKODER_TIME_CALLER
#define ENKODER_TIME_CALLER

typedef void (*voidFunctionPtr)();

//-----------------------------------
//-----------------------------------
template <typename Callable>
struct RegularTimedCaller{
  RegularTimedCaller(Callable callable, const timestamp_t interval):
    m_timeStart(0ul),
    m_timeAwaited(0ul),
    m_callable(callable),
    m_intervalRegular(interval)
  {
    Reset();
  }

  //-----------------------------------
  void Reset(){
  //-----------------------------------
    m_timeStart = micros();
    m_timeAwaited = m_timeStart + m_intervalRegular;
  }
  
  //-----------------------------------
  void CallWhenTime(){
  //-----------------------------------
    const timestamp_t timeNow = micros();

    if (timeNow > m_timeAwaited){
      m_timeStart = timeNow;
      SetAwaitedTime();
      m_callable();
    }
  }
  //-----------------------------------
  virtual void SetAwaitedTime()
  //-----------------------------------
  {
    m_timeAwaited += m_intervalRegular;
  }

  timestamp_t m_timeStart;
  timestamp_t m_timeAwaited;
  Callable m_callable;
  timestamp_t m_intervalRegular;
};

//-----------------------------------
//-----------------------------------
// Asymmetric caller
//-----------------------------------
//-----------------------------------
template <typename Callable>
struct AsymmetricTimedCaller : public RegularTimedCaller<Callable>{
  AsymmetricTimedCaller(Callable callable, const timestamp_t interval1, const timestamp_t interval2):
    RegularTimedCaller<Callable>(callable, interval1),
    m_state(false),
    m_intervalAsymmetric(interval2)
  {}

  void SetAwaitedTime(){
    RegularTimedCaller<Callable>::m_timeAwaited += m_state ? RegularTimedCaller<Callable>::m_intervalRegular : m_intervalAsymmetric; 
    m_state = !m_state;
  }
  bool m_state;
  const timestamp_t m_intervalAsymmetric;
};

#endif // ENKODER_TIME_CALLER
