package com.edpio.api;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.License;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class EdpIoApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(EdpIoApiApplication.class, args);
    }

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("EDP-IO REST API")
                        .version("1.0.0")
                        .description("Enterprise Data Platform with Intelligent Observability - REST API")
                        .contact(new Contact()
                                .name("Data Engineering Team")
                                .url("https://github.com/Cap-alfaMike/EDP-IO"))
                        .license(new License()
                                .name("MIT")
                                .url("https://opensource.org/licenses/MIT")));
    }
}
