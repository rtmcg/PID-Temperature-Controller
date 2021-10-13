/**
 * Based on "Serial Input Basics" by user Robin2 on Arduino forums.
 * See https://forum.arduino.cc/t/serial-input-basics-updated/382007
 */


const char startMarker = '<';
const char endMarker   = '>'; 

void receive_data() {
  static boolean recv_in_progress = false;
  static byte index = 0;
  char rc;

  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();

    if (recv_in_progress == true) {
      if (rc != endMarker) {
        received_data[index] = rc;
        index++;
        if (index >= data_size) {
          index = data_size - 1;
          // Send warning to user that data buffer is full.
        }
      }
      else {
        received_data[index] = '\0'; // terminate the string
        recv_in_progress = false;
        index = 0;
        newData = true;
      }
    }

    else if (rc == startMarker) {
        recv_in_progress = true;
    }
  }
}
