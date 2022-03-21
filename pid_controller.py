'''
<pid_controller.py> to be run with <pid_controller_api.py>
Connects to an Arduino microcontroller running <PID.ino>

For use in the McGill University physics course PHYS 339.
Written by Brandon Ruffolo in 2021-22.
brandon.ruffolo@mcgill.ca
'''

import mcphysics   as _mp
import spinmob.egg as _egg
import traceback   as _traceback
import spinmob     as _s
import time        as _time

from pid_controller_api import pid_api

try: from serial.tools.list_ports import comports as _comports
except: _comports = None

_p = _traceback.print_last
_g = _egg.gui

_dac_bit_depth = 12 
_dac_voltage   = 5.

_debug_enabled = True

# Dark theme
_s.settings['dark_theme_qt'] = True

## Fonts ##
style_1    = 'font-size: 17pt; font-weight: bold; color: ' +('white'              if _s.settings['dark_theme_qt'] else 'royalblue')
style_2    = 'font-size: 17pt; font-weight: bold; color: ' +('mediumspringgreen'  if _s.settings['dark_theme_qt'] else 'mediumspringgreen')
style_3    = 'font-size: 14pt; font-weight: bold; color: ' +('lightcoral'         if _s.settings['dark_theme_qt'] else 'lightcoral')
style_4    = 'font-size: 14pt; font-weight: bold; color: ' +('paleturquoise'      if _s.settings['dark_theme_qt'] else 'lightcoral')
style_5    = 'font-size: 14pt; font-weight: bold; color: ' +('paleturquoise'      if _s.settings['dark_theme_qt'] else 'lightcoral')
style_6    = 'font-size: 14pt; font-weight: bold; color: ' +('mediumspringgreen'  if _s.settings['dark_theme_qt'] else 'mediumspringgreen')



class pid_controller(_g.BaseObject):
    """
    Graphical interface for the Arduino based PID temperature controller.
    
    Parameters
    ----------
    name='Arduino_PID' : str
        Unique name to give this instance, so that its settings will not
        collide with other egg objects.
    
    temperature_limit=85 : float
        Upper limit on the temperature setpoint (C).
    
    show=True : bool
        Whether to show the window after creating.
        
    block=False : bool
        Whether to block the console when showing the window.
        
    window_size=[1,1] : list
        Dimensions of the window.
    """
    def __init__(self, name='Arduino_PID', api_class = pid_api, temperature_limit=85, show=True, block=False, window_size=None):
        
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
        self.window   = _g.Window(self.name, autosettings_path=name+'.window',event_close = self._window_close)
        

       # Get all the available ports
        self._ports = [] # Actual port names for connecting
        ports       = [] # Pretty port names for combo box
        
        default_port = None
        
        if _comports:
            for inx, p in enumerate(_comports()):
                self._ports.append(p.device)
                ports      .append(p.description)
                
                if 'Arduino' in p.description:
                    default_port = inx
                    

        ports      .append('Simulation')
        self._ports.append('Simulation')
        
        # Populate the GUI window 
        self.populate_window(ports, default_port, temperature_limit, show, block)
        
        # Create Timer for collecting data 
        self.timer = _g.Timer(interval_ms=1000, single_shot=False)
        self.timer.signal_tick.connect(self._timer_tick)

        # Show the GUI!
        self.window.show(block)


    def _number_setpoint_changed(self, *a):
        """
        Called when someone changes the setpoint number in the GUI.
        Updates the temperature setpoint on the arduino.
        
        """
        # Set the temperature setpoint
        self.api.set_temperature_setpoint(self.number_setpoint.get_value())
    
    
    def _number_dac_changed(self):
        """
        Called when someone changes the dac output number in the GUI.
        Updates the dac output on the arduino.
        
        Note
        ----
        The true output voltage of the dac will be the closest voltage
        that can be generated with the dac's bit depth.
        
        """
        
        voltage = self.number_dac.get_value()
        
        # Convert floating point number into closest integer using _dac_bit_depth 
        bit_voltage = round( (2**_dac_bit_depth-1)*voltage/5.)
        
        self.api.set_dac(bit_voltage)
        
        
    def _number_parameter_changed(self):
        """
        Called when someone changes one of the control parameters in the GUI.
        Updates all the control parameters on the arduino.

        """
        
        band = self.number_proportional.get_value()
        t_i  = self.number_integral    .get_value()
        t_d  = self.number_derivative  .get_value()
        
        self.api.set_parameters(band, t_i, t_d)


    def _number_period_changed(self):
        """
        Called when someone changes the control period number in the GUI.
        Updates the control period on the arduino.

        """
        _period = self.number_period.get_value()
        
        self.api.set_period(_period)
        
        
    def _timer_tick(self, *a):
        """
        Called whenever the timer ticks. 
        Updates all parameters and the plot and saves the latest data.
        
        """
        
        t                        = _time.time()-self.t0
        T, S, dac_level, P, I, D, period = self.api.get_all_variables()
        
        # Convert dac_level to a fraction (based on DAC bit depth)
        output_fraction = dac_level/(2**_dac_bit_depth-1)
        
        # Compute the dac output voltage
        dac_voltage = _dac_voltage*output_fraction
        
        # Update the temperature, dac voltage, and setpoint
        self.number_temperature.set_value(T)
        self.number_dac        .set_value(dac_voltage, block_signals=True)
        self.number_setpoint   .set_value(S, block_signals=True)
        
        # Update control parameters
        self.number_proportional.set_value(P, block_signals=True)
        self.number_integral    .set_value(I, block_signals=True)
        self.number_derivative  .set_value(D, block_signals=True)
        self.number_period      .set_value(period, block_signals=True)
                
        # Append this to the databox
        self.plot.append_row([t, T, T-S, 100*output_fraction], ckeys=['Time (s)', 'Temperature (C)', 'Temperature Error (C)', 'DAC Voltage (%)'],)
        self.plot.plot()        

        # Update GUI
        self.window.process_events()
        

    def _button_connect_toggled(self, *a):
        """
        Called when the connect button is toggled in the GUI. 
        Creates the API and imports data from the arduino.
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
            if self.api.simulation:
                self.label_status.set_text('*** Simulation ***')
                self.label_status.set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
                self.button_connect.set_colors(background='pink')
            else:
                self.label_status.set_text('Connected').set_colors('white' if _s.settings['dark_theme_qt'] else 'blue')
                
                self.button_open_loop  .enable()
                self.button_closed_loop.enable()
                
                # Get temperature and parameter data currently on the arduino
                T            = self.api.get_temperature()
                S            = self.api.get_temperature_setpoint()
                period       = self.api.get_period()
                P, I, D      = self.api.get_parameters()
                dac_output   = self.api.get_dac()
                
                # Update the temperature, setpoint, and parameter tabs
                self.number_temperature(T)
                self.number_setpoint    .set_value(S,          block_signals=True)
                self.number_period      .set_value(period,     block_signals=True)
                self.number_proportional.set_value(P,          block_signals=True)
                self.number_integral    .set_value(I,          block_signals=True)
                self.number_derivative  .set_value(D,          block_signals=True)
                self.number_dac         .set_value(dac_output, block_signals=True)

            # Record the time if it's not already there.
            if self.t0 is None: self.t0 = _time.time()

            # Enable the grid
            self.grid_bot.enable()

            # Disable other controls
            self.combo_baudrates.disable()
            self.combo_ports.disable()
            self.number_timeout.disable()
            
            # Change the button color to indicate we are connected
            self.button_connect.set_colors(background = 'blue')

        # Otherwise, shut it down
        else:
            
            # Turn off the open/closed loop buttons
            if self.button_open_loop.is_checked()  : self.button_open_loop.click()
            if self.button_closed_loop.is_checked(): self.button_closed_loop.click()
            
                            
            self.button_open_loop  .disable()
            self.button_closed_loop.disable()
            
            # Disconnect the API
            self.api.disconnect()
            
            #
            self.label_status.set_text('')
            self.button_connect.set_colors()
            
            # Disable plotting
            self.grid_bot.disable()

            # Re-enable other controls
            self.combo_baudrates.enable()
            self.combo_ports.enable()
            self.number_timeout.enable()
    
    
    def _button_closed_loop_toggled(self):
        """
        Called when the closed loop button is toggled in the GUI.
        Enables all closed loop control parameter fields in the GUI
        (band, derivative, integral, period).
        Disables all open loop control parameter fields in the GUI
        (Dac output).
        Changes arduino mode to CLOSED_LOOP.
        

        Raises
        ------
        Exception
            If the arduino fails to change mode.

        """
        
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
                self.number_proportional.enable()
                self.number_integral    .enable()
                self.number_derivative  .enable()
                self.number_period      .enable()
                
                
                # Change button color as indicator
                self.button_closed_loop.set_colors(text = 'white',background='limegreen')
                
                _debug('CLOSED_LOOP mode enabled.')
                
            except:
                self.number_setpoint.set_value(0)
                self.button_connect.set_checked(False)
                

        else:
            # Stop the data collection timer
            self.timer.stop()
            
            # Disable access to PID variables in the GUI
            self.number_proportional.disable()
            self.number_integral    .disable()
            self.number_derivative  .disable()
            self.number_period      .disable()
            
            # Reset button color
            self.button_closed_loop.set_colors(background='')
            
            _debug('Closed loop mode disabled.')
        
        
    def _button_open_loop_toggled(self):
        """
        Called when the open loop button is toggled in the GUI.
        Enables all open loop control parameter fields in the GUI (Dac output).
        Disables all closed loop control parameter fields in the GUI
        (band, derivative, integral, period).
        Changes arduino mode to CLOSED_LOOP.
        

        Raises
        ------
        Exception
            If the arduino fails to change mode.

        """
        
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
                self.number_dac.enable()
                
                # Change button color as indicator
                self.button_open_loop.set_colors(text = 'white',background='red')
                
                _debug('OPEN_LOOP mode enabled.')
            except:
                self.number_setpoint.set_value(0)
                self.button_connect.set_checked(False)
                self.label_status.set_text('Could not get temperature.').set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
        else:
            
            # Stop data collection timer
            self.timer.stop()
            
            # Disable access to manual control variables in the GUI
            self.number_dac.disable()
            
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
    
    
    def populate_window(self, ports, default_port, temperature_limit, show, block):
        """
        All the GUI window populating shoved into one convenient (and out of site) place. 
        """
        
        ## Create partitions in the GUI window ##
        
        self.grid_top = self.window.place_object(
            _g.GridLayout(margins=False),0,0,alignment=1,column_span=2)
        
        self.window.new_autorow()
        self.grid_mid = self.window.place_object(_g.GridLayout(margins=False),0,1,alignment=1,column_span=1) 
        
        self.window.new_autorow()
        self.grid_temperature = self.window.place_object(_g.GridLayout(margins=False),0,3,alignment=1,column_span=1)
        
        self.window.new_autorow()
        self.grid_params = self.window.place_object(_g.GridLayout(margins=False),0,4,alignment=1,column_span=1)
        
        self.window.new_autorow()
        self.grid_params1 = self.window.place_object(_g.GridLayout(margins=False),1,4,alignment=1,column_span=1)
        
        self.window.new_autorow()
        self.grid_bot = self.window.place_object(_g.GridLayout(margins=False),0,5,alignment=0,column_span=4)
        
        ## Add widgets (buttons, selectors, ect..) to the GUI ##
        
        # Add port selector to GUI 
        self._label_port = self.grid_top.add(_g.Label('Port:'))
        self.combo_ports = self.grid_top.add(_g.ComboBox(ports, default_index = default_port, autosettings_path=self.name+'.combo_ports'))
        
        # Add BAUD selector to GUI 
        self.grid_top.add(_g.Label('Baud:'))
        self.combo_baudrates = self.grid_top.add(
            _g.ComboBox(['1200','2400','4800', '9600', '19200', '38400', '57600', '115200'],default_index=7,autosettings_path=
                        self.name+'.combo_baudrates'))

        # Add Timeout selector to GUI 
        self.grid_top.add(_g.Label('Timeout:'))
        self.number_timeout = self.grid_top.add(
            _g.NumberBox(500, dec=True, bounds=(1, None), suffix=' ms',
                         tip='How long to wait for an answer before giving up (ms).', autosettings_path=self.name+'.number_timeout')).set_width(100)

        # Add a button to connect to serial port to GUI
        self.button_connect  = self.grid_top.add(_g.Button('Connect', checkable=True,tip='Connect to the selected serial port.'))
        self.button_connect.signal_toggled.connect(self._button_connect_toggled)

        ## Add mode buttons to GUI (open and closed loop control modes)
        self.grid_mid.add(_g.Label('Mode:')).set_style('color: azure')
        
        # Open loop (manual) control mode activation button
        self.button_open_loop  = self.grid_mid.add(_g.Button('Open Loop' ,checkable=True, tip='Enable manual temperature control.')).disable()
        self.button_open_loop.signal_toggled.connect(self._button_open_loop_toggled)
        
        # Closed loop control mode activation button
        self.button_closed_loop = self.grid_mid.add(_g.Button('Closed Loop',checkable=True, tip='Enable PID temperature control.')).disable()
        self.button_closed_loop.signal_toggled.connect(self._button_closed_loop_toggled)
        
        
        # Status
        self.label_status = self.grid_top.add(_g.Label(''))

        # Error
        self.grid_top.new_autorow()
        self.label_message = self.grid_top.add(_g.Label(''), column_span=1).set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
        
        # By default the bottom grid is disabled
        self.grid_bot.disable()


        # Other data
        self.t0 = None

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=self.name)

        # Show the window.
        if show: self.window.show(block)
          
        self.window.set_size([0,0])
        
        # Data box width
        box_width = 175
        
        ## Create tabs for each data feild we want ##
        
        # Tab for monitoring measured temperature
        self.grid_temperature.add(_g.Label('Measured Temperature:'), alignment=2).set_style(style_1)
        self.number_temperature = self.grid_temperature.add(_g.NumberBox(
            value=-273.16, suffix='°C', tip='Last recorded temperature value.'), alignment=2).set_width(box_width).disable().set_style(style_1)
        
        
        # Tab for setting the temperature setpoint
        self.grid_params.add(_g.Label('Setpoint Temperature:'), alignment=1).set_style(style_4)
        self.number_setpoint = self.grid_params.add(_g.NumberBox(
            -273.16, bounds=(-273.16, temperature_limit), suffix='°C',signal_changed = self._number_setpoint_changed,
            tip = 'Targeted temperature.'), alignment=1).set_width(box_width).set_style(style_4)  
        
        # New row
        self.grid_params.new_autorow()
        
        # Tab for setting the control period
        self.grid_params.add(_g.Label('Contol Period:'), alignment=1).set_style(style_5)
        self.number_period = self.grid_params.add(_g.NumberBox(
            value = 100, suffix = 'ms', bounds = (0,10000), autosettings_path = self.name+'.Period',
            signal_changed = self._number_period_changed,
            tip = 'Time between calls to the control function.'), alignment=1).set_width(box_width).disable().set_style(style_5)

        # New row
        self.grid_params.new_autorow()
        
        # Tab for monitoring and/or setting the DAC output voltage 
        self.grid_params.add(_g.Label('DAC output:'), alignment=1).set_style(style_3)
        self.number_dac = self.grid_params.add(_g.NumberBox(
            value=0.000, suffix='V', decimals = 4, tip='Arduino DAC output to peltier driver (0-5.000 V).',
            signal_changed = self._number_dac_changed), alignment=1).set_width(box_width).disable().set_style(style_3)
    
        # Tabs for band PID value
        self.grid_params1.add(_g.Label('Band:'),alignment=1).set_style(style_6)
        self.number_proportional = self.grid_params1.add(_g.NumberBox(
            value = 10.0, suffix = '°C', bounds = (0,10.0), decimals=4,
            autosettings_path = self.name+'.Proportional', signal_changed = self._number_parameter_changed,
            tip = 'Prportional band.'), alignment=1).set_width(box_width).disable().set_style(style_6)
        
        # New row
        self.grid_params1.new_autorow()
        
        # Tab for integral time PID value
        self.grid_params1.add(_g.Label('Integral time:'),alignment=1).set_style(style_6)
        self.number_integral = self.grid_params1.add(_g.NumberBox(
            value = 88.29, suffix = 'ms', bounds = (0,10000.0), decimals=4,
            autosettings_path = self.name+'.integral', signal_changed = self._number_parameter_changed,
            tip = 'Integral action time.'), alignment=1).set_width(box_width).disable().set_style(style_6)
        
        # New row
        self.grid_params1.new_autorow()
        
        # Tab for derivative time PID value
        self.grid_params1.add(_g.Label('Derivative time:'),alignment=1).set_style(style_6)
        self.number_derivative = self.grid_params1.add(_g.NumberBox(
            value = 1.02, suffix = 'ms', bounds = (0,100.0), decimals=4,
            autosettings_path = self.name+'.derivative', signal_changed = self._number_parameter_changed,
            tip = 'Derivative action time.'), alignment=1).set_width(box_width).disable().set_style(style_6)
        
        # New row
        self.grid_bot.new_autorow()
        
        ## Make the plotter ##
        self.plot = self.grid_bot.add(_g.DataboxPlot(
            file_type='*.csv',
            autosettings_path=self.name+'.plot',
            delimiter=',', show_logger=True), alignment=0, column_span=10)

        # Bottom log file controls
        self.grid_bot.new_autorow()
        
        

def _debug(*a):
    if _debug_enabled:
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

if __name__ == '__main__':
    _egg.clear_egg_settings()
    self = pid_controller(temperature_limit=80)