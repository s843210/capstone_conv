package com.errorzero.conv.service.auth;

import com.errorzero.conv.config.AdminAccountProperties;
import com.errorzero.conv.domain.AppUser;
import com.errorzero.conv.domain.AuthProvider;
import com.errorzero.conv.domain.UserRole;
import com.errorzero.conv.repository.AppUserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Component
@RequiredArgsConstructor
public class AdminAccountInitializer implements ApplicationRunner {

    private final AdminAccountProperties adminAccountProperties;
    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        String loginId = normalize(adminAccountProperties.getLoginId());
        String password = normalize(adminAccountProperties.getPassword());

        if (loginId == null || password == null) {
            log.info("관리자 초기 계정 설정이 없어 자동 생성을 건너뜁니다.");
            return;
        }

        appUserRepository.findByLoginId(loginId).ifPresentOrElse(
                user -> log.info("관리자 계정이 이미 존재합니다: {}", loginId),
                () -> createAdmin(loginId, password)
        );
    }

    private void createAdmin(String loginId, String password) {
        String name = normalize(adminAccountProperties.getName());
        String email = normalize(adminAccountProperties.getEmail());

        AppUser admin = AppUser.builder()
                .loginId(loginId)
                .email(email)
                .name(name == null ? loginId : name)
                .provider(AuthProvider.LOCAL)
                .role(UserRole.ADMIN)
                .passwordHash(passwordEncoder.encode(password))
                .active(true)
                .build();

        appUserRepository.save(admin);
        log.info("관리자 계정을 생성했습니다: {}", loginId);
    }

    private String normalize(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
