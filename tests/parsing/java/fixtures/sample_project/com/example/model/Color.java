package com.example.model;

public enum Color {
    RED,
    GREEN,
    BLUE;

    private int brightness;

    Color() {
        this.brightness = 100;
    }

    public int getBrightness() {
        return brightness;
    }
}
