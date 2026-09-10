#include <Arduino.h>
#include "gravity_soil_moisture_sensor.h"

/**
 * @brief Function to initialize the Gravity Soil Moisture Sensor
 * @param analog_pin : GPIO analog pin
 * @return true if a valid value is available, false otherwise
 */
bool GravitySoilMoistureSensor::Setup(const uint8_t analog_pin)
{
    _analog_pin = analog_pin;
    return Read(10, 2) > 0;
}

/**
 * @brief Function to read the soil moisture value
 * @param samples  : Number of samples to take. Defaults to 128
 * @param delay_ms : Delay in milliseconds between each sample reading. Defaults to 1
 * @return The moisture value. A valid reading is between 1 and 3500
 */
uint16_t GravitySoilMoistureSensor::Read(uint16_t samples, uint16_t delay_ms)
{
    uint64_t accumulator = 0;

    for (uint16_t i = 0; i < samples; i++) {
        delay(delay_ms);
        accumulator += analogRead(_analog_pin);
    }

    // El sensor entrega sequedad (mayor ADC = mas seco).
    // Restamos del valor maximo (4095) para obtener el nivel de humedad.
    uint16_t raw_avg = (uint16_t)(accumulator / samples);
    if (raw_avg >= 4095) return 0;

    uint16_t value = 4095 - raw_avg;

    // Filtro contra ruido espurio
    if (value <= 3500) {
        return value;
    } else {
        return 3500;
    }
}
