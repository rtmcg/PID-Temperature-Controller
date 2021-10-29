void set_period(){     
/*
 * Sets the time between calls to control().
 * 
 * period: period to be set in milliseconds.
 */    
  strtok_index = strtok(NULL, ",");
  unsigned int period = atoi(strtok_index);
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

  Serial.println(period);
}

void set_parameters(){
    strtok_index = strtok(NULL, ",");       // This continues where the previous call left off
    band       = atof(strtok_index);     

    strtok_index = strtok(NULL, ",");
    t_i        = atof(strtok_index);
    
    strtok_index = strtok(NULL, ",");
    t_d        = atof(strtok_index);
  }

void set_dac(){
  strtok_index = strtok(NULL, ",");
  unsigned int voltage_12bit = atoi(strtok_index);

  if(mode == OPEN_LOOP){
      //dac.setVoltage(voltage_12bit,false);
      dac_output = voltage_12bit;
      return;
    }
    Serial.println("Arduino must be in OPEN_LOOP mode in order to directly manipulate the dac output.");
}

void set_mode(){

    unsigned int _mode;
    strtok_index = strtok(NULL,",");
    
    if(strcmp(strtok_index,"OPEN_LOOP") == 0){
      mode = OPEN_LOOP  ;
    }   
    else if(strcmp(strtok_index,"CLOSED_LOOP") == 0) {
      mode = CLOSED_LOOP;
    }
    else{
      Serial.println("Invaild Mode.");
      return;
    }
  }

void set_setpoint(){
  strtok_index = strtok(NULL, ",");      
  setpoint       = atof(strtok_index); 
}

void get_parameters(){
  Serial.print(band,4);
  Serial.print(',');
  Serial.print(t_i,4);
  Serial.print(',');
  Serial.println(t_d,4);    
}

void get_dac(){
  Serial.println(dac_output,4);
}

void get_mode(){
  Serial.println(MODE_NAMES[mode]);
}

void get_temperature(){ 
  Serial.println(temperature,4);
}

void get_setpoint(){
  Serial.println(setpoint,4);
}
