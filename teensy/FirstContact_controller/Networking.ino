/*
Networking: The ethernet, DNS, and MQTT WLED messaging logic.
*/

#include "Networking.h"
#include "defines.h"

//using namespace qindesign::network;


// --- UDP and DNS Setup ---
EthernetUDP udp;
const unsigned int DNS_PORT = 53;

byte mac[] = {0x92, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};
#if !(USING_DHCP)
IPAddress NETWORK_IP(192, 168, 1, 48);
IPAddress NETWORK_MASK(255, 255, 255, 0);
IPAddress NETWORK_GATEWAY(192, 168, 1, 20);
IPAddress NETWORK_DNS(192, 168, 1, 20);
IPAddress UDP_LOG_PC_IP(192, 168, 1, 50);
#endif
IPAddress server(192, 168, 4, 1); // MQTT Broker (Raspberry PI)

char *hostname = 0; // Filled by reverse DNS lookup
EthernetClient ethClient;

// --- DNS Helper Functions ---

/*
stringToCharArray(String str):

Explanation and Important Considerations:
  - Takes an Arduino String and returns a dynamically allocated char array.
  - Caller must eventually delete[] the returned pointer.
*/
char *stringToCharArray(String str) {
  if (str.length() == 0) {
    return nullptr;
  }
  char *charArray = new char[str.length() + 1];
  if (charArray == nullptr) {
    return nullptr;
  }
  str.toCharArray(charArray, str.length() + 1);
  return charArray;
}

/*
  DNS Server declaration: now declared without initialization.
*/
IPAddress dnsServer;
byte responseBuffer[512];

int buildDnsPtrQuery(byte *buffer, int buflen, const String &reverseName) {
  uint16_t id = random(0, 65535);
  buffer[0] = (id >> 8) & 0xFF;
  buffer[1] = id & 0xFF;
  buffer[2] = 0x01; // Recursion desired
  buffer[3] = 0x00;
  buffer[4] = 0x00;
  buffer[5] = 0x01; // QDCOUNT = 1
  for (int i = 6; i < 12; i++)
    buffer[i] = 0;
  int pos = 12, start = 0;
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
    if (dotIndex == -1)
      break;
    start = dotIndex + 1;
  }
  buffer[pos++] = 0x00; // Terminate QNAME
  buffer[pos++] = 0x00;
  buffer[pos++] = 0x0C; // QTYPE: PTR
  buffer[pos++] = 0x00;
  buffer[pos++] = 0x01; // QCLASS: IN
  return pos;
}

String parsePtrResponse(byte *buffer, int buflen, int queryLength) {
  String result = "";
  int offset = queryLength + 12; // Skip header and query
  while (offset < buflen) {
    if ((buffer[offset] & 0xC0) == 0xC0) {
      int pointerOffset = ((buffer[offset] & 0x3F) << 8) | buffer[offset + 1];
      offset += 2;
      int tempOffset = pointerOffset;
      while (tempOffset < buflen) {
        int length = buffer[tempOffset];
        if (length == 0)
          break;
        for (int i = 1; i <= length; i++) {
          result += (char)buffer[tempOffset + i];
        }
        tempOffset += length + 1;
        if (buffer[tempOffset] != 0) {
          result += ".";
        }
      }
      break;
    } else {
      int length = buffer[offset];
      if (length == 0)
        break;
      for (int i = 1; i <= length; i++) {
        result += (char)buffer[offset + i];
      }
      offset += length + 1;
      if (buffer[offset] != 0 && (buffer[offset] & 0xC0) != 0xC0)
        result += ".";
    }
  }
  return result;
}

String reverseDnsLookup(IPAddress ip) {
  String reverseName = String(ip[3]) + "." + String(ip[2]) + "." +
                       String(ip[1]) + "." + String(ip[0]) + ".in-addr.arpa";
  byte queryBuffer[512];
  int queryLength =
      buildDnsPtrQuery(queryBuffer, sizeof(queryBuffer), reverseName);
  dnsServer = Ethernet.dnsServerIP();
  udp.beginPacket(dnsServer, DNS_PORT);
  udp.write(queryBuffer, queryLength);
  udp.endPacket();
  unsigned long startTime = millis();
  while (millis() - startTime < 2000) {
    int packetSize = udp.parsePacket();
    if (packetSize > 0) {
      int len = udp.read(responseBuffer, sizeof(responseBuffer));
      String hostname = parsePtrResponse(responseBuffer, len, queryLength);
      return hostname;
    }
  }
  return String("Timeout");
}

// --- Ethernet Setup ---

void initEthernet() {
networkErrorRetry: // Entry point if we fail to initialize network

  bool networkError = false;

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
  displayNetworkStatus("DHCP Waiting...");

  Ethernet.begin();
  // give the Ethernet shield minimum 1 sec for DHCP and 2 secs for staticP to initialize:
  // delay(1000);  XXX 3
#else
  // Start the Ethernet connection, using static IP
  Serial.print("Initialize Ethernet using STATIC IP => ");
  char staticIpMsg[32];
  sprintf(staticIpMsg, "Static IP:%d.%d.%d.%d", NETWORK_IP[0], NETWORK_IP[1], NETWORK_IP[2], NETWORK_IP[3]);
  displayNetworkStatus(staticIpMsg);
  Ethernet.begin(NETWORK_IP, NETWORK_MASK, NETWORK_GATEWAY, NETWORK_DNS);
#endif

  if (!Ethernet.waitForLocalIP(5000)) {
    networkError = true;

    Serial.println("Failed to configure Ethernet");
    displayNetworkStatus("** Network Failed **");

    if (!Ethernet.linkStatus()) {
      displayNetworkStatus("CHECK ETHERNET CABLE");
      Serial.println("Ethernet cable is not connected.");
      delay(5000);
    }
  } else {
    networkError = false;

    IPAddress ipAddress = Ethernet.localIP();

    char ipString[128];
    sprintf(ipString, "IP:%d.%d.%d.%d", ipAddress[0], ipAddress[1],
            ipAddress[2], ipAddress[3]);

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

  Serial.printf("Hostname:");
  Serial.print(Hostname);

  hostname = stringToCharArray(Hostname);

  displayHostname(hostname);

  /* The data was allocated, but we will not delete it since we may need to print again */
  /* Remove this commment to delete the allocated string *
  delete[] hostname;
  */
}

String getLocalIp() {
  IPAddress ip = Ethernet.localIP();
  return String(ip[0]) + "." + String(ip[1]) + "." + String(ip[2]) + "." +
         String(ip[3]);
}

// Networking accessors for Lights.ino
IPAddress getServer() {
  return server;
}

char* getHostname() {
  return hostname;
}

EthernetClient& getEthClient() {
  return ethClient;
}
