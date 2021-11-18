#define sgn(x) ((x) < 0 ? -1 : ((x) > 0 ? 1 : 0))

void set_period(unsigned int _period){     
/*
 * Sets the time between calls to control().
 * 
 * period: period to be set in milliseconds.
 */    
  unsigned int num_clk_ticks = floor(16e6*_period/1024000) - 1; // Calculate the number of clock ticks in the specified period
  
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

  period = _period;
}

void set_parameters(float _band, float _t_integral, float _t_derivative){
    
    band         = _band;
    t_integral   = _t_integral;
    t_derivative = _t_derivative;   
  }

void set_dac(int voltage_12bit){
  
  if(ENABLE_OUTPUT){

    // Check if a polarity change is needed
    if (sgn(dac_output) != sgn(voltage_12bit)){

      // Bring the dac output to zero temporarily for safe polarity change
      dac.setVoltage(0,false);
      
      if( sgn(voltage_12bit) ){
        digitalWrite(POLARITY_PIN,LOW);}
      else{ 
        digitalWrite(POLARITY_PIN,HIGH);}
    }
    dac.setVoltage(abs(voltage_12bit),false);
  }
  dac_output = voltage_12bit;
}

void set_mode(MODES _mode){
    mode = _mode;
}

void set_setpoint(float _setpoint){
  setpoint = _setpoint;
}

int get_dac(){
  return dac_output;
}

MODES get_mode(){
  return mode;
}

float get_temperature(){ 
  return temperature;
}

float get_setpoint(){
  return setpoint;
}

int get_period(){
  return period;
}
