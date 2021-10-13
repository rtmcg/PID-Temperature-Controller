#include <Wire.h>
#include <Adafruit_MCP4725.h>
#define BAUD 9600
#define THERMISTOR_PIN A2
 
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


enum MODES{OPEN_LOOP,CLOSED_LOOP};
enum MODES mode = OPEN_LOOP;


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
/* Timer1 compare interrupt 
 * 
 */
  //control();   
}


char * strtokIndx;                    // This is used by strtok() as an index

void parseData() {      // split the data into its parts
    strtokIndx = strtok(temp_data,",");   // Get the first part - the string
    strcpy(functionCall, strtokIndx);    // Copy it to function_call
    
  if(strcmp(functionCall,"set_parameters")  == 0){ set_parameters();  }
  if(strcmp(functionCall,"set_dac_voltage") == 0){ set_dac_voltage(); }
  if(strcmp(functionCall,"set_mode")==0){ set_mode(); }
}



void set_period(int period){     
/*
 * Sets the time between calls to control().
 * 
 * period: period to be set in milliseconds.
 */    
  unsigned int _number = floor(16e6*period/1024000) - 1; // Calculate the number of clock ticks in the specified period
  
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
  TCCR1B |= (1 << CS12) | (1 << CS10);    // Set a prescaler of 1024 on Timer1 
  TIMSK1 |= (1 << OCIE1A);                // Enable Timer1 output compare match interrupt
  sei();                                  // Re-enable interrupts
}

void set_parameters(){
    strtokIndx = strtok(NULL, ",");       // This continues where the previous call left off
    band       = atof(strtokIndx);     

    strtokIndx = strtok(NULL, ",");
    t_i        = atof(strtokIndx);
    
    strtokIndx = strtok(NULL, ",");
    t_d        = atof(strtokIndx);

    Serial.println(band,4);
    Serial.println(t_i, 4);
    Serial.println(t_d, 4);
  }

void set_dac_voltage(){
  strtokIndx = strtok(NULL, ",");
  unsigned int voltage_12bit = atoi(strtokIndx);

  if(mode == OPEN_LOOP){
      //dac.setVoltage(voltage_12bit,false);
      dac_output = voltage_12bit;
      Serial.println(dac_output);    
      return;
    }
    Serial.println("Arduino must be in OPEN_LOOP mode in order to directly manipulate the dac output.");
}

void set_mode(){

    unsigned int _mode;
    strtokIndx = strtok(NULL,",");
    
    if(strcmp(strtokIndx,"OPEN_LOOP") == 0){
      mode = OPEN_LOOP  ;
    }   
    else if(strcmp(strtokIndx,"CLOSED_LOOP") == 0) {
      mode = CLOSED_LOOP;
    }
    else{
      Serial.println("Invaild Mode.");
      return;
    }
    Serial.println(mode);
  }
/**
void get_temperature(){
   double thermistor_voltage = analogRead(THERMISTOR_PIN); 
}

void get_dac_voltage(){
  return dac_voltage;
}

void get_mode(){
  return mode;
}
*/
