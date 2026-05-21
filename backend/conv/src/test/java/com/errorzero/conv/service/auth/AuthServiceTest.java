package com.errorzero.conv.service.auth;

import com.errorzero.conv.domain.AppUser;
import com.errorzero.conv.domain.AuthProvider;
import com.errorzero.conv.domain.UserRole;
import com.errorzero.conv.dto.AdminLoginRequestDto;
import com.errorzero.conv.dto.AuthResponseDto;
import com.errorzero.conv.dto.GoogleLoginRequestDto;
import com.errorzero.conv.dto.StudentDevLoginRequestDto;
import com.errorzero.conv.repository.AppUserRepository;
import com.errorzero.conv.security.AuthUserPrincipal;
import com.errorzero.conv.security.JwtProperties;
import com.errorzero.conv.security.JwtTokenService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private AppUserRepository appUserRepository;

    @Mock
    private GoogleIdTokenVerifierService googleIdTokenVerifierService;

    private PasswordEncoder passwordEncoder;
    private JwtTokenService jwtTokenService;
    private AuthService authService;

    @BeforeEach
    void setUp() {
        passwordEncoder = new BCryptPasswordEncoder();
        JwtProperties jwtProperties = new JwtProperties();
        jwtProperties.setSecret("test-secret-with-enough-length");
        jwtProperties.setIssuer("test-issuer");
        jwtProperties.setExpirationMinutes(30L);
        jwtTokenService = new JwtTokenService(jwtProperties, new ObjectMapper());
        authService = new AuthService(appUserRepository, passwordEncoder, jwtTokenService, googleIdTokenVerifierService);
    }

    @Test
    void loginAdmin_validCredentials_returnsJwt() {
        AppUser admin = adminUser(passwordEncoder.encode("admin1234"));
        when(appUserRepository.findByLoginId("admin")).thenReturn(Optional.of(admin));

        AuthResponseDto response = authService.loginAdmin(loginRequest("admin", "admin1234"));

        assertThat(response.getTokenType()).isEqualTo("Bearer");
        assertThat(response.getAccessToken()).isNotBlank();
        assertThat(response.getUser().getLoginId()).isEqualTo("admin");
        assertThat(response.getUser().getRole()).isEqualTo(UserRole.ADMIN);
        assertThat(admin.getLastLoginAt()).isNotNull();

        AuthUserPrincipal principal = jwtTokenService.parseToken(response.getAccessToken());
        assertThat(principal.userId()).isEqualTo(1L);
        assertThat(principal.loginId()).isEqualTo("admin");
        assertThat(principal.role()).isEqualTo(UserRole.ADMIN);
        verify(appUserRepository).findByLoginId("admin");
    }

    @Test
    void loginAdmin_wrongPassword_rejectsLogin() {
        AppUser admin = adminUser(passwordEncoder.encode("admin1234"));
        when(appUserRepository.findByLoginId("admin")).thenReturn(Optional.of(admin));

        assertThatThrownBy(() -> authService.loginAdmin(loginRequest("admin", "wrong")))
                .isInstanceOf(BadCredentialsException.class)
                .hasMessageContaining("아이디 또는 비밀번호");
    }

    @Test
    void loginAdmin_nonAdminUser_rejectsLogin() {
        AppUser student = AppUser.builder()
                .id(2L)
                .loginId("student")
                .email("student@example.com")
                .name("student")
                .provider(AuthProvider.GOOGLE)
                .providerUserId("google-sub")
                .role(UserRole.STUDENT)
                .active(true)
                .build();
        when(appUserRepository.findByLoginId("student")).thenReturn(Optional.of(student));

        assertThatThrownBy(() -> authService.loginAdmin(loginRequest("student", "admin1234")))
                .isInstanceOf(BadCredentialsException.class);
    }

    @Test
    void loginStudentDev_newStudent_createsStudentAndReturnsJwt() {
        when(appUserRepository.findByLoginId("20240001")).thenReturn(Optional.empty());
        when(appUserRepository.save(org.mockito.ArgumentMatchers.any(AppUser.class))).thenAnswer(invocation -> {
            AppUser saved = invocation.getArgument(0);
            saved.setId(3L);
            return saved;
        });

        AuthResponseDto response = authService.loginStudentDev(studentLoginRequest("20240001", "홍길동", "student@example.com"));

        assertThat(response.getTokenType()).isEqualTo("Bearer");
        assertThat(response.getUser().getLoginId()).isEqualTo("20240001");
        assertThat(response.getUser().getRole()).isEqualTo(UserRole.STUDENT);
        assertThat(response.getUser().getProvider()).isEqualTo(AuthProvider.DEV);

        AuthUserPrincipal principal = jwtTokenService.parseToken(response.getAccessToken());
        assertThat(principal.userId()).isEqualTo(3L);
        assertThat(principal.role()).isEqualTo(UserRole.STUDENT);
        assertThat(principal.provider()).isEqualTo(AuthProvider.DEV);
    }

    @Test
    void loginStudentDev_existingStudent_updatesProfileAndReturnsJwt() {
        AppUser student = AppUser.builder()
                .id(4L)
                .loginId("20240002")
                .email("old@example.com")
                .name("이전이름")
                .provider(AuthProvider.DEV)
                .providerUserId("dev:20240002")
                .role(UserRole.STUDENT)
                .active(true)
                .build();
        when(appUserRepository.findByLoginId("20240002")).thenReturn(Optional.of(student));

        AuthResponseDto response = authService.loginStudentDev(studentLoginRequest("20240002", "김학생", "new@example.com"));

        assertThat(response.getUser().getName()).isEqualTo("김학생");
        assertThat(response.getUser().getEmail()).isEqualTo("new@example.com");
        assertThat(student.getLastLoginAt()).isNotNull();
    }

    @Test
    void loginGoogle_newStudent_createsGoogleStudentAndReturnsJwt() {
        GoogleUserInfo googleUser = new GoogleUserInfo(
                "google-sub-1",
                "student@example.com",
                "구글학생",
                null
        );
        when(googleIdTokenVerifierService.verify("google-id-token")).thenReturn(googleUser);
        when(appUserRepository.findByProviderAndProviderUserId(AuthProvider.GOOGLE, "google-sub-1"))
                .thenReturn(Optional.empty());
        when(appUserRepository.findByEmail("student@example.com")).thenReturn(Optional.empty());
        when(appUserRepository.findByLoginId("student@example.com")).thenReturn(Optional.empty());
        when(appUserRepository.save(any(AppUser.class))).thenAnswer(invocation -> {
            AppUser saved = invocation.getArgument(0);
            saved.setId(5L);
            return saved;
        });

        AuthResponseDto response = authService.loginGoogle(googleLoginRequest("google-id-token"));

        assertThat(response.getTokenType()).isEqualTo("Bearer");
        assertThat(response.getUser().getLoginId()).isEqualTo("student@example.com");
        assertThat(response.getUser().getRole()).isEqualTo(UserRole.STUDENT);
        assertThat(response.getUser().getProvider()).isEqualTo(AuthProvider.GOOGLE);

        AuthUserPrincipal principal = jwtTokenService.parseToken(response.getAccessToken());
        assertThat(principal.userId()).isEqualTo(5L);
        assertThat(principal.provider()).isEqualTo(AuthProvider.GOOGLE);
    }

    @Test
    void loginGoogle_existingStudent_updatesProfileAndReturnsJwt() {
        GoogleUserInfo googleUser = new GoogleUserInfo(
                "google-sub-2",
                "new@example.com",
                "새이름",
                null
        );
        AppUser student = AppUser.builder()
                .id(6L)
                .loginId("old@example.com")
                .email("old@example.com")
                .name("이전이름")
                .provider(AuthProvider.GOOGLE)
                .providerUserId("google-sub-2")
                .role(UserRole.STUDENT)
                .active(true)
                .build();
        when(googleIdTokenVerifierService.verify("google-id-token")).thenReturn(googleUser);
        when(appUserRepository.findByProviderAndProviderUserId(AuthProvider.GOOGLE, "google-sub-2"))
                .thenReturn(Optional.of(student));
        when(appUserRepository.findByEmail("new@example.com")).thenReturn(Optional.empty());

        AuthResponseDto response = authService.loginGoogle(googleLoginRequest("google-id-token"));

        assertThat(response.getUser().getLoginId()).isEqualTo("old@example.com");
        assertThat(response.getUser().getEmail()).isEqualTo("new@example.com");
        assertThat(response.getUser().getName()).isEqualTo("새이름");
        assertThat(student.getLastLoginAt()).isNotNull();
    }

    private AppUser adminUser(String passwordHash) {
        return AppUser.builder()
                .id(1L)
                .loginId("admin")
                .email("admin@campus-store.local")
                .name("관리자")
                .provider(AuthProvider.LOCAL)
                .role(UserRole.ADMIN)
                .passwordHash(passwordHash)
                .active(true)
                .build();
    }

    private AdminLoginRequestDto loginRequest(String loginId, String password) {
        AdminLoginRequestDto request = new AdminLoginRequestDto();
        request.setLoginId(loginId);
        request.setPassword(password);
        return request;
    }

    private StudentDevLoginRequestDto studentLoginRequest(String loginId, String name, String email) {
        StudentDevLoginRequestDto request = new StudentDevLoginRequestDto();
        request.setLoginId(loginId);
        request.setName(name);
        request.setEmail(email);
        return request;
    }

    private GoogleLoginRequestDto googleLoginRequest(String idToken) {
        GoogleLoginRequestDto request = new GoogleLoginRequestDto();
        request.setIdToken(idToken);
        return request;
    }
}
