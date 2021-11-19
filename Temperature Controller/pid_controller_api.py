import mcphysics   as _mp
import time as _time


_serial_left_marker  = '<'
_serial_right_marker = '>'  

_debug_enabled       = True
_dac_bit_depth       = 12  


class pid_api():
    """
    Commands-only object for interacting with an Arduino
    temperature controller.
    
    Parameters
    ----------
    port='COM3' : str
        Name of the port to connect to.
        
    baudrate=9600 : int
        Baud rate of the connection. Must match the instrument setting.
        
    timeout=1000 : number
        How long to wait for responses before giving up (ms). 
        
    temperature_limit=85 : float
        Upper limit on the temperature setpoint (C).
        
    """
    def __init__(self, port='COM3', baudrate=9600, timeout=1000, temperature_limit=85):

        self._temperature_limit = temperature_limit        

        # Check for installed libraries
        if not _mp._serial:
            _s._warn('You need to install pyserial to use the Arduino based PID temperature controller.')
            self.simulation = True
            _debug('Simulation enabled.')

        # Assume everything will work for now
        else: self.simulation = False

        # If the port is "Simulation"
        if port=='Simulation': 
            self.simulation      = True
            self.simulation_mode = "OPEN_LOOP" 
            _debug('Simulation enabled.')

        # If we have all the libraries, try connecting.
        if not self.simulation:
            _debug("Attempting serial communication with following parameters:\nPort    : "+port+"\nBaudrate: "+str(baudrate)+" BPS\nTimeout : "+str(timeout)+" ms\n")
            
            try:
                # Create the instrument and ensure the settings are correct.
                self.serial = _mp._serial.Serial(port=port, baudrate=baudrate, timeout=timeout/1000)
                
                _debug("Serial communication to port %s enabled.\n"%port)
                

            # Something went wrong. Go into simulation mode.
            except Exception as e:
                print('Could not open connection to '+port+' at baudrate '+str(baudrate)+' BPS. Entering simulation mode.')
                print(e)
                self.serial = None
                self.simulation = True
        
        # Give the arduino time to run setup loop!
        _time.sleep(2)
                                
    def disconnect(self):
        """
        Disconnects.
        """
        if not self.simulation: 
            self.serial.close()
            _debug('Serial port closed.')

    def get_dac(self):
        """
        Gets the current output power (percent).
        """
        if self.simulation: return _n.random.randint(0,4095)
        else:                    
            self.write('get_dac')
            return 5.*int(self.read())/(2**_dac_bit_depth-1)

    def get_temperature(self):
        """
        Gets the current temperature in Celcius.
        """
        if self.simulation: return _n.round(_n.random.rand()+24, 1)
        else:
             self.write('get_temperature')
             return float(self.read())

    def get_temperature_setpoint(self):
        """
        Gets the current temperature setpoint in Celcius.
        """
        if self.simulation: return 25.4
        else:                    
             self.write('get_setpoint')
             
             # Convert to floating point number and return
             return float(self.read())
    
    def get_parameters(self):
        """
        Get the PID control parameters on the arduino.
        Returns
        -------
        Band: float
            The proportional band.
            
        t_i:  float
            The integral time.
            
        t_d: float
            The derivative time.
        """
        self.write('get_parameters')  
        raw_params = self.read().split(',')
        
        # Convert to floating point numbers
        band = float(raw_params[0])
        ti   = float(raw_params[1])
        td   = float(raw_params[2]) 
        
        return band, ti, td
        
    def get_mode(self):
        """
        Get the current operating mode of the of the arduino temperature controller.
        Returns
        -------
        str
            The current operating mode.
        """
        if self.simulation:
            return self.simulation_mode
        
        self.write("get_mode")
        return self.read()
    
    def set_dac(self,voltage):
        """
        Sets the DAC output voltage.
        Parameters
        ----------
        voltage : float
            The desired dac output voltage.
        
        Note
        ----
        The true output voltage of the dac will be the closest voltage
        that can be generated with the dac's bit depth.
        
        """
        
        if self.simulation: return
        
        # Get the control mode
        mode = self.get_mode()
        
        # Convert floating point number into closest integer using _dac_bit_depth 
        voltage_bit = round( (2**_dac_bit_depth-1)*voltage/5.)
        
        # Check that we are in OPEN_LOOP operation before attempting to set dac voltage
        if(mode == "OPEN_LOOP"):
            self.write("set_dac, "+str(voltage_bit))
        else:
            print("Doing nothing. DAC output voltage can only be directly controlled in OPEN_LOOP mode!")        
    
    def set_temperature_setpoint(self, T=20.0, temperature_limit=None):
        """
        Sets the temperature setpoint to the supplied value in Celcius.
        
        Parameters
        ----------
        T=20.0 : float
            Temperature setpoint (C).
            
        temperature_limit=None : None or float
            If None, uses self._temperature_limit. Otherwise uses the specified
            value to place an upper bound on the setpoint (C).
        """
        if temperature_limit is None: temperature_limit = self._temperature_limit
        
        if T > temperature_limit:
            print('Setpoint above the limit! Doing nothing.')
            return
        
        if not self.simulation:
            self.write('set_setpoint,'+str(T))
    
    def set_parameters(self,band, t_i, t_d):
        """
        Set the PID control parameters on the arduino.
        Parameters
        ----------
        band : float
            The proportional band.
        t_i : float
            The integral time.
        t_d : float
            The derivative time.
        Returns
        -------
        None.
        """
        if self.simulation: return 
        
        self.write('set_parameters,%.2f,%.2f,%.2f'%(band,t_i,t_d)) 
        
    def set_mode(self,mode):
        """
        Set the current operating mode of the of the arduino temperature controller.
        Parameters
        ----------
        mode : str
            The desired operating mode.
        Returns
        -------
        None.
        """
        
        if( mode != "OPEN_LOOP" and mode != "CLOSED_LOOP"):
            print("Controller mode has not been changed. %s is not a vaild mode."%mode)
            return 
        
        if self.simulation: 
            self.simulation_mode = mode
            return
        
        self.write("set_mode,%s"%mode)
        
    def set_period(self,period):
        """
        Set the control loop period.

        Parameters
        ----------
        period : int
            Control loop period [milliseconds].

        """
        if simulation_mode:
            return
        
        self.write('set_period,'+int(period))
    
    def get_period(self):
        """
        Get the control loop period.

        Returns
        -------
        int
            Control loop period [milliseconds].

        """
        
        self.write("get_period")
        
        return int(self.read())
        
    def write(self,raw_data):
        """
        Writes data to the serial line, formatted appropriately to be read by the arduino temperature controller.        
        Parameters
        ----------
        raw_data : str
            Raw data string to be sent to the arduino.
        Returns
        -------
        None.
        """
        encoded_data = (_serial_left_marker + raw_data + _serial_right_marker).encode()
        self.serial.write(encoded_data) 
    
    def read(self):
        """
        Reads data from the serial line.
        Returns
        -------
        TYPE
            DESCRIPTION.
        """
        return self.serial.read_until(expected = '\r\n'.encode()).decode().strip('\r\n')

def _debug(*a):
    if _debug_enabled:
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))