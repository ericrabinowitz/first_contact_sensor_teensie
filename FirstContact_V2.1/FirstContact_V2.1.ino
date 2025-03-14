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
  FTP is available for file transfer to the MicroSD card, but we aren't using using it.

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
          QNEthernet v0.30.1
          PubSubClient MQTT 3.1.1  v2.8
          FTP_Server_teensy41. v1.2.0
          ArduinoMqttClient by Arduino. v0.1.8
          AdaFruit GFX Library v1.11.11
          AdaFruit BusIO v1.17.0
          AdaFruit SSD1306 v2.5.13
          LightMDNS v1.0.5

Consider Removing:
          Ethernet_Generic by Various.  v2.8.1
          PPOSClient v1.0
          TeensyView by SparkFun. v1.1.0


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
// On an arduino UNO:       A4(SDA), A5(SCL)
// On an arduino MEGA 2560: 20(SDA), 21(SCL)
// On an arduino LEONARDO:   2(SDA),  3(SCL), ...
#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
//#define SCREEN_ADDRESS 0x3D ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32
#define SCREEN_ADDRESS 0xBC
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
// Use these for the SD+Wiz820 or other adaptors
//#define SDCARD_CS_PIN    4
//#define SDCARD_MOSI_PIN  11
//#define SDCARD_SCK_PIN   13
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

float thresh = 0.01;
unsigned int contact = 0;

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
uint16_t main_period_ms = 100; 
// ------ Audio Contact Defines - End
// GUItool: end automatically generated code


// ------
// ------
// Begin Ethernet Requirements
#include "defines.h" 

#include <SPI.h>
#include <SerialFlash.h>  
#include <SD.h> 
#include <SPI.h> 
#include <QNEthernet.h>

#define PASV_RESPONSE_STYLE_NEW       true 
#define FTP_FILESYST                  FTP_SDFAT2 

// Default 2048 
#define FTP_BUF_SIZE                  8192 

#define FTP_USER_NAME_LEN             64        // Max permissible and default are 64 
#define FTP_USER_PWD_LEN             128        // Max permissible and default are 128 

byte mac[] = {  0x92, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
#if 0 // This is replaced with DHCP informatiom.   Use these as static definitions if standalone 
IPAddress NETWORK_IP      (192,168,1,48); //static IP
IPAddress NETWORK_MASK    (255,255,255,0);
IPAddress NETWORK_GATEWAY (192,168,1,20);
IPAddress NETWORK_DNS     (192,168,1,20);
IPAddress UDP_LOG_PC_IP   (192,168,1,50);
#endif
IPAddress server          (192,168,4,1);

// End  Ethernet Requirements
// ------
// Begin Ethernet Setup
 #define FTP_ACCOUNT       "teensy4x" 
 #define FTP_PASSWORD      "ftp_test" 


#include <QNEthernet.h>
#include <string>
#include <cstring>

using namespace qindesign::network;


 void initEthernet() 
 { 

  networkErrorRetry: // Entry point if we fail to initialize network

   bool networkError;
   
   networkError = false;

 #if USE_QN_ETHERNET 
   Serial.println(F("=========== USE_QN_ETHERNET ===========")); 
 #elif USE_NATIVE_ETHERNET 
   Serial.println(F("======== USE_NATIVE_ETHERNET ========")); 
 #elif USE_ETHERNET_GENERIC 
   Serial.println(F("======== USE_ETHERNET_GENERIC ========")); 
 #else 
   Serial.println(F("=======================================")); 
 #endif 
  
 #if USE_NATIVE_ETHERNET 
  
   // start the ethernet connection and the server: 
   // Use DHCP dynamic IP and random mac 
   uint16_t index = millis() % NUMBER_OF_MAC; 
   // Use Static IP 
   //Ethernet.begin(mac[index], ip); 
   Ethernet.begin(mac[index]); 
  
   Serial.print(F("Using mac index = ")); 
   Serial.println(index); 
  
   Serial.print(F("Connected! IP address: ")); 
   Serial.println(Ethernet.localIP()); 
  
 #elif USE_QN_ETHERNET 


//  display.print(Ethernet.localIP());

 #if USING_DHCP 

   // Start the Ethernet connection, using DHCP 
   Serial.print("Initialize Ethernet using DHCP => "); 
   displayNetworkStatus( "DHCP Waiting...");

   Ethernet.begin(); 
   // give the Ethernet shield minimum 1 sec for DHCP and 2 secs for staticP to initialize: 
   delay(1000); 
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

    // Convert to DNS name
      Ethernet.hostByName(host, ip)
    
    // Use the DNS name
    Serial.println(dnsName.c_str());


    } 
  
   // give the Ethernet shield minimum 1 sec for DHCP and 2 secs for staticP to initialize: 
   //delay(2000); 
  
 #else 
  
   FTP_LOGWARN(F("Default SPI pinout:")); 
   FTP_LOGWARN1(F("MOSI:"), MOSI); 
   FTP_LOGWARN1(F("MISO:"), MISO); 
   FTP_LOGWARN1(F("SCK:"),  SCK); 
   FTP_LOGWARN1(F("SS:"),   SS); 
   FTP_LOGWARN(F("=========================")); 
    
   // unknown board, do nothing, use default SS = 10 
   #ifndef USE_THIS_SS_PIN 
     #define USE_THIS_SS_PIN   10    // For other boards 
   #endif 
  
   #if defined(BOARD_NAME) 
     FTP_LOGWARN3(F("Board :"), BOARD_NAME, F(", setCsPin:"), USE_THIS_SS_PIN); 
   #else 
     FTP_LOGWARN1(F("Unknown board setCsPin:"), USE_THIS_SS_PIN); 
   #endif 
  
   // For other boards, to change if necessary  
   Ethernet.init (USE_THIS_SS_PIN); 
  
   // start the ethernet connection and the server: 
   // Use DHCP dynamic IP and random mac 
   uint16_t index = millis() % NUMBER_OF_MAC; 
   // Use Static IP 
   //Ethernet.begin(mac[index], ip); 
   Ethernet.begin(mac[index]); 
   Ethernet.macAddress(mac);
   Serial.print("IP Address = "); 
   Serial.println(Ethernet.localIP()); 
    
 #endif 


  if (networkError == true)
    goto networkErrorRetry;
 } 

// End Ethernet Setup




// ------
#include <SPI.h>
#include <PubSubClient.h>




/*
   mqttSubCallback() - Receive MQTT Messages from MQTT Broker (Raspbery Pi)

*/
void mqttSubCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (unsigned int i=0;i<length;i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

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
      //client.subscribe("wled/command");
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
      client.publish(
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
      client.publish(
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
  audioShield.volume(0.4);

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
  delay(1000);
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
  delay(2000);
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

  // TCP/IP Setup
  initEthernet();

  // MQTT Setup
  client.setServer(server, 1883);
  client.setCallback(mqttSubCallback);

  // Allow the hardware to sort itself out
  delay(1500);

  AudioMemory(22); // NOTE this number is simply a guess.   Working: 12 for Sens, 8 for Wav Player + margin
  audioSenseSetup(); 
  audioMusicSetup();
}

void loop()
{
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  audioSenseLoop();
}