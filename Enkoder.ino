#include "typedefs.h"
#include "constants.h"
#include "steppermotor.h"
#include "opticalencoder.h"
#include "timecaller.h"
#include "statemachine.h"

//-----------------------------------
void SetAnalogReadPrescaleTo16(){
//-----------------------------------
  sbi(ADCSRA,ADPS2) ;
  cbi(ADCSRA,ADPS1) ;
  cbi(ADCSRA,ADPS0) ;
}


int buttonState;
int globalState;


//-----------------------------------
void setup() {
//-----------------------------------
  SetAnalogReadPrescaleTo16();
  
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

//-----------------------------------
//-----------------------------------
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


//-----------------------------------
void printTime(){
//-----------------------------------
  char lineBuffer[64] = {0};
  sprintf(lineBuffer, "[G] Time is: %20lu", micros());
  Serial.println(lineBuffer);
}

//-----------------------------------
void printGlobalState(){
//-----------------------------------
  char lineBuffer[30] = {0};
  sprintf(lineBuffer, "[G] Global state = %d", globalState);
  Serial.println(lineBuffer);
}

StepperMotor ra_StepperMotor;
OnBoardLedLighter onBoardLedLighter;
OpticalEncoder raEncoder;

//-----------------------------------
//-----------------------------------
struct EncoderReader{
  EncoderReader(OpticalEncoder& encoder) : m_encoder(encoder) {}
  void operator() (){
//    printTime();
    const double phi = m_encoder.ReadAngle();
    const double phi_arcsek = arcsecsForPulse*((PI + phi)/PI)/2.0;
    printReadoutToSerial(phi_arcsek);
  }
  private:
  OpticalEncoder& m_encoder;
  //-----------------------------------
  void printReadoutToSerial(const double phi )const{
  //-----------------------------------
    char lineBuffer[128] = {0};
    snprintf(lineBuffer, sizeof(lineBuffer), "[E] A:%16lu,B:%16lu,C:%16ld,D:%16ld,F:%16ld,T:%16lu",
      m_encoder.GetLastChannelA(), 
      m_encoder.GetLastChannelB(), 
      static_cast<long>(m_encoder.GetCalcA() * 100.0),
      static_cast<long>(m_encoder.GetCalcB() * 100.0),
      static_cast<long>(phi * 100.0),
      micros());
    Serial.println(lineBuffer);
  }
};

EncoderReader encoderReaderRA(raEncoder);

RegularTimedCaller<EncoderReader>     encoderReaderCaller     (encoderReaderRA,     10000ul);
RegularTimedCaller<voidFunctionPtr>   serialGlobalStatePrinter(printGlobalState,  1000000ul);
RegularTimedCaller<OnBoardLedLighter> ledLighterCallerSlow    (onBoardLedLighter,  600000ul);
RegularTimedCaller<OnBoardLedLighter> ledLighterCallerMedium  (onBoardLedLighter,  300000ul);
RegularTimedCaller<OnBoardLedLighter> ledLighterCallerFast    (onBoardLedLighter,  100000ul);
RegularTimedCaller<StepperMotor>      raStepperCaller         (ra_StepperMotor, interwalIdealnyKolo);

//-----------------------------------
bool getButtonPressed(int& b){
//-----------------------------------
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

//-----------------------------------
//-----------------------------------
/////////////////////////// FORWARD OPEN ////////////////
//-----------------------------------
//-----------------------------------
int beginForwardOpen(){
//-----------------------------------
  ledLighterCallerSlow.Reset();
  raStepperCaller.Reset();
  
  ra_StepperMotor.SetDirection(DIR_STARWISE);

  return STATE_FORWARD_OPEN_LOOP;
}

//-----------------------------------
void performStateForwardOpen(){
//-----------------------------------
  ledLighterCallerSlow.CallWhenTime();
  raStepperCaller.CallWhenTime();
}

//-----------------------------------
int nextStateForwardOpen(const int whichButton){
//-----------------------------------
  switch (whichButton){
    case BUTTON_PIN_START:    return beginStop();
    case BUTTON_PIN_FORWARD:  return beginForwardClosed();
    case BUTTON_PIN_BACKWARD: return beginBackwards();
    default:                  return STATE_FORWARD_OPEN_LOOP;
  }
}

//-----------------------------------
//-----------------------------------
///////////////////////// FORWARD CLOSED //////////////////////
//-----------------------------------
//-----------------------------------
int beginForwardClosed(){
//-----------------------------------
  ledLighterCallerMedium.Reset();
  raStepperCaller.Reset();
  encoderReaderCaller.Reset();
  
  ra_StepperMotor.SetDirection(DIR_STARWISE);

  return STATE_FORWARD_CLOSED_LOOP;
}

//-----------------------------------
void performStateForwardClosed(){
//-----------------------------------
  ledLighterCallerMedium.CallWhenTime();
  raStepperCaller.CallWhenTime();
  encoderReaderCaller.CallWhenTime();  
}

//-----------------------------------
int nextStateForwardClosed(const int whichButton){
//-----------------------------------
  switch (whichButton){
    case BUTTON_PIN_START:    return beginStop();
    case BUTTON_PIN_FORWARD:  return beginForwardOpen();
    case BUTTON_PIN_BACKWARD: return beginBackwards();
    default:                  return STATE_FORWARD_CLOSED_LOOP;
  }
}

//-----------------------------------
//-----------------------------------
/////////////////////////// BACKWARDS ////////////////////////////////////
//-----------------------------------
//-----------------------------------
int beginBackwards(){
//-----------------------------------
  ledLighterCallerFast.Reset();
  
  ra_StepperMotor.SetDirection(DIR_COUNTER_STARWISE);

  return STATE_BACKWARD;
}

//-----------------------------------
void performStateBackward(){
//-----------------------------------
  ra_StepperMotor.Step();
  ledLighterCallerFast.CallWhenTime();
}

//-----------------------------------
int nextStateBackward(const int whichButton){
//-----------------------------------
  switch (whichButton){
    case BUTTON_PIN_START:    return beginStop();
    case BUTTON_PIN_FORWARD:  return beginForwardOpen();     
    default:                  return STATE_BACKWARD;
  }
}

//-----------------------------------
//-----------------------------------
/////////////////////////// STOP ////////////////////////////////////
//-----------------------------------
//-----------------------------------
int beginStop(){
//-----------------------------------
  return STATE_STOP;
}

//-----------------------------------
void performStateStop(){
//-----------------------------------
  digitalWrite(LED_BUILTIN, LOW);
  delay(20);
}

//-----------------------------------
int nextStateStop(const int whichButton){
//-----------------------------------
  switch (whichButton){
    case BUTTON_PIN_FORWARD:  return beginForwardOpen();
    case BUTTON_PIN_BACKWARD: return beginBackwards();
    default:                  return STATE_STOP;
  }
}

//-----------------------------------
//-----------------------------------
//-----------------------------------
int performNext(int whichButton){
//-----------------------------------
   switch (globalState){
    case STATE_STOP:                return nextStateStop(whichButton);     
    case STATE_FORWARD_OPEN_LOOP:   return nextStateForwardOpen(whichButton);  
    case STATE_FORWARD_CLOSED_LOOP: return nextStateForwardClosed(whichButton);  
    case STATE_BACKWARD:            return nextStateBackward(whichButton); 
  }
  return globalState;
}

//-----------------------------------
void printStates(const int button){
//-----------------------------------
  char sBuffer[30];
  sprintf(sBuffer, "[G] Global state = %d", globalState);
  Serial.println(sBuffer);
  sprintf(sBuffer, "[G] Button state = %d", buttonState);
  Serial.println(sBuffer);
  sprintf(sBuffer, "[G] Which button = %d", button);
  Serial.println(sBuffer); 
}

//-----------------------------------
void performState(){  
//-----------------------------------
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
//-----------------------------------
//-----------------------------------
void loop() {  // MAIN LOOP
//-----------------------------------
//-----------------------------------
  performState();
  serialGlobalStatePrinter.CallWhenTime();
}
