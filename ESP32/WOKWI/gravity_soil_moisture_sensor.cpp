#include <Arduino.h>
#include "gravity_soil_moisture_sensor.h"

bool GravitySoilMoistureSensor::Setup(const uint8_t analog_pin)
{
    _analog_pin = analog_pin;
    return Read(10, 2) > 0;
}

uint16_t GravitySoilMoistureSensor::Read(uint16_t samples, uint16_t delay_ms)
{
    uint64_t accumulator = 0;

    for (uint16_t i = 0; i < samples; i++) {
        delay(delay_ms);
        accumulator += analogRead(_analog_pin);
    }

    uint16_t raw_avg = (uint16_t)(accumulator / samples);
    if (raw_avg >= 4095) return 0;

    uint16_t value = 4095 - raw_avg;

    if (value <= 3500) {
        return value;
    } else {
        return 3500;
    }
}
