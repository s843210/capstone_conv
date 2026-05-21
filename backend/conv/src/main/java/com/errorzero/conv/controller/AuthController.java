package com.errorzero.conv.controller;

import com.errorzero.conv.dto.AdminLoginRequestDto;
import com.errorzero.conv.dto.AuthResponseDto;
import com.errorzero.conv.dto.AuthUserResponseDto;
import com.errorzero.conv.dto.GoogleLoginRequestDto;
import com.errorzero.conv.dto.StudentDevLoginRequestDto;
import com.errorzero.conv.security.AuthUserPrincipal;
import com.errorzero.conv.service.auth.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/admin/login")
    public ResponseEntity<AuthResponseDto> loginAdmin(
            @Valid @RequestBody AdminLoginRequestDto request
    ) {
        return ResponseEntity.ok(authService.loginAdmin(request));
    }

    @PostMapping("/student/dev-login")
    public ResponseEntity<AuthResponseDto> loginStudentDev(
            @Valid @RequestBody StudentDevLoginRequestDto request
    ) {
        return ResponseEntity.ok(authService.loginStudentDev(request));
    }

    @PostMapping("/google")
    public ResponseEntity<AuthResponseDto> loginGoogle(
            @Valid @RequestBody GoogleLoginRequestDto request
    ) {
        return ResponseEntity.ok(authService.loginGoogle(request));
    }

    @GetMapping("/me")
    public ResponseEntity<AuthUserResponseDto> getMe(
            @AuthenticationPrincipal AuthUserPrincipal principal
    ) {
        if (principal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        return ResponseEntity.ok(authService.toUserResponse(principal));
    }
}
