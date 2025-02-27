/*
 Basic MQTT example

 This sketch demonstrates the basic capabilities of the library.
 It connects to an MQTT server then:
  - publishes "hello world" to the topic "outTopic"
  - subscribes to the topic "inTopic", printing out any messages
    it receives. NB - it assumes the received payloads are strings not binary

 It will reconnect to the server if the connection is lost using a blocking
 reconnect function. See the 'mqtt_reconnect_nonblocking' example for how to
 achieve the same result without blocking the main loop.
 
*/

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
IPAddress server          (192,168,0,105);

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
    if (client.connect("arduinoClient")) {
      Serial.println("connected");
      // Once connected, publish an announcement...
      client.publish("wled/dee","hello world");
      // ... and resubscribe
      client.subscribe("wled/command");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void setup()
{
  while (!Serial);
  delay(100);
  Serial.printf("MQTT Demo\n");

  initEthernet();

  client.setServer(server, 1883);
  client.setCallback(callback);

  // Allow the hardware to sort itself out
  delay(1500);
}

void loop()
{
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}