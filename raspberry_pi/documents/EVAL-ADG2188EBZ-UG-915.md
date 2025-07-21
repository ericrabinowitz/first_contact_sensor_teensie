# EVAL-ADG2188EBZ User Guide

## UG- 915

#### One Technology Way • P. O. Box 9106 • Norwood, MA 02062 -9106, U.S.A. • Tel: 781.329.4700 • Fax: 781.461.3113 • http://www.analog.com

## Evaluation Board for I^2 C CMOS 8 × 8 Analog Switch Array with Dual/Single Supplies

**PLEASE SEE THE LAST PAGE FOR AN IMPORTANT
WARNING AND LEGAL TERMS AND CONDITIONS.** Rev. A | Page 1 of 12

### FEATURES

**Full-featured evaluation board for the ADG
Various link options
USB port
E VAL-ADG2188EBZ evaluation software for control of switches
Functions with or without a PC**

### EVALUATION KIT CONTENTS

**E VAL-ADG2188EBZ evaluation board
E VAL-ADG2188EBZ evaluation software CD
USB cable**

### DOCUMENTS NEEDED

**ADG2188 data sheet**

### SOFTWARE NEEDED

**E VAL-ADG2188EBZ evaluation software CD**

### GENERAL DESCRIPTION

```
This user guide describes the evaluation board for the ADG
I^2 C CMOS 8 × 8 analog switch array with dual/single supplies.
The array is bidirectional, and, as a result, the rows and columns
can configure as either inputs or outputs. Any number of
combinations can be active at one time.
The ADG2188 has a maximum difference of 15 V between the
VDD and VSS inputs. Therefore, take care to not to exceed the
maximum of 15 V difference when connecting the power supplies.
The evaluation board interfaces to the USB port of a PC. The
evaluation software is available with the evaluation board that
allows the user to easily program the ADG2188. The E VA L-
ADG2188EBZ can also be used as a standalone board.
Complete specifications for the ADG2188 are available in the
ADG2188 data sheet available from Analog Devices, Inc., and
should be consulted in conjunction with this data sheet when
using the evaluation board.
```
### EVALUATION BOARD BLOCK DIAGRAM

```
Figure 1.
```
```
3.3V
LINEAR
REGULATOR
```
```
Y
Y
```
```
POWER SUPPLY INPUTS
```
```
ADG
CMOS ANALOG
SWITCH ARRAY
```
```
RESET
```
```
CONTROLLER
CY7C
```
```
USB
CONNECTOR
```
```
I/O
```
```
X0 X
```
```
I/O
I/O
```
```
SCL
SCA
```
```
VL VSS GND VDD
```
```
VBUS
```
```
DGND
```
```
I/O 05978-
```

## UG- 915 EVAL-ADG2188EBZ User Guide

## TABLE OF CONTENTS

### Features .............................................................................................. 1

### Evaluation Kit Contents ................................................................... 1

### Documents Needed .......................................................................... 1

### Software Needed ............................................................................... 1

### General Description ......................................................................... 1

### Evaluation Board Block Diagram ................................................... 1

### Revision History ............................................................................... 2

### Evaluation Board Hardware ............................................................ 3

### Power Supplies .............................................................................. 3

### Link Options ..................................................................................

### Evaluation Board Software Quick Start Procedures .....................

### Software Installation .....................................................................

### Software Operation .......................................................................

### Evaluation Board Schematics and Artwork ...................................

### Ordering Information .................................................................... 11

### Bill of Materials ........................................................................... 11

### REVISION HISTORY

**4/16—Rev. 0 to Rev. A**
Changes to Features Section and General Description Section ....... 1
Added Evaluation Kit Contents Section, Documents Needed
Section, and Software Needed Section .......................................... 1
Changes to Evaluation Board Hardware Section Title,
Power Supplies Section, and Table 1 .............................................. 3
Changes to Setup for Control Without a PC Section and
Ta b l e 3 ................................................................................................ 4
Changes to Evaluation Board Software Quick Start Procedures
Section, Software Installation Section, Software Operation
Section, Setting the I^2 C Address Section and Figure 4 .................... 5
Added Reinitialize Software Section and Figure 2;
Renumbered Sequentially ................................................................ 5
Changes to LDSW (Load Switch) Section, RESET Function
Section, and Figure 5 ........................................................................ 6
Added All On Function Section ..................................................... 6
Changes to Figure 7 .......................................................................... 8
Changes to Table 4 .......................................................................... 11

**6/06—Revision 0: Initial Version**


## EVAL-ADG2188EBZ User Guide UG- 915

## EVALUATION BOARD HARDWARE

### POWER SUPPLIES

The E VA L-ADG2188EBZ can operate with single and dual
supplies. The ADG2188 is specified to operate in single-supply
mode at 12 V ± 10% operation. It is also specified to operate at
±5 V dual supply. To apply these supplies to the evaluation
board, adhere to the following guidelines:

- The VL pin provides the digital supply for the ADG
    and all digital circuitry on the board. This supply can be
    applied externally or the USB port can power the digital
    circuitry (Link 5 inserted). Note that in this case, the logic
    supply power is 3.3 V.
- The positive supply voltage (for example, 12 V) is applied
    between the AVDD and AGND inputs of the ADG
    evaluation board. Note the maximum single supply the
    ADG2188 can handle is 15 V. In this case, the AVS S input
    must equal 0 V.
       - The negative supply (for example, −5 V) is applied between
          the AVSS and AGND inputs for the negative supply (VSS)
          of the ADG2188. Note that the maximum voltage between
          AV D D a n d AVS S i s 1 5 V.
       Both analog GND and digital GND inputs are provided on the
       board. The AGND and DGND planes are connected at one
       location on the evaluation board close to the ADG2188 It is
       recommended not to connect AGND and DGND elsewhere in
       the system to avoid ground loop problems.
       Each supply is decoupled to the relevant ground plane with
       10 μF and 0.1 μF capacitors. Each device supply pin is also
       decoupled with a 10 μF and 0.1 μF capacitor pair to the relevant
       ground plane.

### LINK OPTIONS

```
There are a number of links and switch options on the
evaluation board that must be set for the required operating
setup before using the board. The functions of these link
options are described in Ta b l e 1.
```
**Table 1. Link Functions
Link No. Function**
LK1 This link chooses the first LSB bit of the chip address on the USB I^2 C interface. Note the I^2 C address must be set before the
evaluation board software is launched.
When inserted, the address bit is set to 0.
When removed, the address bit is set to 1.
LK2 This link chooses the second LSB bit of the chip address on the USB I^2 C interface. Note the I^2 C must be set before the
evaluation board software is launched.
When inserted, the address bit is set to 0.
When removed, the address bit is set to 1.
LK3 This link chooses the third LSB bit of the chip address on the USB I^2 C interface. Note the I^2 C address must be set before the
evaluation board software is launched.
When inserted, the address bit is set to 0.
When removed, the address bit is set to 1.
LK4 This link selects whether the supply at VSS is sourced from ground or from AVSS the input. If sourced from ground, the
evaluation board becomes a single supply system.
Position A: VSS sourced from AVSS.
Position B: VSS is connected to ground. This implies single-supply operation of the ADG2188.
LK5 This link selects whether the logic supply power comes from the USB power (if connected to a PC) or from the user supplied
VL (if used as a standalone unit).
When inserted, logic power supply comes from USB supply power, that is, 3.3 V.
When removed, logic power supply comes from the user supplied VL.


## UG- 915 EVAL-ADG2188EBZ User Guide

#### Setup for PC Control

The default setup for the E VA L-ADG2188EBZ is controlled by the
PC via the USB port. The default link options are listed in Ta bl e 2.

**Table 2. Default Link Options
Link No. Option**
LK1 Inserted; therefore, the LSB is 0.
LK2 Inserted; therefore, the second LSB is 0.
LK3 Inserted; therefore, the third LSB is 0.
LK4 Position A; therefore, the AVSS input supplies the
power to the VSS pin.
LK5 Inserted; therefore, logic power supply comes
from USB power.

#### Setup for Control Without a PC

```
The E VA L-ADG2188EBZ can also be used as a standalone
board. This option is designed for a PC without a USB port or
for users to use the I^2 C interface within the system being evaluated.
Ta b l e 3 lists the link options that must be set to operate the
evaluation board without a PC.
```
```
Table 3. Link Options Setup for Control Without a PC
Link No. Option
LK1, LK2, LK3 User configurable. Does not affect whether
the board is connected to a PC or not.
LK4 Position A.
LK5 Removed.
```
```
SMB connectors are provided for the SDA and SCL inputs.
Switches turn on and off via the I^2 C bus. The read/write
procedures are provided in the ADG2188 data sheet and must
be consulted when using this evaluation board in standalone
mode.
```

## UG- 915

## EVAL-ADG2188EBZ User

## Guide

## EVALUATION BOARD SOFTWARE QUICK START PROCEDURES

The ADG2188 evaluation kit includes self installing E VA L-
ADG2188EBZ evaluation software CD. Install the evaluation
software before connecting the evaluation board to the USB
port of the PC, ensuring the evaluation board is correctly
recognized when connected to the PC.

### SOFTWARE INSTALLATION

To install the software,

1. Insert the evaluation software CD into the PC. The
    installation software launches automatically. If it does not,
    use Windows Explorer to locate the file **setup.exe** on the
    CD. Double-click the **setup.exe** file to begin the
    installation procedure.
2. At the software installation prompt, select a destination
    directory. By default, the directory is **C:\Program Files\**
    **Analog Devices\ADG2188**. After the directory is selected,
    the installation procedure copies the files into the relevant
    directories on the hard drive. The installation program creates
    a program group called **Analog Devices** with a subgroup
    called **ADG2188** in the **Start** menu of the taskbar.
3. After the installation of the evaluation software is complete, a
    welcome window displays for the installation of the **ADI**
    **PAD Drivers**. Click **Install** to install the drivers.
4. After installing the drivers, power up the ADG
    evaluation board as described in the Power Supplies
    section and connect the board to the USB port of the PC
    using the supplied cable.

### SOFTWARE OPERATION

To launch the software, click **Start** > **All Programs** > **Analog
Devices** > **ADG2188** > **ADG2188 Evaluation Software**. The
**Configuration** tab of the evaluation software displays as shown
in Figure 2.

```
Figure 2. Configuration Tab
```
```
If the ADG2188 evaluation board is not connected to the USB
port when the software is launched, a Hardware Select dialog
box displays, seen in Figure 3. Connect the evaluation board to
the USB port of the PC, wait for a few seconds, click Rescan
and then click Select.
```
```
Figure 3. Hardware Select Dialog Box
```
#### Reinitialize Software

```
Click Reinitialize Software in the Configuration tab to reset
the software to the default state. Reinitialize the software whenever
the evaluation board is reconnected to the PC or if a new
evaluation board isused.
```
#### Setting the I^2 C Address

```
The device address is set in the Device Address tab (shown in
Figure 4).
```
```
Figure 4. Device Address Tab
Set the device address by clicking on the relevant bit. Click Set
Device Address to update the device address in the software.
Note the address set must correspond to the address set with
the jumpers on the evaluation board and must be set before the
evaluation board software begins to function.
```
```
05978-
```
```
05978-
```
```
05978-
```

## UG- 915 EVAL-ADG2188EBZ User Guide

#### LDSW (Load Switch)

If the load switch function in the **Configuration** tab is on, the
switches can update simultaneously (for example, for RGB
colors in video switching). Otherwise, if the load switch is off,
the switch condition updates upon completion of each I^2 C write,
that is, immediately upon clicking an LED button on the **Analog
Crosspoint Switch Control** in the **Configuration** tab. The LED
is green if the switch is on and is black if the switch is off.

If the load switch is on, clicking an LED in **Analog Crosspoint
Switch Control** stores the switch status temporarily until
**Update Switches** is clicked. When an LED is clicked, a red LED
indicates the switch turns on and a dark green LED indicates
that the switch turns off. All switches update simultaneously
upon clicking **Update Switches**. The red LEDs turn green and
the dark green LED turns black, indicating the switches are on
and off, respectively.

#### Switch Status

To see what the status of the switch array is at any given time,
click the **Switch Status** tab (shown in Figure 5). The green LED
in the **Analog Crosspoint Switch Status** indicates that the
switch is on and the black LED indicates the switch is off.

```
Figure 5. Switch Status Tab
```
#### RESET Function

```
There is a RESET button on the board that can reset the switch
a r r a y. A lt e r n a t i v e l y, clicking Reset All (Off ) in the Configuration
tab of the software resets all switches.
```
#### All On Function

```
Clicking All On button in the Configuration tab of the
software turns on all the switches.
```
```
05978-
```

## EVAL-ADG2188EBZ User Guide UG-

## EVALUATION BOARD SCHEMATICS AND ARTWORK

```
Figure 6. Schematic of USB Controller Circuitry
```
```
05978-
```

## UG- 915 EVAL-ADG2188EBZ User Guide

```
Figure 7. Schematic of ADG2188 Circuitry
```
```
05978-
```

## EVAL-ADG2188EBZ User Guide UG- 915

```
Figure 8. Component Placement Drawing
```
```
Figure 9. Component Side PCB Drawing
```
```
05978-
```
```
05978-
```

## UG- 915 EVAL-ADG2188EBZ User Guide

```
Figure 10. Solder Side PCB Drawing
```
```
05978-
```

## EVAL-ADG2188EBZ User Guide UG- 915

## ORDERING INFORMATION

### BILL OF MATERIALS

**Table 4. Component Listing
Qty. Reference Designator Description Distributor Part Number**
19 C1, C3, C5 to C9, C11,
C15, C16, C18 to C22,
C24, C26, C28, C

```
0.1 μF, 50 V, X7R SMD ceramic capacitors, 0603 package FEC FEC 499-
```
```
2 C2, C29 10 μF, TA J _ B, 16 V, SMD tantalum capacitors FEC FEC 498-
3 C4, C13, C14 10 μF, X5R ceramic capacitors, 0805 package Digikey 490-1709-1-ND
4 C12, C25, C27, C31 10 μF, TA J _ A, 6.3 V, SMD tantalum capacitors FEC FEC 197-
2 C10, C17 22 pF, 50 V, X7R SMD ceramic capacitors, 0603 package FEC FEC 722-
1 C23 2.2 μF, 6.3 V, X5R SMD ceramic capacitors, 0603 package Digikey 490-1552-1-ND
1 D1 Diode SOT23 FEC FEC 304-
1 D4 LED, 0805 package FEC FEC 359- 9681
1 J1 USB Mini-B connector Digikey, Farnell FEC 476-8309,
WM2499CT-ND
4 J2 4-pin terminal block FEC FEC 151-
5 K1 to K5 SIP-2P, 2-pin header and shorting shunts FEC FEC 511-705, FEC 150-
411
16 R1 to R4, R12 to R21, R26,
R
```
```
SMD resistors, 0603 package FEC Not Inserted
```
```
2 R5, R6 75 Ω, SMD resistors, 0603 package FEC FEC 357-
1 R7 0 Ω, SMD resistor, 0603 package FEC FEC 772-
2 R8, R9 2.2 kΩ, SMD resistors, 0603 package FEC FEC 911-
1 R10 10 kΩ, SMD resistor, 0603 package FEC FEC 911-
1 R11 1 kΩ, SMD resistor, 0603 package FEC FEC 911-
4 R28 to R31 10 kΩ, SMD resistors, 0603 package FEC FEC 911-
```
(^1) RESET Push button switch, sealed 6 mm x 8 mm FEC FEC177-
5 T1 to T5 Te s t points Not applicable Do not insert
1 U4 8 × 8 analog switch array Analog Devices ADG2188YCP
1 U2 24LC64 Digikey 24LC64-I/SN-ND
1 U3 USB microcontroller Cyprus CY7C68013-56LFC
1 U5 3.3 V regulator Analog Devices ADP3303AR-3.
2 SCL, SDA 50 Ω straight SMB jacks FEC FEC 365-
8 X2_X1, X2_X3, X4_X5,
X6_X7, Y0_Y1, Y2_Y3,
Y4_Y5, Y6_Y
Sockets, phono, printed circuit board (PCB), gold, one pair FEC FEC 382-
1 X TA L 1 24 MHz, CM309S, SMD crystal FEC FEC 569-


## UG- 915 EVAL-ADG2188EBZ User Guide

## NOTES

```
ESD Caution
ESD (electrostatic discharge) sensitive device. Charged devices and circuit boards can discharge without detection. Although this product features patented or proprietary protection
circuitry, damage may occur on devices subjected to high energy ESD. Therefore, proper ESD precautions should be taken to avoid performance degradation or loss of functionality.
Legal Terms and Conditions
By using the evaluation board discussed herein (together with any tools, components documentation or support materials, the “Evaluation Board”), you are agreeing to be bound by the terms and conditions
set forth below (“Agreement”) unless you have purchased the Evaluation Board, in which case the Analog Devices Standard Terms and Conditions of Sale shall govern. Do not use the Evaluation Board until
you have read and agreed to the Agreement. Your use of the Evaluation Board shall signify your acceptance of the Agreement. This Agreement is made by and between you (“Customer”) and Analog Devices,
Inc. (“ADI”), with its principal place of business at One Technology Way, Norwood, MA 02062, USA. Subject to the terms and conditions of the Agreement, ADI hereby grants to Customer a free, limited, personal,
temporary, non-exclusive, non-sublicensable, non-transferable license to use the Evaluation Board FOR EVALUATION PURPOSES ONLY. Customer understands and agrees that the Evaluation Board is provided
for the sole and exclusive purpose referenced above, and agrees not to use the Evaluation Board for any other purpose. Furthermore, the license granted is expressly made subject to the following additional
limitations: Customer shall not (i) rent, lease, display, sell, transfer, assign, sublicense, or distribute the Evaluation Board; and (ii) permit any Third Party to access the Evaluation Board. As used herein, the term
“ T h i r d P a r t y ” includes any entity other than ADI, Customer, their employees, affiliates and in-house consultants. The Evaluation Board is NOT sold to Customer; all rights not expressly granted herein, including
ownership of the Evaluation Board, are reserved by ADI. CONFIDENTIALITY. This Agreement and the Evaluation Board shall all be considered the confidential and proprietary information of ADI. Customer
may not disclose or transfer any portion of the Evaluation Board to any other party for any reason. Upon discontinuation of use of the Evaluation Board or termination of this Agreement, Customer agrees to
promptly return the Evaluation Board to ADI. ADDITIONAL RESTRICTIONS. Customer may not disassemble, decompile or reverse engineer chips on the Evaluation Board. Customer shall inform ADI of any
occurred damages or any modifications or alterations it makes to the Evaluation Board, including but not limited to soldering or any other activity that affects the material content of the Evaluation Board.
Modifications to the Evaluation Board must comply with applicable law, including but not limited to the RoHS Directive. TERMINATION. ADI may terminate this Agreement at any time upon giving written
notice to Customer. Customer agrees to return to ADI the Evaluation Board at that time. LIMITATION OF LIABILITY. THE EVALUATION BOARD PROVIDED HEREUNDER IS PROVIDED “AS IS” AND ADI MAKES NO
WARRANTIES OR REPRESENTATIONS OF ANY KIND WITH RESPECT TO IT. ADI SPECIFICALLY DISCLAIMS ANY REPRESENTATIONS, ENDORSEMENTS, GUARANTEES, OR WARRANTIES, EXPRESS OR IMPLIED,
RELATED TO THE EVALUATION BOARD INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTY OF MERCHANTABILITY, TITLE, FITNESS FOR A PARTICULAR PURPOSE OR NONINFRINGEMENT OF
INTELLECTUAL PROPERTY RIGHTS. IN NO EVENT WILL ADI AND ITS LICENSORS BE LIABLE FOR ANY INCIDENTAL, SPECIAL, INDIRECT, OR CONSEQUENTIAL DAMAGES RESULTING FROM CUSTOMER’S
POSSESSION OR USE OF THE EVALUATION BOARD, INCLUDING BUT NOT LIMITED TO LOST PROFITS, DELAY COSTS, LABOR COSTS OR LOSS OF GOODWILL. ADI’S TOTAL LIABILIT Y FROM ANY AND ALL CAUSES
SHALL BE LIMITED TO THE AMOUNT OF ONE HUNDRED US DOLLARS ($100.00). EXPORT. Customer agrees that it will not directly or indirectly export the Evaluation Board to another country, and that it will
comply with all applicable United States federal laws and regulations relating to exports. GOVERNING LAW. This Agreement shall be governed by and construed in accordance with the substantive laws of
the Commonwealth of Massachusetts (excluding conflict of law rules). Any legal action regarding this Agreement will be heard in the state or federal courts having jurisdiction in Suffolk County, Massachusetts,
and Customer hereby submits to the personal jurisdiction and venue of such courts. The United Nations Convention on Contracts for the International Sale of Goods shall not apply to this Agreement and is
expressly disclaimed.
```
```
©2012– 2016 Analog Devices, Inc. All rights reserved. Trademarks and
registered trademarks are the property of their respective owners.
UG05978-0-4/16(A)
```

