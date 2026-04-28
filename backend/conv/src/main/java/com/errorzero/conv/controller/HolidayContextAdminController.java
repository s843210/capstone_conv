package com.errorzero.conv.controller;

import com.errorzero.conv.config.WeatherProperties;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.dto.HolidayContextBackfillResponseDto;
import com.errorzero.conv.dto.HolidayContextJobResponseDto;
import com.errorzero.conv.service.holiday.HolidayContextService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/admin/context/holiday")
@RequiredArgsConstructor
@Validated
@Tag(name = "Holiday Context Admin API", description = "daily_context 공휴일 값 자동 업서트 API")
public class HolidayContextAdminController {

    private final HolidayContextService holidayContextService;
    private final WeatherProperties weatherProperties;

    @Operation(summary = "단건 공휴일 업서트", description = "targetDate 기준으로 is_holiday를 계산해 daily_context에 upsert합니다.")
    @PostMapping
    public ResponseEntity<HolidayContextJobResponseDto> upsertHoliday(
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate targetDate
    ) {
        String runId = UUID.randomUUID().toString();
        LocalDate effectiveTargetDate = targetDate != null
                ? targetDate
                : LocalDate.now(ZoneId.of(weatherProperties.getScheduleZone())).plusDays(1);

        DailyContext saved = holidayContextService.upsertHoliday(effectiveTargetDate);
        return ResponseEntity.ok(HolidayContextJobResponseDto.builder()
                .runId(runId)
                .status("SUCCESS")
                .targetDate(saved.getTargetDate())
                .isHoliday(saved.getIsHoliday())
                .updatedAt(saved.getUpdatedAt())
                .message("daily_context is_holiday 업서트 완료")
                .build());
    }

    @Operation(summary = "공휴일 기간 백필", description = "from~to 기간에 대해 is_holiday 값을 계산해 daily_context에 upsert합니다.")
    @PostMapping("/backfill")
    public ResponseEntity<HolidayContextBackfillResponseDto> backfillHoliday(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(defaultValue = "365") @Max(value = 3660, message = "maxDays는 3660 이하여야 합니다") int maxDays
    ) {
        if (from.isAfter(to)) {
            throw new IllegalArgumentException("from 날짜는 to 날짜보다 늦을 수 없습니다.");
        }

        long totalDays = from.datesUntil(to.plusDays(1)).count();
        if (totalDays > maxDays) {
            throw new IllegalArgumentException("요청 기간이 너무 깁니다. maxDays를 늘리거나 기간을 줄여주세요.");
        }

        String runId = UUID.randomUUID().toString();
        int successCount = 0;
        int failureCount = 0;
        List<String> errors = new ArrayList<>();

        LocalDate cursor = from;
        while (!cursor.isAfter(to)) {
            try {
                holidayContextService.upsertHoliday(cursor);
                successCount++;
            } catch (Exception ex) {
                failureCount++;
                if (errors.size() < 20) {
                    errors.add(cursor + " => " + ex.getMessage());
                }
            }
            cursor = cursor.plusDays(1);
        }

        String status = failureCount == 0 ? "SUCCESS" : (successCount == 0 ? "FAILED" : "PARTIAL_SUCCESS");

        return ResponseEntity.ok(HolidayContextBackfillResponseDto.builder()
                .runId(runId)
                .status(status)
                .from(from)
                .to(to)
                .successCount(successCount)
                .failureCount(failureCount)
                .errors(errors)
                .build());
    }
}
