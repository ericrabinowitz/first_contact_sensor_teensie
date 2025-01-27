#include <stdlib.h>
#include <TimerOne.h>
#include <SPI.h>
#include <fnet.h>
#include <QNEthernet.h>

#define SPI_MOSI        11
#define SPI_MISO        12
#define SPI_SCK         13
#define SPI_FREQ  1000000                                 //SPI frequency (1 MHz)
static  SPISettings spi_settings                          //SPI settings
        = SPISettings(SPI_FREQ, MSBFIRST, SPI_MODE1);

byte mac[] = {
  0x92, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };

IPAddress ip(192.168.1.2);
//, 254, 86, 246);
IPAddress subnet(255, 255, 0, 0);
IPAddress serv(169, 254, 86, 215);
IPAddress gateway(169, 254, 86, 1);

EthernetServer server(23);

EthernetClient client = server.available();

boolean alreadyConnected = false;

String inputString;
String inputCommand;
byte buf[1024];

uint8_t msg_received = 0;
uint8_t msg_send = 0;

float temperatures[] = {5, 4.3, 1234, 23, 1.23, -5.0000034};

bool alarm = true;


void setup() {

  Serial.begin(115200);
  Serial.println("Server online!");


  SPI.setMISO(SPI_MISO);                                     //set MISO pin
  SPI.setMOSI(SPI_MOSI);                                     //set MOSI pin
  SPI.setSCK(SPI_SCK);                                       //set clock pin
  SPI.begin();                                            //start SPI bus

  Ethernet.begin(mac, ip, gateway, subnet);
  if(Ethernet.hardwareStatus() == EthernetNoHardware){
    Serial.println("Ethernet is not available. Check hardware status!");
    while(true){;}
  }
  if(Ethernet.linkStatus() == LinkOFF){
    Serial.println("Ethernet cable is not connected");
  }
  server.begin();
  Serial.print("Server IP-address: ");
  Serial.println(Ethernet.localIP());
}

void loop() {

  if(client){
    new_client();
    communication();
  }

  control_interface();
}


void print_command_list(){
  Serial.println("Command list:");
  Serial.println("");
}

void new_client(){
  if(!alreadyConnected){
    client.flush();
    Serial.println("New Client available.");
    Serial.print("Client IP: ");
    Serial.println(client.remoteIP());
    client.println("Hello, client!");
    client.print("Server IP: ");
    client.println(ip);
    client.println(Ethernet.localIP());
    alreadyConnected = true;
  }
}


void communication(){

  if(client.available() > 0){
    
    char thisChar = client.read();
    inputCommand = client.readString();
//    server.write(thisChar);
//    Serial.write(thisChar);


    switch(thisChar){
      
      case 'temp':
        for(int i=0; i<6; i++){
          server.write(temperatures[i]);
          client.print(temperatures[i]);
          client.print("  ");
        }
        Serial.println("All temperature values have been sent.");
        client.println();
      break;

      case 'reads':
        inputString = client.readString();
        Serial.print(inputString);
//        client.write(inputString);
        server.write("Danke für die Nachricht ;)");
      break;

      case 'h':
        print_command_list();
        server.write("Command list has been print to Serial\r\n");
      break;

      case 'a':
        server.write(alarm);
        client.print("Alarmstatus: ");
        client.print(alarm);
      break;

      case 'b':
        server.write("Achtung, ich gebe dir den Alarm-Status zurück!");
        thisChar = 'a';
      break;
      
      case 'runs':
        server.write("deep, run wild");
      break;

      case 'traffic':
        while(client.connected()){
          client.read(buf,1024);
        }
        client.stop();
        Serial.println("Client disconnected");
      break;

      default:
        server.write("No valid input");
      break;

    }

    }
}


void control_interface(){

  String input = "";

  if(Serial.available() > 0){
    input = Serial.readString();
    msg_send = (input.substring(0,4)).toInt();
    Serial.print("Zu sendende Nachricht: ");
    Serial.println(msg_send);
  }
  
}