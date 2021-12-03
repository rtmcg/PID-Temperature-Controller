
#include <Wire.h>
#include <Adafruit_MCP4725.h>
#include <Adafruit_MAX31865.h>

#define BAUD 9600
#define POLARITY_PIN  8

#define RREF      4300.0  // The value of the Rref resistor in the RTD package.
#define RNOMINAL  1000.0  // The 'nominal' 0-degrees-C resistance of the sensor

#define ENABLE_OUTPUT true 

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
int dac_output = 0;          // The MCP4725 is a 12-bit DAC, so this variable must be <= 2**12-1 = 4095 

/** Setup MAX 31865 resistance-to-digital converter **/
Adafruit_MAX31865 rtd = Adafruit_MAX31865(10, 11, 12, 13); // Use software SPI: CS, DI, DO, CLK

/** Serial data handling **/
const byte data_size = 64;        // Size of the data buffer receiving from the serial line 
char received_data[data_size];    // Array for storing received data
char temp_data    [data_size];    // Temporary array for use when parsing
char functionCall[20]  = {0};     //
boolean newData = false;          // Flag used to indicate if new data has been found on the serial line
char * strtok_index;              // Used by strtok() as an index

/** Control Modes **/
enum MODES{OPEN_LOOP,CLOSED_LOOP};
enum MODES mode = OPEN_LOOP;
const char *MODE_NAMES[] = {"OPEN_LOOP","CLOSED_LOOP"};

void control(){
  /*
   * This is the control function used to change power 
   * sent to the peltier based on the current setpoint and  
   * most recently measured temperature.
   */
  /*
  if (error >= band/2) {
    set_dac(4095);
  } 
  else if (error < -1*band/2) {
    set_dac(0);
  }*/
  double p = band*error + t_integral;

  if(p>4095){p=4095;}

  set_dac(p);
}

void initialize(){
  /*
   * Initial control parameters 
   */
  set_setpoint(24.50);
  set_parameters(1.0, 0, 0);
  set_period(1000);
  set_dac(0);
}

void setup() {
  Serial.begin(BAUD);               
  if(ENABLE_OUTPUT){
    pinMode(POLARITY_PIN, OUTPUT);    // Enable Polarity pin
    digitalWrite(POLARITY_PIN, LOW);  // Set Polarity pin LOW
    
    dac.begin(0x62);                  // Start communication with the external DAC
    dac.setVoltage(0, false);         // Set DAC output to ZERO
  }
  rtd.begin(MAX31865_3WIRE);          // Begin SPI communcation with the MAX 31865 chip
  initialize();                       // Initialize relevant variables 
}

void loop() {
  receive_data();                       /* Look for and grab data on the serial line. */
                                        /* If new data is found, the newData flag will be set */ 

  if (newData == true) {
      strcpy(temp_data, received_data); /* this temporary copy is necessary to protect the original data    */
                                        /* because strtok() used in parseData() replaces the commas with \0 */
      parseData();                      // Parse the data for commands
      newData = false;                  // Reset newData flag
  }
  
  read_temperature();
}

void read_temperature(){
  temperature = rtd.temperature(RNOMINAL, RREF); // One shot temperature measurement of the rtd 
  error       = temperature - setpoint;          // 
}

ISR(TIMER1_COMPA_vect){ 
/* 
 *  Timer1 compare interrupt 
 *  This interrupt is called at regular intervals. This interval can be set with the set_period() function.  
 *  The main function of this interrupt is to call the control() function at fixed time intervals.
 */
 
  if(mode == CLOSED_LOOP){
    interrupts(); /* Re-enable interrupts (allowing nested interrupts) */
                  /* Interrupts are needed to communicate with the DAC (MCP4725) via I2C */
                  
    control();    
  }
}
