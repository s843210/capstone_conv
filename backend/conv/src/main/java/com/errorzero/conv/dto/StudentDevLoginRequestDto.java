package com.errorzero.conv.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class StudentDevLoginRequestDto {

    @NotBlank(message = "loginId는 필수입니다")
    @Size(max = 100, message = "loginId는 100자 이하로 입력해 주세요")
    private String loginId;

    @NotBlank(message = "name은 필수입니다")
    @Size(max = 100, message = "name은 100자 이하로 입력해 주세요")
    private String name;

    @Email(message = "email 형식이 올바르지 않습니다")
    @Size(max = 255, message = "email은 255자 이하로 입력해 주세요")
    private String email;
}
