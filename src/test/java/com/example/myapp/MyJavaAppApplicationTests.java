package com.example.myapp;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@SpringJUnitConfig
class MyJavaAppApplicationTests {

    @Test
    void contextLoads() {
        // Test that Spring context loads successfully
        assertTrue(true);
    }

    @Test
    void testBasicFunctionality() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String result = app.hello();
        assertEquals("Hello from My Java App!", result);
    }

    @Test
    void testHealthEndpoint() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String health = app.health();
        assertEquals("UP", health);
    }

    @Test
    void testStatusEndpoint() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String status = app.status();
        assertEquals("Application is running successfully", status);
    }

    @Test
    void testInfoEndpoint() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String info = app.info();
        assertEquals("My Java App - Version 1.0.0", info);
    }

    @Test
    void testApplicationNotNull() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        assertNotNull(app);
    }
}