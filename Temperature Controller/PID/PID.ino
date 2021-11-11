#include <Wire.h>
#include <Adafruit_MCP4725.h>

#define BAUD 9600
#define THERMISTOR_PIN A2
#define POLARITY_PIN   1

#define ENABLE_OUTPUT false 

/** Basic parameters **/ 
double temperature; 
double setpoint;
double error;

/** PID control parameters **/
double band        ;   // Proportional band
double t_integral  ;   // Integral time
double t_derivative;   // Derivative time

unsigned int period;   // 1000 ms period 

/** Setup the external DAC **/
Adafruit_MCP4725 dac;    // New DAC object
unsigned int dac_output; // The MCP4725 is a 12-bit DAC, so this variable must be <= 4095 

/** Serial data handling **/
const byte data_size = 64;        // Size of the data buffer receiving from the serial line 
char received_data[data_size];    // Array for storing received data
char temp_data    [data_size];    // Temporary array for use when parsing
char functionCall[20]  = {0};     //
boolean newData = false;          //
char * strtok_index;              // Used by strtok() as an index

/** Control Modes **/
enum MODES{OPEN_LOOP,CLOSED_LOOP};
enum MODES mode = OPEN_LOOP;
const char *MODE_NAMES[] = {"OPEN_LOOP","CLOSED_LOOP"};

void control(){
  /*
   * 
   * 
   */
  
  long sum = 0, sumsq = 0;
  int value;
  const int N = 16;                 // Number of samples 
  
  for (int i = 0; i < N; i++) {     
    value =  analogRead(THERMISTOR_PIN);    
    sum += value;                           
    sumsq += value*(long)value;             // Need to type cast to long because int is 16 bit 
  }
 
  double mu, sigma;
  mu = sum / (double) N;            // Mean
  sigma = sqrt((sumsq - sum*mu)/N); // Variance 

  temperature = mu;
  error = (temperature - setpoint);

  if (error > band/2) {
    dac_output = 0;
  } 
  else if (error < -1*band/2) {
    dac_output = 4095;
  }
  
  if(ENABLE_OUTPUT){ dac.setVoltage(dac_output,false); }
}

void initialize(){
  setpoint = 24.50;

  band         = 10.0;
  t_integral   =  8.2;
  t_derivative =  2.32;

  period = 1000;
  unsigned int num_clk_ticks = floor(16e6*period/1024000) - 1; // Calculate the number of clock ticks in the specified period
  
  // Manipulating registers in the AVR chip (here the ATmega328 for the arduino uno), see the datasheet for details.
  cli();                    // Disable interrupts

  TCCR1A = 0;               // Blank out Timer control register A 
  TCCR1B = 0;               // Blank out Timer control register B 
  TCNT1  = 0;               // Initialize Timer1's counter value to be 0
  OCR1A  = num_clk_ticks;   /* Set the output compare register 1 to the number of ticks found earlier */    
                            /* Note that OCR1a is a 16-bit register, so _number <= 65,535             */ 

  TCCR1B |= (1 << WGM12);                 // Enable clear timer on compare match (CTC) mode
  TCCR1B |= (1 << CS12) | (1 << CS10);    // Set a prescaler of 1024 on Timer1 
  TIMSK1 |= (1 << OCIE1A);                // Enable Timer1 output compare match interrupt
  sei();                                  // Re-enable interrupts
}

void setup() {
  Serial.begin(BAUD);
  //Serial.println("Hello");
  if(ENABLE_OUTPUT){dac.begin(0x60);}
  initialize();
}

void loop() {
    receive_data();

    if (newData == true) {
        strcpy(temp_data, received_data); /* this temporary copy is necessary to protect the original data    */
                                          /* because strtok() used in parseData() replaces the commas with \0 */
        parseData();
        newData = false;
    }
}

ISR(TIMER1_COMPA_vect){ 
/* 
 *  Timer1 compare interrupt 
 */
  control();   
}
