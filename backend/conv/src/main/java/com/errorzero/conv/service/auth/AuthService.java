package com.errorzero.conv.service.auth;

import com.errorzero.conv.domain.AppUser;
import com.errorzero.conv.domain.AuthProvider;
import com.errorzero.conv.domain.UserRole;
import com.errorzero.conv.dto.AdminLoginRequestDto;
import com.errorzero.conv.dto.AuthResponseDto;
import com.errorzero.conv.dto.AuthUserResponseDto;
import com.errorzero.conv.dto.GoogleLoginRequestDto;
import com.errorzero.conv.dto.StudentDevLoginRequestDto;
import com.errorzero.conv.repository.AppUserRepository;
import com.errorzero.conv.security.AuthUserPrincipal;
import com.errorzero.conv.security.JwtTokenService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.DisabledException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Objects;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenService jwtTokenService;
    private final GoogleIdTokenVerifierService googleIdTokenVerifierService;

    @Transactional
    public AuthResponseDto loginAdmin(AdminLoginRequestDto request) {
        String loginId = required(request.getLoginId());
        String password = required(request.getPassword());

        AppUser user = appUserRepository.findByLoginId(loginId)
                .orElseThrow(() -> new BadCredentialsException("아이디 또는 비밀번호가 올바르지 않습니다."));

        if (!Boolean.TRUE.equals(user.getActive())) {
            throw new DisabledException("비활성화된 계정입니다.");
        }

        if (user.getProvider() != AuthProvider.LOCAL || user.getRole() != UserRole.ADMIN) {
            throw new BadCredentialsException("아이디 또는 비밀번호가 올바르지 않습니다.");
        }

        if (!passwordEncoder.matches(password, user.getPasswordHash())) {
            throw new BadCredentialsException("아이디 또는 비밀번호가 올바르지 않습니다.");
        }

        user.setLastLoginAt(LocalDateTime.now());
        String accessToken = jwtTokenService.createToken(user);

        return new AuthResponseDto(accessToken, "Bearer", toUserResponse(user));
    }

    @Transactional
    public AuthResponseDto loginStudentDev(StudentDevLoginRequestDto request) {
        String loginId = requiredStudentField(request.getLoginId(), "loginId");
        String name = requiredStudentField(request.getName(), "name");
        String email = normalize(request.getEmail());

        AppUser user = appUserRepository.findByLoginId(loginId)
                .map(existingUser -> updateDevStudent(existingUser, name, email))
                .orElseGet(() -> createDevStudent(loginId, name, email));

        user.setLastLoginAt(LocalDateTime.now());
        String accessToken = jwtTokenService.createToken(user);

        return new AuthResponseDto(accessToken, "Bearer", toUserResponse(user));
    }

    @Transactional
    public AuthResponseDto loginGoogle(GoogleLoginRequestDto request) {
        String idToken = requiredStudentField(request.getIdToken(), "idToken");
        GoogleUserInfo googleUser = googleIdTokenVerifierService.verify(idToken);

        AppUser user = appUserRepository.findByProviderAndProviderUserId(AuthProvider.GOOGLE, googleUser.subject())
                .map(existingUser -> updateGoogleStudent(existingUser, googleUser))
                .orElseGet(() -> createGoogleStudent(googleUser));

        user.setLastLoginAt(LocalDateTime.now());
        String accessToken = jwtTokenService.createToken(user);

        return new AuthResponseDto(accessToken, "Bearer", toUserResponse(user));
    }

    public AuthUserResponseDto toUserResponse(AuthUserPrincipal principal) {
        return new AuthUserResponseDto(
                principal.userId(),
                principal.loginId(),
                principal.email(),
                principal.name(),
                principal.role(),
                principal.provider()
        );
    }

    private AuthUserResponseDto toUserResponse(AppUser user) {
        return new AuthUserResponseDto(
                user.getId(),
                user.getLoginId(),
                user.getEmail(),
                user.getName(),
                user.getRole(),
                user.getProvider()
        );
    }

    private AppUser createDevStudent(String loginId, String name, String email) {
        AppUser user = AppUser.builder()
                .loginId(loginId)
                .email(email)
                .name(name)
                .provider(AuthProvider.DEV)
                .providerUserId("dev:" + loginId)
                .role(UserRole.STUDENT)
                .active(true)
                .build();

        return appUserRepository.save(user);
    }

    private AppUser updateDevStudent(AppUser user, String name, String email) {
        if (user.getRole() != UserRole.STUDENT || user.getProvider() != AuthProvider.DEV) {
            throw new BadCredentialsException("학생 임시 로그인 계정이 아닙니다.");
        }

        if (!Boolean.TRUE.equals(user.getActive())) {
            throw new DisabledException("비활성화된 계정입니다.");
        }

        user.setName(name);
        user.setEmail(email);
        return user;
    }

    private AppUser createGoogleStudent(GoogleUserInfo googleUser) {
        appUserRepository.findByEmail(googleUser.email()).ifPresent(existingUser -> {
            throw new BadCredentialsException("이미 다른 로그인 방식으로 가입된 이메일입니다.");
        });

        String loginId = resolveGoogleLoginId(googleUser);
        appUserRepository.findByLoginId(loginId).ifPresent(existingUser -> {
            throw new BadCredentialsException("이미 사용 중인 로그인 ID입니다.");
        });

        AppUser user = AppUser.builder()
                .loginId(loginId)
                .email(googleUser.email())
                .name(googleUser.name())
                .provider(AuthProvider.GOOGLE)
                .providerUserId(googleUser.subject())
                .role(UserRole.STUDENT)
                .active(true)
                .build();

        return appUserRepository.save(user);
    }

    private AppUser updateGoogleStudent(AppUser user, GoogleUserInfo googleUser) {
        if (user.getRole() != UserRole.STUDENT || user.getProvider() != AuthProvider.GOOGLE) {
            throw new BadCredentialsException("학생 Google 로그인 계정이 아닙니다.");
        }

        if (!Boolean.TRUE.equals(user.getActive())) {
            throw new DisabledException("비활성화된 계정입니다.");
        }

        appUserRepository.findByEmail(googleUser.email())
                .filter(existingUser -> !Objects.equals(existingUser.getId(), user.getId()))
                .ifPresent(existingUser -> {
                    throw new BadCredentialsException("이미 다른 계정에서 사용 중인 이메일입니다.");
                });

        user.setEmail(googleUser.email());
        user.setName(googleUser.name());
        return user;
    }

    private String resolveGoogleLoginId(GoogleUserInfo googleUser) {
        return requiredStudentField(googleUser.email(), "email");
    }

    private String required(String value) {
        if (value == null || value.isBlank()) {
            throw new BadCredentialsException("아이디 또는 비밀번호가 올바르지 않습니다.");
        }
        return value.trim();
    }

    private String requiredStudentField(String value, String fieldName) {
        String normalized = normalize(value);
        if (normalized == null) {
            throw new IllegalArgumentException(fieldName + "는 필수입니다");
        }
        return normalized;
    }

    private String normalize(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
