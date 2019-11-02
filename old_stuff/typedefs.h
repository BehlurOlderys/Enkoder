#ifndef ENKODER_SIMPLE_TYPEDEFS
#define ENKODER_SIMPLE_TYPEDEFS

// defines for setting and clearing register bits
#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif

#define timestamp_t unsigned long
#define direction_t bool
#define analogReadout_t unsigned long

#endif

