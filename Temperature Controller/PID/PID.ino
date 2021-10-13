#include <Wire.h>
#include <Adafruit_MCP4725.h>
#define BAUD 9600

const double _tick = 1024000/16e6;  // period of a single clock cycle, in milliseconds
 
double temperature; 
double setpoint;
double error;

/** PID control parameters **/
double band;  // Proportional band
double t_i;   // Integral time
double t_d;   // Derivative time

/** Setup the external DAC **/
Adafruit_MCP4725 dac;    // New DAC object
unsigned int dac_output; // The MCP4725 is a 12-bit DAC, so this variable must be <= 4095 

/** Serial data handling **/
const byte data_size = 64;        // Size of the data buffer receiving from the serial line 
char received_data[data_size];    // Array for storing received data
char temp_data    [data_size];    // Temporary array for use when parsing
char functionCall[20]  = {0};
boolean newData = false;


void initialize(){
  setpoint = 25.0;

  band = 10.0;
  t_i  =  0.0;
  t_d  =  0.0;

}

void setup() {
  Serial.begin(BAUD);
  //dac.begin(0x60);
  //initialize();
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

void setPeriod(int period){     
/*
 * Sets the time between calls to control().
 * 
 * period: period to be set in milliseconds.
 */    
  unsigned int _number = floor(period / _tick) - 1; // Calculate the number of clock ticks in the specified period
  
  //char buf[256];
  //sprintf(buf,"DEBUG\tsetPeriod(%d): number = %d, tick = %ld us, actual period = %ld us\n", period, number, (long)(1e3*tick), (long)(1e3*tick*(number+1)));
  //Serial.print(buf);
  
  // Manipulating registers in the AVR chip (here the ATmega328 for the arduino uno), see the datasheet for details.
  cli();                    // Disable interrupts

  TCCR1A = 0;               // Blank out Timer control register A 
  TCCR1B = 0;               // Blank out Timer control register B 
  TCNT1  = 0;               // Initialize Timer1's counter value to be 0
  OCR1A  = _number;         /* Set the output compare register 1 to the number of ticks found earlier */    
                            /* Note that OCR1a is a 16-bit register, so _number <= 65,535             */ 

  TCCR1B |= (1 << WGM12);                 // Enable clear timer on compare match (CTC) mode
  TCCR1B |= (1 << CS12) | (1 << CS10);    // Set a prescaler of 1024 on Timer1 (this is what converts seconds to milliseconds, with 2.4% error)
  TIMSK1 |= (1 << OCIE1A);                // Enable Timer1 output compare match interrupt
  sei();                                  // Re-enable interrupts
}

ISR(TIMER1_COMPA_vect){ 
/* Timer1 compare interrupt 
 * 
 */
  //control();   
}

void parseData() {      // split the data into its parts

    char * strtokIndx;                    // This is used by strtok() as an index

    strtokIndx = strtok(temp_data,",");   // Get the first part - the string
    strcpy(functionCall, strtokIndx);    // Copy it to function_call
    
  if(strcmp(functionCall,"set_parameters")==0){

    strtokIndx = strtok(NULL, ",");       // This continues where the previous call left off
    Serial.println(atof(strtokIndx),4);     

    strtokIndx = strtok(NULL, ",");
    Serial.println(atof(strtokIndx),4);
    
    strtokIndx = strtok(NULL, ",");
    Serial.println(atof(strtokIndx),4);

  }
}
