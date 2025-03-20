/*

2/1/2025
FIRST CONTACT ART PROJECT 
Contact Sensor and Music Player - Eric Linn Rabinowitz. 415-336-6938

This code is the contact sensor + Music Player that runs in each sculpture.

Details:
========
  Human Contact Sensing
  The contact sensing is performed by sending a sine wave through the line out pin(s)
  of the Audio Shield DAC to the sculpture hands.
  The receiving side listens for the sinewave tone.
  The sinewave generation, tone detection and DAC drivers are part of the PJRC audio library.

Audio Player:
-------------
  Audio wave files are stored in a MicroSd card on the Teensy board with a DOS-format.
  There is another MicroSd slot on the Audio but it is not used.

  Audio is played using using thr PJRC audio library

Audio Mixing:
-------------
  Both the sensing and audio player share the PJRC audio library and send their outputs through the same
  DAC (Digital to Analog Converter).   Mixing of the signals is performed with the PJRC Audio Library.

Networking
-----------
  A  CAT-5 network interface is connected to an external, on-board ethernet chip via a SPI in interface.
  A full TCP/UDP-IP stack is utilized using the QNEthernet library
  The network address is obtained using DHCP from the Rasspberry PI.
  DNS is used for all network devices.
  We employed MQTT (aka 'Mosquito') for messaging.
  This software acts as both a MQTT publisher and subscriber for events.
  The MQTT Broker (databasde server) is running on a Raspberry PI on the network.

Hardware:  
---------
          Teensy 4.1 + Teensy Audio Shield (DAC)
          Ethernet adapter and cable
          SSD1307 OledDisplay


Software Requirements:
======================
          Arduino IDE 2.3.4

Boards Support:
          Teensy (for Arduino IDE 2.0.4 or later). v.1.59.0
            Instructions to install: https://www.pjrc.com/teensy/td_download.html 
            Installer For IDE: https://www.pjrc.com/teensy/package_teensy_index.json
            NOTE: I think this also installs the Audio library
Libraries:
          Using library SPI at version 1.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SPI 
          Using library Wire at version 1.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/Wire 
          Using library Adafruit GFX Library at version 1.12.0 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_GFX_Library 
          Using library Adafruit BusIO at version 1.17.0 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_BusIO 
          Using library Adafruit SSD1306 at version 2.5.13 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_SSD1306 
          Using library Audio at version 1.3 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/Audio 
          Using library SD at version 2.0.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SD 
          Using library SdFat at version 2.1.2 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SdFat 
          Using library SerialFlash at version 0.5 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SerialFlash 
          Using library QNEthernet at version 0.31.0 in folder: /Users/eric/work/FirstContact/libraries/QNEthernet 
          Using library PubSubClient at version 2.8 in folder: /Users/eric/work/FirstContact/libraries/PubSubClient 




*/

//
// OLED DISPLAY
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define DISPLAY_ENABLED 1
#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
// The pins for I2C are defined by the Wire-library. 
#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
//#define SCREEN_ADDRESS 0x3D ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32
#define SCREEN_ADDRESS 0xBC // NOTE: This value is not documented well and totally confusing when looking at the pcb silkcreen
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire2, OLED_RESET);
// OLED DISPLAY
//



// ------ Audio Includes - Start
#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>
// ------ Audio Includes - End


/* I Added these files to the MicroSd Card */

char file[][40] {
    "Formant Squish2.wav",
    "fire.wav",
    "venus.wav",
    "mars.wav",
    "hold_on.wav",
    "thats_it.wav",
    "connected.wav",
    "disconnected.wav",
    "0.wav",
    "1.wav",
    "2.wav",
    "3.wav",
    "4.wav",
    "5.wav",
    "6.wav",
    "7.wav",
    "8.wav",
    "9.wav",
    "10.wav",
    "comeon.wav",
    "come_here.wav",
    "are_you_from.wav",
    "commander2.wav",
    "standing_by2.wav",
    "Alternating Harmonics2.wav",
    "sample_022.wav",
    "Formant Squish2.wav",
    "Hollow Distorted FM2.wav",
    "wow.wav",
    "feelsreallygood.wav",
    "feelsgood.wav",
};
#define MAX_FILES 31


// Audio Files used for Contact and Idle States
//
#ifdef TEST_CONNECTION_ENABLE
#define SONG_NAME_IDLE "disconnected.wav"
#define SONG_NAME_CONTACT "connected.wav"
#else
#define SONG_NAME_IDLE "eros_dormant1.wav"
#define SONG_NAME_CONTACT "eros_active1.wav"
#endif

// Audio Playa Date End

// ------ Audio SD Card Start
//
// Use these with the Teensy 3.5 & 3.6 & 4.1 SD card
#define SDCARD_CS_PIN    BUILTIN_SDCARD
#define SDCARD_MOSI_PIN  11  // not actually used
#define SDCARD_SCK_PIN   13  // not actually used


void playMusic (const char * song);
//
// ------ Audio SD Card End



// ------ Audio Contact Defines - Start
#define LED1_PIN 3
#define LED2_PIN 4
#define LED3_PIN 5


// 
// Frequencies to Transmit and listen for through hands (f_1 and f_2 are the tx frequencies)
const int f_1 = 20; 
const int f_2 = 20; 
const int f_3 = 20; 
const int f_4 = 20; 

float thresh = 0.01;      // This is the tone dection sensitivity.  Currently dset for maximum sensitivity.  Edit with caution and experimentation.
unsigned int contact = 0; //Current state of contacted.   Either 1 or 0

// GUItool: begin automatically generated code
//AudioSynthWaveformSine   sine2;          //xy=190.99998474121094,122.99998474121094
AudioInputI2S            audioIn;        //xy=192.99998474121094,369
AudioSynthWaveformSine   sine1;          //xy=207.99998474121094,60.99998474121094

/*
AudioAnalyzeToneDetect   right_f_4; //xy=466.20001220703125,575.2000122070312
AudioAnalyzeToneDetect   right_f_3;        //xy=467,540
AudioAnalyzeToneDetect   right_f_2;        //xy=471,502
AudioAnalyzeToneDetect   right_f_1;        //xy=472,464
AudioAnalyzeToneDetect   left_f_4;           //xy=474,384
AudioAnalyzeToneDetect   left_f_3;           //xy=475,348
AudioAnalyzeToneDetect   left_f_2;           //xy=477,313
*/
AudioAnalyzeToneDetect   right_f_1;        //xy=472,464
AudioAnalyzeToneDetect   left_f_1;           //xy=483,276
AudioOutputI2S           audioOut;       //xy=711,92.99998474121094
AudioMixer4              mixerRight;
AudioMixer4              mixerLeft;

AudioConnection          patchCordM1L(sine1, 0, mixerLeft, 0);
//AudioConnection          patchCordM1R(sine1, 0, mixerRight, 0);


//AudioConnection          patchCordM2L(sine2, 0, mixerLeft, 1);
//AudioConnection          patchCordM2R(sine2, 0, mixerRight, 1);

//
// Audio Player
AudioPlaySdWav           playSdWav1;
AudioConnection          patchCord11(playSdWav1, 0, mixerLeft, 2);
AudioConnection          patchCord12(playSdWav1, 1, mixerRight, 2);
// Audio Player
//

AudioConnection          patchCord2(audioIn, 0, left_f_1, 0);
AudioConnection          patchCord6(audioIn, 1, right_f_1, 0);
/*
AudioConnection          patchCord3(audioIn, 0, left_f_2, 0);
AudioConnection          patchCord4(audioIn, 0, left_f_3, 0);
AudioConnection          patchCord5(audioIn, 0, left_f_4, 0);
AudioConnection          patchCord6(audioIn, 1, right_f_1, 0);
AudioConnection          patchCord7(audioIn, 1, right_f_2, 0);
AudioConnection          patchCord8(audioIn, 1, right_f_3, 0);
AudioConnection          patchCord9(audioIn, 1, right_f_4, 0);
*/


AudioConnection          patchCordMOL(mixerLeft, 0, audioOut, 0);
AudioConnection          patchCordMOR(mixerRight, 0, audioOut, 1);

AudioControlSGTL5000     audioShield;    //xy=709,177.99998474121094

elapsedMillis since_main = 0;
uint16_t main_period_ms = 150; 
// ------ Audio Contact Defines - End
// GUItool: end automatically generated code


// ------
// ------
// Begin Ethernet Requirements
#include "defines.h" 

#include <SPI.h>
#include <SerialFlash.h>  
#include <SD.h> 
#include <QNEthernet.h>

// Create a UDP instance
EthernetUDP udp;
const unsigned int DNS_PORT = 53;


byte mac[] = {  0x92, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
#if !(USING_DHCP) 
// This is replaced with DHCP informatiom.   Use these as static definitions if standalone 
IPAddress NETWORK_IP      (192,168,1,48); //static IP
IPAddress NETWORK_MASK    (255,255,255,0);
IPAddress NETWORK_GATEWAY (192,168,1,20);
IPAddress NETWORK_DNS     (192,168,1,20);
IPAddress UDP_LOG_PC_IP   (192,168,1,50);
#endif

IPAddress server          (192,168,4,1); // Raspberry PI

// End  Ethernet Requirements
// ------
// Begin Ethernet Setup


#include <QNEthernet.h>
#include <string>
#include <cstring>


using namespace qindesign::network;

/*
stringToCharArray(String str):


Explanation and Important Considerations:
          It takes an Arduino String object as input.
          It allocates memory dynamically for a char array using new char[str.length() + 1]. The + 1 is crucial to accommodate the null terminator (\0) required by C-style strings.
          It copies the contents of the String object to the char array using str.toCharArray(charArray, str.length() + 1).
          It returns a char* pointer to the newly created array.
          It now handles empty strings by returning a nullptr.
          It also handles memory allocation failures by returning a nullptr.
          Memory Management:

          Crucially, you must delete[] charArray; when you're finished with the char array. Failure to do so will result in a memory leak.
          Set the pointer to nullptr after deleting the memory. This prevents dangling pointer issues.
          The example code demonstrates proper memory management.
          printf() Usage:

          The printf() function expects a char* (C-style string) as its %s argument.
          The stringToCharArray() function converts the Arduino String to the required format.
          Error Handling:

          The code now includes checks to handle cases where memory allocation fails.
          It also handles empty strings.
          Alternative (Using c_str()):

          For read-only use (where you don't need to modify the resulting char array), you can use the String.c_str() method. This returns a const char* that points to the internal buffer of the String object.
          Important: The c_str() method returns a pointer to internal String data, which may become invalid if the String object is modified or goes out of scope. Therefore, use it immediately or make a copy.
          Example:
          C++

          String myString = "Hello, world!";
          printf("String: %s\n", myString.c_str());
          Using c_str() is generally preferred when you don't need to modify the string, as it avoids dynamic memory allocation and deallocation.
          Which method to use:

          Use myString.c_str() when you only need to read the string's value and you are sure the string will remain in scope.
          Use stringToCharArray() when you need to modify the string or when you need a separate copy of the string that will persist beyond the scope of the original String object. Remember to free the memory.


*/

char* stringToCharArray(String str) {
  if (str.length() == 0) {
    return nullptr; // Return nullptr for empty strings
  }

  char* charArray = new char[str.length() + 1]; // Allocate memory for the char array
  if (charArray == nullptr) {
    return nullptr; // Handle memory allocation failure
  }

  str.toCharArray(charArray, str.length() + 1); // Copy the String to the char array
  return charArray;
}




//////////////////////////////

/*
  DNS Server declaration 
      CHANGED: Previously hard-coded as:
      IPAddress dnsServer(192, 168, 4, 1);
      Now declare without initialization.
      IPAddress dnsServer;   <-- DNS server will be obtained from DHCP

*/
IPAddress dnsServer;
// Buffer for DNS responses.
byte responseBuffer[512];

// Helper function: Build a DNS PTR query packet for a given reverse name.
int buildDnsPtrQuery(byte* buffer, int buflen, const String &reverseName) {
  uint16_t id = random(0, 65535);
  buffer[0] = (id >> 8) & 0xFF;
  buffer[1] = id & 0xFF;
  buffer[2] = 0x01; // Recursion desired
  buffer[3] = 0x00;
  buffer[4] = 0x00; buffer[5] = 0x01; // QDCOUNT = 1
  buffer[6] = buffer[7] = buffer[8] = buffer[9] = buffer[10] = buffer[11] = 0;
  int pos = 12;
  int start = 0;
  while (true) {
    int dotIndex = reverseName.indexOf('.', start);
    String label;
    if (dotIndex == -1) {
      label = reverseName.substring(start);
    } else {
      label = reverseName.substring(start, dotIndex);
    }
    int labelLen = label.length();
    buffer[pos++] = labelLen;
    for (int i = 0; i < labelLen; i++) {
      buffer[pos++] = label.charAt(i);
    }
    if (dotIndex == -1) break;
    start = dotIndex + 1;
  }
  buffer[pos++] = 0x00; // Terminate QNAME
  buffer[pos++] = 0x00; buffer[pos++] = 0x0c; // QTYPE: PTR
  buffer[pos++] = 0x00; buffer[pos++] = 0x01; // QCLASS: IN
  return pos;
}


String parsePtrResponse(byte* buffer, int buflen, int queryLength) {
  String result = "";
  int offset = queryLength + 12; // Skip header and query

  while (offset < buflen) {
    if ((buffer[offset] & 0xC0) == 0xC0) { // Check for pointer
      int pointerOffset = ((buffer[offset] & 0x3F) << 8) | buffer[offset + 1];
      offset += 2;
      int tempOffset = pointerOffset;
      while (tempOffset < buflen) {
        int length = buffer[tempOffset];
        if (length == 0) {
          break;
        }
        for (int i = 1; i <= length; i++) {
          result += (char)buffer[tempOffset + i];
        }
        tempOffset += length + 1;
        if (buffer[tempOffset] != 0) {
          result += ".";
        }
      }
      break; // PTR record found and parsed
    } else {
      int length = buffer[offset];
      if (length == 0) {
        break; // End of name
      }
      for (int i = 1; i <= length; i++) {
        result += (char)buffer[offset + i];
      }
      offset += length + 1;
      if (buffer[offset] != 0 && (buffer[offset] & 0xC0) != 0xC0 ) {
        result += ".";
      }
    }
  }

  return result;
}

// Example usage within an Arduino sketch:
/*
void setup() {
  Serial.begin(115200);
  Ethernet.begin(mac, ip); // Replace mac and ip with your values

  // ... (DNS query and response handling) ...

  // Example buffer (replace with your actual DNS response buffer)
  byte buffer[] = {
    0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x07, 0x69, 0x6E, 0x2D, 0x61, 0x64, 0x64, 0x72, 0x04, 0x61, 0x72, 0x70, 0x61, 0x00,
    0x00, 0x0C, 0x00, 0x01, 0xC0, 0x0C, 0x00, 0x0C, 0x00, 0x01, 0x00, 0x00, 0x0E, 0x10,
    0x00, 0x04, 0xC0, 0x10
  };

  int buflen = sizeof(buffer);
  int queryLength = 23; //Adjust to your query length.

  String ptrName = parsePtrResponse(buffer, buflen, queryLength);
  Serial.print("PTR Name: ");
  Serial.println(ptrName);
}

void loop() {
  // ...
}
*/

// Function to perform a reverse DNS lookup for a given IP address.
String reverseDnsLookup(IPAddress ip) {
  String reverseName = String(ip[3]) + "." + String(ip[2]) + "." +
                      String(ip[1]) + "." + String(ip[0]) + ".in-addr.arpa";
                      
  //Serial.print("Performing reverse lookup for: ");
  //Serial.println(reverseName);
  byte queryBuffer[512];
  int queryLength = buildDnsPtrQuery(queryBuffer, sizeof(queryBuffer), reverseName);
  

  dnsServer = Ethernet.dnsServerIP();

  //
  String dnsServerString = String(dnsServer[0]) + "." + String(dnsServer[1]) + "." +
                      String(dnsServer[2]) + "." + String(dnsServer[3]);

  //Serial.print("DNS Server:"); Serial.print(dnsServerString); Serial.printf(" Port:%d\n", DNS_PORT);
  // Use the DNS server obtained from DHCP.
  udp.beginPacket(dnsServer, DNS_PORT);
  udp.write(queryBuffer, queryLength);
  udp.endPacket();
  
  unsigned long startTime = millis();
  while (millis() - startTime < 2000) { // 2-second timeout
    int packetSize = udp.parsePacket();
    if (packetSize > 0) {
      int len = udp.read(responseBuffer, sizeof(responseBuffer));

      /*
      Serial.print("Received response of length: ");
      Serial.println(len);
      */
      String hostname = parsePtrResponse(responseBuffer, len, queryLength);
      /*
      Serial.printf ("\(");
      for ( int n = 0; n < len; ++n)
        Serial.printf ("%c", responseBuffer[n]);
      Serial.printf ("\n");
      Serial.printf ("HOSTNAME(%s)\n", hostname );
      */
      return hostname;
    }
  }
  return String("Timeout");
}

//////////////////////////////


 void initEthernet() 
 { 

  networkErrorRetry: // Entry point if we fail to initialize network

   bool networkError;
   
   networkError = false;

 #if USE_QN_ETHERNET 
   Serial.println(F("=========== USE_QN_ETHERNET ===========")); 
 // Alternate TCP/IP stacks will not be supported with my code
 #elif USE_NATIVE_ETHERNET 
  #error
   Serial.println(F("======== USE_NATIVE_ETHERNET ========")); 
 #elif USE_ETHERNET_GENERIC 
   #error
   Serial.println(F("======== USE_ETHERNET_GENERIC ========")); 
#else 
  #error
    Serial.println(F("========= NO NETWORK TYPE DEFINED ==========")); 
#endif 




 #if USING_DHCP 

   // Start the Ethernet connection, using DHCP 
   Serial.print("Initialize Ethernet using DHCP => "); 
   displayNetworkStatus( "DHCP Waiting...");

   Ethernet.begin(); 
   // give the Ethernet shield minimum 1 sec for DHCP and 2 secs for staticP to initialize: 
   // delay(1000);  XXX 3 
 #else 
   // Start the Ethernet connection, using static IP 
   Serial.print("Initialize Ethernet using STATIC IP => "); 
   displayNetworkStatus( "Static IP:" F(NETWORK_IP));
   Ethernet.begin(NETWORK_IP, NETWORK_MASK, NETWORK_GATEWAY, NETWORK_DNS);  
 #endif 
  
   if (!Ethernet.waitForLocalIP(5000)) 
   { 
     networkError = true;

     Serial.println("Failed to configure Ethernet"); 
     displayNetworkStatus( "** Network Failed **");
  
     if (!Ethernet.linkStatus()) 
     { 
       displayNetworkStatus( "CHECK ETHERNET CABLE" );
       Serial.println("Ethernet cable is not connected."); 
       delay(5000);
     } 
   } 
   else 
   { 
      networkError = false;

      //char text[128];
      //sprintf (text, "IP:%s", Ethernet.localIP() );
      //displayNetworkStatus ( Ethernet.localIP().printTo() );

      IPAddress ipAddress = Ethernet.localIP(); // Assuming Ethernet.localIP() returns an IP address

      // Convert IP address to char* (C-string)
      char ipString[128];  // Enough space for an IPv4 address in dot-decimal format

      sprintf(ipString, "IP:%d.%d.%d.%d", ipAddress[0], ipAddress[1], ipAddress[2], ipAddress[3]);

      displayNetworkStatus(ipString);

      Serial.print("IP Address = "); 
      Serial.println(Ethernet.localIP()); 

    } 
  
   // give the Ethernet shield minimum 1 sec for DHCP and 2 secs for staticP to initialize: 
   //delay(2000); 
  

  if (networkError == true)
    goto networkErrorRetry;

// DNS Port 
  // Start UDP on a specific local port (use any free port, here 12345)
  Serial.println(F("======== Begin UDP ============"));
  //delay (1000);
  udp.begin(12345);

  Serial.println(F("======== Reverse DNS Lookup ============"));


  String Hostname = reverseDnsLookup(Ethernet.localIP());

  //Serial.printf ("Hostname:",reverseDnsLookup(Ethernet.localIP()) );
  Serial.printf ("Hostname:");
  Serial.print (Hostname);

  //Serial.println( reverseDnsLookup(Ethernet.localIP()));

  char *hostname = stringToCharArray(Hostname);

  displayHostname ( hostname);
  delete[] hostname;

 } 

// End Ethernet Setup

// ------

#include <PubSubClient.h>

/*
   mqttSubCallback() - Receive MQTT Messages from MQTT Broker (Raspbery Pi)

*/
void mqttSubCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("\nmqttSubCallback() Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (unsigned int i=0;i<length;i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

// MQTTT 
EthernetClient ethClient;
PubSubClient client(ethClient);

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ArduinoClient")) {
      Serial.println("connected");
      // Once connected, publish an announcement...
      //client.publish("wled/dee","hello world");


      Serial.println("Sending ON");
      client.publish(
        "wled/all/api",
        "{\"on\": true, \"bri\": 255, \"seg\": [{\"col\": [255, 0, 0], \"fx\": 40}, {\"col\": [0, 255, 0], \"fx\": 80}, {\"col\": [0, 0, 255], \"fx\": 70}]}"
      );
        // ... and resubscribe
      client.subscribe("wled/all/api");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}


/*
  printState() - Print the contact state to the serial console
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void printState(unsigned int on) {
    static unsigned int init = 0;
    static unsigned int previous = 0;

    if ( init == 0 ) {
      previous = on;
    }

    if ( init == 1 ) {
      if ( previous == on ) {
        return;
      }
    }
    
    previous = on;

    if ( on == 1 )
      {
        Serial.print ("CONTACT\n");
      } else {
        Serial.print ("--OFF---\n");
      }

    

  //uncomment these lines to see how much CPU time
  //the tone detectors and audio library are using

      Serial.print("CPU=");
      Serial.print(AudioProcessorUsage());
      Serial.print("%, max=");
      Serial.print(AudioProcessorUsageMax());
      Serial.print("%   ");
      Serial.print("\n");

  init = 1;

}

/*
  publishState() - Publish via MQTT if we are on(Connected) or off
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void publishState(unsigned int on) {
    static unsigned int init = 0;
    static unsigned int previous = 0;
    bool publishStatus = false;

    if ( init == 0 ) {
      previous = on;
    }

    if ( init == 1 ) {
      if ( previous == on ) {
        return;
      }
    }
    
    if ( on == 1 )
      publishStatus = client.publish(
         "wled/all/api",
        "{\"on\": true, \
          \"bri\": 255, \
          \"seg\": \
        [{\"col\": [255, 255, 0],   \"fx\": 36},  \
         {\"col\": [0, 255, 255],   \"fx\": 36},   \
         {\"col\": [128, 128, 255], \"fx\": 36}]   \
         }" 
      );
    else
      publishStatus = client.publish(
          "wled/all/api",
         "{\"on\": true, \
          \"bri\": 255, \
          \"seg\":  \
        [{\"col\": [255, 0, 0], \"fx\": 42},    \
         {\"col\": [0, 255, 0], \"fx\": 42},    \
         {\"col\": [0, 0, 255], \"fx\": 42}]    \
         }" 

#if 0
        "wled/all/api",
        "{\"on\": false, \"bri\": 255, \"seg\": [{\"col\": [255, 0, 0], \"fx\": 0}, {\"col\": [0, 255, 0], \"fx\": 00}, {\"col\": [0, 0, 255], \"fx\": 00}]}"
#endif
      );

    if ( publishStatus == true )
    	previous = on;

    init = 1;
}

/* Play Audio Based On State */
void playState(unsigned int on)
{
    if ( on == 1 )
      playMusic (SONG_NAME_CONTACT, on);
    else
      playMusic (SONG_NAME_IDLE, on);
}



// Contact Sense Start
//
void audioSenseSetup() {
  // Audio connections require memory to work.  For more
  // detailed information, see the MemoryAndCpuUsage example
  // AudioMemory(12 + 8); // 12 for Sens, 8 for Wav Player

  // Enable the audio shield and set the output volume.
  audioShield.enable();
  audioShield.volume(0.75);

    // Configure the tone detectors with the frequency and number
  // of cycles to match.  These numbers were picked for match
  // times of approx 30 ms.  Longer times are more precise.
  
  const int sample_time_ms = main_period_ms/2;

  left_f_1.frequency(f_1,  sample_time_ms*f_1/1000);  //(1209, 36);
  /*
  left_f_2.frequency(f_2,  sample_time_ms*f_2/1000);
  left_f_3.frequency(f_3,  sample_time_ms*f_3/1000);
  left_f_4.frequency(f_4,  sample_time_ms*f_4/1000);
  */
  right_f_1.frequency(f_1, sample_time_ms*f_1/1000);  // assuming the calcs get optomized out
  /*
  right_f_2.frequency(f_2, sample_time_ms*f_2/1000);
  right_f_3.frequency(f_3, sample_time_ms*f_3/1000);
  right_f_4.frequency(f_4, sample_time_ms*f_4/1000);
*/
  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  pinMode(LED3_PIN, OUTPUT);

  // start the outputs
  AudioNoInterrupts();  // disable audio library momentarily
  sine1.frequency(f_1); // left
  sine1.amplitude(1.0);
  /*
  sine2.frequency(f_4); // right
  sine2.amplitude(1.0);
  */
  AudioInterrupts();    // enable, both tones will start together
}


/*
  audioSenseProcessSignal() - 
          - Read the audio line-in
          - perform a tone-detection
          - Report contact/no-contact to:
              - Music Player
              - MQTT
*/
void audioSenseProcessSignal() {
  float l1, r1;
  //uint8_t led1_val, led2_val;

  // read tone detectors
  l1 = left_f_1.read();
  r1 = right_f_1.read();

/*
  float l1, l2, l3, l4, r1, r2, r3, r4;
  // read all seven tone detectors
  l1 = left_f_1.read();
  r1 = right_f_1.read();
  l2 = left_f_2.read();
  l3 = left_f_3.read();
  l4 = left_f_4.read();
  r1 = right_f_1.read();
  r2 = right_f_2.read();
  r3 = right_f_3.read();
  r4 = right_f_4.read();
*/
#ifdef DEBUG_PRINT
  // print the raw data, for troubleshooting
  //Serial.print("tones: ");
  Serial.print(l1);
  Serial.print(", ");
  Serial.print(l2);
  Serial.print(", ");
  Serial.print(l3);
  Serial.print(", ");
  Serial.print(l4);
  Serial.print(",   ");
  Serial.print(r1);
  Serial.print(", ");
  Serial.print(r2);
  Serial.print(", ");
  Serial.print(r3);
  Serial.print(", ");
  Serial.print(r4);
  Serial.print("\n");
#endif

  if (
    l1 > thresh ||   r1 > thresh
  )
  /*
    l2 > thresh ||
    l3 > thresh ||
    r1 > thresh ||
    r2 > thresh ||
    l3 > thresh 
  ) 
  */
  {
      contact = 1;
  }
  else {
      contact = 0;
  }
 

  publishState(contact); // MQTT
  playState(contact);    // Audio Music Player
  printState(contact);  // Serial Console



 #if 0
  if (signal_num == 1) {
    led1_val = (r1 > thresh) ? 1 : 0;
  }
  
  if (signal_num == 2) {
    led2_val = (r2 > thresh) ? 1 : 0;
  }


  //analogWrite(LED1_PIN, (1-r1)*255); // write result to LED
  //analogWrite(LED2_PIN, (1-l4)*255); // write result to LED
  //analogWrite(LED3_PIN, (1-c3)*255); // write result to LED 

#endif
}

const float row_threshold = 0.2;
const float column_threshold = 0.2;

void audioSenseLoop() {

    sine1.amplitude(1.0);
    audioSenseProcessSignal();
}
// Contact Sense End
//


//
// Music Player Start

void audioMusicSetup() {
  //audioMemory(8); // NOTE:   This memory allocation should be combined with Audio Sense Setup
  //audioShield.enable();
  //audioShield.volume(0.5);

  //
  // Setup the SPI driver for MicroSd Card 
  // Our project uses the on board MicroSd, NOT the AudioShield's MicroSd slot
  //
  SPI.setMOSI(SDCARD_MOSI_PIN);
  SPI.setSCK(SDCARD_SCK_PIN);
  if (!(SD.begin(SDCARD_CS_PIN))) {
    while (1) {
      Serial.println("Unable to access the SD card");
      delay(500);
    }
  }
  // delay(1000); XXX 1
}

void playMusic (const char * song, unsigned int state) 
{
  static unsigned int init = 0;
  static unsigned int previous_state = 0;

  if ( init == 0 ) {
      previous_state = state;
  }

  if ((playSdWav1.isPlaying() ==true) && (previous_state == state))
  {
    return;
  }

  if ( previous_state != state ) {
    playSdWav1.stop();
  }

  previous_state = state;

  if (playSdWav1.play(song) == false) {
    Serial.println("Error playing ");
    Serial.println(song);
  }

  init = 1;
}
// Music Player End
//

void displayHostname ( char * hostname )
{
  display.setCursor(0,20);  
  display.print("name:");
  display.print(hostname);
  display.display();
}

/*
 * displayActivityStatus() - display a wandering eye and show any acitivy
 */
void displayActivityStatus(  )
{
  long unsigned mod;

  #define ACTIVITY_BAR_FRACTIONS 32

  static unsigned int init = 0;

  unsigned long int mills;
  static unsigned long time;
  static unsigned long deltaTime = 0;
  static bool direction = true;

  unsigned int Xposition;
  static unsigned int Xposition_last = 0;



  if ( init == 0 ) {
    time = millis();
    init = 1;
  }

  
  // Handle wrap-around
  mills = millis();
  if ( time > mills )
    time = mills;

  deltaTime = (mills - time) % 1000;

  mod = deltaTime % (1000 / ACTIVITY_BAR_FRACTIONS);
  if ( mod != 0 )     
    return;

  unsigned int x_unscaled;
  unsigned int x_scaled;

  x_unscaled = deltaTime / ACTIVITY_BAR_FRACTIONS; // - 1;
  x_scaled   = x_unscaled * 128 / ACTIVITY_BAR_FRACTIONS ; 

  if ( direction ) {
    Xposition = x_scaled; 
  } 
  else {
    Xposition = 124 - x_scaled;
 }


#ifdef ACTIVITY_DEBUG_ENABLE
  printf ("Direction:%s time:%u delta_t:%u x_unscaled:%u Xpos:%u\n", direction ? "F" : "B", time, deltaTime, x_unscaled,Xposition);
#endif
  /* 
    Clear the activity line 
  */
  display.setTextColor(SSD1306_WHITE);

  display.fillRect(Xposition_last, 30, 10, 10, SSD1306_BLACK);  // Erase text area


  /*
    Draw a small box on the line position it based on the fraction of a second
  */

  display.fillRect(Xposition, 30, 10, 10, SSD1306_WHITE);  // Erase text area
  display.display();


  /* Flip the direction */
  if ( x_unscaled == (ACTIVITY_BAR_FRACTIONS - 1))  {
    direction = direction ? false : true;
  }

  Xposition_last = Xposition;

}


void displayNetworkStatus( const char string[] )
{
  //display.setTextSize(2);             // Draw 2X-scale text
  display.setTextColor(SSD1306_WHITE);
  //display.print(F("IP:")); 
  display.setCursor(0,10);
  display.fillRect(0, 10, 128, 20, SSD1306_BLACK);  // Erase text area
  //display.printf (".....................");
  display.display();
  display.setCursor(0,10); 
  display.print(string);
  
  //isplay.print(Ethernet.localIP());
  display.display();
}

void displaySplashScreen(void) {
  display.clearDisplay();

  display.setTextSize(1);             // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setCursor(0,0);             // Start at top-left corner
  display.println(F("    1st CONTACT!"));
  display.println(F(""));
  display.println(F(""));

  display.setCursor(0,10); 
  //display.setTextSize(2);             // Draw 2X-scale text
  display.setTextColor(SSD1306_WHITE);
  display.print(F("IP:")); 
  display.print(Ethernet.localIP());

  display.setTextSize(1);             // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setCursor(0,55); 

  display.println(F(__DATE__ "  " __TIME__));
 

  display.display();
  //delay(2000); XXX
}

void displaySetup()
{
  Wire2.begin();

   // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    //for(;;); // Don't proceed, loop forever
  }

  // Show initial display buffer contents on the screen --
  // the library initializes this with an Adafruit splash screen.
  //display.display();
  //delay(2000); // Pause for 2 seconds

  // Clear the buffer
  display.clearDisplay();

  // Draw a single pixel in white
  display.drawPixel(10, 10, SSD1306_WHITE);

  // Show the display buffer on the screen. You MUST call display() after
  // drawing commands to make them visible on screen!
  display.display();
  delay(750);

  displaySplashScreen();

  // display.display() is NOT necessary after every single drawing command,
  // unless that's what you want...rather, you can batch up a bunch of
  // drawing operations and then update the screen all at once by calling
  // display.display(). These examples demonstrate both approaches...
}

void setup()
{
  
  displaySetup();

  Serial.printf("_______FIRST CONTACT_______ ");
  Serial.printf("%s %sd \n", __DATE__, __TIME__);

  

  Serial.printf("_______Init Ethernet_______\n");
  // TCP/IP Setup
  initEthernet();

  // MQTT Setup
  Serial.printf("_______Init MQTT Publisher_______\n");
  client.setServer(server, 1883);
  client.setCallback(mqttSubCallback);

  // Allow the hardware to sort itself out
  // delay(1500); XXX

  Serial.printf("_______Audio Memory Init________\n");
  AudioMemory(22); // NOTE this number is simply a guess.   Working: 12 for Sens, 8 for Wav Player + margin

  Serial.printf("_______Audio Sense Init________\n");
  audioSenseSetup(); 

  Serial.printf("_______Audio Music Init________\n");
  audioMusicSetup();
}

void loop()
{
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  audioSenseLoop();

  displayActivityStatus();
}
