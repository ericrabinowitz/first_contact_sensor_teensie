#include "SdFat.h"
#include <string>
#include <vector>
#include <algorithm>

// some aliases to reduce typing....
using string = std::string;
using strVec = std::vector<string>;

SdFat sd;


// Use these with the Teensy Audio Shield
//#define SDCARD_CS_PIN    10
//#define SDCARD_MOSI_PIN  7   // Teensy 4 ignores this, uses pin 11
//#define SDCARD_SCK_PIN   14  // Teensy 4 ignores this, uses pin 13

// Use these with the Teensy 3.5 & 3.6 & 4.1 SD card
#define SDCARD_CS_PIN    BUILTIN_SDCARD
#define SDCARD_MOSI_PIN  11  // not actually used
#define SDCARD_SCK_PIN   13  // not actually used


void setup()
{
    while (!Serial) {}
    
    sd.begin(SdioConfig(FIFO_SDIO));

    // read filnames from some directory (here: root)
    SdFile dir("/", O_RDONLY);
    strVec filenames = getFilenames(dir);

    // use the stl sorting algorithmus
    std::sort(filenames.begin(), filenames.end(), [](string a, string b) { return a < b; });

    // print the sorted names
    for (string& name : filenames)
    {
        Serial.println(name.c_str());
    }
}

void loop(){
}

//-----------------------------------------------
strVec getFilenames(SdFile& dir)
{
    strVec filenames;

    SdFile file;
    while (file.openNext(&dir, O_RDONLY))
    {
        constexpr size_t maxFileLen = 30;

        char buf[maxFileLen];
        file.getName(buf, maxFileLen);
        filenames.emplace_back(buf);  // directly construct the string in the vector to avoid copies
    }
    return filenames;  // Ok, std::vector implements move semantics -> nothing will be copied here
}
