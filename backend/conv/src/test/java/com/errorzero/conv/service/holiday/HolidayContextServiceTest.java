package com.errorzero.conv.service.holiday;

import com.errorzero.conv.config.HolidayProperties;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.repository.DailyContextRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class HolidayContextServiceTest {

    @Mock
    private DailyContextRepository dailyContextRepository;

    @Mock
    private HolidayApiClient holidayApiClient;

    private HolidayProperties holidayProperties;

    private HolidayContextService holidayContextService;

    @BeforeEach
    void setUp() {
        holidayProperties = new HolidayProperties();
        holidayProperties.setEnabled(true);
        holidayProperties.setIncludeWeekend(true);
        holidayProperties.setApiEnabled(true);

        holidayContextService = new HolidayContextService(dailyContextRepository, holidayApiClient, holidayProperties);
    }

    @Test
    void saturday_isHolidayEvenIfApiFalse() {
        LocalDate saturday = LocalDate.of(2026, 5, 2);

        short result = holidayContextService.resolveHolidayFlag(saturday);

        assertThat(result).isEqualTo((short) 1);
    }

    @Test
    void weekday_usesApiHolidayValue() {
        LocalDate weekday = LocalDate.of(2026, 5, 4);
        when(holidayApiClient.isPublicHoliday(weekday)).thenReturn(true);

        short result = holidayContextService.resolveHolidayFlag(weekday);

        assertThat(result).isEqualTo((short) 1);
    }

    @Test
    void upsertHoliday_createsRowWhenMissing() {
        LocalDate date = LocalDate.of(2026, 5, 5);
        when(dailyContextRepository.findById(date)).thenReturn(Optional.empty());
        when(holidayApiClient.isPublicHoliday(date)).thenReturn(true);
        when(dailyContextRepository.save(any(DailyContext.class))).thenAnswer(invocation -> invocation.getArgument(0));

        DailyContext saved = holidayContextService.upsertHoliday(date);

        assertThat(saved.getTargetDate()).isEqualTo(date);
        assertThat(saved.getIsHoliday()).isEqualTo((short) 1);
        assertThat(saved.getAcademicEvent()).isEqualTo(0);
        assertThat(saved.getBuildingHeadcount()).isEqualTo(0);
    }

    @Test
    void upsertHoliday_keepsExistingNonHolidayColumns() {
        LocalDate date = LocalDate.of(2026, 5, 6);
        DailyContext existing = DailyContext.createDefault(date);
        existing.setAcademicEvent(2);
        existing.setBuildingHeadcount(777);
        existing.setAvgTempC(19.0);

        when(dailyContextRepository.findById(date)).thenReturn(Optional.of(existing));
        when(holidayApiClient.isPublicHoliday(date)).thenReturn(false);
        when(dailyContextRepository.save(any(DailyContext.class))).thenAnswer(invocation -> invocation.getArgument(0));

        DailyContext saved = holidayContextService.upsertHoliday(date);

        assertThat(saved.getIsHoliday()).isEqualTo((short) 0);
        assertThat(saved.getAcademicEvent()).isEqualTo(2);
        assertThat(saved.getBuildingHeadcount()).isEqualTo(777);
        assertThat(saved.getAvgTempC()).isEqualTo(19.0);
    }
}
