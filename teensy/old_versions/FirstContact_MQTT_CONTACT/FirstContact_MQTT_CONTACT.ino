/*
DHCP, MQTT, Contact Sense
 
*/
// ------ Audio Includes - Start
#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>
// ------ Audio Includes - End

// ------ Audio Defines - Start
#define LED1_PIN 3
#define LED2_PIN 4
#define LED3_PIN 5

const int f_1 = 1047; // c6  1046.5
const int f_2 = 1109; // c6# 1108.7
const int f_3 = 1175; // d6  1174.7
const int f_4 = 1245; // d6# 1244.5

float thresh = 0.01;
unsigned int contact = 0;

// GUItool: begin automatically generated code
AudioSynthWaveformSine   sine2;          //xy=190.99998474121094,122.99998474121094
AudioInputI2S            audioIn;        //xy=192.99998474121094,369
AudioSynthWaveformSine   sine1;          //xy=207.99998474121094,60.99998474121094
AudioAnalyzeToneDetect   right_f_4; //xy=466.20001220703125,575.2000122070312
AudioAnalyzeToneDetect   right_f_3;        //xy=467,540
AudioAnalyzeToneDetect   right_f_2;        //xy=471,502
AudioAnalyzeToneDetect   right_f_1;        //xy=472,464
AudioAnalyzeToneDetect   left_f_4;           //xy=474,384
AudioAnalyzeToneDetect   left_f_3;           //xy=475,348
AudioAnalyzeToneDetect   left_f_2;           //xy=477,313
AudioAnalyzeToneDetect   left_f_1;           //xy=483,276
AudioOutputI2S           audioOut;       //xy=711,92.99998474121094
AudioConnection          patchCord1(sine2, 0, audioOut, 1);
AudioConnection          patchCord2(audioIn, 0, left_f_1, 0);
AudioConnection          patchCord3(audioIn, 0, left_f_2, 0);
AudioConnection          patchCord4(audioIn, 0, left_f_3, 0);
AudioConnection          patchCord5(audioIn, 0, left_f_4, 0);
AudioConnection          patchCord6(audioIn, 1, right_f_1, 0);
AudioConnection          patchCord7(audioIn, 1, right_f_2, 0);
AudioConnection          patchCord8(audioIn, 1, right_f_3, 0);
AudioConnection          patchCord9(audioIn, 1, right_f_4, 0);
AudioConnection          patchCord10(sine1, 0, audioOut, 0);
AudioControlSGTL5000     audioShield;    //xy=709,177.99998474121094
// GUItool: end automatically generated code
elapsedMillis since_main = 0;
uint16_t main_period_ms = 60; 
// ------ Audio Defines - End


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
#if 0
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
  
 void initEthernet() 
 { 
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



 #if USING_DHCP 

   // Start the Ethernet connection, using DHCP 
   Serial.print("Initialize Ethernet using DHCP => "); 
   Ethernet.begin(); 
   // give the Ethernet shield minimum 1 sec for DHCP and 2 secs for staticP to initialize: 
   delay(1000); 
 #else 
   // Start the Ethernet connection, using static IP 
   Serial.print("Initialize Ethernet using STATIC IP => "); 
   Ethernet.begin(NETWORK_IP, NETWORK_MASK, NETWORK_GATEWAY, NETWORK_DNS);  
 #endif 
  
   if (!Ethernet.waitForLocalIP(5000)) 
   { 
     Serial.println("Failed to configure Ethernet"); 
  
     if (!Ethernet.linkStatus()) 
     { 
       Serial.println("Ethernet cable is not connected."); 
     } 
  
     // Stay here forever 
     while (true) 
     { 
       delay(1); 
     } 
   } 
   else 
   { 
     Serial.print("IP Address = "); 
     Serial.println(Ethernet.localIP()); 
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
 } 

// End Ethernet Setup




// ------
#include <SPI.h>
#include <PubSubClient.h>

// Update these with values suitable for your network.
void callback(char* topic, byte* payload, unsigned int length) {
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

void publishOn(unsigned int on) {
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
        "{\"on\": true, \"bri\": 255, \"seg\": [{\"col\": [255, 0, 0], \"fx\": 40}, {\"col\": [0, 255, 0], \"fx\": 80}, {\"col\": [0, 0, 255], \"fx\": 70}]}"
      );
    else
      client.publish(
        "wled/all/api",
        "{\"on\": false, \"bri\": 255, \"seg\": [{\"col\": [255, 0, 0], \"fx\": 40}, {\"col\": [0, 255, 0], \"fx\": 80}, {\"col\": [0, 0, 255], \"fx\": 70}]}"
      );

    init = 1;
}

void audioSetup() {
  // Audio connections require memory to work.  For more
  // detailed information, see the MemoryAndCpuUsage example
  AudioMemory(12);

  // Enable the audio shield and set the output volume.
  audioShield.enable();
  audioShield.volume(0.5);

    // Configure the tone detectors with the frequency and number
  // of cycles to match.  These numbers were picked for match
  // times of approx 30 ms.  Longer times are more precise.
  
  const int sample_time_ms = main_period_ms/2;

  left_f_1.frequency(f_1,  sample_time_ms*f_1/1000);  //(1209, 36);
  left_f_2.frequency(f_2,  sample_time_ms*f_2/1000);
  left_f_3.frequency(f_3,  sample_time_ms*f_3/1000);
  left_f_4.frequency(f_4,  sample_time_ms*f_4/1000);
  right_f_1.frequency(f_1, sample_time_ms*f_1/1000);  // assuming the calcs get optomized out
  right_f_2.frequency(f_2, sample_time_ms*f_2/1000);
  right_f_3.frequency(f_3, sample_time_ms*f_3/1000);
  right_f_4.frequency(f_4, sample_time_ms*f_4/1000);

  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  pinMode(LED3_PIN, OUTPUT);

  // start the outputs
  AudioNoInterrupts();  // disable audio library momentarily
  sine1.frequency(f_1); // left
  sine1.amplitude(1.0);
  sine2.frequency(f_4); // right
  sine2.amplitude(1.0);
  AudioInterrupts();    // enable, both tones will start together
}


void audioProcessSignal(uint8_t signal_num) {
  float l1, l2, l3, l4, r1, r2, r3, r4;
  //uint8_t led1_val, led2_val;

  // read all seven tone detectors
  l1 = left_f_1.read();
  l2 = left_f_2.read();
  l3 = left_f_3.read();
  l4 = left_f_4.read();
  r1 = right_f_1.read();
  r2 = right_f_2.read();
  r3 = right_f_3.read();
  r4 = right_f_4.read();

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
    l1 > thresh ||
    l2 > thresh ||
    l3 > thresh ||
    r1 > thresh ||
    r2 > thresh ||
    l3 > thresh 
  ) {
      contact = 1;
  }
  else {
      contact = 0;
  }
 


  //uncomment these lines to see how much CPU time
  //the tone detectors and audio library are using
  // Serial.print("CPU=");
  // Serial.print(AudioProcessorUsage());
  // Serial.print("%, max=");
  // Serial.print(AudioProcessorUsageMax());
  // Serial.print("%   ");
  // Serial.print("\n");

  publishOn(contact);

#ifdef DEBUG_PRINT
  if ( contact == 1 )
  {
    Serial.print ("CONTACT\n");
  } else {
    Serial.print ("--------\n");
  }
#endif

 #if 0
  if (signal_num == 1) {
    led1_val = (r1 > thresh) ? 1 : 0;
  }
  
  if (signal_num == 2) {
    led2_val = (r2 > thresh) ? 1 : 0;
  }
#endif

  //analogWrite(LED1_PIN, (1-r1)*255); // write result to LED
  //analogWrite(LED2_PIN, (1-l4)*255); // write result to LED
  //analogWrite(LED3_PIN, (1-c3)*255); // write result to LED 
}

const float row_threshold = 0.2;
const float column_threshold = 0.2;

void audioLoop() {
  if (since_main >= main_period_ms) {
    since_main = 0;
    sine1.amplitude(1.0);
    sine2.amplitude(0.0);
    audioProcessSignal(2); // process the previous signal
  }

  if (since_main >= main_period_ms/2) {
    sine1.amplitude(0.0);
    sine2.amplitude(1.0);
    audioProcessSignal(1); // process the previous signal
  }
}

void setup()
{
  while (!Serial && millis () < 1000u)  {// wait up to 1 seconds for the serial console to be available
    delay (10);
 };
  Serial.printf("MQTT Demo\n");

  initEthernet();
  client.setServer(server, 1883);
  client.setCallback(callback);

  // Allow the hardware to sort itself out
  delay(1500);

  audioSetup();
}

void loop()
{
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  audioLoop();
}