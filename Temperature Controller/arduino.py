import mcphysics as _mp
import numpy as _n
import spinmob.egg as _egg
import traceback as _traceback
import spinmob as _s
import time as _time

try: from serial.tools.list_ports import comports as _comports
except: _comports = None

_p = _traceback.print_last
_g = _egg.gui

_serial_left_marker  = '<'
_serial_right_marker = '>'    

_debug_enabled = True

# Dark theme
_s.settings['dark_theme_qt'] = True

## Fonts ##
style_big_blue      = 'font-size: 15pt; font-weight: bold; color: '+('cyan'              if _s.settings['dark_theme_qt'] else 'blue')
style_big_red       = 'font-size: 15pt; font-weight: bold; color: '+('lavenderblush'     if _s.settings['dark_theme_qt'] else 'red')
style_big_purple    = 'font-size: 15pt; font-weight: bold; color: '+('lightcoral'        if _s.settings['dark_theme_qt'] else 'lightcoral')
style_big_green    =  'font-size: 15pt; font-weight: bold; color: '+('mediumspringgreen' if _s.settings['dark_theme_qt'] else 'mediumspringgreen')

## TODO: 
    # fix connect button turn off
    # add all required get and set (get_mode(), set_mode(), get_dac_output(),ect..)
    # Potentially add plotter tabs, so we can have more than one plotter object.

class arduino_controller_api():
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
        
    temperature_limit=120 : float
        Upper limit on the temperature setpoint (C).
    """
    def __init__(self, port='COM3', baudrate=9600, timeout=1000, temperature_limit=120):

        self._temperature_limit = temperature_limit        

        # Check for installed libraries
        if not _mp._serial:
            _s._warn('You need to install pyserial to use the Arduino based PID temperature controller.')
            self.simulation_mode = True
            _debug('Simulation mode enabled.')

        # Assume everything will work for now
        else: self.simulation_mode = False

        # If the port is "Simulation"
        if port=='Simulation': 
            self.simulation_mode = True
            _debug('Simulation mode enabled.')

        # If we have all the libraries, try connecting.
        if not self.simulation_mode:
            _debug("Attempting serial communication with following parameters:\nPort    : "+port+"\nBaudrate: "+str(baudrate)+" BPS\nTimeout : "+str(timeout)+" ms\n")
            
            try:
                # Create the instrument and ensure the settings are correct.
                self.serial = _mp._serial.Serial(port=port, baudrate=baudrate, timeout=timeout/1000)
                

            # Something went wrong. Go into simulation mode.
            except Exception as e:
                print('Could not open connection to '+port+' at baudrate '+str(baudrate)+' BPS. Entering simulation mode.')
                print(e)
                self.serial = None
                self.simulation_mode = True
                
        if(self.serial != None): _debug("Serial communication to port %s enabled.\n"%port)
                
    def disconnect(self):
        """
        Disconnects.
        """
        if not self.simulation_mode: 
            self.serial.close()
            _debug('Serial port closed.')

    def get_main_output_power(self):
        """
        Gets the current output power (percent).
        """
        if self.simulation_mode: return _n.random.randint(0,200)
        else:                    
            self.write('get_dac')
            return 100*(float(self.read()))/4095

    def get_temperature(self):
        """
        Gets the current temperature in Celcius.
        """
        if self.simulation_mode: return _n.round(_n.random.rand()+24, 1)
        else:                    
             self.write('get_temperature')
             return float(self.read())

    def get_temperature_setpoint(self):
        """
        Gets the current temperature setpoint in Celcius.
        """
        if self.simulation_mode: return 24.5
        else:                    
             self.write('get_setpoint')
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
        self.write("get_mode")
        return self.read()
    
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
        
        if not self.simulation_mode:
            self.write('set_temperature,'+str(T))

    
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
        self.write("set_mode,%s"%mode)
        
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
    

class arduino_controller(_g.BaseObject):
    """
    Graphical interface for the Arduino based PID temperature controller.

    Parameters
    ----------
    name='auber_syl53x2p' : str
        Unique name to give this instance, so that its settings will not
        collide with other egg objects.

    temperature_limit=450 : float
        Upper limit on the temperature setpoint (C).
    
    show=True : bool
        Whether to show the window after creating.

    block=False : bool
        Whether to block the console when showing the window.

    window_size=[1,1] : list
        Dimensions of the window.

    """
    def __init__(self, name='Arduino_PID', api_class = arduino_controller_api, temperature_limit=500, show=True, block=False, window_size=[1,300]):
        
        if not _mp._serial: _s._warn('You need to install pyserial to use the Arduino based PID temperature controller.')
        
        # Remebmer the name.
        self.name = name

        # Checks periodically for the last exception
        self.timer_exceptions = _g.TimerExceptions()
        self.timer_exceptions.signal_new_exception.connect(self._new_exception)

        # Where the actual api will live after we connect.
        self.api = None
        self._api_class = api_class

        # Create GUI window
        self.window   = _g.Window(self.name, size=window_size, autosettings_path=name+'.window',event_close = self._window_close)
        
        # Create partitions in the GUI window
        self.grid_top = self.window.place_object(_g.GridLayout(margins=False), alignment=0)
        self.window.new_autorow()
        self.grid_mid = self.window.place_object(_g.GridLayout(margins=False), alignment=0) 
        self.window.new_autorow()
        self.grid_bot = self.window.place_object(_g.GridLayout(margins=False), alignment=0)

       # Get all the available ports
        self._ports = [] # Actual port names for connecting
        ports       = [] # Pretty port names for combo box
        
        if _comports:
            for p in _comports():
                self._ports.append(p.device)
                ports      .append(p.description)

        ports      .append('Simulation')
        self._ports.append('Simulation')
        
        # Add port selector to GUI
        self._label_port = self.grid_top.add(_g.Label('Port:'))
        self.combo_ports = self.grid_top.add(_g.ComboBox(ports, autosettings_path=name+'.combo_ports'))
        
        # Add BAUD selector to GUI
        self.grid_top.add(_g.Label('Baud:'))
        self.combo_baudrates = self.grid_top.add(
            _g.ComboBox(['1200','2400','4800', '9600', '19200', '38400', '57600', '115200'],default_index=3,autosettings_path=name+'.ombo_baudrates'))

        # Add Timeout selctor to GUI
        self.grid_top.add(_g.Label('Timeout:'))
        self.number_timeout = self.grid_top.add(
            _g.NumberBox(200, dec=True, bounds=(1, None), suffix=' ms',
                         tip='How long to wait for an answer before giving up (ms).', autosettings_path=name+'.number_timeout')).set_width(100)

        # Add a button to connect to serial port to GUI
        self.button_connect  = self.grid_top.add(_g.Button('Connect', checkable=True,tip='Connect to the selected serial port.'))
        self.button_connect.signal_toggled.connect(self._button_connect_toggled)

        # Add mode selector button to GUI (manual and control temperature control modes)
        self.grid_mid.add(_g.Label('Mode:')).set_style('color: azure')
        self.button_open_loop  = self.grid_mid.add(_g.Button('Open Loop' ,checkable=True, tip='Enable manual temperature control.'))
        self.button_open_loop.signal_toggled.connect(self._button_open_loop_toggled)
        
        self.button_closed_loop = self.grid_mid.add(_g.Button('Closed Loop',checkable=True, tip='Enable PID temperature control.'))
        self.button_closed_loop.signal_toggled.connect(self._button_closed_loop_toggled)
        
        # Stretch remaining space
        self.grid_top.set_column_stretch(self.grid_top._auto_column)
        self.grid_mid.set_column_stretch(self.grid_mid._auto_column)
        
        # Status
        self.label_status = self.grid_top.add(_g.Label(''))

        # Error
        self.grid_top.new_autorow()
        self.label_message = self.grid_top.add(_g.Label(''), column_span=10).set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
        
        # By default the bottom grid is disabled
        self.grid_bot.disable()

        # Expand the bottom grid
        self.window.set_row_stretch(2)

        # Other data
        self.t0 = None

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=name)

        # Show the window.
        if show: self.window.show(block)
          
        self.window.set_size([0,0])
        
        # Tab for measured temperature
        self.grid_bot.new_autorow()
        
        self.grid_bot.add(_g.Label('Measured:'), alignment=2).set_style(style_big_red)
        self.number_temperature = self.grid_bot.add(_g.NumberBox(
            value=-273.16, suffix='°C', tip='Last recorded temperature value.'
            )).set_width(175).disable().set_style(style_big_red)
        
        self.grid_bot.add(_g.Label('Setpoint:'), alignment=2).set_style(style_big_blue)
        self.number_setpoint = self.grid_bot.add(_g.NumberBox(
            -273.16, bounds=(-273.16, temperature_limit), suffix='°C',
            signal_changed=self._number_setpoint_changed, tip = 'Targeted temperature.'
            )).set_width(175).set_style(style_big_blue)       
        
        #
        #self.grid_bot.new_autorow()
        self.grid_bot.add(_g.Label('DAC Output:'), alignment=2).set_style(style_big_purple)
        
        self.number_output_percentage = self.grid_bot.add(_g.NumberBox(
            value=2.542, suffix='V', decimals = 4, tip='Arduino DAC output to peltie driver (0-5.000 V).'
            )).set_width(175).disable().set_style(style_big_purple)
        
        # Tabs for proportional, integral, and derivative values
        self.grid_bot.new_autorow()
        
        self.grid_bot.add(_g.Label('Band:'),alignment=2).set_style(style_big_green)
        self.proportional = self.grid_bot.add(_g.NumberBox(
            value = 10.0, suffix = '°C', bounds = (0,100.0), decimals=4,
            autosettings_path = name+'.Proportional',
            tip               = 'Prportional band.',
            )).set_width(175).disable().set_style(style_big_green)
        
        
        self.grid_bot.add(_g.Label('Integral time:'),alignment=2).set_style(style_big_green)
        self.integral = self.grid_bot.add(_g.NumberBox(
            value = 88.29, suffix = 's', bounds = (0,100.0), decimals=4,
            autosettings_path = name+'.integral',
            tip               = 'Integral action time.',
            )).set_width(175).disable().set_style(style_big_green)
        
        
        self.grid_bot.add(_g.Label('Derivative time:'),alignment=2).set_style(style_big_green)
        self.derivative = self.grid_bot.add(_g.NumberBox(
            value = 1.02, suffix = 's', bounds = (0,100.0), decimals=4,
            autosettings_path = name+'.derivative',
            tip               = 'Derivative action time.',
            )).set_width(175).disable().set_style(style_big_green)
        
        self.grid_bot.new_autorow()
        #self.grid_bot.set_row_stretch(self.grid_bot._auto_row)
        
        # Make the plotter.
        self.grid_bot.new_autorow()
        self.plot = self.grid_bot.add(_g.DataboxPlot(
            file_type='*.csv',
            autosettings_path=name+'.plot',
            delimiter=',', show_logger=True), alignment=0, column_span=10)

        # Timer for collecting data
        self.timer = _g.Timer(interval_ms=1000, single_shot=False)
        self.timer.signal_tick.connect(self._timer_tick)

        # Bottom log file controls
        self.grid_bot.new_autorow()

        # Finally show it.
        self.window.show(block)


    def _number_setpoint_changed(self, *a):
        """
        Called when someone changes the number.
        """
        # Set the temperature setpoint
        self.api.set_temperature_setpoint(self.number_setpoint.get_value())


    def _timer_tick(self, *a):
        """
        Called whenever the timer ticks. Let's update the plot and save the latest data.
        """
        # Get the time, temperature, and setpoint
        t = _time.time()-self.t0
        T = self.api.get_temperature()
        S = self.api.get_temperature_setpoint()
        P = self.api.get_main_output_power()
        self.number_setpoint.set_value(S, block_signals=True)

        # Append this to the databox
        self.plot.append_row([t, T, S, P], ckeys=['Time (s)', 'Temperature (C)', 'Setpoint (C)', 'Power (%)'])
        self.plot.plot()

        # Update the big red text.
        self.number_temperature(T)

        self.window.process_events()


    def _after_button_connect_toggled(self):
        """
        Called after the connection or disconnection routine.
        """


    def _button_connect_toggled(self, *a):
        """
        Connect by creating the API.
        """
        if self._api_class is None:
            raise Exception('You need to specify an api_class when creating a serial GUI object.')

        # If we checked it, open the connection and start the timer.
        if self.button_connect.is_checked():
            port = self.get_selected_port()
            self.api = self._api_class(
                    port=port,
                    baudrate=int(self.combo_baudrates.get_text()),
                    timeout=self.number_timeout.get_value())
            
            # If we're in simulation mode
            if self.api.simulation_mode:
                self.label_status.set_text('*** Simulation Mode ***')
                self.label_status.set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
                self.button_connect.set_colors(background='pink')
            else:
                self.label_status.set_text('Connected').set_colors('white' if _s.settings['dark_theme_qt'] else 'blue')

            # Record the time if it's not already there.
            if self.t0 is None: self.t0 = _time.time()

            # Enable the grid
            self.grid_bot.enable()

            # Disable other controls
            self.combo_baudrates.disable()
            self.combo_ports.disable()
            
            # 
            self.button_connect.set_colors(background = 'blue')

        # Otherwise, shut it down
        else:
            
            if self.button_open_loop.is_checked()  : self.button_open_loop.click()
            if self.button_closed_loop.is_checked(): self.button_closed_loop.click()
            
            self.api.disconnect()
            self.label_status.set_text('')
            self.button_connect.set_colors()
            self.grid_bot.disable()

            # Enable other controls
            self.combo_baudrates.enable()
            self.combo_ports.enable()
            self.number_timeout.enable()
            
            self.button_connect.set_colors(background = '')

        # User function
        self._after_button_connect_toggled()

    
    def _button_closed_loop_toggled(self):
        
        _debug('button_closed_loop clicked.')
        
        # Turn-off manual control, if enabled!
        if self.button_open_loop.is_checked(): self.button_open_loop.click()
        
        if self.button_closed_loop.is_checked():
            try:
                
                # Set the arduino to closed loop mode
                self.api.set_mode("CLOSED_LOOP")
                
                # Verify the arduino has changed mode
                if( self.api.get_mode() != "CLOSED_LOOP"):
                    print("problem...")
                    raise Exception("Arduino failed to change mode to CLOSED_LOOP.")
                    
                # Start data collection timer
                self.timer.start()
                
                # Enable access to PID variables in the GUI
                self.proportional.enable()
                self.integral    .enable()
                self.derivative  .enable()
                
                # Change button color as indicator
                self.button_closed_loop.set_colors(text = 'white',background='limegreen')
                
                _debug('Closed loop mode enabled.')
                
            except:
                self.number_setpoint.set_value(0)
                self.button_connect.set_checked(False)
                self.label_status.set_text('Could not get temperature.').set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
        else:
            # Stop the data collection timer
            self.timer.stop()
            
            # Disable access to PID variables in the GUI
            self.proportional.disable()
            self.integral.disable()
            self.derivative.disable()
            
            # Reset button color
            self.button_closed_loop.set_colors(background='')
            
            _debug('Closed loop mode disabled.')
        
        
    def _button_open_loop_toggled(self):
        
        _debug('button_open_loop clicked.')
        
        if self.button_closed_loop.is_checked(): self.button_closed_loop.click()
        
        if self.button_open_loop.is_checked():
            try:
                # Set the arduino to closed loop mode
                self.api.set_mode("OPEN_LOOP")
                
                # Verify the arduino has changed mode
                if( self.api.get_mode() != "OPEN_LOOP"):
                    print("problem...")
                    raise Exception("Arduino failed to change mode to OPEN_LOOP.")
                
                # Start data collection timer
                self.timer.start()
                
                # Disable access to manual control variables in the GUI
                self.number_output_percentage.enable()
                
                # Change button color as indicator
                self.button_open_loop.set_colors(text = 'white',background='red')
                
                _debug('Open loop mode enabled.')
            except:
                self.number_setpoint.set_value(0)
                self.button_connect.set_checked(False)
                self.label_status.set_text('Could not get temperature.').set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
        else:
            
            # Stop data collection timer
            self.timer.stop()
            
            # Disable access to manual control variables in the GUI
            self.number_output_percentage.disable()
            
            # Reset button color
            self.button_open_loop.set_colors(background='')
            
            _debug('Open loop mode disabled.')

    
    def _new_exception(self, a):
        """
        Just updates the status with the exception.
        """
        self.label_message(str(a)).set_colors('red')


    def _window_close(self):
        """
        Disconnects. When you close the window.
        """
        print('Window closed but not destroyed. Use show() to bring it back.')
        if self.button_connect():
            print('  Disconnecting...')
            self.button_connect(False)


    def get_selected_port(self):
        """
        Returns the actual port string from the combo box.
        """
        return self._ports[self.combo_ports.get_index()]


def _debug(*a):
    if _debug_enabled:
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

if __name__ == '__main__':
    _egg.clear_egg_settings()
    self = arduino_controller(temperature_limit=700)
    #self = arduino_controller_api(temperature_limit=700)