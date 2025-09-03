package com.example.myapp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class MyJavaAppApplication {

    public static void main(String[] args) {
        SpringApplication.run(MyJavaAppApplication.class, args);
    }

    @GetMapping("/")
    public String hello() {
        return "Hello from My Java App!";
    }

    @GetMapping("/health")
    public String health() {
        return "UP";
    }

    @GetMapping("/api/status")
    public String status() {
        return "Application is running successfully";
    }

    @GetMapping("/api/info")
    public String info() {
        return "My Java App - Version 1.0.0";
    }
}