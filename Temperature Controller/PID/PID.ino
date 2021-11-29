
#include <Wire.h>
#include <Adafruit_MCP4725.h>
#include <Adafruit_MAX31865.h>

#define BAUD 9600
#define POLARITY_PIN  8

#define RREF      4300.0  // The value of the Rref resistor in the RTD package.
#define RNOMINAL  1000.0  // The 'nominal' 0-degrees-C resistance of the sensor

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
int dac_output;          // The MCP4725 is a 12-bit DAC, so this variable must be <= 2**12-1 = 4095 

/** Setup MAX 31865 resistance-to-digital converter **/
Adafruit_MAX31865 rtd = Adafruit_MAX31865(10, 11, 12, 13); // Use software SPI: CS, DI, DO, CLK

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
    pinMode(POLARITY_PIN, OUTPUT);    // Enable Polarity pin
    digitalWrite(POLARITY_PIN, LOW);  //
    dac.begin(0x60);                  // Start communication with the external DAC
  }
  rtd.begin(MAX31865_3WIRE);          // Begin SPI communcation with the MAX 31865 chip
  initialize();                       // Initialize relevant variables 
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
  temperature = rtd.temperature(RNOMINAL, RREF);
  error       = temperature - setpoint;         
}

ISR(TIMER1_COMPA_vect){ 
/* 
 *  Timer1 compare interrupt 
 */
 
  if(mode == CLOSED_LOOP){
    control();   
  }
}
