
/*
  ArduinoMqttClient - WiFi Simple Sender

  This example connects to a MQTT broker and publishes a message to
  a topic once a second.

  The circuit:
  - Arduino MKR 1000, MKR 1010 or Uno WiFi Rev2 board

  This example code is in the public domain.
*/
#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

// Begin Ethernet Requirements
#include "defines.h" 
  
#include <SD.h> 
#include <SPI.h> 
#include <QNEthernet.h>
#include <WiFi.h>

#define PASV_RESPONSE_STYLE_NEW       true 
#define FTP_FILESYST                  FTP_SDFAT2 

// Default 2048 
#define FTP_BUF_SIZE                  8192 

#define FTP_USER_NAME_LEN             64        // Max permissible and default are 64 
#define FTP_USER_PWD_LEN             128        // Max permissible and default are 128 

byte mac[] = {
  0x92, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
IPAddress NETWORK_IP      (192,168,1,48); //static IP
IPAddress NETWORK_MASK    (255,255,255,0);
IPAddress NETWORK_GATEWAY (192,168,1,20);
IPAddress NETWORK_DNS     (192,168,1,20);
IPAddress UDP_LOG_PC_IP   (192,168,1,50);
// End  Ethernet Requirements
#include <ArduinoMqttClient.h>
#if defined(ARDUINO_SAMD_MKRWIFI1010) || defined(ARDUINO_SAMD_NANO_33_IOT) || defined(ARDUINO_AVR_UNO_WIFI_REV2)
  #include <WiFiNINA.h>
#elif defined(ARDUINO_SAMD_MKR1000)
  #include <WiFi101.h>
#elif defined(ARDUINO_ARCH_ESP8266)
  #include <ESP8266WiFi.h>
#elif defined(ARDUINO_PORTENTA_H7_M7) || defined(ARDUINO_NICLA_VISION) || defined(ARDUINO_ARCH_ESP32) || defined(ARDUINO_GIGA) || defined(ARDUINO_OPTA)
  #include <WiFi.h>
#elif defined(ARDUINO_PORTENTA_C33)
  #include <WiFiC3.h>
#elif defined(ARDUINO_UNOR4_WIFI)
  #include <WiFiS3.h>
#endif

#include "arduino_secrets.h"
///////please enter your sensitive data in the Secret tab/arduino_secrets.h
char ssid[] = SECRET_SSID;    // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)

// To connect with SSL/TLS:
// 1) Change WiFiClient to WiFiSSLClient.
// 2) Change port value from 1883 to 8883.
// 3) Change broker value to a server with a known SSL/TLS root certificate 
//    flashed in the WiFi module.

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

const char broker[] = "test.mosquitto.org";
int        port     = 1883;
const char topic[]  = "arduino/simple";

const long interval = 1000;
unsigned long previousMillis = 0;

int count = 0;
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

void setup() {
  //Initialize serial and wait for port to open:
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }

  initEthernet();



  Serial.println("You're connected to the network");
  Serial.println();

  // You can provide a unique client ID, if not set the library uses Arduino-millis()
  // Each client must have a unique client ID
  // mqttClient.setId("clientId");

  // You can provide a username and password for authentication
  // mqttClient.setUsernamePassword("username", "password");

  Serial.print("Attempting to connect to the MQTT broker: ");
  Serial.println(broker);

  if (!mqttClient.connect(broker, port)) {
    Serial.print("MQTT connection failed! Error code = ");
    Serial.println(mqttClient.connectError());

    while (1);
  }

  Serial.println("You're connected to the MQTT broker!");
  Serial.println();
}

void loop() {
  // call poll() regularly to allow the library to send MQTT keep alives which
  // avoids being disconnected by the broker
  mqttClient.poll();

  // to avoid having delays in loop, we'll use the strategy from BlinkWithoutDelay
  // see: File -> Examples -> 02.Digital -> BlinkWithoutDelay for more info
  unsigned long currentMillis = millis();
  
  if (currentMillis - previousMillis >= interval) {
    // save the last time a message was sent
    previousMillis = currentMillis;

    Serial.print("Sending message to topic: ");
    Serial.println(topic);
    Serial.print("hello ");
    Serial.println(count);

    // send message, the Print interface can be used to set the message contents
    mqttClient.beginMessage(topic);
    mqttClient.print("hello ");
    mqttClient.print(count);
    mqttClient.endMessage();

    Serial.println();

    count++;
  }
}
