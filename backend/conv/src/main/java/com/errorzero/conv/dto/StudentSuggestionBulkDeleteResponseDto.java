package com.errorzero.conv.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class StudentSuggestionBulkDeleteResponseDto {
    private int removedCount;
    private int failedCount;
}
