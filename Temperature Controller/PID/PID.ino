#include <Wire.h>
#include <Adafruit_MCP4725.h>

#define BAUD 9600
#define RTD_PIN       A2
#define POLARITY_PIN  8

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
int dac_output;          // The MCP4725 is a 12-bit DAC, so this variable must be <= 4095 

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

const int N = 16;       // Number of samples

void control(){
  /*
   * 
   * 
   */

  if (error > band/2) {
    set_dac(0);
  } 
  else if (error < -1*band/2) {
    set_dac(4095);
  }
}

void initialize(){
  set_setpoint(24.50);
  set_parameters(10.0, 8.26, 2.32);
  set_period(1000);
  set_dac(0);
}

void setup() {
  Serial.begin(BAUD);               
  if(ENABLE_OUTPUT){
    pinMode(POLARITY_PIN, OUTPUT);
    digitalWrite(POLARITY_PIN, LOW);
    dac.begin(0x60);
  }
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
  read_temperature();

}

void read_temperature(){

  long sum = 0;
  long sum_squared = 0;   //
  int value;              //
  
  for (int i = 0; i < N; i++) {     
    value       =  analogRead(RTD_PIN);    
    sum         += value;                           
    sum_squared += value*(long)value;  // Need to type cast to long because int is 16 bit 
  }
 
  double mu, sigma;   
  
  mu    = sum / (double) N;               // Mean
  sigma = sqrt((sum_squared - sum*mu)/N); // Variance 

  temperature = 5.0*mu/(1023);
  error = (temperature - setpoint);
}

ISR(TIMER1_COMPA_vect){ 
/* 
 *  Timer1 compare interrupt 
 */
 
  if(mode == CLOSED_LOOP){
    control();   
  }
}
