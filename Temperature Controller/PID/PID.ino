#include <Wire.h>
#include <Adafruit_MCP4725.h>
#include <Adafruit_MAX31865.h>

#define BAUD 9600
#define POLARITY_PIN  8

#define RREF      4300.0  // The value of the Rref resistor in the RTD package.
#define RNOMINAL  1000.0  // The 'nominal' 0-degrees-C resistance of the sensor

#define ENABLE_OUTPUT true 

/** Basic parameters **/ 
double temperature; // Will hold the most currently recorded temperature from the RTD
double setpoint;    // Temperature setpoint 
double error;       // Temperature error relative to setpoint 

/** PID control parameters **/
double band        ;   // Proportional band
double t_integral  ;   // Integral time
double t_derivative;   // Derivative time

/** Timing parameters **/
unsigned int period;   // Control period (in milliseconds)
double dt;             // Time step between temperature measurements used in the control loop
 
double time_control; // Time of the temperature measurement last used to update the control function   
double time_recent ; // Time of the most recently taken temperature measurement

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
   * This is the control function used to change the voltage 
   * applied to the peltier based. 
   * 
   * Calculations of the control function are based on the current setpoint and  
   * most recently measured temperature.
   */ 
  
  if (error >= band/2) {
    set_dac(4095);
  } 
  else if (error < -1*band/2) {
    set_dac(0);
  }
}

void initialize(){
  /*
   * Initialalize control parameters 
   */
  set_setpoint(24.50);
  set_parameters(1.0, 1000.0, 1.0);
  set_period(800);
  set_dac(0);

  /* Doing a preliminary temperature reading */
  temperature = rtd.temperature(RNOMINAL, RREF);                                        
  time_control = millis(); 
  time_recent  = millis();
}

void setup() {
  Serial.begin(BAUD);               
  if(ENABLE_OUTPUT)
  {
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
  /**
   * Measure the RTD temperature, and update the temperature error and measurement time.
   * 
   * NOTE: This measurment takes in excess of 100-140 milliseconds to complete! 
   * Take this into account if you wish to make your control period very small.
   */
  temperature             = rtd.temperature(RNOMINAL, RREF); // One shot temperature measurement of the rtd 
  error                   = temperature - setpoint;          // Compute the temperature error.
  time_recent = millis();                                    // Update the time that this measurement was taken
}

ISR(TIMER1_COMPA_vect){ 
/* 
 *  Timer1 compare interrupt 
 *  
 *  This interrupt is called at a regular intervals, that can be set with the set_period() function.  
 *  The main function of this interrupt is to call the control() function at fixed time intervals.
 *  
 *  NOTE: This interupt will not be active until set_period() is called!
 */
  
  if(mode == CLOSED_LOOP){
    dt = time_recent - time_control; // Update the time differential
    time_control = time_recent;      // Update the time of the temperature measurement used in the control loop
  
    interrupts(); /* Re-enable interrupts (allowing nested interrupts) */
                  /* Interrupts are needed to communicate with the DAC (MCP4725) via I2C */
                  
    control();    
  }
}
