import usb
import sys
import usb.core
import usb.util
import time

#TODO: Add inline documentation

class rDG1022:
    
    slookup = {1:"(undefined)",
              2:"DEV_DEP_MSG_IN",
              126:"(undefined)",
              127:"VENDOR_SPECIFIC_IN"}
    
    sleepVal = 0.1
    
    def __init__(self, **kwargs):
        
        # Check for verbose (debug) mode
        verbose = False
        if "verbose" in kwargs:
            if kwargs["verbose"]=="True":
                print("-------------------------------------------")
                print("Initializing Rigol DG1022 object in verbose mode.")
                verbose = True
                
        # Find our Rigol DG1022
        self.dev = usb.core.find(idVendor=0x1ab1, idProduct=0x0588)

        if self.dev is None:
            raise ValueError('Device not found')

        # Claim the device, detach the infernal, useless usbtmc module
        if self.dev.is_kernel_driver_active(0):
            reattach = True
            self.dev.detach_kernel_driver(0)

        # Set device configuration
        self.dev.set_configuration()
        
        if verbose:
            print("Connected to "+ str(self.dev))
        
        # Choosing our configuration and interface
        self.cfg = self.dev[0]
        self.intf = self.cfg[(0,0)]
        
        # Define endpoints
        # USB Control endpoint - do we need to use this?
        self.ep_ctl = self.dev[0][(0,0)][0]
        #Bulk endpoint out (host to USB488) this is No. 130
        self.ep_out = usb.util.find_descriptor(
            self.intf,
            custom_match = \
                lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_OUT
        )
        #Bulk endpoint in (USB488 to host) this is No 131
        self.ep_in = usb.util.find_descriptor(
            self.intf,
            custom_match = \
                lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_IN
        )
        
        # Request timeout in milliseconds
        self.timeout=1000
        # Number of bytes to read in during requests
        self.readLength = 2048
        
        #
        # USBTMC State Variables
        #
        self.MsgID = 1
        self.bTag = 1

    def __del__(self):
        # Release USB Resources
        usb.util.dispose_resources(self.dev)
        
    def list_configs(self):
        # List all our configurations and endpoints
        for cfg in self.dev:
            sys.stdout.write(str(cfg.bConfigurationValue) + '\n')
            for intf in cfg:
                sys.stdout.write('\t' + \
                                 str(intf.bInterfaceNumber) + \
                                 ',' + \
                                 str(intf.bAlternateSetting) + \
                                 '\n')
                for ep in intf:
                    sys.stdout.write('\t\t' + \
                                     str(ep.bEndpointAddress) + \
                                     '\n')

# Send a message to the device authorizing it to respond to a previous request.
    def bulkin_auth(self,**kwargs):
        # Check for verbose (debug) mode
        verbose = False
        if "verbose" in kwargs:
            if kwargs["verbose"]=="True":
                print("-------------------------------------------")
                print("Starting bulkin_auth() operation in verbose mode.")
                verbose = True
                
        # sleep for a bit
        #time.sleep(self.sleepVal)
        
        # REQUEST_DEV_DEP_MSG_IN
        # This function sends a message authorizing the device to respond
        self.MsgID = 2
        #
        # Header Data
        #
        
        # Create retval, return message and append MsgID byte
        retval = bytearray([self.MsgID])
        # Then, bTag byte - cycling message ID
        retval.append(self.bTag)
        # Then, bTagInverse byte, (ones complement)
        bTagInv = self.bTag^0xFF
        retval.append(int(bTagInv))
        
        # Then, 0x00 just because that's what we do per spec
        retval.append(0x00)
        
        # Then, USBTMC Command messsage specific header (8 bytes)
        
        # Bytes 4-7 send the transfer size in bytes, not including 
        # any alignment bytes or header bytes. Little Endian. 
        # Size 0x00000000 (4 bytes)
        xferSize = self.ep_ctl.wMaxPacketSize
        xfBytes = xferSize.to_bytes(4,byteorder="little", signed=False)
        
        for b in xfBytes:
            retval.append(b)
        
        #Then, bmTransfer attributes byte
        # Bits 7 thru 2 low, bit 1 high, bit 0 low.
        # Bit 1 enables terminal character
        bmTransfer = int("00000000",2)
        retval.append(bmTransfer)
        
        # Bit 9 is TermChar
        retval.append(0x00)
        
        # Bytes 10 and 11 are empty by spec
        for i in range(2):
            retval.append(0x00)         
            
        if verbose:
            #Sanity check - print the message
            print("Sending REQUEST_DEV_DEP_MSG_IN")
            print("Max return message size: " + str(xferSize) + " chars")
            print("Message to be sent:")
            i=0
            for b in retval:
                if (i%4)==3:
                    print(hex(b))
                else:
                    print(hex(b)+ ' ',end='')

                i+=1

        
        self.bTagIncrement()
        return retval
    
    def compose_message(self,text,**kwargs):
        # Check for verbose (debug) mode
        verbose = False
        if "verbose" in kwargs:
            if kwargs["verbose"]=="True":
                print("-------------------------------------------")
                print("Starting compose_message() operation in verbose mode.")
                verbose = True
                
        # We want a device-specific message using the bulk-in and bulk-out communication ports.
        self.MsgID = 1

        # First, convert our message to bytes and get its size
        text_b = str.encode(text)
        xferSize = len(text_b)
            
        #
        # Header Data
        #
        
        # Create retval, return message and append MsgID byte
        retval = bytearray([self.MsgID])
        # Then, bTag byte - cycling message ID
        retval.append(self.bTag)
        # Then, bTagInverse byte, (ones complement)
        bTagInv = self.bTag^0xFF
        retval.append(int(bTagInv))
        
        # Then, 0x00 just because that's what we do per spec
        retval.append(0x00)
        
        # Then, USBTMC Command messsage specific header (8 bytes)
        
        # Bytes 4-7 send the transfer size in bytes, not including 
        # any alignment bytes or header bytes. Little Endian. 
        # Size 0x00000000 (4 bytes)
        xfBytes = xferSize.to_bytes(4,byteorder="little", signed=False)
        
        for b in xfBytes:
            retval.append(b)
        
        #Then, bmTransfer attributes byte
        # Bits 7 thru 1 are all zeroes by specification
        # Bit zero is EOM - is this the only message?
        bmTransfer = 0x01
        retval.append(bmTransfer)
        
        # Bytes 9-11 (3 bytes) are 0x000000 by specification
        for i in range(3):
            retval.append(0x00)

        #
        # Message data
        #
        
        for byte in text_b:
            retval.append(int(byte))
        #
        # Alignment Bytes
        #
        #Total number of bytes must be a multiple of 4. 
        #Add 0-3 bytes of value 0x00 to accomplish this.
        # Header is composed of 12 bytes.
        alignment = 4-(xferSize % 4)
        
        #print("Alignment total: " + str(alignment))
        
        for i in range(alignment):
            retval.append(0x00)
            
        

        #Sanity check - print the message
        if verbose:
            print("Message size: " + str(xferSize) + " chars")
            print("Message to be sent:")
            i=0
            for b in retval:
                if (i%4)==3:
                    print(hex(b))
                else:
                    print(hex(b)+ ' ',end='')

                i+=1

        #increment message counter
        self.bTagIncrement()
        return retval
        
        
    def bTagIncrement(self):
        if self.bTag<255:
            self.bTag+=1
        else:
            self.bTag=1
        
    # Write a command to the bulk IN port
    def writeCommand(self,bmsg, **kwargs):
        # Check for verbose (debug) mode
        verbose = False
        if "verbose" in kwargs:
            if kwargs["verbose"]=="True":
                print("-------------------------------------------")
                print("Starting writeCommand() operation in verbose mode.")
                verbose = True
                
        #Reset device to ensure a fresh transaction (prevents weird timeout errors)
        self.dev.reset()

        # sleep for a bit
        #time.sleep(self.sleepVal)
        
        if verbose:
            print("Message: " + str(bmsg))
            print("To endpoint: " + str(self.ep_out.bEndpointAddress))
        
        # actually write the message
        assert self.dev.write(self.ep_out.bEndpointAddress,bmsg,self.timeout) == len(bmsg)
        #increment the message counter
        self.bTagIncrement()
        
        if verbose:
            print("writeCommand() successful. \n")

    # Write a message to the control endpoint to reset the interface.
    def writeClear(self, **kwargs):
        verbose = False
        if "verbose" in kwargs:
            if kwargs["verbose"]=="True":
                print("-------------------------------------------")
                print("Starting writeClear() operation in verbose mode.")
                verbose = True

        message = bytearray()
        
        # Making a control request to reset the interface
        #bmRequest Type = 0xA1
        #bRequest = 0x05 
        # wValue = 0x00
        # wIndex = 0x00
        self.dev.ctrl_transfer(0xA1, 0x05, 0x00, 0x00, 0x01)

        #Wait for device to do what we asked
        #time.sleep(0.1)

        if verbose:
            print("Checking clear status. \n")
        # Checking if our clear status completed.
        #bmRequest Type = 0xA1
        #bRequest = 0x06 
        # wValue = 0x00
        # wIndex = 0x00
        # wLength = 0x02
        ret = self.dev.ctrl_transfer(0xA1, 0x06, 0x00, 0x00, 0x02)
        
        sret = ""
        for x in ret:
            sret += hex(x) + " "

        if verbose:
            print("Machine response: " + sret)

        if verbose:
            print("writeClear() successful. \n\n ")

        #TODO: add a thrown exception if we get anything but 0x01 back.


        
#TODO: Add fault tolerance to read() for cases where there's nothing to read.
    def read(self,**kwargs):
        # Check for verbose (debug) mode
        verbose = False
        if "verbose" in kwargs:
            if kwargs["verbose"]=="True":
                print("-------------------------------------------")
                print("Starting read() operation in verbose mode.")
                verbose = True
            
        # Authorize device spitting out response
        #time.sleep(0.1)
        if verbose:
            print("Authorizing device to respond to query");
        bcommand = self.bulkin_auth()
        self.writeCommand(bcommand)
        #time.sleep(0.1)
        
        # Read device's response
        if verbose:
            print("\n Reading from USB endpoint: " + hex(self.ep_in.bEndpointAddress))
        retval = self.dev.read(self.ep_in.bEndpointAddress,self.ep_ctl.wMaxPacketSize)
        
        # Useful variables - fill in depending on context
        message = '' 
        nmsg = ''

        #
        # Header Data
        #
        
        # Transfer input into a byte array
        mret = bytearray()
        for b in retval:
            mret.append(b)
        
        # Make a nicely formatted hex version of the input
        hret = ""
        j = 0
        for i in mret:
            hret += hex(i)
            hret += " "
            if (j%4)==3:
                hret += "\n"
            j+=1
        

        # Print header data
        if verbose:
            print("\n Message Header: ")
        
        try:
            MsgID_string = self.slookup[mret[0]]
        except KeyError:
            MsgID_string = "Reserved MsgID value"
        
        if verbose:
            print("MsgID: " + hex(mret[0]) + " " + MsgID_string)
            print("bTag: " +  hex(mret[1]))
            print("bTagInverse: " +  hex(mret[2]))
            print("Reserved (0x00): " +  hex(mret[3]) + "\n\n")
        
        #
        # command-specific data
        #
        
        if(MsgID_string == "DEV_DEP_MSG_IN"):
            
            #
            # Deal with command-specific header data
            #
            
            # Pull transfer size from data
            xfersizeh = ""
            for h in mret[4:7]:
                xfersizeh += hex(h)
                xfersizeh += " "

            xfersize = int.from_bytes(mret[4:7],byteorder='little', signed=False)
            
            # Pull transfer attributes from data
            xferAttr = bin(mret[8])

            # Pull reserved bytes
            reserved = ""
            for h in mret[9:11]:
                reserved += hex(h)
                reserved += " "

            # Get ASCII message, if any
            message = ""
            for h in mret[12:]:
                message += chr(h)
                
            # Determine if we finished reading the transmisson
            msg_remainder = xfersize-len(message)
            if verbose:
                print("Remaining characters: " + str(msg_remainder))
            
            # Set aside space for any further bytes
            newbytes = bytearray()
            
            while msg_remainder > 0:
                self.bulkin_auth()
                #time.sleep(0.1) #take a breather
                inData = self.dev.read(self.ep_in.bEndpointAddress,msg_remainder)
                
                # Transfer input into a byte array
                for b in inData:
                    newbytes.append(b)
                
                # Stop asking for data if there's no new data
                if(len(inData)==0):
                    break
                    
                # Subtract length of new data from msg_remainder
                msg_remainder -= len(inData)
                    
            # Get ASCII translation
            nmsg = ""
            for h in newbytes:
                nmsg += chr(h)
 
            
            if verbose:
                print("New Data: " + str(newbytes))
                print("New ASCII: " + nmsg)
                print("DEV_DEP_MSG_IN Specific header data: ")
                print("Transfer size: " + str(xfersize))
                print("bmTransferAttributes: " + xferAttr )
                print("Reserved 0x00: " + reserved )
                print("Message output: " + message + nmsg)
                print("Read operation successful.\n\n")
                
        return message+nmsg


    
    ##################################################
    #                Specific Functions              #
    ##################################################
    
    # This part of the file enumerates some device-specific functions
    # that build on the API developed above.

    # Ask a question of the device and get a response
    def query(self, msg):
        bmsg = self.compose_message(msg)
        self.writeCommand(bmsg)
        retval = self.read()
        return(retval)

    def v1(self, voltage):
        cmd = self.compose_message("VOLT " + str(voltage))
        self.writeCommand(cmd)
        
    def v2(self, voltage):
        cmd = self.compose_message("VOLT:CH2 " + str(voltage))
        self.writeCommand(cmd)
        
    def ch1(self):
        cmd = self.compose_message("OUTP ON")
        self.writeCommand(cmd)
        
    def ch2(self):
        cmd = self.compose_message("OUTP:CH2 ON")
        self.writeCommand(cmd)
        
    def f1(self, frequency):
        cmd = self.compose_message("FREQ " + str(frequency))
        self.writeCommand(cmd)
        
    def f2(self, frequency):
        cmd = self.compose_message("FREQ:CH2 " + str(frequency))
        self.writeCommand(cmd)
