package com.errorzero.conv.service.academic;

import com.errorzero.conv.domain.AcademicEventRule;
import com.errorzero.conv.domain.BuildingHeadcountProfile;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.repository.AcademicEventRuleRepository;
import com.errorzero.conv.repository.BuildingHeadcountProfileRepository;
import com.errorzero.conv.repository.DailyContextRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AcademicContextServiceTest {

    @Mock
    private DailyContextRepository dailyContextRepository;

    @Mock
    private AcademicEventRuleRepository academicEventRuleRepository;

    @Mock
    private BuildingHeadcountProfileRepository buildingHeadcountProfileRepository;

    private AcademicContextService academicContextService;

    @BeforeEach
    void setUp() {
        academicContextService = new AcademicContextService(
                dailyContextRepository,
                academicEventRuleRepository,
                buildingHeadcountProfileRepository
        );
    }

    @Test
    void resolveAcademicEvent_prefersHigherPriorityEvent() {
        LocalDate date = LocalDate.of(2026, 5, 6);

        AcademicEventRule semester = AcademicEventRule.builder()
                .eventCode(1)
                .startDate(LocalDate.of(2026, 3, 2))
                .endDate(LocalDate.of(2026, 6, 20))
                .build();
        AcademicEventRule exam = AcademicEventRule.builder()
                .eventCode(2)
                .startDate(LocalDate.of(2026, 5, 1))
                .endDate(LocalDate.of(2026, 5, 7))
                .build();

        when(academicEventRuleRepository.findAllByStartDateLessThanEqualAndEndDateGreaterThanEqual(date, date))
                .thenReturn(List.of(semester, exam));

        int code = academicContextService.resolveAcademicEvent(date);

        assertThat(code).isEqualTo(2);
    }

    @Test
    void resolveBuildingHeadcount_eventNotSemester_returnsDefault20() {
        LocalDate date = LocalDate.of(2026, 5, 6);
        BuildingHeadcountProfile profile = BuildingHeadcountProfile.defaultProfile();
        profile.setDefaultCount(20);
        profile.setMonday(111);

        when(buildingHeadcountProfileRepository.findById((short) 1)).thenReturn(Optional.of(profile));

        int count = academicContextService.resolveBuildingHeadcount(date, 2);

        assertThat(count).isEqualTo(20);
    }

    @Test
    void resolveBuildingHeadcount_semesterWeekday_usesWeekdayValue() {
        LocalDate monday = LocalDate.of(2026, 5, 4);
        BuildingHeadcountProfile profile = BuildingHeadcountProfile.defaultProfile();
        profile.setMonday(123);

        when(buildingHeadcountProfileRepository.findById((short) 1)).thenReturn(Optional.of(profile));

        int count = academicContextService.resolveBuildingHeadcount(monday, 1);

        assertThat(count).isEqualTo(123);
    }

    @Test
    void upsertAcademicContext_createsAndSetsEventAndHeadcount() {
        LocalDate date = LocalDate.of(2026, 5, 6);
        AcademicEventRule rule = AcademicEventRule.builder()
                .eventCode(1)
                .startDate(LocalDate.of(2026, 3, 1))
                .endDate(LocalDate.of(2026, 6, 30))
                .build();
        BuildingHeadcountProfile profile = BuildingHeadcountProfile.defaultProfile();
        profile.setWednesday(135);

        when(dailyContextRepository.findById(date)).thenReturn(Optional.empty());
        when(academicEventRuleRepository.findAllByStartDateLessThanEqualAndEndDateGreaterThanEqual(date, date))
                .thenReturn(List.of(rule));
        when(buildingHeadcountProfileRepository.findById((short) 1)).thenReturn(Optional.of(profile));
        when(dailyContextRepository.save(any(DailyContext.class))).thenAnswer(invocation -> invocation.getArgument(0));

        DailyContext saved = academicContextService.upsertAcademicContext(date);

        assertThat(saved.getTargetDate()).isEqualTo(date);
        assertThat(saved.getAcademicEvent()).isEqualTo(1);
        assertThat(saved.getBuildingHeadcount()).isEqualTo(135);
    }
}
