#include <ezButton.h>
#include <SoftwareSerial.h>

// Definición de pines del Joystick
#define VRX_PIN  A0
#define VRY_PIN  A1
#define SW_PIN   2

// Definición de pines para el módulo Bluetooth HC-06
// RX del Arduino al TX del HC-06, TX del Arduino al RX del HC-06 (usa divisor de voltaje)
#define BT_RX 10
#define BT_TX 11

SoftwareSerial BTSerial(BT_RX, BT_TX);
ezButton button(SW_PIN);

// Variables del Joystick
float xValue = 0; 
float yValue = 0; 
float lastXValue = 0; // Para guardar la posición anterior X
float lastYValue = 0; // Para guardar la posición anterior Y

// Variables para control de tiempo
unsigned long lastTime = 0;
unsigned long lastPressTime = 0;

// Configuración de sensibilidad (Puedes ajustar estos valores)
const int updateInterval = 50;           // Leer el joystick cada 50ms
const float thresholdMovimiento = 0.6;   // Qué tanta diferencia se considera "brusco" (0.0 a 1.0+)
const int thresholdDobleClic = 300;      // Tiempo máximo entre clics para considerarlo rápido (ms)

void setup() {
  Serial.begin(9600);    // Monitor Serial del PC
  BTSerial.begin(9600);  // Monitor Serial por Bluetooth (HC-06)
  
  button.setDebounceTime(50); // Anti-rebote del botón
  
  Serial.println("Iniciando sistema...");
  BTSerial.println("Bluetooth conectado y listo.");
}

void loop() {
  button.loop(); 
  unsigned long currentTime = millis();

  // 1. DETECCIÓN DE PULSACIONES RÁPIDAS (Doble Clic)
  if (button.isPressed()) {
    unsigned long timeSinceLastPress = currentTime - lastPressTime;
    
    // Si la última vez que se presionó fue hace menos del umbral, es una pulsación rápida
    if (timeSinceLastPress > 50 && timeSinceLastPress <= thresholdDobleClic) {
      Serial.println("¡ALERTA! Pulsación de botón muy rápida.");
      BTSerial.println("¡ALERTA! Pulsación de botón muy rápida.");
    }
    
    lastPressTime = currentTime; // Guardamos el momento de esta pulsación
  }

  // 2. DETECCIÓN DE MOVIMIENTOS BRUSCOS
  // Evaluamos los movimientos en intervalos fijos (ej. cada 50ms)
  if (currentTime - lastTime >= updateInterval) {
    
    // Leemos valores actuales
    xValue = (analogRead(VRX_PIN) - 560.0) / 560.0;
    yValue = (analogRead(VRY_PIN) - 560.0) / 560.0;

    // Calculamos qué tanto cambió la posición desde la última lectura (Valor Absoluto)
    float deltaX = abs(xValue - lastXValue);
    float deltaY = abs(yValue - lastYValue);

    // Si el cambio en X o Y es mayor a nuestra sensibilidad, disparamos alerta
    if (deltaX > thresholdMovimiento || deltaY > thresholdMovimiento) {
      Serial.print("¡ALERTA! Movimiento brusco detectado. X:");
      Serial.print(deltaX);
      Serial.print(" Y:");
      Serial.println(deltaY);
      
      // Enviar también por Bluetooth
      BTSerial.println("¡ALERTA! Movimiento brusco del Joystick.");
    }

    // Actualizamos las variables para la siguiente comparación
    lastXValue = xValue;
    lastYValue = yValue;
    lastTime = currentTime;
  }
}