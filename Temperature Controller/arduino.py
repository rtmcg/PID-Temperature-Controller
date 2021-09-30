
"""
@author(s): 
            James Fraser - Original (2018)
            Greg         - Modified for Python 3 (2020-2021)
            Brandon      - Modified for new version of this lab
"""

import serial    as _serial
import numpy     as _n
import datetime  as _dt
import struct    as _struct
import threading as _threading
import time      as _time

_debug = False

class arduino:
    """
    Class for talking to an arduino. 

    Parameters
    ----------
    port = 'COM3': str
        Name of the port to connect to. 

    verbose = False: boolean
        Whether or not to print additional details of the operation of this software.
    """


    def __init__(self, port = 'COM3', verbose = True):
        
        self._verbose = verbose
        self.running  = False     # When not running

        self.mainStorage   = []   # Storage for arduino data
        self.headerTable   = []   # Storage for recorded variables
        self.unitTable     = []   # Storage for units
        self.initVar       = []   # List for initalized variables
        self.initSetRecord = []   # List for recording initial settings
        
        self.initVarCount = 0 # Counts initial variables
        self.recVarCount  = 0 # Recorded variable counts

        if self._verbose: print("Verbose mode activated.")        
        print("\nAttempting to open serial port...")

        # Try opening the port
        try:
            self.device = _serial.Serial(port, baudrate = 115200, timeout = 1.0)
            print(f"Found device at {port}. \n")
        except:
            raise Exception(f"Unable to connect to Arduino at " + port + ". Check that it's plugged in and the drivers are properly installed.")
        
        self.reboot() # Reboot the arduino (as a precaution?)
        if self._verbose: print("Buffer contents before Handshake: ",self.device.read(100))

        for attempt in range(1,10):
            # Attempt handshake protocol with the arduino
            try:
                self.send("HANDSHAKE")
                resp = self.getResp().replace("\t","") # readline from arduino & get rid of tabs
                
                if self._verbose: print("Arduino handshake response on attempt %d: %s"%(attempt,repr(resp)))
                
                if resp == "HANDSHAKE": # If get this from arduino
                    print("Successful handshake, Arduino and Python are communicating.\n") 
                    break 
            except: # If no response is received 
                if self._verbose: print("No response recieved.\n") 
            
            if attempt == 10: # Too many attempts
                # Close port, print exception.
                self.device.close() 
                raise Exception(f"\nUnable to handshake with Arduino. Ask Technician for help.")  

        # Get the initial variables from the arduino
        self.getInitVar() 

        # Creates thread for data collection
        self.thread = _threading.Thread(target = self.dataCollection, name = "Data collection loop") 


    def reboot(self):
        """
        Reboots the arduino by toggling the dtr line.
        """
        if _debug: print("Rebooting arduino by dtr toggle.\n")

        # Toggle the dtr line
        self.device.dtr = True 
        self.device.dtr = False
        self.device.dtr = True  

        # Sleep to give the arduino time to run its setup routine
        _time.sleep(1) 


    def send(self,message):
        """
        Writes the supplied message to the Arduino.

        Parameters
        ----------
        message: str
            String message to send to arduino.

        """
        message = message + '\n' # Add a newline, since arduino code expects it
        self.device.write(message.encode()) # Encode string to bytes and write to serial port
        if _debug: print("Send: " + repr(message) )
   
     
    def getResp(self):
        """
        Reads a message and returns it.
        """

        # Readline from serial port, using latin-1 (iso-8859-1 for single bytes)
        message = self.device.readline().decode('ISO-8859-1', errors='ignore')

        # Clean up the message
        message = message.split('\r\n')[0].replace('\n', '')
        if _debug: print("Received: %s "%repr(message))

        return message
    
        
    def getInitVar(self):
        """
        Get the initial variables defined in the Arduino code.
        """

        if self._verbose : print("Acquiring INIT variables from Arduino.\n")
        rowCount = 0
        outputArry = []
        trying = True     # Run condition
        while trying:
            rawVar = self.getResp()                 # Get it    
            if (rawVar != "READY") :                # After HANDSHAKE is sent, ARduino responds with all the INIT variables, followed by READY
                    splitVar = rawVar.split("\t")   # Clean it
                    rowCount+=1                     # Add to count
                    for i in splitVar:
                        #if (i is not'=' )and (i != ""): # cleans junk
                        if i != '=' and i != "": # cleans junk # is not gave a warning, said to use !=
                            outputArry.append(i)    # Put into the variable array
                
            elif (rawVar == "READY"):               # Indicates all INIT variables have been sent
                trying = False                      # Change run condition
                print("INIT variables acquired: ")
                outputArry = _n.reshape(outputArry, (rowCount-1,4))     # Minus 1 because there's a junk line to remove
                for i in outputArry:
                    i[2] = convertHexToDec(i[2])                   # Convert the values from hex float to dec float
                print(outputArry)   
                self.initVar = outputArry # initial variables set to output array
                self.initVarCount = rowCount-1 # counts initial variables            
    
    
    def genLabelTables(self):
        """
        Using the first two batches of data from the Arduino, two tables for the  
        This is not used for the INIT variables.
        """
        run = 0                                  # Running condition for the while loop
        if self._verbose: print("CREATING LABEL TABLES")
        while run == 0:
            line = self.getResp()                # Read line of data
            line = line.split("\t")              # Split data by tab 
            print("\nLINE: ", line)
            if (line[0] =="VALUE"):              # Lines with VALUE in the first position represent the recorded variables
                self.headerTable.append(line[1]) # Index one is where the variable names are stored
                self.unitTable.append(line[4])   # Index four is where the variale's units are stored
                if self._verbose : print("Header Table: ", self.headerTable)
                if self._verbose : print("Unit Table: ", self.unitTable)
            elif (line[0] == "INDEX"):           # If it begins with INDEX, then one full block has been completed
                run = 1 
                self.headerTable.append('Time Index')   # add to header table
                self.recVarCount = len(self.headerTable) # number of variables received


    def associate(self, frame):
        """
        Get access to the TKInter object's methods.

        Parameters
        ----------    
        frame:                             

        """
        self.frame = frame
        
    
    def start(self):       
        """
            Start the program. 

            NOTE
            ----------
            This should only be called once, and from the tkinter object.
        """
        self.mainStorage = [] # list for data
        print("\nBeginning data acquisition, this may take a moment or two, depending on certain settings\n")       
        clearing = True # while clearing junk
        attemptCount = 0
        while clearing :    # This while loop clears the junk, and will permit the START signal to be properly received. could probably be optimized
            if attemptCount == 5: # if doesn't clear junk after 5 tries, raise exception
                raise Exception("EXCEPTION: Unable to successfully start data acquisition.")
            resp = self.device.readline().decode(errors='ignore')   # Clears junk #changed for python3
            if self._verbose : print("Response in start method:", resp)
            #if (resp ==''):                 # THIS DOES NOT SEEM LIKE A GOOD SOLUTION     
            if resp == '':                 # THIS DOES NOT SEEM LIKE A GOOD SOLUTION 
                attemptCount += 1              
                self.send("START") # write to arduino
                #resp = self.device.readline()
                resp = self.device.readline().decode(errors='ignore')#.split('\r\n')[0]  #changed for python3
                #if (resp == 'INDEX\t0\t1\n'): 
                print('raw_resp' , resp) # testing
                if resp == 'INDEX\t0\t1\n': # excpected response  
                    clearing = False # leave loop
                    if self._verbose: print("Done clearing junk!")
            #elif (resp =='INDEX\t0\t1\n'):
            elif resp == 'INDEX\t0\t1\n': # expected response
                clearing = False # leave loop
                if self._verbose: print("Done clearing junk!")
                
        self.genLabelTables()               # Get string table of labels from Arduino, should grow arbitrarily large. 
                                            # If start() = self.send("START"), would need to put the clearing code into  self.genLabelTables()


    def stop(self):  
        """
        Stops data collection and data retention
        """ 
        self.send("STOP")
        self.running = False


    def set(self, varName, inputVal):
        """
        Changed parameters defined on the Arduino. 
        
        
        Parameters
        ----------
        varName: str
            String representing the name of the variable that will be modified.

        inputVal: 
            New value for the corresponding variable.
        
        NOTE
        ----------
        Best used only when running, and could probably use a run condition based on the flag self.running

        """

        # Check that the proper data type has been submitted
        try: inputVal = str( float(inputVal) ) 
        except:
            print("\nCANNOT SET, BAD INPUT: Only integer and float values are accepted.\n")
            return
        
        
        running_flag = False
        
        # Stop data collection if it is currently running.
        if self.running == True : 
            if self._verbose: print("PAUSING DATA COLLECTION.")
            self.running = False  # Stops data collection
            running_flag = True   # Flag to indicate we've temporarily turned off the running condition
            
        print("Sending to Arduino")                                                  
        packedMessage = "SET "+ varName + " " + str(inputVal) # put together set message
        if len(self.mainStorage) > 0: # if data in mainstorage
            latestVals = self.mainStorage[-1] # last value in main storage
        else:
            latestVals = [0] # if no values in main storage, probably should be [0,0,0,0], though set buttons are deactivated when program starts, so there should be some data 
        self.initSetRecord.append([varName, inputVal, latestVals[4]]) # changed latestVals[0] to latestVals[4] so time index is recorded, not out, gets variable and new set value
        
        self.send(packedMessage) # sends set message to arduino
        self.device.flush() # Wait for the serial line to finish clearing
        self.send("\n")     # Add a newline character to finish the message
        
        print("Sent " + packedMessage + " to Arduino")                   

        # Restart data collection if it was previously running                     
        if running_flag == True:  self.running = True


    def save(self, fileName = ''):   
        """
        Writes data from main storage into a comma seperated value (csv) file. 
        If any SET operations have been done, they will be written to a seperate file.

        Parameters
        ----------
        fileName: str
            String representing name of the file that will be created.
        
        NOTE
        ----------
        If no file name is supplied, the data will be placed in files named with the current date and time.
        """
        
        if fileName == '': # If no file name was submitted
            timeDate = _dt.datetime.now().strftime("%Y%m%d_%H%M%S") # Get datetime string

            # Create file names
            fileName    =  timeDate + " PRIMARY THERMAL DATA.csv"      
            initRecName =  timeDate + " INIT CHANGES.csv"  
        elif fileName != '':
            initRecName = fileName + " INIT CHANGES.csv"
            fileName    = fileName + '.csv' 
            
        # Add the header table to the main storage array, for ease of reading when the data is examined later
        self.mainStorage.insert(0, self.headerTable) 
        if self._verbose: print("Main storage array:", self.mainStorage)
        
        # Save the data    
        _n.savetxt(fileName, self.mainStorage, delimiter =",", fmt = '%s')
        print("\n\nSaved main storage under the filename: ", fileName, "\n\n")
        
        # If any SET operations have been recorded, save them too
        if len(self.initSetRecord) > 0:

            # Create header
            initRecHeader =["Variable", "Value", "Time Index"]

            # Place header at top of record
            self.initSetRecord.insert(0, initRecHeader)

            # Save the data
            _n.savetxt(initRecName, self.initSetRecord, delimiter = ',' , fmt = '%s')
            print("Changes to INIT variables have been recorded and saved as: ", (initRecName))


    def closePort(self):
        """
        Close the serial port.

        """

        # Cancel a pending read operation from another thread
        self.device.cancel_read()

        # Close the port 
        self.device.close()

        # Delete device object
        del self.device

        if self._verbose: print("\nPort closed.\n")
        
        
    def dataCollection(self):          
        """
        Primary method for data collection from the arduino.

        NOTE
        ----------
        This is an inifinite loop continually running in a 'threading' thread.
        The data collection operations of this function are activated and deactivated 
        via the exposed start() and stop() functions.

        """
        tempStorage = []
        
        if self._verbose : print("\nStarting data collection loop.")
        
        while True:
            while self.running:
                try:
                    resp = self.getResp()               # Readline
                except:
                    resp = '' # use continue to not return empty string when read errors, changed for python 3
                if resp != '':                      # Necessary, because had to add a Serial.println() in Arduino that limits problems junk data
                    respSplit = resp.split("\t")    # Create table
                    
                    #if (len(respSplit) != 5 ) and  (len(respSplit) != 3 ):  # Helps avoid processing junk
                    if len(respSplit) != 5 and len(respSplit) != 3:  # Helps avoid processing junk
                        if self._verbose: print("\n\nGARBAGE FOUND IN dataCollection (", respSplit,") BAD RESPONSE LENGTH.\n\n")
                        
                    elif respSplit[0] == "INDEX":               # Get the time index
                        tempStorage.append(int(respSplit[2]))   # Append the index to tempStorage
                        
                    elif respSplit[0] == "VALUE":                       # Collect the unit
                        respConv = self.convertHexToDec(respSplit[3])   # Converts from hex float to decimal float
                        tempStorage.append(respConv)                    # Convert then add value to the tempStorage  
                        
                    else :
                        if self._verbose: print("\n\nGARBAGE FOUND IN dataCollection: ", resp, "\n\n")        # Catches the garbage of length 5 and 3
                        
                    #if (len(tempStorage) == (len(self.headerTable))) :  # Once a block has been completely read, it's time to append the data to the main storage array
                    if len(tempStorage) == len(self.headerTable):  # Once a block has been completely read, it's time to append the data to the main storage array
                            self.mainStorage.append(tempStorage)        # Add temp to main array
                            if self._verbose: print("DATA STORED AS: ", tempStorage, "\n")
                            tempStorage = []
                   
 
def convertHexToDec(hexVal): 
    """
    Converts Hexadecimal values to Decimal.
    """
    try:
        if hexVal == '0': hexVal = "00000000" # Turn into hexadecimal value
        
        # Struct module performs conversions between Python values and C structs represented as Python bytes objects. 
        # Create bytes from hexadecimal value, unpack it as float from big-endian byte order, 
        # and take first value since result is tuple
        value = _struct.unpack('!f', bytes.fromhex(hexVal))[0]

        return value    
    except: print("JUNK DATA: " + hexVal)
