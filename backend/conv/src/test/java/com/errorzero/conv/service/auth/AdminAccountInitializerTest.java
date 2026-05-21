package com.errorzero.conv.service.auth;

import com.errorzero.conv.config.AdminAccountProperties;
import com.errorzero.conv.domain.AppUser;
import com.errorzero.conv.domain.AuthProvider;
import com.errorzero.conv.domain.UserRole;
import com.errorzero.conv.repository.AppUserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AdminAccountInitializerTest {

    @Mock
    private AppUserRepository appUserRepository;

    private AdminAccountProperties properties;
    private PasswordEncoder passwordEncoder;
    private AdminAccountInitializer initializer;

    @BeforeEach
    void setUp() {
        properties = new AdminAccountProperties();
        properties.setLoginId("admin");
        properties.setPassword("admin1234");
        properties.setName("관리자");
        properties.setEmail("admin@campus-store.local");
        passwordEncoder = new BCryptPasswordEncoder();
        initializer = new AdminAccountInitializer(properties, appUserRepository, passwordEncoder);
    }

    @Test
    void run_withoutExistingAdmin_createsAdminUser() {
        when(appUserRepository.findByLoginId("admin")).thenReturn(Optional.empty());

        initializer.run(null);

        ArgumentCaptor<AppUser> captor = ArgumentCaptor.forClass(AppUser.class);
        verify(appUserRepository).save(captor.capture());

        AppUser saved = captor.getValue();
        assertThat(saved.getLoginId()).isEqualTo("admin");
        assertThat(saved.getEmail()).isEqualTo("admin@campus-store.local");
        assertThat(saved.getProvider()).isEqualTo(AuthProvider.LOCAL);
        assertThat(saved.getRole()).isEqualTo(UserRole.ADMIN);
        assertThat(saved.getPasswordHash()).isNotEqualTo("admin1234");
        assertThat(passwordEncoder.matches("admin1234", saved.getPasswordHash())).isTrue();
    }

    @Test
    void run_withExistingAdmin_doesNotCreateAgain() {
        when(appUserRepository.findByLoginId("admin")).thenReturn(Optional.of(AppUser.builder().loginId("admin").build()));

        initializer.run(null);

        verify(appUserRepository, never()).save(any(AppUser.class));
    }
}
