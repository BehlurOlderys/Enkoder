#ifndef ENKODER_SIMPLE_CONSTANTS
#define ENKODER_SIMPLE_CONSTANTS

#include "Arduino.h"

const double Rmm = 444.0; // dlugosc ramienia [mm]
const double Hmm = 1.0; // skok sruby [mm]
const double DGs = 86164.0; // doba gwiazdowa [s]
const double KNO = 200.0; // kroki na obrot
const double MKn = 8.0; // mikrokroki
const double MKpO = KNO * MKn; // mikrokroki na obrót
const double Dhmm = Hmm / MKpO; // skok mikrokroku [mm]
const double Obwod = 2 * PI * Rmm; 
const double ArcSekPerKrok = 1296000.0 * Dhmm / Obwod;
const double Wrs = 2 * PI / DGs; // predkosc katowa gwiazdowa [rad/s]
const double Was = 1296000. / DGs; // predkosc katowa gwiazdowa [arcsek/s]
const double Vmms = Wrs * Rmm; // predkosc liniowa konca ramienia [mm/s]
const double Fhz = Vmms / Dhmm; // czestosc mikrokrokow silnika [Hz]
const double interwalIdealnyKolo =  1000000.0 / Fhz; // czas na jeden mikrokrok [us]
const double minInterwal  = 15000.0;
const double maxInterwal = 25000.0;
const int arcsecsForPulse = 720; // 1800 pulses per revolution = 1296000 / 18000 = 720 arcsec / pulse
const double arcsecsForAngle = double(arcsecsForPulse) / (2.0);
double const piPocz = PI / 4.0;
double const piKoni = piPocz + PI;
double const AngularVelocityArcSecPerUs = 1296000.0 / (1000000.0 * DGs);  // ~15e-5 arcsec/us

const unsigned int minimalStepperDelayUs = 500;  // 0.5ms = 500us
const double KpBase = interwalIdealnyKolo / 5.0;

const int DIR_STARWISE = HIGH;
const int DIR_COUNTER_STARWISE = LOW;

const timestamp_t MAX_UNSIGNED_LONG = 4294967295;

//-----------------------------------------
// Pins:
//-----------------------------------------
const int OUTPUT_PIN_DIR = 3;
const int OUTPUT_PIN_STEP = 2;
const int BUTTON_PIN_START = 4;
const int BUTTON_PIN_FORWARD = 5;
const int BUTTON_PIN_BACKWARD = 6;
const int CHANNEL_A_ANALOG_PIN = 0;
const int CHANNEL_B_ANALOG_PIN = 1;
//-----------------------------------------
// States:
//-----------------------------------------

const int STATE_STOP = 0;
const int STATE_FORWARD_OPEN_LOOP = 1;
const int STATE_FORWARD_CLOSED_LOOP = 2;
const int STATE_BACKWARD = 3;

const int NO_BUTTON_PRESSED = 0;
const int SOME_BUTTON_PRESSED = 1;

#endif
