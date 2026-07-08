from django.db import models


class MemberQuerySet(models.QuerySet):
    def with_attendance_count(self) -> MemberQuerySet:
        return self.annotate(attendance_count=models.Count("event_attendances"))

    def with_average_score(self) -> MemberQuerySet:
        return self.annotate(
            average_score=models.Avg(
                "event_attendances__team_event_participation__score",
            ),
        )
