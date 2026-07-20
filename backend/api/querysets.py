from django.db.models import Avg, Count, QuerySet


class MemberQuerySet(QuerySet):
    def with_attendance_count(self) -> MemberQuerySet:
        return self.annotate(attendance_count=Count("event_attendances"))

    def with_average_score(self) -> MemberQuerySet:
        return self.annotate(
            average_score=Avg(
                "event_attendances__team_event_participation__score",
            ),
        )
