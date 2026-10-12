package com.example.model;

import com.example.service.Walker;

public class Dog extends Animal implements Walker {
    private Color color;

    public Dog(String name, int age, Color color) {
        super(name, age);
        this.color = color;
    }

    @Override
    public String speak() {
        return "Woof";
    }

    @Override
    public void walk(int steps) {
        // walk implementation
    }

    public Color getColor() {
        return color;
    }
}
