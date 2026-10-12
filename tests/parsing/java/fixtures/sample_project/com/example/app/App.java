package com.example.app;

import com.example.service.AnimalService;
import com.example.model.Dog;

@SpringBootApplication
public class App {
    private final AnimalService service;

    public App() {
        this.service = new AnimalService();
    }

    public static void main(String[] args) {
        App app = new App();
        app.run();
    }

    public void run() {
        Dog rex = service.createDog("Rex", 3);
    }
}
