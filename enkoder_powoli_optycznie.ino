#include "typedefs.h"
#include "constants.h"
#include "steppermotor.h"
#include "opticalencoder.h"

const int STATE_STOP = 0;
const int STATE_FORWARD_OPEN_LOOP = 1;
const int STATE_FORWARD_CLOSED_LOOP = 2;
const int STATE_BACKWARD = 3;

const int NO_BUTTON_PRESSED = 0;
const int SOME_BUTTON_PRESSED = 1;

int buttonState;
int globalState;

const timestamp_t MAX_UNSIGNED_LONG = 4294967295;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(OUTPUT_PIN_DIR, OUTPUT);
  pinMode(OUTPUT_PIN_STEP, OUTPUT);
  pinMode(BUTTON_PIN_START, INPUT);
  pinMode(BUTTON_PIN_FORWARD, INPUT);
  pinMode(BUTTON_PIN_BACKWARD, INPUT);

  globalState = STATE_STOP;
  buttonState = NO_BUTTON_PRESSED;

  Serial.begin(115200);
}

struct OnBoardLedLighter{
  OnBoardLedLighter():
    m_isLedOn(false)
  {}

  void operator()(){
    toggle();
  }
  void turnOn(){
    digitalWrite(LED_BUILTIN, HIGH);
  }
  void turnOff(){
    digitalWrite(LED_BUILTIN, LOW);
  }
  void toggle(){
    if (m_isLedOn){
      turnOff();
      m_isLedOn = false;
    }else{
      turnOn();
      m_isLedOn = true;
    }
  }
  bool m_isLedOn;
};

void printTime(){
  char lineBuffer[64] = {0};
  sprintf(lineBuffer, "[G] Time is: %20lu", micros());
  Serial.println(lineBuffer);
}

void printGlobalState(){
  char lineBuffer[30] = {0};
  sprintf(lineBuffer, "[G] Global state = %d", globalState);
  Serial.println(lineBuffer);
}



typedef void (*voidFunctionPtr)();

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

  void Reset(){
    m_timeStart = micros();
    m_timeAwaited = m_timeStart + m_intervalRegular;
  }
  
  void CallWhenTime(){
    const timestamp_t timeNow = micros();

    if (timeNow > m_timeAwaited){
      m_timeStart = timeNow;
      SetAwaitedTime();
      m_callable();
    }
  }
  virtual void SetAwaitedTime()
  {
    m_timeAwaited += m_intervalRegular;
  }

  timestamp_t m_timeStart;
  timestamp_t m_timeAwaited;
  Callable m_callable;
  timestamp_t m_intervalRegular;
};

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


StepperMotor ra_StepperMotor;
OnBoardLedLighter onBoardLedLighter;
OpticalEncoder raEncoder;

struct EncoderReader{
  EncoderReader(OpticalEncoder& encoder) : m_encoder(encoder) {}
  void operator() (){
//    printTime();
    const double phi = m_encoder.ReadAngle();
    printReadoutToSerial(phi);
  }
  private:
  OpticalEncoder& m_encoder;
  //-----------------------------------
  void printReadoutToSerial(const double phi )const{
  //-----------------------------------
    char lineBuffer[128] = {0};
    snprintf(lineBuffer, sizeof(lineBuffer), "[E] A:%16lu,B:%16lu,C:%10d,D:%10d,F:%10d,T:%16lu,",
      m_encoder.GetLastChannelA(), 
      m_encoder.GetLastChannelB(), 
      static_cast<int>(m_encoder.GetLastErrorA() * 100.0),
      static_cast<int>(m_encoder.GetLastErrorB() * 100.0),
      static_cast<int>(phi * 100.0),
      micros());
    Serial.println(lineBuffer);
  }
};

EncoderReader encoderReaderRA(raEncoder);

RegularTimedCaller<EncoderReader>     encoderReaderCaller     (encoderReaderRA, 20000ul);
RegularTimedCaller<voidFunctionPtr>   serialGlobalStatePrinter(printGlobalState, 1000000ul);
RegularTimedCaller<OnBoardLedLighter> ledLighterCallerSlow    (onBoardLedLighter, 600000ul);
RegularTimedCaller<OnBoardLedLighter> ledLighterCallerMedium  (onBoardLedLighter, 300000ul);
RegularTimedCaller<OnBoardLedLighter> ledLighterCallerFast    (onBoardLedLighter, 100000ul);
RegularTimedCaller<StepperMotor>      raStepperCaller         (ra_StepperMotor, interwalIdealnyKolo);

bool getButtonPressed(int& b){
  if (digitalRead(BUTTON_PIN_START) == HIGH){
    b = BUTTON_PIN_START; 
    return true;
  }
  if (digitalRead(BUTTON_PIN_FORWARD) == HIGH){
    b = BUTTON_PIN_FORWARD; 
    return true;
  }
  if (digitalRead(BUTTON_PIN_BACKWARD) == HIGH){
    b = BUTTON_PIN_BACKWARD; 
    return true;
  }
  return false;
}

/////////////////////////// FORWARD OPEN ////////////////
int beginForwardOpen(){
  ledLighterCallerSlow.Reset();
  raStepperCaller.Reset();
  
  ra_StepperMotor.SetDirection(DIR_STARWISE);

  return STATE_FORWARD_OPEN_LOOP;
}

void performStateForwardOpen(){
  ledLighterCallerSlow.CallWhenTime();
  raStepperCaller.CallWhenTime();
}

int nextStateForwardOpen(const int whichButton){
  switch (whichButton){
    case BUTTON_PIN_START:    return beginStop();
    case BUTTON_PIN_FORWARD:  return beginForwardClosed();
    case BUTTON_PIN_BACKWARD: return beginBackwards();
    default:                  return STATE_FORWARD_OPEN_LOOP;
  }
}

///////////////////////// FORWARD CLOSED //////////////////////

int beginForwardClosed(){
  ledLighterCallerMedium.Reset();
  raStepperCaller.Reset();
  encoderReaderCaller.Reset();
  
  ra_StepperMotor.SetDirection(DIR_STARWISE);

  return STATE_FORWARD_CLOSED_LOOP;
}

void performStateForwardClosed(){
  ledLighterCallerMedium.CallWhenTime();
  raStepperCaller.CallWhenTime();
  encoderReaderCaller.CallWhenTime();  
}

int nextStateForwardClosed(const int whichButton){
  switch (whichButton){
    case BUTTON_PIN_START:    return beginStop();
    case BUTTON_PIN_FORWARD:  return beginForwardOpen();
    case BUTTON_PIN_BACKWARD: return beginBackwards();
    default:                  return STATE_FORWARD_CLOSED_LOOP;
  }
}

/////////////////////////// BACKWARDS ////////////////////////////////////

int beginBackwards(){
  ledLighterCallerFast.Reset();
  
  ra_StepperMotor.SetDirection(DIR_COUNTER_STARWISE);

  return STATE_BACKWARD;
}

void performStateBackward(){
  ra_StepperMotor.Step();
  ledLighterCallerFast.CallWhenTime();
}

int nextStateBackward(const int whichButton){
  switch (whichButton){
    case BUTTON_PIN_START:    return beginStop();
    case BUTTON_PIN_FORWARD:  return beginForwardOpen();     
    default:                  return STATE_BACKWARD;
  }
}

int beginStop(){
  return STATE_STOP;
}

void performStateStop(){
  digitalWrite(LED_BUILTIN, LOW);
  delay(20);
}

int nextStateStop(const int whichButton){
  switch (whichButton){
    case BUTTON_PIN_FORWARD:  return beginForwardOpen();
    case BUTTON_PIN_BACKWARD: return beginBackwards();
    default:                  return STATE_STOP;
  }
}

int performNext(int whichButton){
   switch (globalState){
    case STATE_STOP:                return nextStateStop(whichButton);     
    case STATE_FORWARD_OPEN_LOOP:   return nextStateForwardOpen(whichButton);  
    case STATE_FORWARD_CLOSED_LOOP:   return nextStateForwardClosed(whichButton);  
    case STATE_BACKWARD:            return nextStateBackward(whichButton); 
  }
  return globalState;
}

void printStates(const int button){
  char sBuffer[30];
  sprintf(sBuffer, "[G] Global state = %d", globalState);
  Serial.println(sBuffer);
  sprintf(sBuffer, "[G] Button state = %d", buttonState);
  Serial.println(sBuffer);
  sprintf(sBuffer, "[G] Which button = %d", button);
  Serial.println(sBuffer); 
}

void performState(){  
  if (buttonState == NO_BUTTON_PRESSED)
  { 
    int whichButton = 0;
    const bool isButtonPressed =  getButtonPressed(whichButton);
    if (isButtonPressed){
      buttonState = SOME_BUTTON_PRESSED;
      globalState = performNext(whichButton);
      printStates(whichButton);
      delay(500);
      return;
    }
    else{  // normal state, no button pressed:
      switch (globalState){
        case STATE_STOP:                performStateStop();           return;
        case STATE_FORWARD_OPEN_LOOP:   performStateForwardOpen();    return;
        case STATE_FORWARD_CLOSED_LOOP: performStateForwardClosed();  return;
        case STATE_BACKWARD:            performStateBackward();       return;
        default: return;
      }  // switch
    } // if buttonIsPressed
  }
  else{ //buttonState == SOME_BUTTON_PRESSED
    int dummyButton = 0;
    const bool isButtonPressed =  getButtonPressed(dummyButton);
    if (!isButtonPressed){
      buttonState = NO_BUTTON_PRESSED;
      printStates(dummyButton);
      delay(500);
      return;
    }// if !buttonIsPressed
  } // if buttonState
}

void loop() {
  performState();
  serialGlobalStatePrinter.CallWhenTime();
}
