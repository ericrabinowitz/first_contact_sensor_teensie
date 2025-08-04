/*
Display: Printing to the small OLED display on the teensy.
*/

#include "Display.h"
#include "StatueConfig.h"

// Create the OLED display object using Wire2 (as in original code).
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire2, OLED_RESET);

// Cumulative count of contacts.
// NOTE: Briefly un-linking and re-contacting has different behavior under the
// hood, though still counts as a new contact for this counter.
unsigned long int contactCount = 0;

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

  for (count = 0; count < STRING_BUFFER_LEN; ++count)
    str[count] = 0;

  if (!isInitialized) {
    startTimeMills = millis();
    isInitialized = true;
    return;
  }

  mills = millis();

  millsLapse = mills - startTimeMills;

  // Only update every 1/4 second
  if (millsLapse % 100)
    return;

  secondsLapse = millsLapse / 1000;

  //display.clearDisplay();
  display.fillRect(0, 54, 128, 10, SSD1306_BLACK);
  //display.display();

  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setTextSize(1);
  display.setCursor(0, 55);
  sprintf(str, "%07lu    %02lu:%02lu:%02lu", contactCount, secondsLapse / 3600,
          (secondsLapse % 3600) / 60, (secondsLapse % 3600) % 60);

  display.printf(str);

  display.display();
}

/*
  displayState() - Print the contact state to OLED display
      - This routine is called at high-speed in our main loop
      - It only publishes changes to state
*/
void displayState(ContactState state) {
  char str[128];

  if (state.isUnchanged()) {
    return;
  }

  if (state.isLinked()) {
    ++contactCount;
    display.fillRect(0, 30, 128, 10, SSD1306_BLACK);
    display.setTextSize(3);              // Normal 1:1 pixel scale
    display.setTextColor(SSD1306_WHITE); // Draw white text
    display.setCursor(0, 30);
    sprintf(str, "%07lu", contactCount);
    display.printf(str);
    display.display();
  } else {
    display.fillRect(0, 30, 128, 25, SSD1306_BLACK);
    display.display();
  }
}

void displayHostname(char *hostname) {
  // Append hostname to the statue info on line 0
  display.setCursor(70, 0); // Position after statue name
  display.print(F(" "));
  display.print(hostname);
  display.display();
}

void displayFrequencies(void) {
  // Display RX frequencies on line 3 (y=20) in kHz
  display.fillRect(0, 20, 128, 10, SSD1306_BLACK); // Clear line 3
  display.setCursor(0, 20);
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // Show RX frequencies in kHz on line 3
  display.print(F("RX:"));
  bool first = true;
  for (int i = 0; i < NUM_STATUES; i++) {
    if (i != MY_STATUE_INDEX) {
      if (!first)
        display.print(F(","));
      display.print(STATUE_FREQUENCIES[i] / 1000.0, 1);
      display.print(F("k"));
      first = false;
    }
  }

  display.display();
}

/*
 * displayActivityStatus() - display a wandering eye and show any acitivy
 */
void displayActivityStatus(bool isLinked) {
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
  if (isLinked) {
    isInitialized = false;
    return;
  }

  if (!isInitialized) {
    time = millis();
    isInitialized = true;
  }

  mills = millis();

  // Handle wrap-around
  if (time > mills)
    time = mills;

  deltaTime = (mills - time) % 1000;

  mod = deltaTime % (1000 / ACTIVITY_BAR_FRACTIONS);
  if (mod != 0)
    return;

  unsigned int x_unscaled;
  unsigned int x_scaled;

  x_unscaled = deltaTime / ACTIVITY_BAR_FRACTIONS;
  x_scaled = x_unscaled * 128 / ACTIVITY_BAR_FRACTIONS;

  if (direction) {
    Xposition = x_scaled;
  } else {
    Xposition = 124 - x_scaled;
  }

#ifdef ACTIVITY_DEBUG_ENABLE
  printf("Direction:%s time:%u delta_t:%u x_unscaled:%u Xpos:%u\n",
         direction ? "F" : "B", time, deltaTime, x_unscaled, Xposition);
#endif
  /*
    Clear the  previous activity block
  */
  display.setTextColor(SSD1306_WHITE);

  display.fillRect(Xposition_last, 30, 10, 10, SSD1306_BLACK);

  /*
    Draw a small box on the line position it based on the fraction of a second
  */

  display.fillRect(Xposition, 30, 10, 10, SSD1306_WHITE); // New Block
  display.display();

  /* Flip the direction */
  if (x_unscaled == (ACTIVITY_BAR_FRACTIONS - 1)) {
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

void displayNetworkStatus(const char string[]) {
  display.setTextColor(SSD1306_WHITE);
  display.fillRect(0, 10, 128, 10, SSD1306_BLACK); // Erase line 2 only

  display.setCursor(0, 10);
  display.print(string);

  // Add TX frequency after IP address on same line
  display.print(F(" TX:"));
  display.print(MY_TX_FREQ / 1000.0, 1);
  display.print(F("k"));

  display.display();
}

void displaySplashScreen(void) {
  display.clearDisplay();

  display.setTextSize(1);              // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setCursor(0, 0);             // Start at top-left corner
  display.print(F("ST "));
  display.print(THIS_STATUE_ID);
  display.print(F(": "));
  display.print(MY_STATUE_NAME);

  display.setCursor(0, 25);
  //display.setTextSize(2);             // Draw 2X-scale text
  display.setTextColor(SSD1306_WHITE);
#if STANDALONE_MODE
  display.println(F("STANDALONE MODE"));
#else
  display.print(F("IP:"));
  display.print(getLocalIp());
#endif

  display.setTextSize(1);              // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setCursor(0, 55);
  display.println(F(__DATE__ "  " __TIME__));

  display.display();
  //delay(2000); XXX
}

void displaySetup() {
  Wire2.begin();

  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
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
