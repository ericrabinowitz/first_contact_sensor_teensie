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
        - These need to be installed via library manager.
          Using library Adafruit GFX Library at version 1.12.0 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_GFX_Library
          Using library Adafruit BusIO at version 1.17.0 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_BusIO
          Using library Adafruit SSD1306 at version 2.5.13 in folder: /Users/eric/work/FirstContact/libraries/Adafruit_SSD1306
          Using library QNEthernet at version 0.31.0 in folder: /Users/eric/work/FirstContact/libraries/QNEthernet
          Using library PubSubClient at version 2.8 in folder: /Users/eric/work/FirstContact/libraries/PubSubClient
        - These should already be installed alongsuide teensyduino. Do not install these libraries.
          Using library SPI at version 1.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SPI 
          Using library Wire at version 1.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/Wire 
          Using library Audio at version 1.3 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/Audio 
          Using library SD at version 2.0.0 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SD 
          Using library SdFat at version 2.1.2 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SdFat 
          Using library SerialFlash at version 0.5 in folder: /Users/eric/Library/Arduino15/packages/teensy/hardware/avr/1.59.0/libraries/SerialFlash 





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
    "Missing Link Electra dormant with background.wav",
    "Missing Link Eros dormant.wav",
};
#define MAX_FILES 31


// Audio Files used for Contact and Idle States
//
#ifdef TEST_CONNECTION_ENABLE
#define SONG_NAME_IDLE "disconnected.wav"
// #define SONG_NAME_CONTACT "connected.wav" - removing this as we'll use an array instead
#else
#define SONG_NAME_IDLE "Missing Link Electra dormant with background.wav"
// #define SONG_NAME_CONTACT "eros_active1.wav" - removing this as we'll use an array instead
#endif

// Contact songs array.
const char* contactSongs[] = {
  "Missing Link unSCruz active 1 Remi Wolf Polo Pan Hello.wav",
  "Missing Link unSCruz active 2 MarchForth Gospel A.wav",
  "Missing Link unSCruz active 3 Saint Motel My Type A.wav",
  "Missing Link unSCruz active 4 Seth Lakeman Lady of the Sea 2.wav",
  "Missing Link unSCruz active 5 Jacques Greene Another Girl.wav",
  "Missing Link unSCruz active 6 Chrome Sparks Goddess.wav",
  "Missing Link unSCruz active 7 Jet Are You Gonna Be.wav",
  "Missing Link unSCruz active 8 M83 Midnight City Prydz.wav",
  "Missing Link unSCruz active 9 Flume The Difference.wav",
  "Missing Link unSCruz active 10 Doldinger Bastian.wav",
  "Missing Link unSCruz active 11 Yung Bae Straight Up.wav",
};
#define NUM_CONTACT_SONGS (sizeof(contactSongs) / sizeof(contactSongs[0]))

// Current song index
unsigned int currentSongIndex = 0;


// Audio Playa Date End

// ------ Audio SD Card Start
//
// Use these with the Teensy 3.5 & 3.6 & 4.1 SD card
#define SDCARD_CS_PIN    BUILTIN_SDCARD
#define SDCARD_MOSI_PIN  11  // not actually used
#define SDCARD_SCK_PIN   13  // not actually used

// Music player states
typedef enum {
  MUSIC_STATE_NOT_STARTED,    // No music has started yet.
  MUSIC_STATE_PLAYING,        // Music is playing at normal volume.
  MUSIC_STATE_PAUSED,         // Music is playing but at lower volume.
  MUSIC_STATE_PAUSE_TIMEOUT,  // Music was paused but timeout occurred.
  MUSIC_STATE_PAUSE_FINISHED, // Music was paused and finished.
  MUSIC_STATE_FINISHED        // A song has finished playing.
} MusicState;

void playMusic (unsigned int state);
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
//bool isLinked = false;      // Current state of contact. Either true or false
static unsigned long int contactCount = 0; // Cumulative count of contacts

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

char * hostname = 0; // This will be filled in by Reverse DNS

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

  if (networkError == true)
    goto networkErrorRetry;

// DNS Port 
  // Start UDP on a specific local port (use any free port, here 12345)
  Serial.println(F("======== Begin UDP ============"));

  udp.begin(12345);

  Serial.println(F("======== Reverse DNS Lookup ============"));

  

  String Hostname = reverseDnsLookup(Ethernet.localIP());

  Serial.printf ("Hostname:");
  Serial.print (Hostname);

  //Serial.println( reverseDnsLookup(Ethernet.localIP()));

  hostname = stringToCharArray(Hostname);

  displayHostname ( hostname);

  /* The data was allocated, but we will not delete it since we may need to print again */
  /* Remove this commment to delete the allocated string *
  delete[] hostname;
  */

 } 
// End Ethernet Setup

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

void displayTimeCount() {
  static bool isInitialized = false;

  #define STRING_BUFFER_LEN 128
  char str[STRING_BUFFER_LEN];


  long unsigned int startTimeMills = 0;
  long unsigned int secondsLapse = 0;
  long unsigned int mills = 0;
  long unsigned int millsLapse = 0;

  unsigned int count;

  // Initialize buffer;

  for ( count = 0; count< STRING_BUFFER_LEN; ++count)
    str[count] = 0;

  if ( !isInitialized ) {
      startTimeMills = millis();
      isInitialized = true;
      return;
  }

  mills = millis();

  millsLapse =  mills - startTimeMills;

  // Only update every 1/4 second
  if ( millsLapse % 100 )
    return;
  

  secondsLapse = millsLapse / 1000;

  //display.clearDisplay();
  display.fillRect(0, 54, 128, 10, SSD1306_BLACK); 
  //display.display();

  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setTextSize(1); 
  display.setCursor(0,55);
  sprintf (str, "%07u    %02u:%02u:%02u", contactCount, \
        secondsLapse / 3600,
       (secondsLapse % 3600) / 60,
       (secondsLapse % 3600) % 60);

  display.printf (str);

  display.display();
}


/*
  displayState() - Print the contact state to OLED display
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void displayState(bool isInitialized, bool wasLinked, bool isLinked) {
  char str[128];

  if (isInitialized && wasLinked == isLinked) {
    return;
  }

  if (!isInitialized || isLinked) {
    ++contactCount;

    // Clear the buffer
    //display.clearDisplay();
    display.fillRect(0, 30, 128, 10, SSD1306_BLACK);  
    display.setTextSize(3);             // Normal 1:1 pixel scale
    display.setTextColor(SSD1306_WHITE);        // Draw white text
    display.setCursor(0,30);            

    sprintf (str, "%07u", contactCount);
    display.printf (str);
    display.display();
  } else {
    //display.clearDisplay();
    display.fillRect(0, 30, 128, 25, SSD1306_BLACK);
    display.display();
  }
}

/*
  printState() - Print the contact state to the serial console
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void printState(bool isInitialized, bool wasLinked, bool isLinked) {
  if (isInitialized && wasLinked == isLinked) {
    return;
  }

  if (isLinked) {
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
}

/*
  publishState() - Publish via MQTT if we are on(Connected) or off
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void publishState(bool isInitialized, bool wasLinked, bool isLinked) {
  static bool publishSucceeded = false;

  if (publishSucceeded && isInitialized && wasLinked == isLinked) {
    // No change in state to report.
    return;
  }
  
  if (isLinked)
    publishSucceeded = client.publish(
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
    publishSucceeded = client.publish(
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
}

// Audio

// Whether audio is 'paused' i.e. low volume.
bool isPaused = false;

// Volume
#define PLAYING_AUDIO_VOLUME 0.75
#define PAUSED_AUDIO_VOLUME 0.4

// Define pause timeout duration in milliseconds
#define PAUSE_TIMEOUT_MS 2000 // 2 seconds pause timeout

// Variable to track when pausing started
unsigned long pauseStartTime = 0;

// Helper function to determine the current state of music playback
MusicState getMusicState(unsigned int init) {
  if (init == 0) {
    return MUSIC_STATE_NOT_STARTED;
  }
  if (isPaused) {
    // Check if pause has timed out
    if (millis() - pauseStartTime > PAUSE_TIMEOUT_MS) {
      Serial.println("Music paused timeout.");
      return MUSIC_STATE_PAUSE_TIMEOUT;
    } else if (!playSdWav1.isPlaying()) {
      // If music is paused but not playing it ended while paused.
      // Treat it as timed out.
      Serial.println("Music ended while paused.");
      return MUSIC_STATE_PAUSE_FINISHED;
    }
    return MUSIC_STATE_PAUSED;
  }

  if (!playSdWav1.isPlaying()) {
    return MUSIC_STATE_FINISHED;
  }
  
  return MUSIC_STATE_PLAYING;
}



// Contact Sense Start
//
void audioSenseSetup() {
  // Audio connections require memory to work.  For more
  // detailed information, see the MemoryAndCpuUsage example
  // AudioMemory(12 + 8); // 12 for Sens, 8 for Wav Player

  // Enable the audio shield and set the output volume.
  audioShield.enable();
  audioShield.volume(PLAYING_AUDIO_VOLUME);

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

void debugPrintAudioSense(float l1, float r1) {
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
    }


/*
  audioSenseProcessSignal() - 
          - Read the audio line-in
          - perform a tone-detection
          - Report contact/no-contact to:
              - Music Player
              - MQTT
*/
bool audioSenseProcessSignal() {
  float l1, r1;

  // read tone detectors
  l1 = left_f_1.read();
  r1 = right_f_1.read();
  debugPrintAudioSense(l1, r1);

  static unsigned long lastTransitionTime = millis();
  static bool isInitialized = false;
  static bool wasLinked = false;

  bool isLinked = (l1 > thresh || r1 > thresh);

  if (!isInitialized) {
    wasLinked = isLinked;
  }

  // If state has changed, measure and print transition duration.
  if (!isInitialized | isLinked != wasLinked) {
      unsigned long now = millis();
      unsigned long delta = now - lastTransitionTime;
      Serial.print("Transition from ");
      if (isInitialized) {
        Serial.print(wasLinked ? "linked" : "unlinked");
      } else {
        Serial.print("uninitialized");
      }
      Serial.print(" to ");
      Serial.print(isLinked ? "linked" : "unlinked");
      Serial.print(" after ");
      Serial.print(delta);
      Serial.println("ms.");
      lastTransitionTime = now;
  }

  publishState(isInitialized, wasLinked, isLinked); // MQTT
  playMusic(isInitialized, wasLinked, isLinked);    // Audio Music Player
  printState(isInitialized, wasLinked, isLinked);   // Serial Console
  displayState(isInitialized, wasLinked, isLinked); // OLED Display

  // Update initialized, linked state.
  isInitialized = true;
  wasLinked = isLinked;
  return isLinked;
}

const float row_threshold = 0.2;
const float column_threshold = 0.2;

bool audioSenseLoop() {

    sine1.amplitude(1.0);
    return audioSenseProcessSignal();
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

void pauseMusic ( )
{
  if (!isPaused && playSdWav1.isPlaying()) {
    // Set volume to zero (mute) but keep playing
    audioShield.volume(PAUSED_AUDIO_VOLUME);

    isPaused = true;
    pauseStartTime = millis(); // Record when pausing started
    Serial.println("Music paused (volume minimized)");
  }
}

void resumeMusic() {
  if (isPaused && playSdWav1.isPlaying()) {
    // Restore volume
    audioShield.volume(PLAYING_AUDIO_VOLUME);

    isPaused = false;
    Serial.println("Music resumed (volume restored)");
  } else {
    Serial.println("Music is not paused or not playing");
  }
}

void stopMusic() {
  if (playSdWav1.isPlaying()) {
    playSdWav1.stop();
  }
}

void advanceToNextSong() {
  // Advance to next song
  currentSongIndex = (currentSongIndex + 1) % NUM_CONTACT_SONGS;
  Serial.print("Next song will be: ");
  Serial.println(contactSongs[currentSongIndex]);
}

// Helper function to get the current song to play.
const char* getCurrentSong(bool isLinked) {
  if (isLinked) {
    return contactSongs[currentSongIndex];
  } else {
    return SONG_NAME_IDLE;
  }
}

/* Play Audio Based On State */
void playMusic(bool isInitialized, bool wasLinked, bool isLinked) {
  MusicState musicState = getMusicState(isInitialized);

  // State transition: Connected -> Disconnected.
  if (wasLinked && !isLinked) {
    Serial.println("Transition: Connected -> Disconnected");
    pauseMusic();
  }

  // State transition: Disconnected -> Connected.
  else if (!wasLinked && isLinked) {
    Serial.println("Transition: Disconnected -> Connected");

    if (musicState == MUSIC_STATE_PAUSED) {
      // If we were paused (previous disconnect), resume playback
      Serial.println("Resuming paused music");
      resumeMusic();
    } else if (musicState == MUSIC_STATE_PLAYING) {
      // If we weren't paused, stop any currently playing song.
      // This is expected to be the idle song.
      Serial.println("Stopping current song to play contact song");
      stopMusic();
    }
  }
  
  // Handle pause timeout and finished states.
  switch (musicState) {
    case MUSIC_STATE_PAUSE_TIMEOUT:
    case MUSIC_STATE_PAUSE_FINISHED:
      Serial.println("Pause timed out. Stopping song to switch to dormant.");
      stopMusic();
      advanceToNextSong();
      
      // Reset isPaused since we're stopping the song
      isPaused = false;
      // Also reset the volume to the default
      audioShield.volume(PLAYING_AUDIO_VOLUME);
      break;
    case MUSIC_STATE_FINISHED:
      if (isLinked) {
        Serial.println("Song finished. Advancing to next song.");
        advanceToNextSong();
      } else {
        Serial.println("Idle song finished. Looping.");
      }
      break;
    default:
      // No action needed for other states
      break;
  }

  // Nothing is playing - figure out what to play next
  if (!playSdWav1.isPlaying()) {
    // Start the appropriate song.
    Serial.print("Starting song: ");
    const char* songToPlay = getCurrentSong(isLinked);
    Serial.println(songToPlay);

    if (!playSdWav1.play(songToPlay)) {
      Serial.print("Error playing: ");
      Serial.println(songToPlay);
    }
  }
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
void displayActivityStatus(bool isLinked)
{
  long unsigned mod;

  #define ACTIVITY_BAR_FRACTIONS 32

  static bool isInitialized = false;

  unsigned long int mills;
  static unsigned long time;
  static unsigned long deltaTime = 0;
  static bool direction = true;

  unsigned int Xposition;
  static unsigned int Xposition_last = 0;

  // Only display during idle time
  if ( isLinked ) {
    isInitialized = false;
    return;
  }

  if ( !isInitialized ) {
    time = millis();
  }

  mills = millis();

  // Handle wrap-around
  if ( time > mills )
    time = mills;

  deltaTime = (mills - time) % 1000;

  mod = deltaTime % (1000 / ACTIVITY_BAR_FRACTIONS);
  if ( mod != 0 )     
    return;

  unsigned int x_unscaled;
  unsigned int x_scaled;

  x_unscaled = deltaTime / ACTIVITY_BAR_FRACTIONS; 
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
    Clear the  previous activity block 
  */
  display.setTextColor(SSD1306_WHITE);

  display.fillRect(Xposition_last, 30, 10, 10, SSD1306_BLACK);  

  /*
    Draw a small box on the line position it based on the fraction of a second
  */

  display.fillRect(Xposition, 30, 10, 10, SSD1306_WHITE);  // New Block
  display.display();


  /* Flip the direction */
  if ( x_unscaled == (ACTIVITY_BAR_FRACTIONS - 1))  {
    direction = direction ? false : true;
  }

  Xposition_last = Xposition;

#if 0
  {
    display.setTextSize(1);             // Normal 1:1 pixel scale
    display.setCursor(0,55); 
    display.println(F(__DATE__ "  " __TIME__));
  }
#endif
}


void displayNetworkStatus( const char string[] )
{
  
  display.setTextColor(SSD1306_WHITE);
  display.fillRect(0, 10, 128, 20, SSD1306_BLACK);  // Erase text area

  display.setCursor(0,10); 
  display.print(string);
  
  display.display();
}

void displaySplashScreen(void) {
  display.clearDisplay();

  display.setTextSize(1);             // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE);        // Draw white text
  display.setCursor(0,0);             // Start at top-left corner
  display.println(F("    1st CONTACT!!"));
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
  //display.drawPixel(10, 10, SSD1306_WHITE);

  // Show the display buffer on the screen. You MUST call display() after
  // drawing commands to make them visible on screen!
  display.display();
  //delay(750);

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

  bool isLinked = audioSenseLoop();

  // During Idle Time, animate something to show we are alive
  displayActivityStatus(isLinked);

  displayTimeCount();
}
