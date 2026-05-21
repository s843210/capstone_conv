package com.errorzero.conv.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class AdminLoginRequestDto {

    @NotBlank(message = "loginId는 필수입니다")
    private String loginId;

    @NotBlank(message = "password는 필수입니다")
    private String password;
}
