package com.errorzero.conv.dto;

import com.errorzero.conv.domain.AuthProvider;
import com.errorzero.conv.domain.UserRole;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class AuthUserResponseDto {

    private Long id;
    private String loginId;
    private String email;
    private String name;
    private UserRole role;
    private AuthProvider provider;
}
