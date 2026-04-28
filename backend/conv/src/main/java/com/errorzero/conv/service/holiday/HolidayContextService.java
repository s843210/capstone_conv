package com.errorzero.conv.service.holiday;

import com.errorzero.conv.config.HolidayProperties;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.repository.DailyContextRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.DayOfWeek;
import java.time.LocalDate;

@Slf4j
@Service
@RequiredArgsConstructor
public class HolidayContextService {

    private final DailyContextRepository dailyContextRepository;
    private final HolidayApiClient holidayApiClient;
    private final HolidayProperties holidayProperties;

    @Transactional
    public DailyContext upsertHoliday(LocalDate targetDate) {
        DailyContext context = dailyContextRepository.findById(targetDate)
                .orElseGet(() -> DailyContext.createDefault(targetDate));

        short holidayFlag = resolveHolidayFlag(targetDate);
        context.setIsHoliday(holidayFlag);

        if (context.getAcademicEvent() == null) {
            context.setAcademicEvent(0);
        }
        if (context.getBuildingHeadcount() == null) {
            context.setBuildingHeadcount(0);
        }
        if (context.getPrecipitationMm() == null) {
            context.setPrecipitationMm(0.0);
        }
        if (context.getIsRain() == null) {
            context.setIsRain((short) 0);
        }

        DailyContext saved = dailyContextRepository.save(context);
        log.info("공휴일 업서트 완료: targetDate={}, isHoliday={}", saved.getTargetDate(), saved.getIsHoliday());
        return saved;
    }

    @Transactional(readOnly = true)
    public short resolveHolidayFlag(LocalDate targetDate) {
        if (!holidayProperties.isEnabled()) {
            return 0;
        }

        if (holidayProperties.isIncludeWeekend() && isWeekend(targetDate)) {
            return 1;
        }

        try {
            boolean apiHoliday = holidayApiClient.isPublicHoliday(targetDate);
            return apiHoliday ? (short) 1 : (short) 0;
        } catch (RuntimeException ex) {
            if (holidayProperties.isIncludeWeekend()) {
                // 주말 여부는 이미 위에서 처리했으므로 여기 도달 시 평일 fallback
                log.warn("공휴일 API 실패 fallback 적용: targetDate={}, fallback=0, reason={}", targetDate, ex.getMessage());
                return 0;
            }
            throw ex;
        }
    }

    private boolean isWeekend(LocalDate date) {
        DayOfWeek day = date.getDayOfWeek();
        return day == DayOfWeek.SATURDAY || day == DayOfWeek.SUNDAY;
    }
}
