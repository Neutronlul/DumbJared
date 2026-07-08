import pytest
from model_bakery import baker

from api.models import Member


@pytest.mark.django_db
class TestMemberQuerySet:
    class TestWithAttendanceCount:
        def test_member_with_no_attendances_has_zero_count(self) -> None:
            member = baker.make(Member)

            result = Member.objects.with_attendance_count().get(pk=member.pk)

            assert result.attendance_count == 0

    class TestWithAverageScore:
        def test_member_with_no_scores_has_none_average(self) -> None:
            member = baker.make(Member)

            result = Member.objects.with_average_score().get(pk=member.pk)

            assert result.average_score is None
