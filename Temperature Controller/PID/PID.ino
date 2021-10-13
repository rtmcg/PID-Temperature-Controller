#include <Wire.h>
#include <Adafruit_MCP4725.h>

#define BAUD 9600
#define THERMISTOR_PIN A2

/** Basic parameters **/ 
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
char functionCall[20]  = {0};     //
boolean newData = false;          //
char * strtok_index;              // Used by strtok() as an index

/** Control Modes **/
enum MODES{OPEN_LOOP,CLOSED_LOOP};
enum MODES mode = OPEN_LOOP;
const char *MODE_NAMES[] = {"OPEN_LOOP","CLOSED_LOOP"};

/** Debugging **/
bool _output = false;

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

  temperature = thermistor_temperature(mu);
  error = (temperature - setpoint);

  if (error > band/2) {
    dac_output = 0;
  } 
  else if (error < -1*band/2) {
    dac_output = 4095;
  }
  
  if(_output){ dac.setVoltage(dac_output,false); }
}

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

ISR(TIMER1_COMPA_vect){ 
/* 
 *  Timer1 compare interrupt 
 */
  control();   
}

void parseData() {      // split the data into its parts
   strtok_index = strtok(temp_data,",");   // Get the first part - the string
   strcpy(functionCall, strtok_index);     // Copy it to function_call
    
  if(strcmp(functionCall,"set_parameters")  == 0){ set_parameters();  }
  if(strcmp(functionCall,"set_dac")         == 0){ set_dac();         }
  if(strcmp(functionCall,"set_mode")        == 0){ set_mode();        }
  if(strcmp(functionCall,"set_period")      == 0){ set_period();      }
  if(strcmp(functionCall,"get_dac")         == 0){ get_dac();         }
  if(strcmp(functionCall,"get_mode")        == 0){ get_mode();        }
  if(strcmp(functionCall,"get_temperature") == 0){ get_temperature(); }
  if(strcmp(functionCall,"get_parameters")  == 0){ get_parameters();  }
}

double thermistor_temperature(double thermistor_voltage){
  // Write this !
  return thermistor_voltage;
}
