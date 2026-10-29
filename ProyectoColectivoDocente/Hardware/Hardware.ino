#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9   // Pin de reset
#define SS_PIN 10   // Pin SDA (SS)

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("Acerca tu tarjeta RFID al lector...");
  Serial.println();
}

void loop() {
  // Validar si hay una nueva tarjeta presente
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // Seleccionar la tarjeta
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  Serial.print("UID de la tarjeta: ");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " ");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
  }
  Serial.println();

  // Detener la lectura actual
  mfrc522.PICC_HaltA();
}
