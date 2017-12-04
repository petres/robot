#include <Servo.h>

#define DEBUG 0

const int servoCount = 4;

Servo servo[servoCount];
int pins[servoCount] = {9, 10, 11, 12};

const byte numChars = 16;
char receivedChars[numChars];

boolean gotNewLine = false;

void recvTillNewLine();
void processNewLine(char *);


void setup() {
    Serial.begin(2000000);
    for(int i = 0; i < servoCount; i += 1)
        servo[i].attach(pins[i]);
    
    #if DEBUG
    Serial.println("Ready!");
    #endif
}


void loop() {
    recvTillNewLine();
    if (gotNewLine) {
        processNewLine(receivedChars);
        gotNewLine = false;
    }
}

void recvTillNewLine() {
    static byte ndx = 0;
    char endMarker = '\n';
    char rc;

    while (Serial.available() > 0 && gotNewLine == false) {
        rc = Serial.read();
        if (rc != endMarker) {
            receivedChars[ndx] = rc;
            ndx++;
            if (ndx >= numChars)
                ndx = numChars - 1;
        } else {
            receivedChars[ndx] = '\0';
            ndx = 0;
            gotNewLine = true;
        }
    }
}

void setServoPosition(int servoId, int position) {
    if (servoId < servoCount && position >= 0 && position <= 180) {
        #if DEBUG
        Serial.print("Set Servo ");
        Serial.print(servoId);
        Serial.print(" to ");
        Serial.print(position);
        Serial.println(".");
        #endif

        servo[servoId].write(position);
    } else {
        #if DEBUG
        Serial.println("Invalid values!");
        #endif
    }
}

void processNewLine(char * receivedChars) {
    #if DEBUG
    Serial.print("GOT: '");
    Serial.print(receivedChars);
    Serial.println("'");
    #endif
    char* command = strtok(receivedChars, " ");
    while (command != 0) {
        char* separator = strchr(command, ':');
        if (separator != 0) {
            *separator = 0;
            int servoId = atoi(command);
            ++separator;
            int position = atoi(separator);

            setServoPosition(servoId, position);
        }
        command = strtok(0, " ");
    }
}
