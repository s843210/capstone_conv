package com.errorzero.conv;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class ConvApplication {

	public static void main(String[] args) {
		SpringApplication.run(ConvApplication.class, args);
	}

}
