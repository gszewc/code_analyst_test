package com.example.service;

import java.util.ArrayList;
import java.util.List;

import com.example.model.Animal;
import com.example.model.Dog;
import com.example.model.Color;

@Service
@Transactional
public class AnimalService {
    private final List<Animal> animals;

    public AnimalService() {
        this.animals = new ArrayList<>();
    }

    public void register(Animal animal) {
        animals.add(animal);
    }

    public Dog createDog(String name, int age) {
        Dog dog = new Dog(name, age, Color.RED);
        register(dog);
        return dog;
    }

    public List<Animal> listAll() {
        return animals;
    }
}
