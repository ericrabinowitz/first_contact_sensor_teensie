/* blinkServer 2023/8/22
* cleaned up version of https://forum.pjrc.com/threads/68066-New-lwIP-based-Ethernet-library-for-Teensy-4-1?p=299978&viewfull=1#post299978
* open serial monitor to see what the arduino receives and the server address
* requires DHCP
* for hardware: ..  or bare teensy 4.1
*/

#include <QNEthernet.h>

#define LEDPIN13 13

using namespace qindesign::network;
constexpr uint32_t kDHCPTimeout = 10000;  // 10 seconds
constexpr uint16_t kServerPort = 80; //443 for TLS


byte mac[] = {
  0x92, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };

//IPAddress ip(192,168,1, 48);
//IPAddress subnet(255, 255, 0, 0);
//IPAddress serv(169, 254, 86, 215);
//IPAddress gateway(169, 254, 86, 1);

IPAddress NETWORK_IP      (192,168,1,48); //static IP
IPAddress NETWORK_MASK    (255,255,255,0);
IPAddress NETWORK_GATEWAY (192,168,1,20);
IPAddress NETWORK_DNS     (192,168,1,20);
IPAddress UDP_LOG_PC_IP   (192,168,1,50);


EthernetServer server(kServerPort); //server port

IPAddress ip;
#if 0

uint8_t mac[6];
#endif
int theline=0;
String readString;
boolean gledon=false;

void setup(){

  pinMode(LEDPIN13, OUTPUT); //pin selected to control
  digitalWrite(LEDPIN13, gledon);  //turn off when starting up
 
  //enable serial data print
  Serial.begin(9600);
  while (!Serial && millis()<5000) {
    ; // wait for serial port to connect or 5 seconds
  }
  //Serial.print(CrashReport);
  //stdPrint = &Serial;  // Make printf work (a QNEthernet feature)
 
  Serial.println("blinkServer"); // so I can keep track of what is loaded

  //Ethernet.begin(mac, ip, gateway, subnet);
  Ethernet.begin(NETWORK_IP, NETWORK_MASK, NETWORK_GATEWAY, NETWORK_DNS); 
  if(Ethernet.hardwareStatus() == EthernetNoHardware){
    Serial.println("Ethernet is not available. Check hardware status!");
    while(true){;}
  }
  while (Ethernet.linkStatus() == LinkOFF){
    Serial.println("Ethernet cable is not connected");
    delay(5000); // 5 Second Delay
  }
  Serial.println("Ethernet cable IS NOW connected");

  server.begin();
  Serial.print("Server IP-address: ");
  Serial.println(Ethernet.localIP());




  #if 0

  Ethernet.macAddress(mac);
  Serial.printf("\nMAC address: %02x:%02x:%02x:%02x:%02x:%02x\n", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  if(mac[5]==0xf3){   //host name stuff
    Ethernet.setHostname("GPSD_Box");   
  }else{
    Ethernet.setHostname("bare-Teensy");
  }
 
  printf("Starting Ethernet with DHCP...\n");
  if (!Ethernet.begin()) {
    printf("Failed to start Ethernet\n");
    //return;
  }



  if (!Ethernet.waitForLocalIP(kDHCPTimeout)) {
    printf("Failed to get IP address from DHCP\n");
    gledon=false;
  } else {
    ip = Ethernet.subnetMask();
    printf("    Subnet mask = %u.%u.%u.%u\n", ip[0], ip[1], ip[2], ip[3]);
    ip = Ethernet.gatewayIP();
    printf("    Gateway     = %u.%u.%u.%u\n", ip[0], ip[1], ip[2], ip[3]);
    ip = Ethernet.dnsServerIP();
    printf("    DNS         = %u.%u.%u.%u\n", ip[0], ip[1], ip[2], ip[3]);
  }
  #endif


    // Start the server
    ip = Ethernet.localIP();
    printf("Listening for clients.  Copy this to your browser:  http://%u.%u.%u.%u   \n\n", ip[0], ip[1], ip[2], ip[3]);
    server.begin();
    gledon=true;

 digitalWrite(LEDPIN13, gledon);  //LED will be on when starting up and has ip address
}

void loop(){
  // Create a client connection
  EthernetClient client = server.available();
  if (client) {
    while (client.connected()) {
      if (client.available()) {
        char c = client.read();

        //read char by char HTTP request
        if (readString.length() < 100) {
          readString += c;  //store characters to string
          //Serial.print(c); //uncomment to see in serial monitor
        }

        if (c == '\n') {  //HTTP request ends with '\n'
          theline++;
          Serial.println(theline); //separate responses with a line #
          Serial.print(readString); // \n already included
         
          //set the status of items before sending the HTML in case this is a response to previous change
          //this will prevent having to update again as in formServer.ino
          //note that request not containing "LED+ON" or "LED+OFF" will leave gledon status unchanged
          if(readString.indexOf("LED+ON") >0){
            gledon=true;
            digitalWrite(LEDPIN13, gledon);  
          }else if(readString.indexOf("LED+OFF") >0){
            gledon=false;
            digitalWrite(LEDPIN13, gledon); 
          }

          //now output HTML data header
          //use \ slash to escape the " in the html
          /////////////////////
          client.writeFully("HTTP/1.1 200 OK\n");
          client.writeFully("Content-Type: text/html\n");
          client.writeFully("\n");

          client.writeFully("<HTML>");
          client.writeFully("<HEAD>");
          client.writeFully("<TITLE>blink</TITLE>");
          client.writeFully("</HEAD>");
          client.writeFully("<BODY>");
          client.writeFully("<font size=\"10\">");

          client.writeFully("<H1>blinkServer</H1>");

          char buff[60];
          sprintf(buff, "<FORM ACTION=\"http://%u.%u.%u.%u:80\" method=get >",  ip[0], ip[1], ip[2], ip[3]);
          client.writeFully(buff);
         
          if(gledon){
            client.writeFully("The LED is ON ");
            client.writeFully("<INPUT TYPE=SUBMIT NAME=\"submit\" VALUE=\"TURN LED OFF\" style=\"font-size: 70px\">");
          }else{
            client.writeFully("The LED is OFF ");
            client.writeFully("<INPUT TYPE=SUBMIT NAME=\"submit\" VALUE=\"TURN LED ON\" style=\"font-size: 70px\">");
          }
          client.writeFully("<BR>");
          client.writeFully("</font>");
          client.writeFully("</BODY>");
          client.writeFully("</HTML>");
          client.flush();

          delay(1);
          client.stop();  //stopping client.  Page is done till next request so stop.

          //clearing string for next read
          readString="";
        }
      }
    }
  }
}