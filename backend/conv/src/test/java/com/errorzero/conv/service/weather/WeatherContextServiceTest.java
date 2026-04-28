package com.errorzero.conv.service.weather;

import com.errorzero.conv.config.WeatherProperties;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.repository.DailyContextRepository;
import com.errorzero.conv.service.academic.AcademicContextService;
import com.errorzero.conv.service.holiday.HolidayContextService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class WeatherContextServiceTest {

    @Mock
    private DailyContextRepository dailyContextRepository;

    @Mock
    private WeatherApiClient weatherApiClient;

    @Mock
    private HolidayContextService holidayContextService;

    @Mock
    private AcademicContextService academicContextService;

    private WeatherProperties weatherProperties;

    private WeatherContextService weatherContextService;

    @BeforeEach
    void setUp() {
        weatherProperties = new WeatherProperties();
        weatherProperties.setEnabled(true);
        weatherProperties.setRetryCount(3);
        weatherProperties.setRetryBackoffMillis(1L);

        weatherContextService = new WeatherContextService(
                dailyContextRepository,
                weatherApiClient,
                weatherProperties,
                holidayContextService,
                academicContextService
        );
    }

    @Test
    void upsertWeatherContext_updatesOnlyWeatherFields() {
        LocalDate targetDate = LocalDate.of(2026, 4, 24);

        DailyContext existing = DailyContext.createDefault(targetDate);
        existing.setIsHoliday((short) 1);
        existing.setAcademicEvent(2);
        existing.setBuildingHeadcount(1234);

        when(weatherApiClient.fetchDailyWeather(targetDate))
                .thenReturn(new WeatherSnapshot(17.5, 2.4, (short) 1));
        when(holidayContextService.resolveHolidayFlag(targetDate)).thenReturn((short) 1);
        when(academicContextService.resolveAcademicEvent(targetDate)).thenReturn(2);
        when(academicContextService.resolveBuildingHeadcount(targetDate, 2)).thenReturn(20);
        when(dailyContextRepository.findById(targetDate)).thenReturn(Optional.of(existing));
        when(dailyContextRepository.save(any(DailyContext.class))).thenAnswer(invocation -> invocation.getArgument(0));

        DailyContext saved = weatherContextService.upsertWeatherContext(targetDate);

        assertThat(saved.getAvgTempC()).isEqualTo(17.5);
        assertThat(saved.getPrecipitationMm()).isEqualTo(2.4);
        assertThat(saved.getIsRain()).isEqualTo((short) 1);
        assertThat(saved.getIsHoliday()).isEqualTo((short) 1);
        assertThat(saved.getAcademicEvent()).isEqualTo(2);
        assertThat(saved.getBuildingHeadcount()).isEqualTo(20);
    }

    @Test
    void upsertWeatherContext_createsDefaultWhenMissing() {
        LocalDate targetDate = LocalDate.of(2026, 4, 25);

        when(weatherApiClient.fetchDailyWeather(targetDate))
                .thenReturn(new WeatherSnapshot(20.0, 0.0, (short) 0));
        when(holidayContextService.resolveHolidayFlag(targetDate)).thenReturn((short) 0);
        when(academicContextService.resolveAcademicEvent(targetDate)).thenReturn(1);
        when(academicContextService.resolveBuildingHeadcount(targetDate, 1)).thenReturn(111);
        when(dailyContextRepository.findById(targetDate)).thenReturn(Optional.empty());
        when(dailyContextRepository.save(any(DailyContext.class))).thenAnswer(invocation -> invocation.getArgument(0));

        DailyContext saved = weatherContextService.upsertWeatherContext(targetDate);

        assertThat(saved.getTargetDate()).isEqualTo(targetDate);
        assertThat(saved.getIsHoliday()).isEqualTo((short) 0);
        assertThat(saved.getAcademicEvent()).isEqualTo(1);
        assertThat(saved.getBuildingHeadcount()).isEqualTo(111);
    }

    @Test
    void fetchWeatherWithRetry_retriesAndThenSucceeds() {
        LocalDate targetDate = LocalDate.of(2026, 4, 26);

        when(weatherApiClient.fetchDailyWeather(targetDate))
                .thenThrow(new IllegalStateException("timeout"))
                .thenReturn(new WeatherSnapshot(21.0, 1.1, (short) 1));

        WeatherSnapshot snapshot = weatherContextService.fetchWeatherWithRetry(targetDate);

        assertThat(snapshot.avgTempC()).isEqualTo(21.0);
        verify(weatherApiClient, times(2)).fetchDailyWeather(targetDate);
    }

    @Test
    void upsertWeatherContext_throwsWhenDisabled() {
        weatherProperties.setEnabled(false);

        assertThatThrownBy(() -> weatherContextService.upsertWeatherContext(LocalDate.now()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("비활성화");
    }

    @Test
    void upsertWeatherContext_normalizesNegativePrecipitationToZero() {
        LocalDate targetDate = LocalDate.of(2026, 4, 27);

        when(weatherApiClient.fetchDailyWeather(targetDate))
                .thenReturn(new WeatherSnapshot(14.0, -3.2, (short) 1));
        when(holidayContextService.resolveHolidayFlag(targetDate)).thenReturn((short) 0);
        when(academicContextService.resolveAcademicEvent(targetDate)).thenReturn(0);
        when(academicContextService.resolveBuildingHeadcount(targetDate, 0)).thenReturn(20);
        when(dailyContextRepository.findById(targetDate)).thenReturn(Optional.empty());
        when(dailyContextRepository.save(any(DailyContext.class))).thenAnswer(invocation -> invocation.getArgument(0));

        weatherContextService.upsertWeatherContext(targetDate);

        ArgumentCaptor<DailyContext> captor = ArgumentCaptor.forClass(DailyContext.class);
        verify(dailyContextRepository).save(captor.capture());
        assertThat(captor.getValue().getPrecipitationMm()).isEqualTo(0.0);
    }
}
